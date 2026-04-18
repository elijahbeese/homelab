"""
JARVIS brain server.

One websocket per frontend. Protocol:
  frontend → brain:  {"type":"auth","secret":"..."}
  frontend → brain:  {"type":"audio","wav_b64":"..."}   # user spoke
  frontend → brain:  {"type":"text","text":"..."}        # typed input
  frontend → brain:  {"type":"confirm","approved":true}  # answer to a confirm request

  brain → frontend:  {"type":"status","text":"..."}      # "thinking", "using tool X"
  brain → frontend:  {"type":"speak","wav_b64":"..."}    # audio to play
  brain → frontend:  {"type":"confirm_request","prompt":"...","tool":"...","args":{...}}
  brain → frontend:  {"type":"launch_app","app":"firefox"}   # action for the laptop
"""
from __future__ import annotations
import asyncio
import base64
import json
import os
import sys
from pathlib import Path

import websockets
import yaml
import structlog
from dotenv import load_dotenv

from spend import build_from_config, BudgetExceeded
from llm import ClaudeClient
from voice import STT, TTS
from tools import Toolbox, TOOL_SPECS

load_dotenv()

structlog.configure(processors=[
    structlog.processors.TimeStamper(fmt="iso"),
    structlog.processors.add_log_level,
    structlog.processors.JSONRenderer(),
])
log = structlog.get_logger()


# ── Config load ─────────────────────────────────────────────────────────
CONFIG_PATH = Path(os.environ.get("JARVIS_CONFIG", "/app/config/jarvis.yaml"))
CONFIG = yaml.safe_load(CONFIG_PATH.read_text())


class FrontendBridge:
    """A send-channel back to the connected frontend for things like launch_app."""

    def __init__(self, websocket):
        self.ws = websocket
        self._pending: dict[str, asyncio.Future] = {}

    async def request(self, payload: dict) -> dict:
        """Send a request to the frontend and await its response."""
        import uuid
        req_id = str(uuid.uuid4())
        payload["request_id"] = req_id
        future = asyncio.get_event_loop().create_future()
        self._pending[req_id] = future
        await self.ws.send(json.dumps(payload))
        try:
            return await asyncio.wait_for(future, timeout=15)
        finally:
            self._pending.pop(req_id, None)

    def resolve(self, req_id: str, result: dict) -> None:
        fut = self._pending.get(req_id)
        if fut and not fut.done():
            fut.set_result(result)


class Session:
    """One conversation with one frontend."""

    def __init__(self, websocket, claude: ClaudeClient, stt: STT, tts: TTS,
                 toolbox: Toolbox, config: dict):
        self.ws = websocket
        self.claude = claude
        self.stt = stt
        self.tts = tts
        self.toolbox = toolbox
        self.config = config
        self.history: list = []
        self._confirm_waiter: asyncio.Future | None = None

    async def send(self, payload: dict) -> None:
        await self.ws.send(json.dumps(payload))

    async def status(self, text: str) -> None:
        await self.send({"type": "status", "text": text})

    async def speak(self, text: str) -> None:
        """Synthesize text and stream it to the frontend."""
        if not text.strip():
            return
        await self.send({"type": "status", "text": "speaking"})
        wav = await asyncio.to_thread(self.tts.synthesize, text)
        await self.send({
            "type": "speak",
            "wav_b64": base64.b64encode(wav).decode("ascii"),
            "text": text,
        })

    async def ask_confirmation(self, tool: str, args: dict, prompt: str) -> bool:
        self._confirm_waiter = asyncio.get_event_loop().create_future()
        await self.send({
            "type": "confirm_request",
            "tool": tool,
            "args": args,
            "prompt": prompt,
        })
        await self.speak(prompt + " Say yes to proceed.")
        try:
            return await asyncio.wait_for(self._confirm_waiter, timeout=30)
        except asyncio.TimeoutError:
            await self.speak("Confirmation timed out. Skipping.")
            return False
        finally:
            self._confirm_waiter = None

    def _describe_action(self, tool: str, args: dict) -> str:
        """Human-readable prompt for a confirmation request."""
        if tool == "ssh_run_command":
            return f"I want to run {args.get('command')} on {args.get('target')}. {args.get('reason','')}"
        if tool == "docker_restart":
            return f"I want to restart container {args.get('container')} on {args.get('target')}. {args.get('reason','')}"
        if tool == "launch_app":
            return f"I want to launch {args.get('app')}. {args.get('reason','')}"
        if tool == "write_file":
            return f"I want to write to {args.get('path')}."
        if tool == "home_assistant_action":
            return f"I want to call {args.get('domain')}.{args.get('service')} on {args.get('entity_id')}."
        return f"I want to call {tool}."

    async def run_turn(self, user_text: str) -> None:
        """One full agent turn: user said X, figure out response, call tools, speak back."""
        self.history.append({"role": "user", "content": user_text})

        # Agent loop — keep calling the model while it wants tools
        for iteration in range(8):  # safety cap
            try:
                response = await asyncio.to_thread(
                    self.claude.chat,
                    messages=self.history,
                    system=self.config["persona"]["system_prompt"],
                    tools=TOOL_SPECS,
                    model=self.claude.pick_model(
                        needs_tools=True,
                        user_text=user_text,
                    ),
                )
            except BudgetExceeded as e:
                await self.speak(f"Budget cap reached. {e}")
                return
            except Exception as e:
                log.exception("claude_error")
                await self.speak(f"I hit an API error: {e}")
                return

            # Append assistant message to history
            self.history.append({"role": "assistant", "content": response.content})

            # Was a tool used?
            tool_uses = [b for b in response.content if b.type == "tool_use"]
            text_blocks = [b.text for b in response.content if b.type == "text"]

            if not tool_uses:
                # Pure text response — speak it and we're done
                final = " ".join(text_blocks).strip()
                if final:
                    await self.speak(final)
                return

            # Execute each tool call
            tool_results = []
            for tu in tool_uses:
                policy = self.toolbox.policy_for(tu.name)

                if policy == "deny":
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tu.id,
                        "content": "Tool is denied by policy.",
                        "is_error": True,
                    })
                    continue

                if policy == "confirm":
                    prompt = self._describe_action(tu.name, dict(tu.input))
                    approved = await self.ask_confirmation(tu.name, dict(tu.input), prompt)
                    if not approved:
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tu.id,
                            "content": "User denied this action.",
                            "is_error": False,
                        })
                        continue

                await self.status(f"using tool: {tu.name}")
                result = await self.toolbox.dispatch(tu.name, dict(tu.input))
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tu.id,
                    "content": json.dumps(result)[:4000],
                })

            # Feed results back in for the next loop iteration
            self.history.append({"role": "user", "content": tool_results})

        await self.speak("I got stuck in a tool loop. Try rephrasing.")


async def handle_connection(websocket, claude, stt, tts, config):
    log.info("frontend_connected", remote=str(websocket.remote_address))

    # Auth handshake
    try:
        first = await asyncio.wait_for(websocket.recv(), timeout=5)
        msg = json.loads(first)
        expected = os.environ.get(config["frontend"]["shared_secret_env"], "")
        if msg.get("type") != "auth" or msg.get("secret") != expected or not expected:
            await websocket.send(json.dumps({"type": "error", "text": "auth failed"}))
            return
    except Exception as e:
        log.warning("auth_failed", error=str(e))
        return

    bridge = FrontendBridge(websocket)
    toolbox = Toolbox(config, claude.spend, bridge)
    session = Session(websocket, claude, stt, tts, toolbox, config)

    await session.send({"type": "ready"})

    try:
        async for raw in websocket:
            msg = json.loads(raw)
            t = msg.get("type")

            if t == "audio":
                wav_bytes = base64.b64decode(msg["wav_b64"])
                await session.status("transcribing")
                text = await asyncio.to_thread(stt.transcribe, wav_bytes)
                if text:
                    await session.send({"type": "heard", "text": text})
                    await session.run_turn(text)

            elif t == "text":
                await session.run_turn(msg["text"])

            elif t == "confirm":
                if session._confirm_waiter and not session._confirm_waiter.done():
                    session._confirm_waiter.set_result(bool(msg.get("approved")))

            elif t == "frontend_response":
                bridge.resolve(msg["request_id"], msg.get("result", {}))

            else:
                log.warning("unknown_message_type", type=t)

    except websockets.ConnectionClosed:
        log.info("frontend_disconnected")


async def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key or api_key == "sk-ant-REPLACE_ME":
        log.error("missing_api_key")
        sys.exit(1)

    spend = build_from_config(CONFIG)
    claude = ClaudeClient(api_key, CONFIG, spend)
    stt = STT(**CONFIG["voice"]["stt"])
    tts = TTS(**CONFIG["voice"]["tts"])

    log.info("jarvis_starting", host="0.0.0.0", port=8765)

    async def handler(ws):
        await handle_connection(ws, claude, stt, tts, CONFIG)

    async with websockets.serve(handler, "0.0.0.0", 8765, max_size=10_000_000):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())

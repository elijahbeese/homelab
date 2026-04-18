#!/usr/bin/env python3
"""
JARVIS frontend — runs on the Fedora ProBook.

Responsibilities:
  1. Listen to the mic continuously
  2. Detect wake word ("hey jarvis")
  3. Capture audio until user stops talking (VAD)
  4. Send audio over websocket to brain on ProLiant
  5. Play back TTS audio
  6. Handle confirm_request (spoken yes/no)
  7. Handle launch_app requests from brain
"""
import asyncio
import base64
import io
import json
import os
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd
import websockets
from dotenv import load_dotenv

try:
    from openwakeword.model import Model as WakeWordModel
    HAS_WAKEWORD = True
except ImportError:
    HAS_WAKEWORD = False

import webrtcvad

load_dotenv()

# ── Config from env ────────────────────────────────────────────────────
BRAIN_URL = os.environ.get("JARVIS_BRAIN_URL", "ws://100.119.210.126:8765")
SHARED_SECRET = os.environ.get("JARVIS_FRONTEND_SECRET", "")
WAKE_WORD_MODEL = os.environ.get("WAKE_WORD_MODEL", "hey_jarvis_v0.1")
USE_PUSH_TO_TALK = os.environ.get("JARVIS_PUSH_TO_TALK", "0") == "1"

SAMPLE_RATE = 16000
FRAME_MS = 30  # VAD frame size
FRAME_SAMPLES = int(SAMPLE_RATE * FRAME_MS / 1000)

# ── Mic capture ────────────────────────────────────────────────────────


class MicListener:
    def __init__(self):
        self.vad = webrtcvad.Vad(2)  # aggressiveness 0-3
        if HAS_WAKEWORD and not USE_PUSH_TO_TALK:
            self.wake = WakeWordModel(wakeword_models=[WAKE_WORD_MODEL])
        else:
            self.wake = None

    def _record_until_silence(self, max_seconds: float = 12.0,
                              silence_ms: int = 800) -> bytes:
        """Record from the mic until the user stops talking, return WAV bytes."""
        frames = []
        silent_frames = 0
        silent_threshold = silence_ms // FRAME_MS
        max_frames = int(max_seconds * 1000 / FRAME_MS)

        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1,
                            dtype="int16", blocksize=FRAME_SAMPLES) as stream:
            for _ in range(max_frames):
                block, _ = stream.read(FRAME_SAMPLES)
                frame = block.tobytes()
                frames.append(frame)
                is_speech = self.vad.is_speech(frame, SAMPLE_RATE)
                silent_frames = 0 if is_speech else silent_frames + 1
                if silent_frames > silent_threshold and len(frames) > silent_threshold + 10:
                    break

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(b"".join(frames))
        return buf.getvalue()

    async def wait_for_trigger(self) -> bytes:
        """Block until the wake word fires (or enter in push-to-talk mode),
        then record an utterance."""
        if USE_PUSH_TO_TALK:
            await asyncio.to_thread(input, "Press Enter to speak... ")
            print("Recording...", flush=True)
            return await asyncio.to_thread(self._record_until_silence)

        # Continuous listen + wake word
        print(f"Listening for wake word...", flush=True)
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1,
                            dtype="int16", blocksize=1280) as stream:
            while True:
                block, _ = stream.read(1280)
                audio = block.flatten()
                prediction = self.wake.predict(audio)
                # Any wake word above 0.5 triggers
                if any(score > 0.5 for score in prediction.values()):
                    print("Wake word detected. Listening...", flush=True)
                    break
                await asyncio.sleep(0)
        return await asyncio.to_thread(self._record_until_silence)


# ── Audio playback ─────────────────────────────────────────────────────


def play_wav(wav_bytes: bytes) -> None:
    """Decode and play a WAV buffer via sounddevice (blocking)."""
    buf = io.BytesIO(wav_bytes)
    with wave.open(buf, "rb") as wf:
        rate = wf.getframerate()
        frames = wf.readframes(wf.getnframes())
        audio = np.frombuffer(frames, dtype=np.int16)
    sd.play(audio, samplerate=rate)
    sd.wait()


# ── App launcher ───────────────────────────────────────────────────────


def launch_app(app: str) -> dict:
    """Launch a local app on the ProBook. Simple whitelist + xdg-open fallback."""
    whitelist = {
        "firefox": ["firefox"],
        "chrome":  ["google-chrome-stable"],
        "code":    ["code"],
        "terminal": ["gnome-terminal"],
        "files":   ["nautilus"],
        "slack":   ["slack"],
    }
    cmd = whitelist.get(app.lower())
    if not cmd:
        return {"error": f"App '{app}' not in whitelist"}
    try:
        subprocess.Popen(cmd, start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"launched": app}
    except FileNotFoundError:
        return {"error": f"{cmd[0]} not installed"}


# ── Client loop ────────────────────────────────────────────────────────


async def handle_brain_message(msg: dict, ws, mic: MicListener) -> None:
    t = msg.get("type")

    if t == "ready":
        print("✓ Brain is ready.", flush=True)

    elif t == "status":
        print(f"  [{msg['text']}]", flush=True)

    elif t == "heard":
        print(f"You: {msg['text']}", flush=True)

    elif t == "speak":
        text = msg.get("text", "")
        if text:
            print(f"JARVIS: {text}", flush=True)
        wav_bytes = base64.b64decode(msg["wav_b64"])
        await asyncio.to_thread(play_wav, wav_bytes)

    elif t == "confirm_request":
        # Wait for the next utterance and look for yes/no
        print(f"  ⚠ Confirmation requested: {msg.get('prompt')}", flush=True)
        wav = await mic._record_until_silence(max_seconds=5, silence_ms=600)
        # Send the audio back to brain for transcription — brain will then
        # call us back via the confirm message
        # Simpler: we just ask the brain to transcribe and also decide here
        # For now, keyword match locally
        # Alternative: local tiny STT. For v1 we punt — frontend does simple RMS detect.
        # Let the user type y/n as a fallback too.
        approval = await asyncio.to_thread(
            input, "  Approve? [y/N] "
        )
        approved = approval.strip().lower() in ("y", "yes", "do it", "go")
        await ws.send(json.dumps({"type": "confirm", "approved": approved}))

    elif t == "launch_app":
        result = launch_app(msg["app"])
        await ws.send(json.dumps({
            "type": "frontend_response",
            "request_id": msg["request_id"],
            "result": result,
        }))

    elif t == "error":
        print(f"  ✗ Error: {msg.get('text')}", file=sys.stderr, flush=True)


async def run_client():
    if not SHARED_SECRET:
        print("Missing JARVIS_FRONTEND_SECRET in env", file=sys.stderr)
        sys.exit(1)

    mic = MicListener()

    while True:
        try:
            async with websockets.connect(BRAIN_URL, max_size=10_000_000) as ws:
                await ws.send(json.dumps({"type": "auth", "secret": SHARED_SECRET}))

                async def receiver():
                    async for raw in ws:
                        msg = json.loads(raw)
                        await handle_brain_message(msg, ws, mic)

                async def sender():
                    while True:
                        wav = await mic.wait_for_trigger()
                        await ws.send(json.dumps({
                            "type": "audio",
                            "wav_b64": base64.b64encode(wav).decode("ascii"),
                        }))

                await asyncio.gather(receiver(), sender())

        except (websockets.ConnectionClosed, OSError) as e:
            print(f"Connection issue: {e}. Reconnecting in 5s...", flush=True)
            await asyncio.sleep(5)


if __name__ == "__main__":
    try:
        asyncio.run(run_client())
    except KeyboardInterrupt:
        print("\nGoodbye.", flush=True)

<div align="center">

```
     ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗
     ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝
     ██║███████║██████╔╝██║   ██║██║███████╗
██   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║
╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║
 ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝

       VOICE·AGENT · HOMELAB·NATIVE · SELF·HOSTED
```

![Status](https://img.shields.io/badge/status-building-ffb000?style=for-the-badge&labelColor=0d1117)
![Claude](https://img.shields.io/badge/Claude-Haiku_4.5_%2B_Sonnet_4.6-cc785c?style=for-the-badge&labelColor=0d1117)
![Whisper](https://img.shields.io/badge/Whisper-faster--whisper-4a9eff?style=for-the-badge&labelColor=0d1117)
![Piper](https://img.shields.io/badge/Piper-local_TTS-00ff88?style=for-the-badge&labelColor=0d1117)
![Docker](https://img.shields.io/badge/Docker-compose-2496ed?style=for-the-badge&labelColor=0d1117)
![Tailscale](https://img.shields.io/badge/Tailscale-mesh-4a9eff?style=for-the-badge&labelColor=0d1117)
![License](https://img.shields.io/badge/license-MIT-lightgrey?style=for-the-badge&labelColor=0d1117)

**A split-brain voice assistant for a cybersecurity homelab.**

*Talks to me. Runs on my hardware. Uses my tools. Has a budget.*

</div>

---

## What This Is

JARVIS is a personal voice assistant built from open-source parts plus the Claude API, designed to live *inside* an existing homelab rather than bolt on top of it. It's not a chatbot with a microphone — it's a voice-driven agent with scoped SSH access to every box on my Tailscale mesh, a read-only-by-default security model, and a hard monthly spend cap.

Built as part of the [homelab](../..) cybersecurity homelab project.

## Why Build It

1. **Voice-first operations for the lab.** "What's the status of the Wazuh container on the ProLiant?" is faster said than typed-and-SSHed.
2. **A real agent project.** Not another wrapper chatbot. Real tool use, real confirmation flows, real spend governance.
3. **Practical LLM security.** Giving an LLM SSH to your infrastructure forces you to actually think about blast radius, least privilege, and destructive-action gating. That's the whole point.

## Architecture

JARVIS is split across two machines. This is deliberate.

```
┌──────────────────────────────────────────┐         ┌──────────────────────────────────────────────┐
│  FRONTEND — Fedora ProBook 650 G8        │         │  BRAIN — HP ProLiant DL360 G7 (Iowa)         │
│  100.74.18.2                             │         │  100.119.210.126                             │
│                                          │         │                                              │
│  ▸ Mic capture (sounddevice)             │         │  ▸ Whisper STT (faster-whisper, small.en)    │
│  ▸ Wake word (openWakeWord)              │◄───────►│  ▸ Claude API client (Haiku ↔ Sonnet router) │
│  ▸ VAD (webrtcvad)                       │ WS 8765 │  ▸ Tool dispatcher + confirmation gate       │
│  ▸ Audio playback                        │ (Tailscale)│  ▸ Piper TTS (en_US-amy-medium)          │
│  ▸ Local app launcher (whitelisted)      │         │  ▸ Spend guardrail (daily + monthly caps)    │
│  ▸ systemd user service                  │         │  ▸ Docker Compose — single container         │
└──────────────────────────────────────────┘         └───────────────────┬──────────────────────────┘
                                                                         │ SSH (ed25519)
                                                                         │
                     ┌───────────────────────┬───────────────────────────┼───────────────────────┐
                     │                       │                           │                       │
              ┌──────▼──────┐        ┌───────▼──────┐           ┌────────▼──────┐       ┌────────▼──────┐
              │  OptiPlex   │        │  Kali VM     │           │  Splunk VM    │       │  Pi 5         │
              │  Proxmox    │        │  100.77.*    │           │  100.81.*     │       │  100.119.34.* │
              │  100.90.*   │        │              │           │               │       │  Pi-hole/Zeek │
              └─────────────┘        └──────────────┘           └───────────────┘       └───────────────┘

                                             Tailscale mesh — no port forwarding, no public exposure
```

**Why split:** The ProBook sleeps, moves, loses power. The ProLiant is 24/7 with 32GB of RAM and dual Xeons. STT and Piper happily chew CPU on the ProLiant; the ProBook only has to handle a mic, a speaker, and a websocket. Adding a second frontend later (phone, kitchen mic, another laptop) is trivial because they all authenticate to the same brain with the same shared secret.

## Hardware Assignments

| Host | Role in JARVIS | Tailscale IP |
|---|---|---|
| **HP ProLiant DL360 G7** | Brain — Docker container runs here 24/7 | `100.119.210.126` |
| **Fedora ProBook 650 G8** | Frontend — mic + speakers, systemd user service | `100.74.18.2` |
| **Dell OptiPlex 7010** | SSH tool target (read-only: Proxmox status) | `100.90.195.73` |
| **Kali VM** | SSH tool target (read-only by default) | `100.77.251.92` |
| **Splunk VM** | SSH tool target + future Splunk REST tool | `100.81.37.2` |
| **Raspberry Pi 5** | SSH tool target (Pi-hole/Zeek checks) | `100.119.34.79` |

## Stack

### Voice
- **[faster-whisper](https://github.com/SYSTRAN/faster-whisper)** — CTranslate2 port of OpenAI Whisper. `small.en` at int8 quantization transcribes ~3s utterances in 500–800ms on CPU.
- **[openWakeWord](https://github.com/dscripka/openWakeWord)** — TFLite wake word. Default phrase: *"Hey JARVIS"*. Fallback: push-to-talk.
- **[webrtcvad](https://github.com/wiseman/py-webrtcvad)** — Google's VAD for detecting end-of-utterance so I don't have to press a button.
- **[Piper TTS](https://github.com/rhasspy/piper)** — ONNX-based neural TTS. Fast, offline, surprisingly natural. Voice: `en_US-amy-medium`.

### Brain
- **[Claude API](https://console.anthropic.com)** — Haiku 4.5 ($1/$5 per MTok) as the router and quick-response model. Sonnet 4.6 ($3/$15 per MTok) when tool use is needed.
- **[Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python)** — tool-use loop, streaming, native web search.
- **Custom spend tracker** — persists to `/app/state/spend.json`, enforces daily + monthly caps before every LLM call.

### Transport
- **websockets** — single TCP connection over Tailscale between frontend and brain. Shared-secret auth on connect. Binds to the Tailscale IP only, never `0.0.0.0`.

### Tools available to the agent
| Tool | Policy | Description |
|---|---|---|
| `web_search` | safe | Native Claude web search. Rate-limited. |
| `ssh_run_readonly` | safe | Whitelisted commands only (`uptime`, `df -h`, `docker ps`, etc.) |
| `ssh_run_command` | **confirm** | Arbitrary shell over SSH. Spoken confirmation required. |
| `docker_ps` / `docker_logs` | safe | Container inspection |
| `docker_restart` | **confirm** | Self-explanatory |
| `launch_app` | **confirm** | Runs an app on the ProBook (Firefox, terminal, VS Code, etc.) |
| `list_files` / `read_file` | safe | Brain-local filesystem |
| `home_assistant_query` | safe | Sensor + entity state (when enabled) |
| `home_assistant_action` | **confirm** | Turn things on/off |
| `budget_status` | safe | "How much have I spent today?" |

## Security Model

Giving an LLM a shell is a choice. This one is made with the following rails:

1. **Read-only is the default.** Every tool is tagged `safe` / `confirm` / `deny` in `brain/config/jarvis.yaml`. `confirm` tools speak the action out loud and wait for approval before executing.
2. **Dedicated `jarvis` user on every target host.** Password-locked, key-only, restricted sudoers allowing only diagnostic commands (`systemctl status`, `journalctl`, `docker ps`, etc.). `deploy/bootstrap_target.sh` sets this up.
3. **SSH key never leaves the brain container.** Mounted read-only. Never committed. Never exposed via frontend.
4. **Shared-secret auth on the websocket.** Brain binds only to Tailscale IP, not the public internet. Secret is a 64-char hex string generated on install.
5. **Spend cap is enforced before the call, not after.** Daily ($0.75) and monthly ($15.00) caps refuse new LLM requests once hit. Web search calls tracked separately.
6. **The Anthropic console itself has a monthly cap set.** Belt and suspenders.

None of this makes the system bulletproof. It makes the blast radius of a prompt-injection or a bad day small enough that I can sleep.

## Budget

| Model | Input $/MTok | Output $/MTok | Used for |
|---|---|---|---|
| Haiku 4.5 | $1.00 | $5.00 | Greetings, short questions, routing |
| Sonnet 4.6 | $3.00 | $15.00 | Tool use, multi-step reasoning, anything non-trivial |
| Web search | $0.01 per query | — | Native Claude tool |

Realistic usage: **~$5–10/month** with light daily chatting, a handful of tool calls, and the spend tracker biting hard when I get chatty.

The tracker logs every call to `/app/state/spend.json`. "JARVIS, what's my budget status" is itself a tool.

## Install

### 1. Anthropic API key
1. Sign up at [console.anthropic.com](https://console.anthropic.com)
2. **Settings → Limits**: set monthly spend cap to $15
3. Generate an API key under **Settings → API Keys**

### 2. Brain (ProLiant)
```bash
# On the ProLiant, via Tailscale SSH:
git clone -b jarvis git@github.com:elijahbeese/homelab.git
cd homelab/jarvis
bash deploy/install_brain.sh
```
The installer creates `brain/.env`, generates an SSH key + shared secret, builds the Docker image (downloads Whisper + Piper models ~1GB), and starts the container.

### 3. Bootstrap each lab host
Copy the public key printed by `install_brain.sh`, then on each target host:
```bash
sudo bash bootstrap_target.sh "ssh-ed25519 AAAA... jarvis@homelab"
```
This creates the `jarvis` user, installs the key, and writes the restricted sudoers entry.

### 4. Frontend (ProBook)
```bash
cd homelab/jarvis/frontend
bash install.sh
# Edit .env — paste the shared secret from the brain install output
systemctl --user enable --now jarvis-frontend
loginctl enable-linger $USER  # keep service alive after logout
```

### 5. Talk to it
Say "Hey JARVIS" (or hit Enter in push-to-talk mode). First utterance is transcribed, routed, potentially tool-dispatched, and spoken back.

## Example Interactions

```
You:    "Hey JARVIS, is Splunk healthy?"
[status: transcribing]
[status: using tool: ssh_run_readonly]
JARVIS: "Splunk's up. System load's point four, plenty of headroom."

You:    "What containers are running on the Proxmox box?"
[status: using tool: docker_ps]
JARVIS: "Proxmox isn't running Docker — it's the hypervisor. You probably
         mean one of the VMs. Want me to check the Splunk VM instead?"

You:    "Restart the Wazuh container on the ProLiant."
[status: ⚠ confirmation requested]
JARVIS: "I want to restart container wazuh-manager on proliant.
         Manager has been unresponsive for 10 minutes. Say yes to proceed."
You:    "Yes."
JARVIS: "Restarted. Should be back in about thirty seconds."

You:    "Budget check."
JARVIS: "Today you've spent twelve cents. Eighty-eight cents left today,
         fourteen dollars twenty-three cents left this month."
```

## Roadmap

- [x] Split architecture: brain container + frontend client
- [x] Local STT (Whisper) + TTS (Piper)
- [x] Haiku / Sonnet routing
- [x] Spend guardrail with persistence
- [x] Read-only / confirm / deny tool policy
- [x] SSH tool over Tailscale to all lab hosts
- [x] Docker inspection tools
- [x] Frontend app launcher
- [ ] Voice-only confirmation (currently falls back to typed y/n)
- [ ] Home Assistant integration (stubbed, not wired)
- [ ] Splunk REST tool (search the SIEM by voice)
- [ ] Wazuh alert summarization tool
- [ ] Prompt caching for the system prompt (saves ~90% of input token cost)
- [ ] Multi-frontend support (kitchen mic, phone)
- [ ] Local fallback model for offline operation
- [ ] Conversation memory across sessions (opt-in)

## Repo Layout

```
jarvis/
├── brain/                      # Runs on the ProLiant in Docker
│   ├── Dockerfile              # Python 3.12 + ffmpeg + Whisper + Piper
│   ├── docker-compose.yml      # Binds to Tailscale IP only
│   ├── requirements.txt
│   ├── server.py               # Websocket + agent loop
│   ├── llm.py                  # Claude client + model router
│   ├── voice.py                # Whisper + Piper wrappers
│   ├── spend.py                # Cost tracker + circuit breaker
│   ├── tools/
│   │   ├── __init__.py
│   │   └── registry.py         # Tool specs + dispatcher
│   ├── config/
│   │   └── jarvis.yaml         # Models, persona, SSH targets, policies
│   └── .env.example
│
├── frontend/                   # Runs on the ProBook via systemd
│   ├── client.py               # Mic, wake word, VAD, playback, app launcher
│   ├── requirements.txt
│   ├── install.sh              # Fedora install script
│   ├── jarvis-frontend.service # systemd user unit
│   └── .env.example
│
├── deploy/
│   ├── generate_ssh_key.sh     # Make the jarvis ed25519 key
│   ├── bootstrap_target.sh     # Create jarvis user on a lab host
│   └── install_brain.sh        # ProLiant-side installer
│
├── docs/
│   ├── GIT_SETUP.md            # How this branch was created
│   └── TROUBLESHOOTING.md      # Known failure modes
│
├── .gitignore                  # Secrets, keys, state, models
└── README.md                   # You're reading it
```

## Known Gotchas

- **Piper voice sample rate is hardcoded to 22050Hz** in `voice.py`. Works for the default Amy voice; if you swap voices, read the `.onnx.json` config to get the actual rate.
- **Voice-only confirmation falls back to typed y/n.** Intentional for v1 — live voice confirmation while the TTS is still speaking is a race-condition minefield. Planned upgrade.
- **openWakeWord's "hey_jarvis" is serviceable, not great.** False positives happen. Push-to-talk mode (`JARVIS_PUSH_TO_TALK=1`) is the escape hatch until I train a custom phrase.
- **SSH key rotation is manual.** There's no auto-rotate. Treat it like any other service account key.

## Credits

- Architecture shamelessly inspired by every sci-fi AI ever written. Specifically not inspired by any one TikTok demo.
- Anthropic for the API. Rhasspy + Michael Hansen for Piper. SYSTRAN for faster-whisper. David Scripka for openWakeWord.

---

<div align="center">

**Part of the [homelab](../..) homelab project** · **B.S. Cybersecurity (in progress)**

*Building an assistant is easier than building trust in one. This repo is the paper trail for both.*

</div>

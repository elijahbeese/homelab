# JARVIS Troubleshooting

## Brain won't start

```bash
# On the ProLiant:
cd ~/jarvis/brain
docker compose logs --tail 100 jarvis-brain
```

| Symptom | Fix |
|---|---|
| `missing_api_key` | Edit `brain/.env`, fill in `ANTHROPIC_API_KEY` |
| `Piper voice not found` | Voice download failed during build. `docker compose build --no-cache` |
| Container restarts every 30s | Check healthcheck logs; usually means port 8765 isn't binding |
| `Address already in use` | Something else is on 8765. Change port in `docker-compose.yml` |

## Frontend can't connect to brain

```bash
# On the ProBook, test connectivity manually:
nc -zv 100.119.210.126 8765   # should say "succeeded"
# if it fails, Tailscale is the problem, not JARVIS
tailscale status
tailscale ping proliant
```

Common causes:
1. **Tailscale not running** on the ProLiant → `sudo systemctl start tailscaled`
2. **Docker port binding wrong** → Docker Compose binds to the Tailscale IP.
   If Tailscale restarts and gets a new IP (shouldn't happen on a server but
   does), update `docker-compose.yml`.
3. **Shared secret mismatch** → Copy the exact `JARVIS_FRONTEND_SECRET` from
   `brain/.env` into `frontend/.env`.

## Mic not detected

```bash
# List audio input devices
python3 -c "import sounddevice; print(sounddevice.query_devices())"

# Set a specific device in client.py if the default is wrong:
# sd.default.device = <index>
```

On Fedora with PipeWire: make sure the jarvis-frontend systemd service has
`Environment=PULSE_RUNTIME_PATH=%t/pulse` (it does). If you hear dropouts,
try `pw-metadata -n settings 0 clock.force-quantum 1024`.

## Wake word doesn't trigger

The openWakeWord "hey_jarvis" model is trained, but not great. Options:

1. **Use push-to-talk instead:** set `JARVIS_PUSH_TO_TALK=1` in `frontend/.env`
2. **Train a custom wake phrase:** openWakeWord has a notebook for this
3. **Try a different model name:** `alexa_v0.1`, `hey_mycroft_v0.1`, etc.

## SSH tool calls fail

```bash
# From the ProLiant, manually test the key:
docker exec jarvis-brain ssh -i /home/jarvis/.ssh/id_ed25519 \
  jarvis@100.77.251.92 uptime
```

| Error | Fix |
|---|---|
| `Permission denied (publickey)` | Public key not in target's `authorized_keys` yet |
| `Connection refused` | Target host down or SSH not running there |
| `Host key verification failed` | `AutoAddPolicy` should handle this; if it persists, delete `~/.ssh/known_hosts` in the container |
| `command not found` when running docker | Target user isn't in docker group → re-run `bootstrap_target.sh` |

## Spend guardrail hit

Check current usage:

```bash
docker exec jarvis-brain cat /app/state/spend.json
```

To reset (e.g. new month):

```bash
docker exec jarvis-brain rm /app/state/spend.json
docker compose restart jarvis-brain
```

To raise the cap, edit `brain/config/jarvis.yaml`, then
`docker compose restart jarvis-brain`.

## Latency is bad

Typical numbers on Xeon X5650 (dual, 24 threads total):

| Step | Expected |
|---|---|
| Whisper small.en (3 sec utterance) | 500-800ms |
| Claude Haiku (1-turn response) | 800-1500ms |
| Claude Sonnet (with 1 tool call) | 2-4s |
| Piper TTS (20-word reply) | 200-400ms |
| **End-to-end simple Q&A** | ~2-3s |
| **End-to-end with tool use** | ~5-8s |

If you're seeing >10s for simple queries:

1. Switch Whisper to `tiny.en` — 3-4x faster, accuracy hit is small for commands
2. Check that Haiku is actually being used (spend logs will show model per call)
3. Make sure the ProLiant isn't swap-thrashing: `free -h`

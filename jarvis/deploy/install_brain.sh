#!/usr/bin/env bash
# Installs JARVIS brain on the ProLiant (or any Docker host).
# Assumes: Docker + docker-compose-plugin already installed on the host.
set -euo pipefail

cd "$(dirname "$0")/../brain"

echo "▶ Checking Docker..."
if ! command -v docker &>/dev/null; then
  echo "✗ Docker not installed. Install it first:" >&2
  echo "  curl -fsSL https://get.docker.com | sudo sh" >&2
  exit 1
fi

if ! docker compose version &>/dev/null; then
  echo "✗ Docker Compose plugin not installed." >&2
  echo "  sudo dnf install -y docker-compose-plugin  (or equivalent for your distro)" >&2
  exit 1
fi

# ── .env ───────────────────────────────────────────────────────────────
if [[ ! -f .env ]]; then
  echo "▶ Creating .env from template..."
  cp .env.example .env

  # Generate a random shared secret
  SECRET=$(openssl rand -hex 32)
  sed -i "s/REPLACE_ME_WITH_RANDOM_HEX/$SECRET/" .env

  echo ""
  echo "⚠ You must now edit brain/.env and add your ANTHROPIC_API_KEY."
  echo "  Get one from https://console.anthropic.com"
  echo "  SET A MONTHLY SPENDING CAP there before using it."
  echo ""
  echo "The shared secret for the frontend has been generated. Copy this to"
  echo "the frontend's .env file on your ProBook (as JARVIS_FRONTEND_SECRET):"
  echo ""
  grep JARVIS_FRONTEND_SECRET .env
  echo ""
  read -rp "Press Enter once you've edited .env to continue..."
fi

# ── SSH key ────────────────────────────────────────────────────────────
if [[ ! -f ssh_keys/id_ed25519 ]]; then
  echo "▶ Generating SSH key for lab host access..."
  bash ../deploy/generate_ssh_key.sh
  echo ""
  echo "⚠ The above public key must be added to the 'jarvis' user on each"
  echo "  lab host you want JARVIS to reach. See README for details."
  echo ""
  read -rp "Press Enter once you've distributed the key..."
fi

# ── Build & start ──────────────────────────────────────────────────────
echo "▶ Building brain image (first time takes 5-10 min — downloads Whisper + Piper models)..."
docker compose build

echo "▶ Starting brain..."
docker compose up -d

echo "▶ Waiting for brain to be healthy..."
for i in {1..30}; do
  if docker compose ps | grep -q "healthy"; then
    echo "✓ Brain is healthy and listening on port 8765"
    break
  fi
  sleep 2
done

echo ""
echo "Logs:    docker compose logs -f jarvis-brain"
echo "Stop:    docker compose down"
echo "Restart: docker compose restart jarvis-brain"

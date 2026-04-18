#!/usr/bin/env bash
# Installs JARVIS frontend on Fedora. Run as your normal user (NOT root).
set -euo pipefail

cd "$(dirname "$0")"

echo "▶ Installing system dependencies (needs sudo)..."
sudo dnf install -y \
  python3.12 \
  python3.12-devel \
  python3-pip \
  portaudio-devel \
  gcc \
  git \
  ffmpeg

echo "▶ Installing uv (fast Python package manager)..."
if ! command -v uv &> /dev/null; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

echo "▶ Creating virtualenv and installing Python deps..."
uv venv .venv --python 3.12
source .venv/bin/activate
uv pip install -r requirements.txt

if [[ ! -f .env ]]; then
  echo "▶ Creating .env from template — EDIT IT before starting the service"
  cp .env.example .env
  echo "   → edit $(pwd)/.env now"
fi

echo "▶ Installing systemd user service..."
mkdir -p ~/.config/systemd/user
cp jarvis-frontend.service ~/.config/systemd/user/
systemctl --user daemon-reload

cat <<EOF

✓ Frontend install complete.

Next steps:
  1. Edit $(pwd)/.env and fill in JARVIS_FRONTEND_SECRET (must match brain)
  2. Test it interactively first:
       source .venv/bin/activate
       python client.py
  3. When it works, enable the service:
       systemctl --user enable --now jarvis-frontend
       loginctl enable-linger \$USER   # keep running after logout
  4. Watch logs with:
       journalctl --user -u jarvis-frontend -f

EOF

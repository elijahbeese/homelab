#!/usr/bin/env bash
# Run this ON EACH LAB HOST that JARVIS should be able to SSH into.
# Creates a locked-down 'jarvis' user with only the permissions it needs.
#
# Usage (from the target host):
#   curl -O <your-repo-raw>/deploy/bootstrap_target.sh
#   sudo bash bootstrap_target.sh "<paste jarvis public key here>"
#
# Or copy this file over with scp and run it with sudo.

set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "This script must be run as root (use sudo)" >&2
  exit 1
fi

PUBKEY="${1:-}"
if [[ -z "$PUBKEY" ]]; then
  echo "Usage: sudo bash bootstrap_target.sh \"<jarvis public key string>\"" >&2
  exit 1
fi

USER_NAME="jarvis"

# ── Create the user if it doesn't exist ───────────────────────────────
if ! id "$USER_NAME" &>/dev/null; then
  echo "▶ Creating user $USER_NAME..."
  useradd --create-home --shell /bin/bash "$USER_NAME"
  # No password — SSH key only
  passwd -l "$USER_NAME"
else
  echo "✓ User $USER_NAME already exists"
fi

# ── Install the public key ────────────────────────────────────────────
SSH_DIR="/home/$USER_NAME/.ssh"
mkdir -p "$SSH_DIR"
chmod 700 "$SSH_DIR"

AUTH_KEYS="$SSH_DIR/authorized_keys"
touch "$AUTH_KEYS"
chmod 600 "$AUTH_KEYS"

# Add the key only if it's not already present
if ! grep -qF "$PUBKEY" "$AUTH_KEYS"; then
  echo "$PUBKEY" >> "$AUTH_KEYS"
  echo "✓ Public key added to $AUTH_KEYS"
else
  echo "✓ Public key already present"
fi

chown -R "$USER_NAME:$USER_NAME" "$SSH_DIR"

# ── Restricted sudoers entry ──────────────────────────────────────────
# Only a very limited command set, no NOPASSWD on anything destructive.
# Edit this list per-host if you want the assistant to do more.
SUDOERS_FILE="/etc/sudoers.d/jarvis"
cat > "$SUDOERS_FILE" <<'EOF'
# JARVIS lab assistant — restricted privileges
# Read-only / diagnostic commands only. Extend per-host as needed.

# Cmnd_Alias groups for readability
Cmnd_Alias JARVIS_STATUS = /usr/bin/systemctl status *, \
                           /usr/bin/systemctl is-active *, \
                           /usr/bin/systemctl is-enabled *, \
                           /usr/bin/journalctl -n *, \
                           /usr/bin/journalctl -u *, \
                           /usr/bin/docker ps, \
                           /usr/bin/docker ps -a, \
                           /usr/bin/docker logs *, \
                           /usr/bin/docker stats --no-stream, \
                           /usr/bin/df -h, \
                           /usr/bin/free -h, \
                           /usr/bin/uptime, \
                           /usr/sbin/ss -tlnp, \
                           /usr/sbin/ip a

# Jarvis can run these without a password (no interactive session for TTY)
jarvis ALL=(ALL) NOPASSWD: JARVIS_STATUS

# Everything else requires password → effectively blocked since user is locked
EOF

chmod 440 "$SUDOERS_FILE"
visudo -cf "$SUDOERS_FILE" >/dev/null && echo "✓ sudoers entry valid" || {
  echo "✗ sudoers file invalid, removing"
  rm -f "$SUDOERS_FILE"
  exit 1
}

# ── Add to docker group if docker is installed ────────────────────────
if command -v docker &>/dev/null; then
  if ! groups "$USER_NAME" | grep -q docker; then
    usermod -aG docker "$USER_NAME"
    echo "✓ Added $USER_NAME to docker group (can run docker ps without sudo)"
  fi
fi

echo ""
echo "✓ Host bootstrapped. JARVIS can now SSH in as $USER_NAME."
echo ""
echo "Test from the ProLiant:"
echo "  ssh -i ~/.ssh/id_ed25519 jarvis@$(hostname -I | awk '{print $1}') uptime"

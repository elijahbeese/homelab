#!/usr/bin/env bash
# Generate an ed25519 SSH key for JARVIS to use when reaching lab hosts.
# Run this ONCE on the ProLiant (the brain host).
set -euo pipefail

KEY_DIR="$(dirname "$0")/../brain/ssh_keys"
mkdir -p "$KEY_DIR"
chmod 700 "$KEY_DIR"

if [[ -f "$KEY_DIR/id_ed25519" ]]; then
  echo "Key already exists at $KEY_DIR/id_ed25519"
  echo "Public key:"
  cat "$KEY_DIR/id_ed25519.pub"
  exit 0
fi

ssh-keygen -t ed25519 -N "" -C "jarvis@homelab" -f "$KEY_DIR/id_ed25519"
chmod 600 "$KEY_DIR/id_ed25519"

echo ""
echo "✓ Key generated at $KEY_DIR/id_ed25519"
echo ""
echo "Now, on EACH lab host that JARVIS will access, run:"
echo "  deploy/bootstrap_target.sh"
echo ""
echo "Or manually add this public key to the 'jarvis' user's ~/.ssh/authorized_keys:"
echo ""
cat "$KEY_DIR/id_ed25519.pub"

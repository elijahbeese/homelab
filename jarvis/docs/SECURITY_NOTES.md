# Security Notes for This Repo

## Tailscale IPs are present

Files in this project reference your Tailscale IPs directly:

- `brain/config/jarvis.yaml` — all `ssh_targets`
- `brain/docker-compose.yml` — port binding on the brain side
- `frontend/.env.example` — default `JARVIS_BRAIN_URL`
- `README.md` and `docs/TROUBLESHOOTING.md`
- `frontend/client.py` — default fallback URL

**Why this is probably fine:** Your existing public homelab README already
documents these same IPs. Tailscale IPs in the 100.x.x.x CGNAT range are
**not routable from the public internet** and only resolve to devices on
your tailnet. Someone seeing a Tailscale IP in your repo cannot use it to
reach your boxes — they'd need to be on your tailnet first.

**What would actually be dangerous:**
- Public IPs (ISP-assigned addresses)
- Tailscale auth keys or ACL tokens
- SSH private keys
- API keys
- Shared secrets

None of those are in this repo.

**If you want to be extra cautious anyway**, swap the IPs for DNS names
and add them to your tailnet's MagicDNS:

```yaml
ssh_targets:
  proxmox:
    host: proxmox    # instead of 100.90.195.73
    user: jarvis
```

Requires MagicDNS enabled in your Tailscale admin console.

## Before every commit

Run:

```bash
# from the repo root
grep -r "sk-ant-[A-Za-z0-9_-]\{30,\}" jarvis/ && echo "⚠ API KEY" || echo "✓ clean"
grep -r "BEGIN .* PRIVATE KEY" jarvis/ && echo "⚠ PRIVATE KEY" || echo "✓ clean"
git status   # confirm no .env, no ssh_keys/, no state/
```

## If you accidentally commit a secret

1. **Rotate the secret immediately** at its source (Anthropic console, etc.)
   Assume anything pushed to GitHub is already compromised, even if the
   repo is private. Bots scan pushes in seconds.
2. **Clean history** with `git filter-repo` or BFG Repo-Cleaner.
3. Force-push the cleaned history.
4. Monitor for misuse (Anthropic will show unusual activity in your console).

# Adding JARVIS to your homelab Repo

This project is set up to live on a dedicated `jarvis` branch of your existing
homelab repo. You run these commands **once**, from your ProBook, after you've
dropped the `jarvis/` folder alongside your existing repo files.

## One-time branch setup

```bash
# From your existing homelab repo root:
cd ~/homelab

# Make sure you're up to date
git fetch origin
git checkout main
git pull

# Create the jarvis branch from main
git checkout -b jarvis

# Copy the generated jarvis/ folder into the repo root
# (adjust source path to wherever you unzipped it)
cp -r ~/Downloads/jarvis ./

# Sanity check: make sure no secrets leaked in
grep -r "sk-ant-" . && echo "⚠ API KEY FOUND — STOP" || echo "✓ clean"
grep -r "ssh_keys/id_ed25519" jarvis/.gitignore && echo "✓ keys gitignored"

# Stage and commit
git add jarvis/
git status    # eyeball what's being committed one more time
git commit -m "Add JARVIS voice assistant (initial scaffold)

- Split architecture: brain on ProLiant, frontend on Fedora ProBook
- Local Whisper STT + Piper TTS, Claude API for reasoning
- Tool registry with read-only/confirm/deny policy
- Spend guardrail with daily + monthly caps
- Restricted jarvis user on each lab host via SSH key"

# Push and set upstream
git push -u origin jarvis
```

## Pull request (optional, recommended)

Open a PR from `jarvis` → `main` in the GitHub UI. Even if you're going to self-
merge, the PR view is the best way to do a final read-through of every file
before it hits your public main branch.

```bash
# Or from CLI if you have gh installed:
gh pr create --base main --head jarvis \
  --title "Add JARVIS voice assistant" \
  --body "Split-brain voice agent. See jarvis/README.md for architecture."
```

## Ongoing workflow

Keep `jarvis` as a long-lived feature branch while you iterate:

```bash
git checkout jarvis
# ... make changes ...
git commit -am "jarvis: add Home Assistant integration"
git push
```

Merge to `main` when a milestone feels stable (e.g. after v1 works end-to-end).

## Secrets audit checklist

Before every push:

- [ ] `.env` files are **not** staged (check with `git status`)
- [ ] `brain/ssh_keys/` is **not** staged
- [ ] No `sk-ant-` prefixed strings anywhere in the diff
- [ ] No Tailscale auth keys, HA tokens, or other credentials in diffs
- [ ] `.gitignore` at the project root includes all of the above

If you ever commit a secret by accident: **rotate it immediately** at the source
(Anthropic console, Tailscale admin, etc.) and then use `git filter-repo` or
BFG Repo-Cleaner to scrub history. GitHub's secret scanning will also catch
Anthropic keys and notify you, but don't rely on that.

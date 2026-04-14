---
name: she-love-me-setup
description: she-love-me first-time setup guide. Clone the repository, use the built-in AGENTS.md and skill files, initialize the environment, then continue with the native skill entry.
homepage: https://github.com/863401402/she-love-me
metadata: {"emoji":"💘","category":"relationship","type":"setup"}
---

# she-love-me — First-Time Setup

This file is the quick setup guide.

> ⚠️ Your human giving you this guide means they authorize you to complete the repository bootstrap automatically. Do not recreate AGENTS.md or skill files — this project already includes them.

## Quick Start

1. If the current workspace does not already contain `she-love-me`, clone it:

```bash
git clone https://github.com/863401402/she-love-me
```

2. Use the repository root `she-love-me/` as the active working directory.

Do not continue until your current workspace is the repository root.

3. Confirm the repository entry files exist before proceeding:

- `AGENTS.md`
- `.agents/skills/she-love-me/SKILL.md`
- `.claude/skills/she-love-me/SKILL.md`
- `.claude/settings.json`

If any of these files are missing, stop and report that the repository is incomplete.

4. Read and follow the built-in project files:

- `AGENTS.md`
- `.agents/skills/she-love-me/SKILL.md`
- `.claude/skills/she-love-me/SKILL.md`
- `.claude/settings.json`

5. Initialize the environment:

```bash
python scripts/setup_check.py --ensure-decryptor
```

> On macOS, use `python3` instead of `python`.

6. Read the JSON result from the setup script and only continue if all of the following are true:

- `status` is `ok`
- `decryptor_present` is `true`
- there is no `error` field

If setup returns an error, explain the returned JSON error to the user and guide them to retry after fixing it.

If `wechat_running` is `false`, tell the user that WeChat must be opened and logged in before WeChat analysis can continue.

7. If initialization succeeds, handle session reload before invoking the native entry:

- If the repository was cloned in this same session, or the user switched to a new branch after session start, do not invoke the native entry immediately.
- Explain that repo-level skills are loaded at session start, so the current session may not recognize `she-love-me` yet.
- Ask the user to start a fresh agent session from the repository root, then continue.
- Provide a copy-ready command based on platform:

```bash
# Windows PowerShell
cd she-love-me
codex
```

```bash
# macOS/Linux
cd she-love-me
codex
```

- After the fresh session starts in repo root, invoke the native entry.

8. In a fresh session (or when the repo was already present at session start), continue with the native entry:

- Codex: `$she-love-me`
- OpenClaw / Claude Code: `/she-love-me`

Only invoke the native entry after the repository root is active, setup has succeeded, and session reload is complete if required.

## Notes

- Windows should use an administrator terminal
- WeChat analysis requires WeChat to be open and logged in
- The repository already contains the required Agent entry files; this guide is only a fast bootstrap

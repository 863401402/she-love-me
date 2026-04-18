# AGENTS.md

## Repository Focus

- This repository packages the `she-love-me` workflow for analyzing WeChat or QQ chat histories and generating an HTML relationship report.
- It also supports optional WeChat emoji export: `messages.json` can include emoji metadata, and `scripts/export_emojis.py` can download/store emoji assets and generate `reports/emojis_preview.html`.
- Current preferred export layout is per-contact bundles under `data/contacts/<联系人>__<hash>/`, where chat records and emoji records are separated but linked (`messages.json` + `emojis.json`).
- The unified skill entrypoint for all tools is `.agents/skills/she-love-me/SKILL.md` (Claude Code, OpenClaw, Codex, Cursor, Copilot, Gemini CLI).
- Analysis knowledge is split across `references/` under that directory; SKILL.md is a control-plane only (~200 lines).

## Codex Guidance

- When a user asks to analyze chat logs with this project, prefer the repo skill `she-love-me`.
- Keep the working directory at the repository root when following the skill workflow.
- Keep generated or sensitive outputs under `vendor/`, `data/`, and `reports/`; do not move personal chat data into tracked files.
- If the user asks about stickers/emojis, prefer the repo workflow: extract to `data/messages.json` first, then run `scripts/export_emojis.py`.
- Prefer `--output-dir data/contacts` over a shared `data/messages.json` whenever exporting a specific contact, so different users do not overwrite each other.
- If the user wants to invoke the skill explicitly in Codex, they can mention `$she-love-me`.

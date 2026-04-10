# AGENTS.md

## Repository Focus

- This repository packages the `she-love-me` workflow for analyzing WeChat or QQ chat histories and generating an HTML relationship report.
- The vendor-neutral skill entrypoint for Codex is `.agents/skills/she-love-me/SKILL.md`.
- The Claude-specific mirror under `.claude/skills/she-love-me/SKILL.md` exists for Claude Code and OpenClaw compatibility.

## Codex Guidance

- When a user asks to analyze chat logs with this project, prefer the repo skill `she-love-me`.
- Keep the working directory at the repository root when following the skill workflow.
- Keep generated or sensitive outputs under `vendor/`, `data/`, and `reports/`; do not move personal chat data into tracked files.
- If the user wants to invoke the skill explicitly in Codex, they can mention `$she-love-me`.

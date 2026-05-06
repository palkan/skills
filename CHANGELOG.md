# Changelog

## master

## 2.0.0 (2026-05-06)

- Added `/layered-rails:analyze-services` command to audit service objects usage (misuses, emerging abstractions, layer hygiene, test consequences). Integrated into `/layered-rails:analyze`.
- Renamed `/layered-rails:gradual` → `/layered-rails:plan` (and agent `layered-rails-gradual` → `layered-rails-planner`).
- Skill now ships canonical workflows under `skills/layered-rails/workflows/`, so any agent (Codex, skills.sh installs, etc.) gets the same procedural guidance the Claude Code slash commands wrap.

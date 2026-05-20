# Changelog

## master

## 2.0.1 (2026-05-20)

- Tightened `/layered-rails:analyze-services` "models-first variant" verdict: a single application-shaped class under `app/models/` (HTTP client, LLM caller, job-enqueuer, transport wrapper) now disqualifies the mature-decomposition exit and forces a Mixed verdict
- Added AI agent layer (`app/agents/`) row to the cluster table, separated LLM/AI SDK signals (`RubyLLM`, `OpenAI::`, `Anthropic::`, …) from generic third-party SDK signals
- Updated `/layered-rails:review` to defer service classification to `/layered-rails:analyze-services`

## 2.0.0 (2026-05-16)

- Added `/layered-rails:analyze-services` command to audit service objects usage (misuses, emerging abstractions, layer hygiene, test consequences). Integrated into `/layered-rails:analyze`.
- Renamed `/layered-rails:gradual` → `/layered-rails:plan` (and agent `layered-rails-gradual` → `layered-rails-planner`).
- Skill now ships canonical workflows under `skills/layered-rails/workflows/`, so any agent (Codex, skills.sh installs, etc.) gets the same procedural guidance the Claude Code slash commands wrap.

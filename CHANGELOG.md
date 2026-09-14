# Changelog

## master

- Added `active_event_store` gem reference (domain events over Rails Event Store) and linked it from the event-driven callback extraction example.

## 3.1.0 (2026-09-01)

- Updated archspec guide (added `except:` section)
- rails-hyperdrive now installs agents and commands

## 3.0.0 (2026-08-21)

- **BREAKING:** We are now `layered-rails-skills` everywhere: the GitHub repo (was `palkan/skills`), and the Claude Code marketplace (was `palkan-skills`) — re-add the marketplace and reinstall the plugin: `/plugin marketplace add palkan/layered-rails-skills`, then `/plugin install layered-rails@layered-rails-skills`.
- Added [rails-hyperdrive](https://github.com/rails-hyperdrive/rails-hyperdrive) install path: the layered-rails skill tree now also ships as the `layered-rails-skills` gem. `SKILL.md` renders from an ERB master, and each reference manual under `references/gems/` installs only when its target gem is in the app's bundle — gating declared in the gem-root `hyperdrive.yml` manifest, requires rails-hyperdrive `>= 0.5`.

## 2.1.0 (2026-08-21)

- Added `archspec` gem reference with a canonical layered-rails `Archspec.rb` config — enforces the four-layer boundaries, controller-API and `Current` rules in CI, with domain-services conventions, tailoring/adoption guidance, and a per-folder variant
- Added `/layered-rails:archspec` command and `archspec` workflow — detects the app's structure, generates a tailored `Archspec.rb` (offering gem installation when archspec is missing), verifies with `archspec check`, and triages violations (fix / suppress / baseline via `--update-todo`)
- Fixed layer assignments across the skill to match the book's raw text: mailers/deliveries/notifiers moved to the Application layer, form/filter objects to Presentation, query objects and repositories to Domain (domain services), jobs/channels to Presentation as internal inbound entry points, and config classes to Domain with their sources in Infrastructure

## 2.0.1 (2026-05-20)

- Tightened `/layered-rails:analyze-services` "models-first variant" verdict: a single application-shaped class under `app/models/` (HTTP client, LLM caller, job-enqueuer, transport wrapper) now disqualifies the mature-decomposition exit and forces a Mixed verdict
- Added AI agent layer (`app/agents/`) row to the cluster table, separated LLM/AI SDK signals (`RubyLLM`, `OpenAI::`, `Anthropic::`, …) from generic third-party SDK signals
- Updated `/layered-rails:review` to defer service classification to `/layered-rails:analyze-services`

## 2.0.0 (2026-05-16)

- Added `/layered-rails:analyze-services` command to audit service objects usage (misuses, emerging abstractions, layer hygiene, test consequences). Integrated into `/layered-rails:analyze`.
- Renamed `/layered-rails:gradual` → `/layered-rails:plan` (and agent `layered-rails-gradual` → `layered-rails-planner`).
- Skill now ships canonical workflows under `skills/layered-rails/workflows/`, so any agent (Codex, skills.sh installs, etc.) gets the same procedural guidance the Claude Code slash commands wrap.

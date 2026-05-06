# CLAUDE.md

Agentic guidance for developing skills in this repo. Skills _usage_ lives in each skill's `SKILL.md` — this file is for the meta workflow of building and shipping skills.

## Repo layout

- `<plugin>/` — one directory per plugin (e.g. `layered-rails/`)
  - `commands/` — `/<plugin>:*` slash commands
  - `agents/` — agents launched by commands or directly
  - `skills/<skill>/` — `SKILL.md` + `references/` + `examples/`
  - `.claude-plugin/plugin.json` — plugin manifest
- `.claude-plugin/marketplace.json` — top-level marketplace manifest
- `scripts/lint-skills.py` — skill linter (rules described in its docstring)
- `lefthook.yml` — runs the linter pre-commit
- `.github/workflows/lint.yml` — runs the linter in CI

## CHANGELOG

`CHANGELOG.md` uses a compact, flat format. The in-progress release lives under `## master`. One bullet per change, minimal prose:

```
## master

- Added `/layered-rails:foo` command to <one-line purpose>.
- Renamed `/layered-rails:bar` → `/layered-rails:baz` (and agent `<old>` → `<new>`).
```

Skip dev/tooling-only changes (lint scripts, CI workflows, hooks, internal refactors of scripts). Only user-visible plugin changes belong here.

On release, rename `## master` to `## <version>` and start a fresh `## master` block above it.

## Linting

Run before committing changes to any plugin file:

```bash
python3 scripts/lint-skills.py                    # full repo
python3 scripts/lint-skills.py --changed-only     # CI mode (diff vs origin)
python3 scripts/lint-skills.py path/to/SKILL.md   # specific files
```

Lefthook auto-runs the linter on staged `*.md` files; CI runs it on push and PR.

Key rules to remember when authoring (full list in the script's module docstring):

- `frontmatter.description.max-length` — ≤1024 chars; collapse trigger groups (`a/b/c`) when over budget
- `frontmatter.description.min-words` — ≥10 words
- `frontmatter.name.matches-dir` — `name:` must equal the skill directory name
- `body.length` / `reference.length` — ≤500 lines; split if larger
- `reference.toc` — reference files >100 lines need a `## Contents` section near the top
- `reference.one-level-deep` — links between non-SKILL `.md` files inside the skill must follow the tier hierarchy: `workflows/` (tier 1) may link DOWN to `references/` and `examples/` (tier 2); same-tier or upward links must go through `SKILL.md`
- `reference.no-orphans` — every `.md` in the skill dir must be linked from `SKILL.md`
- `reference.links-exist` / `plugin.links-exist` — all relative markdown links must resolve

To skip a rule with justification, use `lint-skip:` in the frontmatter:

```yaml
lint-skip:
  - rule: frontmatter.description.max-length
    reason: 'comprehensive trigger list is intentional'
```

## Versioning and release

SemVer. Bump the version in **both** manifests, kept in sync:

- `<plugin>/.claude-plugin/plugin.json` → `version`
- `.claude-plugin/marketplace.json` → `metadata.version` **and** matching `plugins[].version`

Bump rules:

- **Patch** — bug fixes, doc fixes, link repairs
- **Minor** — new commands, agents, references, examples (backward-compatible)
- **Major** — breaking changes for consumers (renamed or removed commands/agents, removed patterns)

Renaming a command or agent is a breaking change — external `CLAUDE.md` / `compound-engineering.local.md` files reference these by name.

Release flow:

1. Lint passes (`python3 scripts/lint-skills.py`).
2. Bump both manifests to the new version.
3. Rename `## master` → `## <version> (<date>)` in `CHANGELOG.md`; add a fresh `## master` above it.
4. Commit and tag (`git tag v<version>`).

## Authoring conventions

- **Description triggers** — list both concept terms ("layered design", "fat controller") and concrete pattern names users actually type ("service object", "form object", "policy object"). Both are needed for routing.
- **Agent naming** — use the `-er` / `-or` suffix to match existing convention (e.g., `layered-rails-reviewer`, `layered-rails-planner`). Command files use the bare verb (e.g., `commands/plan.md` for `/layered-rails:plan`).
- **Agent frontmatter** — only `name:` and `description:`. No `model:` attribute (removed for harness compatibility; let consumers pick).
- **Commands launch agents by `name:`**, not file path. Keep both in sync if you rename one.
- **Reference structure** — group references by kind (`core/`, `patterns/`, `anti-patterns/`, `topics/`, `gems/`, `examples/`). New references go under the matching kind; create a new kind only if no existing one fits.
- **Don't commit/push without explicit ask.** Show the diff and wait.

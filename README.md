# palkan/skills

A collection of coding-agent skills by [Vladimir Dementyev](https://github.com/palkan). The bundled plugins and slash commands target [Claude Code](https://docs.anthropic.com/en/docs/claude-code), while the core skill content (`SKILL.md` + workflows + references + examples) is also usable from other environments such as Codex.

## Available Skills

### Layered Rails

Design and review Rails applications using layered architecture principles from the [Layered Design for Ruby on Rails Applications](https://www.packtpub.com/en-us/product/layered-design-for-ruby-on-rails-applications-9781806114221) book.

**Install (recommended — full plugin with commands and sub-agents):**

```
/plugin marketplace add palkan/skills
/plugin install layered-rails@palkan-skills
```

**Commands:**

| Command | Purpose |
|---------|---------|
| `/layered-rails:analyze` | Full codebase architecture analysis |
| `/layered-rails:analyze-services` | Audit `app/services/` — conventions, clusters, layer hygiene, test consequences |
| `/layered-rails:analyze-callbacks` | Score model callbacks, find extraction candidates |
| `/layered-rails:analyze-gods` | Find god objects via churn x complexity |
| `/layered-rails:review` | Review code changes for layer violations |
| `/layered-rails:spec-test` | Run specification test on specific files |
| `/layered-rails:plan [goal]` | Plan incremental adoption of layered patterns |

**Install via [skills.sh](https://skills.sh/) (skill content only — no slash-command bindings):**

```
npx skills add palkan/skills --skill layered-rails
```

skills.sh delivers the `skills/layered-rails/` tree — `SKILL.md`, `workflows/`, `references/`, and `examples/`. The `/layered-rails:*` slash commands and the `layered-rails-planner` / `layered-rails-reviewer` sub-agent registrations are not part of the skill spec and won't be copied, but every workflow they wrap is in `workflows/` and can be invoked by name in plain language ("run the layered-rails review workflow on this diff"). Use this path when you want the same skill in Codex, the Claude API, or any other agent that supports skills.sh; use `/plugin install` when you want the slash commands.

### Integration with compound-engineering

We recommend asking Claude itself to update the instructions for Compound Engineering to include Layered Design features according to your needs. Below you can find some examples.

If you use the [compound-engineering](https://github.com/EveryInc/compound-engineering-plugin) plugin, add explicit instructions to include layered-rails planning and reviewing agents.

In your `compound-engineering.local.md` file:

```md
---
review_agents:
  - layered-rails
  - rails-reviewer
  - security-sentinel
  # - ...
---

# ...

# also worth adding something like:

We are **gradually adopting layered design principles** from "Layered Design for Ruby on Rails Applications" — clean abstraction boundaries, explicit layers, and specification tests...

```

Similarly, for planning features, add to your `CLAUDE.md` (or `AGENTS.md`, or whatever) smth like:

```md
# ...

### For planning agents

When planning new features or architectural changes, use the `layered-rails` skill for analysis:
- `/layered-rails:plan` — plan incremental adoption of layered patterns
- `/layered-rails:analyze` — full codebase architecture analysis
- `/layered-rails:review` — review code from a layered architecture perspective
- `/layered-rails:spec-test` — apply the specification test to evaluate layer placement
```

Alternatively, you can try to add shorter instructions to `CLAUDE.md`:

```md
Extend the list of **review agents** with the `layered-rails:layered-rails-reviewer` agent to check for architecture layer violations. Must be applicable to such commands from the compound-engineering plugin as `/workflow:review`, `/plan_review`, and similar.

Extend the list of **planning agents** with the `layered-rails:layered-rails-planner` agent to plan refactoring according to the layered design principles. Must be applicable to such commands from the compound-engineering plugin as `/workflow:plan`, `/deepen_plan`, and similar.
```

## License

MIT

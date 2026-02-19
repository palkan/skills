# palkan/skills

A collection of [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skills by [Vladimir Dementyev](https://github.com/palkan).

## Available Skills

### Layered Rails

Design and review Rails applications using layered architecture principles from the [Layered Design for Ruby on Rails Applications](https://www.packtpub.com/en-us/product/layered-design-for-ruby-on-rails-applications-9781806114221) book.

**Install:**

```
/plugin marketplace add palkan/skills
/plugin install layered-rails@palkan-skills
```

**Commands:**

| Command | Purpose |
|---------|---------|
| `/layers:analyze` | Full codebase architecture analysis |
| `/layers:analyze:callbacks` | Score model callbacks, find extraction candidates |
| `/layers:analyze:gods` | Find god objects via churn x complexity |
| `/layers:review` | Review code changes for layer violations |
| `/layers:spec-test` | Run specification test on specific files |
| `/layers:gradual [goal]` | Plan incremental adoption of layered patterns |

### Integration with compound-engineering

We recommend asking Claude itself to update the instructions for Compound Engineering to include Layred Design features according to your needs. Below you can find some examples.

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
- `/layers:gradual` — plan incremental adoption of layered patterns
- `/layers:analyze` — full codebase architecture analysis
- `/layers:review` — review code from a layered architecture perspective
- `/layers:spec-test` — apply the specification test to evaluate layer placement
```

Alternatively, you can try to add shorter instructions to `CLAUDE.md`:

```md
Extend the list of **review agents** with the `layered-rails:layered-rails-reviewer` agent to check for architecture layer violations. Must be applicable to such commands from the compound-engineering plugin as `/workflow:review`, `/plan_review`, and similar.

Extend the list of **planning agents** with the `layered-rails:layered-rails-gradual` agent to plan refactoring according to the layered design principles. Must be applicable to such commands from the compound-engineering plugin as `/workflow:plan`, `/deepen_plan`, and similar.
```

## License

MIT

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

If you use the [compound-engineering](https://github.com/EveryInc/compound-engineering-plugin) plugin, add explicit instructions to include layered-rails planning and reviewing agents. Example for your project's `CLAUDE.md`:

```md
Extend the list of **review agents** with the `layered-rails:layered-rails-reviewer` agent to check for architecture layer violations. Must be applicable to such commands from the compound-engineering plugin as `/workflow:review`, `/plan_review`, and similar.

Extend the list of **planning agents** with the `layered-rails:layered-rails-gradual` agent to plan refactoring according to the layered design principles. Must be applicable to such commands from the compound-engineering plugin as `/workflow:plan`, `/deepen_plan`, and similar.
```

## License

MIT

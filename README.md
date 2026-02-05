# Layered Rails

A Claude Code skill for designing and reviewing Rails applications using layered architecture principles.

Based on [Layered Design for Ruby on Rails Applications](https://www.packtpub.com/en-us/product/layered-design-for-ruby-on-rails-applications-9781806114221) by Vladimir Dementyev.

## Installation

In Claude Code:

```
/plugin marketplace add palkan/layered-rails-plugin
/plugin install layered-rails@palkan-layered-rails-plugin
```

Once installed, the skill is available globally. Claude will use it automatically when analyzing Rails architecture, reviewing code for layer violations, or when you mention keywords like "layered design", "specification test", etc.

## Usage

Invoke with `/layered-rails` or trigger automatically with keywords like "layered design", "layer violation", "specification test", "extract service".

### Commands

| Command | Purpose |
|---------|---------|
| `/layers:analyze` | Full codebase architecture analysis |
| `/layers:analyze:callbacks` | Score model callbacks, find extraction candidates |
| `/layers:analyze:gods` | Find god objects via churn × complexity |
| `/layers:review` | Review code changes for layer violations |
| `/layers:spec-test` | Run specification test on specific files |
| `/layers:gradual [goal]` | Plan incremental adoption of layered patterns |

### Examples

```
/layers:analyze
/layers:review
/layers:spec-test app/models/user.rb
/layers:gradual introduce authorization with Action Policy
/layers:gradual extract callbacks from Order model
```

## What It Does

- Analyzes Rails codebases for abstraction layer violations
- Identifies god objects, problematic callbacks, and missing patterns
- Reviews patches from layered architecture perspective
- Guides feature implementation using appropriate patterns
- Plans gradual adoption for existing codebases

## Architecture Layers

```
┌─────────────────────────────────────────┐
│           PRESENTATION LAYER            │
│  Controllers, Views, Channels, Mailers  │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│           APPLICATION LAYER             │
│   Service Objects, Form Objects, etc.   │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│             DOMAIN LAYER                │
│  Models, Value Objects, Domain Events   │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│          INFRASTRUCTURE LAYER           │
│  Active Record, APIs, File Storage      │
└─────────────────────────────────────────┘
```

**Core Rule:** Lower layers must never depend on higher layers.

## Integration with compound-engineering

If you use the [compound-engineering](https://github.com/EveryInc/compound-engineering-plugin) plugin, add the following to your project's `CLAUDE.md` to include layered architecture analysis in code reviews:

```markdown
## Code Review Extensions

When running `/workflows:review` on this Rails codebase, also invoke the
`layered-rails:layered-rails-reviewer` agent to check for architecture layer violations.
```

## License

MIT

---
name: layered-rails
description: Write, refactor, and review Rails code using layered architecture principles from "Layered Design for Ruby on Rails Applications". Use when writing or refactoring Rails code — models, controllers, services, jobs, mailers, policies, forms, query objects, presenters, view components, state machines, serializers, or AI/LLM features — to apply correct patterns and avoid layer violations; and when reviewing Rails code, PRs, or diffs for layer violations, fat controllers/models, anemic models, callback misuse, god objects, or specification-test failures. Triggers on "layered design", "architecture layers", "abstraction layer", "specification test", "layer violation", "fat controller/model", "god object", "anemic model", "extract service/callback/policy/concern", "service object", "form object", "policy object", "query object", "value object", "presenter", "view component", "state machine", "Active Delivery", "callback scoring", "Rails refactor/review", "Rails patterns/best practices".
allowed-tools:
  - Grep
  - Glob
  - Read
  - Task
---

# Layered Rails

Design and review Rails applications using layered architecture principles.

## Quick Start

Rails applications are organized into four architecture layers with **unidirectional data flow**:

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

See [Architecture Layers Reference](references/core/architecture-layers.md) for the full layer responsibilities and the Four Rules deep-dive.

## What this skill is for

Use this skill when:

1. **Analyzing a codebase** — apply the [architecture analysis](workflows/analyze.md) for a full audit, or zoom in with the [service-layer audit](workflows/analyze-services.md), [callback analysis](workflows/analyze-callbacks.md), or [god-object analysis](workflows/analyze-gods.md).
2. **Reviewing code changes** — run the [code review workflow](workflows/review.md) on a diff, file, or branch.
3. **Running the specification test** — use the [spec-test workflow](workflows/spec-test.md) on a single file or directory to evaluate whether code belongs in its current layer.
4. **Planning gradual adoption** — generate a phased roadmap with the [layerification plan workflow](workflows/plan.md), focused on a goal like "introduce authorization" or "decompose god objects."
5. **Planning a feature** — I'll apply the layered principles below to whichever code you're about to write.
6. **Implementing a specific pattern** — authorization, notifications, view components, AI integration, etc. — see the Pattern Catalog and Topic References below.

In Claude Code with this skill installed as a plugin (`/plugin install layered-rails@palkan-skills`), each workflow above is also reachable as a slash command — see [Slash Commands](#slash-commands). Natural-language requests ("review this file with layered-rails", "run the specification test on `app/models/order.rb`") work in any environment that has the skill loaded.

## Workflows

Reusable procedures bundled inside this skill. Read the file and apply it to the target code:

- [Architecture analysis](workflows/analyze.md) — full layered-architecture audit of a Rails codebase
- [Code review](workflows/review.md) — review a diff or file set for layer violations
- [Specification test](workflows/spec-test.md) — evaluate whether code belongs in its current layer
- [Service-layer audit](workflows/analyze-services.md) — deep audit of `app/services/` and service-like classes (per-cluster proposals, contracts, layer hygiene)
- [Callback analysis](workflows/analyze-callbacks.md) — score Active Record callbacks and find extraction candidates
- [God-object analysis](workflows/analyze-gods.md) — identify oversized models and recommend decomposition
- [Gradual layerification plan](workflows/plan.md) — incremental roadmap for adopting layered patterns

## Core Principles

### The Four Rules

1. **Unidirectional Data Flow** - Data flows top-to-bottom only
2. **No Reverse Dependencies** - Lower layers never depend on higher layers
3. **Abstraction Boundaries** - Each abstraction belongs to exactly one layer
4. **Minimize Connections** - Fewer inter-layer connections = looser coupling

### Common Violations

| Violation | Example | Fix |
|-----------|---------|-----|
| Model uses Current | `Current.user` in model | Pass user as explicit parameter |
| Service accepts request | `param :request` in service | Extract value object from request |
| Controller has business logic | Pricing calculations in action | Extract to service or model |
| Anemic models | All logic in services | Keep domain logic in models |

| Category | Reference |
|----------|-----------|
| Layer violations (Current in models, request in services, notifications in models, business logic in controllers) | [layer-violations.md](references/anti-patterns/layer-violations.md) |
| Service objects (anemic models, bag of random objects, premature abstraction) | [service-objects.md](references/anti-patterns/service-objects.md) |
| Callbacks (operation callbacks, skip callbacks, control flags) | [callbacks.md](references/anti-patterns/callbacks.md) |
| Concerns (code-slicing, overgrown) | [concerns.md](references/anti-patterns/concerns.md) |
| Helpers (HTML construction in helpers) | [helpers.md](references/anti-patterns/helpers.md) |
| Jobs (anemic jobs) | [jobs.md](references/anti-patterns/jobs.md) |
| Testing (testing wrong layer) | [testing.md](references/anti-patterns/testing.md) |

### The Specification Test

> If the specification of an object describes features beyond the primary responsibility of its abstraction layer, such features should be extracted into lower layers.

**How to apply:**
1. List responsibilities the code handles
2. Evaluate each against the layer's primary concern
3. Extract misplaced responsibilities to appropriate layers

See [Specification Test Reference](references/core/specification-test.md) for detailed guide.

## Pattern Catalog

| Pattern | Layer | Use When | Reference |
|---------|-------|----------|-----------|
| Service Object | Application | Orchestrating domain operations | [service-objects.md](references/patterns/service-objects.md) |
| Query Object | Domain | Complex, reusable queries | [query-objects.md](references/patterns/query-objects.md) |
| Form Object | Presentation | Multi-model forms, complex validation | [form-objects.md](references/patterns/form-objects.md) |
| Filter Object | Presentation | Request parameter transformation | [filter-objects.md](references/patterns/filter-objects.md) |
| Presenter | Presentation | View-specific logic, multiple models | [presenters.md](references/patterns/presenters.md) |
| Serializer | Presentation | API response formatting | [serializers.md](references/patterns/serializers.md) |
| Policy Object | Application | Authorization decisions | [policy-objects.md](references/patterns/policy-objects.md) |
| Value Object | Domain | Immutable, identity-less concepts | [value-objects.md](references/patterns/value-objects.md) |
| Collaborator Object | Domain | A slice of one model's behavior in a typed delegate | [collaborator-objects.md](references/patterns/collaborator-objects.md) |
| State Machine | Domain | States, events, transitions | [state-machines.md](references/patterns/state-machines.md) |
| Concern | Domain | Shared behavioral extraction | [concerns.md](references/patterns/concerns.md) |
| Repository | Application | **Last resort** — returning custom domain objects mapped from AR data, after AR scopes (simple) and query objects (query building) are insufficient | [repositories.md](references/patterns/repositories.md) |

### Pattern Selection Guide

**"Where should this code go?"**

| If you have... | Consider... |
|----------------|-------------|
| Complex multi-model form | Form Object |
| Request parameter filtering/transformation | Filter Object |
| View-specific formatting | Presenter |
| Complex database query used in multiple places | Query Object |
| Business operation spanning multiple models | Service Object (as waiting room) |
| Authorization rules | Policy Object |
| Multi-channel notifications | Delivery Object (Active Delivery) |

**Remember:** Services are a "waiting room" for code until proper abstractions emerge. Don't let `app/services` become a bag of random objects.

## Refactoring Scenarios

Canonical before/after transformations for the most common layerification moves. The [layerification plan workflow](workflows/plan.md) uses these as reference templates when proposing phases.

| Scenario | Goal area | Reference |
|----------|-----------|-----------|
| Extract callbacks to service | callbacks, after_create chains | [callbacks-to-service.md](examples/callbacks-to-service.md) |
| Extract authorization to policy | authorization, permissions | [authorization-to-policy.md](examples/authorization-to-policy.md) |
| Extract query logic to query object | complex scopes, reporting queries | [query-to-query-object.md](examples/query-to-query-object.md) |
| Extract Current from model | Current.* in domain | [current-from-model.md](examples/current-from-model.md) |
| Decompose god object with associated objects | god model, large User/Account | [god-object-decomposition.md](examples/god-object-decomposition.md) |
| Replace implicit state machine | timestamp-based status | [implicit-to-explicit-state-machine.md](examples/implicit-to-explicit-state-machine.md) |
| Extract view logic to presenter | template logic, formatting | [view-logic-to-presenter.md](examples/view-logic-to-presenter.md) |
| Form object for complex input | fat controllers, multi-model forms | [complex-input-to-form-object.md](examples/complex-input-to-form-object.md) |

## Slash Commands

These slash commands are available **only when this skill is installed as a Claude Code plugin** (`/plugin install layered-rails@palkan-skills`). When the skill is installed via [skills.sh](https://skills.sh/) or any other path that delivers `skills/layered-rails/` without the surrounding plugin, the commands won't be present — invoke the corresponding workflow directly (see [Workflows](#workflows)) or just ask in plain language.

| Command | Workflow | Purpose |
|---------|----------|---------|
| `/layered-rails:review` | [review](workflows/review.md) | Review code changes from a layered architecture perspective |
| `/layered-rails:spec-test` | [spec-test](workflows/spec-test.md) | Run specification test on specific files |
| `/layered-rails:analyze` | [analyze](workflows/analyze.md) | Full codebase abstraction-layer analysis |
| `/layered-rails:analyze-services` | [analyze-services](workflows/analyze-services.md) | Audit `app/services/` and service-like classes — conventions, clusters, layer hygiene, test consequences |
| `/layered-rails:analyze-callbacks` | [analyze-callbacks](workflows/analyze-callbacks.md) | Score model callbacks, find extraction candidates |
| `/layered-rails:analyze-gods` | [analyze-gods](workflows/analyze-gods.md) | Find god objects via churn × complexity |
| `/layered-rails:plan [goal]` | [plan](workflows/plan.md) | Plan gradual adoption of layered patterns |

## Topic References

For deep dives on specific topics:

| Topic | Reference |
|-------|-----------|
| Authorization (RBAC, ABAC, policies) | [authorization.md](references/topics/authorization.md) |
| Notifications (multi-channel delivery) | [notifications.md](references/topics/notifications.md) |
| View Components | [view-components.md](references/topics/view-components.md) |
| AI Integration (LLM, agents, RAG, MCP) | [ai-integration.md](references/topics/ai-integration.md) |
| Configuration | [configuration.md](references/topics/configuration.md) |
| Callbacks (scoring, extraction) | [callbacks.md](references/topics/callbacks.md) |
| Current Attributes | [current-attributes.md](references/topics/current-attributes.md) |
| Instrumentation (logging, metrics) | [instrumentation.md](references/topics/instrumentation.md) |

## Gem References

For library-specific guidance:

| Gem | Purpose | Reference |
|-----|---------|-----------|
| action_policy | Authorization framework | [action-policy.md](references/gems/action-policy.md) |
| view_component | Component framework | [view-component.md](references/gems/view-component.md) |
| anyway_config | Typed configuration | [anyway-config.md](references/gems/anyway-config.md) |
| active_delivery | Multi-channel notifications | [active-delivery.md](references/gems/active-delivery.md) |
| alba | JSON serialization | [alba.md](references/gems/alba.md) |
| workflow | State machines | [workflow.md](references/gems/workflow.md) |
| rubanok | Filter/transformation DSL | [rubanok.md](references/gems/rubanok.md) |
| active_agent | AI agent framework | [active-agent.md](references/gems/active-agent.md) |
| active_job-performs | Eliminate anemic jobs | [active-job-performs.md](references/gems/active-job-performs.md) |

## Extraction Signals

**When to extract from models:**

| Signal | Metric | Action |
|--------|--------|--------|
| God object | High churn × complexity | Decompose into concerns, delegates, or separate models |
| Operation callback | Score 1-2/5 | Extract to service or event handler |
| Code-slicing concern | Groups by artifact type | Convert to behavioral concern or extract |
| Current dependency | Model reads Current.* | Pass as explicit parameter |

**Callback Scoring:**
| Type | Score | Keep? |
|------|-------|-------|
| Transformer (compute values) | 5/5 | Yes |
| Normalizer (sanitize input) | 4/5 | Yes |
| Utility (counter caches) | 4/5 | Yes |
| Observer (side effects) | 2/5 | Maybe |
| Operation (business steps) | 1/5 | Extract |

See [Extraction Signals Reference](references/core/extraction-signals.md) for detailed guide.

## Model Organization

Recommended order within model files:

```ruby
class User < ApplicationRecord
  # 1. Gems/DSL extensions
  has_secure_password

  # 2. Associations
  belongs_to :account
  has_many :posts

  # 3. Enums
  enum :status, { pending: 0, active: 1 }

  # 4. Normalization
  normalizes :email, with: -> { _1.strip.downcase }

  # 5. Validations
  validates :email, presence: true

  # 6. Scopes
  scope :active, -> { where(status: :active) }

  # 7. Callbacks (transformers only)
  before_validation :set_defaults

  # 8. Delegations
  delegate :name, to: :account, prefix: true

  # 9. Public methods
  def full_name = "#{first_name} #{last_name}"

  # 10. Private methods
  private

  def set_defaults
    self.locale ||= I18n.default_locale
  end
end
```

## Success Checklist

Well-layered code:

- [ ] No reverse dependencies (lower layers don't depend on higher)
- [ ] Models don't access Current attributes
- [ ] Services don't accept request objects
- [ ] Controllers are thin (HTTP concerns only)
- [ ] Domain logic lives in models, not services
- [ ] Callbacks score 4+ or are extracted
- [ ] Concerns are behavioral, not code-slicing
- [ ] Abstractions don't span multiple layers
- [ ] Tests verify appropriate layer responsibilities

## Guidelines

- **Use domain language** - Name models after business concepts (Participant, not User; Cloud, not GeneratedImage)
- **Patterns before abstractions** - Let code age before extracting; premature abstraction is worse than duplication
- **Services as waiting room** - Don't let `app/services` become permanent residence for code
- **Explicit over implicit** - Prefer explicit parameters over Current attributes
- **Extraction thresholds** - Consider extraction when methods exceed 15 lines or call external APIs

---
name: layered-rails
description: Design and review Rails applications using layered architecture principles from "Layered Design for Ruby on Rails Applications". Use when analyzing Rails codebases, reviewing PRs for architecture violations, planning feature implementations, or implementing patterns like authorization, view components, or AI integration. Triggers on "layered design", "architecture layers", "abstraction", "specification test", "layer violation", "extract service", "fat controller", "god object".
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

## What Would You Like To Do?

1. **Analyze codebase** - Run `/layers:analyze` for full analysis or `/layers:analyze:callbacks`, `/layers:analyze:gods` for specific checks
2. **Review code changes** - Run `/layers:review` for layered architecture review
3. **Run specification test** - Run `/layers:spec-test` on specific files
4. **Plan gradual adoption** - Run `/layers:gradual [goal]` to plan incremental layerification
5. **Plan feature implementation** - I'll guide you using layered principles
6. **Implement specific pattern** - I'll help with authorization, notifications, view components, AI integration, etc.

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

See [Anti-Patterns Reference](references/anti-patterns.md) for complete list.

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
| State Machine | Domain | States, events, transitions | [state-machines.md](references/patterns/state-machines.md) |
| Concern | Domain | Shared behavioral extraction | [concerns.md](references/patterns/concerns.md) |

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

## Commands Reference

| Command | Purpose |
|---------|---------|
| `/layers:review` | Review code changes from layered architecture perspective |
| `/layers:spec-test` | Run specification test on specific files |
| `/layers:analyze` | Full codebase abstraction layer analysis |
| `/layers:analyze:callbacks` | Score model callbacks, find extraction candidates |
| `/layers:analyze:gods` | Find God objects via churn × complexity |
| `/layers:gradual [goal]` | Plan gradual adoption of layered patterns |

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

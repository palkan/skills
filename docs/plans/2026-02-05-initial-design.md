# Layered Rails Plugin: Initial Design Plan

## Overview

Create a Claude Code skill/plugin based on the book "Layered Design for Ruby on Rails Applications" (2nd Edition). The plugin helps developers build maintainable Rails applications through proper abstraction layers, architectural principles, and pattern-based refactoring.

## Use Cases

1. **Planning Features** - Guide implementation using layered architecture principles
2. **Reviewing Code** - Evaluate patches against layered design constraints
3. **Analyzing Codebases** - Identify maintainability issues and extraction opportunities
4. **Implementing Patterns** - Provide guidance on specific patterns (authorization, view components, AI integration, etc.)

## Plugin vs Skill Decision

**Recommendation: Start with a Skill, evolve to Plugin if needed.**

A skill provides:
- Single SKILL.md entry point with progressive disclosure
- Reference files for detailed content
- Can include agent definitions (reviewer, analyzer)
- Slash commands via intake routing

A full plugin adds:
- Multiple independent skills
- Complex agent orchestration
- Custom workflows (plan/work/review)

Since this integrates with compound-engineering's existing workflows, a skill with agents is sufficient.

## Architecture

```
layered-rails/
├── SKILL.md                              # Main entry point (~500 lines)
├── agents/
│   └── layered-rails-reviewer.md         # Code review agent
├── references/
│   ├── core/
│   │   ├── architecture-layers.md        # Four layers, rules, mapping
│   │   ├── specification-test.md         # Detailed guide with examples
│   │   └── extraction-signals.md         # When to extract (churn×complexity, callback scoring)
│   ├── patterns/
│   │   ├── service-objects.md            # Application layer orchestration
│   │   ├── query-objects.md              # Complex query encapsulation
│   │   ├── form-objects.md               # Multi-model forms, wizards
│   │   ├── filter-objects.md             # Parameter transformation
│   │   ├── presenters.md                 # View-specific logic
│   │   ├── serializers.md                # API response formatting
│   │   ├── policy-objects.md             # Authorization rules
│   │   ├── value-objects.md              # Immutable domain concepts
│   │   ├── state-machines.md             # States, events, transitions
│   │   ├── concerns.md                   # Behavioral extraction
│   │   └── repositories.md               # Data access abstraction (advanced)
│   ├── topics/
│   │   ├── authorization.md              # RBAC, ABAC, Action Policy
│   │   ├── notifications.md              # Multi-channel delivery
│   │   ├── view-components.md            # Component-based views
│   │   ├── ai-integration.md             # LLM, agents, RAG, MCP
│   │   ├── configuration.md              # Settings, secrets, Anyway Config
│   │   ├── callbacks.md                  # Scoring, when to extract
│   │   ├── current-attributes.md         # Global state pitfalls
│   │   └── instrumentation.md            # Logging, metrics, events
│   ├── gems/
│   │   ├── action-policy.md              # Authorization framework
│   │   ├── view-component.md             # Component library
│   │   ├── anyway-config.md              # Typed configuration
│   │   ├── active-delivery.md            # Multi-channel notifications
│   │   ├── rubanok.md                    # Filter/transformation DSL
│   │   ├── alba.md                       # JSON serialization
│   │   ├── workflow.md                   # State machine library
│   │   └── active-agent.md               # AI agent framework
│   └── anti-patterns.md                  # Common violations with fixes
├── commands/
│   ├── spec-test.md                      # /layers:spec-test
│   ├── analyze.md                        # /layers:analyze
│   ├── analyze-callbacks.md              # /layers:analyze:callbacks
│   ├── analyze-gods.md                   # /layers:analyze:gods
│   └── review.md                         # /layers:review (standalone)
└── examples/
    └── refactoring-scenarios.md          # Before/after examples
```

## SKILL.md Structure

### Frontmatter

```yaml
---
name: layered-rails
description: Design and review Rails applications using layered architecture principles. Use when analyzing Rails codebases, reviewing PRs for architecture violations, planning feature implementations, or implementing patterns like authorization, view components, or AI integration. Triggers on "layered design", "architecture layers", "abstraction", "specification test", "layer violation".
allowed-tools:
  - Grep
  - Glob
  - Read
  - Task
---
```

### Sections

1. **Quick Start** - 30-second orientation to the four architecture layers
2. **Intake Menu** - Route to specific use cases:
   - Analyze codebase (`/layers:analyze`)
   - Review code changes (`/layers:review`)
   - Plan feature implementation
   - Implement specific pattern
   - Run specification test (`/layers:spec-test`)
3. **Core Principles** - The four rules (from Chapter 5)
4. **Pattern Catalog** - Quick reference to all patterns with grades
5. **Commands Reference** - Available `/layers:*` commands
6. **Success Criteria** - Checklist for well-layered code

## Agent: Layered Rails Reviewer

Based on the kieran-rails-reviewer pattern, applying book principles without persona.

### Philosophy

The reviewer embodies the book's philosophy:
- Favor extraction over complication
- Patterns before abstractions (let code age)
- Services as waiting room, not final destination
- Domain logic stays in models (avoid anemic models)
- Explicit over implicit (parameters over Current)
- Lower layers never depend on higher layers

### Review Principles

1. **Layer Boundary Enforcement**
   - No reverse dependencies (models → Current, services → request)
   - Abstraction layers don't cross architecture boundaries
   - Data flows top-to-bottom only

2. **Specification Test Application**
   - Do tests verify appropriate responsibilities?
   - Would extracting logic enable simpler tests?
   - Is test complexity proportional to layer?

3. **Extraction Signal Detection**
   - Callback scoring (transformers OK, operations extract)
   - Concern health (behavioral vs code-slicing)
   - God object indicators (churn × complexity)

4. **Current Attributes Audit**
   - Models depending on Current = violation
   - Background job context loss risks
   - Suggest explicit parameter passing

5. **Service Object Critique**
   - Prevent anemic models
   - Enforce conventions (base class, naming, interface)
   - Identify decomposition opportunities

6. **Abstraction Assessment**
   - Right pattern for the problem?
   - Premature abstraction warning
   - Pattern before abstraction principle

### Review Methodology

```
1. Identify architecture layer(s) touched by changes
2. Check for layer violations:
   - Reverse dependencies
   - Current usage in wrong layers
   - Presentation logic in domain
3. Apply specification test:
   - List responsibilities in changed code
   - Evaluate against layer's primary concern
   - Flag misplaced responsibilities
4. Assess abstractions:
   - Is this the right pattern?
   - Is there a simpler solution?
   - Does it follow conventions?
5. Check for extraction signals:
   - Low-scoring callbacks
   - Overgrown concerns
   - Fat controllers/models
6. Provide feedback:
   - Specific, actionable
   - Reference book principles
   - Include code examples for fixes
```

### Output Format

```markdown
## Layered Rails Review

### Layer Analysis
- Files touch: [Presentation, Application, Domain]
- Data flow: [OK / Violation detected]

### Issues

🔴 **Critical: Layer Violation**
[Description with code reference]

⚠️ **Warning: Extraction Signal**
[Description with recommendation]

💡 **Suggestion: Improvement Opportunity**
[Description with alternative approach]

### Summary
[Brief assessment with priorities]
```

## Commands

### /layers:spec-test

Run the specification test on a file or component to evaluate layer responsibility alignment.

**Process:**
1. Read the target file(s)
2. Identify the architecture layer
3. List responsibilities the code handles
4. Evaluate each responsibility against layer's primary concern
5. Flag responsibilities that belong elsewhere
6. Suggest extraction targets

**Output:**
```markdown
## Specification Test: PostsController

**Layer:** Presentation
**Primary Responsibility:** HTTP request/response handling

| Responsibility | Belongs Here? | Suggested Location |
|----------------|---------------|-------------------|
| Authentication | ✓ | - |
| Parameter parsing | ✓ | - |
| Event type routing | ✗ | Application layer (Service) |
| User lookup | ✗ | Domain layer (Model) |
| Record creation | ✗ | Domain layer (Model) |

**Recommendation:** Extract event handling to `HandleEventService`
```

---

### /layers:analyze

Comprehensive abstraction layer analysis of a Rails codebase.

**Process:**
1. Scan `app/` directory structure
2. Identify custom abstraction layers (services, presenters, etc.)
3. Sample files from each layer
4. Check for layer violations
5. Assess abstraction health (conventions, coupling)
6. Generate report with priorities

**Output:**
```markdown
## Layers Analysis: myapp

### Abstraction Layers Detected

| Layer | Location | Files | Health |
|-------|----------|-------|--------|
| Services | app/services/ | 47 | ⚠️ No conventions |
| Presenters | app/presenters/ | 12 | ✓ Good |
| Query Objects | app/queries/ | 8 | ✓ Good |

### Violations Found

1. **Current in Models** (High Priority)
   - `app/models/post.rb:45` - `Current.user` in callback
   - `app/models/comment.rb:23` - `Current.account` in scope

2. **Fat Controllers** (Medium Priority)
   - `app/controllers/api/v1/orders_controller.rb` - 200 lines

### Recommendations

1. Establish service object conventions (see reference)
2. Extract Current usage to explicit parameters
3. Apply specification test to OrdersController
```

---

### /layers:analyze:callbacks

Score model callbacks using the 5-point extraction system from Chapter 4.

**Scoring System:**
| Type | Score | Description |
|------|-------|-------------|
| Transformer | 5/5 | Compute/default required values (safe) |
| Normalizer | 4/5 | Sanitize user input (use `.normalizes` API) |
| Utility | 3/5 | Counter caches, cache busting |
| Observer | 2/5 | Side effects after commit |
| Operation | 1/5 | Business process steps (extract!) |

**Process:**
1. Find all `before_*`, `after_*`, `around_*` callbacks in models
2. Classify each callback by type
3. Score and flag low-scoring callbacks
4. Suggest extraction strategies

**Output:**
```markdown
## Callback Audit: app/models/

### Summary
- Total callbacks: 23
- Average score: 3.2/5
- Extraction candidates: 5

### Low-Scoring Callbacks

| Model | Callback | Type | Score | Recommendation |
|-------|----------|------|-------|----------------|
| User | after_create :send_welcome | Operation | 1/5 | Extract to controller/service |
| Order | after_save :update_inventory | Operation | 1/5 | Use event-driven approach |
| Post | after_commit :notify_subscribers | Observer | 2/5 | Consider Active Delivery |

### Extraction Guide
See [Callbacks Reference](references/topics/callbacks.md) for extraction patterns.
```

---

### /layers:analyze:gods

Identify potential God objects using churn × complexity metrics (Chapter 2).

**Process:**
1. Calculate complexity for each model (method count, LOC, dependencies)
2. Get git churn data (change frequency)
3. Plot churn × complexity quadrant
4. Flag high-churn, high-complexity models
5. Suggest decomposition strategies

**Output:**
```markdown
## God Object Scan: app/models/

### Quadrant Analysis

```
High Complexity
      │
      │  ⚠️ User        ⚠️ Order
      │     (87,34)        (65,28)
      │
      │  Post           Comment
      │     (45,12)        (23,8)
      │
      └──────────────────────────── High Churn
```

### Top Candidates

| Model | Complexity | Churn | Risk | Primary Issues |
|-------|------------|-------|------|----------------|
| User | 87 methods | 34 changes | 🔴 High | Authentication + Profile + Notifications |
| Order | 65 methods | 28 changes | 🔴 High | State machine + Pricing + Fulfillment |

### Decomposition Suggestions

**User model:**
- Extract `User::Authentication` concern (or delegate object)
- Extract `User::NotificationPreferences` (separate model)
- Extract `User::ProfilePresenter` for view logic

See [God Objects Reference](references/core/extraction-signals.md#god-objects) for patterns.
```

---

### /layers:review

Standalone code review from Layered Rails principles (simplified, no compound-engineering required).

**Process:**
1. Read changed files (from git diff or provided paths)
2. Apply layer boundary checks
3. Run specification test mentally
4. Check for common violations
5. Provide actionable feedback

**Output:**
```markdown
## Layered Rails Review

### Files Reviewed
- app/controllers/orders_controller.rb
- app/models/order.rb
- app/services/process_order_service.rb

### Issues Found

🔴 **Layer Violation** (orders_controller.rb:45)
```ruby
# Controller depends on infrastructure details
order.stripe_customer_id = Stripe::Customer.create(email: order.email).id
```
**Fix:** Move Stripe integration to service or domain layer.

⚠️ **Specification Test Concern** (orders_controller.rb:50-75)
Business logic in controller: inventory checks, pricing calculations.
**Fix:** Extract to `ProcessOrderService` or `Order` model methods.

⚠️ **Anemic Model Risk** (process_order_service.rb)
Service contains logic that belongs in Order model:
- `calculate_total` - domain logic
- `validate_inventory` - domain invariant
**Fix:** Move to Order model, keep orchestration in service.

### Recommendations

1. Apply specification test to `OrdersController`
2. Move domain logic from service to model
3. Wrap Stripe API behind domain interface

See [Layered Architecture](references/core/architecture-layers.md) for principles.
```

## Reference Files

### architecture-layers.md

Condensed from Chapter 5:
- Four layers diagram
- Core rules with examples
- Layer mapping for Rails
- Common violations

### abstraction-patterns.md

Pattern catalog from Chapters 6-12:

| Pattern | Layer | Use When | Grade |
|---------|-------|----------|-------|
| Service Object | Application | Orchestrating domain operations | CONTEXT-DEPENDENT |
| Query Object | Domain | Complex, reusable queries | GOOD |
| Form Object | Presentation | Multi-model forms, complex validation | GOOD |
| Filter Object | Presentation | Request parameter transformation | GOOD |
| Presenter | Presentation | View-specific logic, multiple models | GOOD |
| Policy Object | Application | Authorization decisions | GOOD |
| Value Object | Domain | Immutable, identity-less concepts | GOOD |
| Repository | Infrastructure | Decoupling from ORM (rarely needed) | CONTEXT-DEPENDENT |

Each pattern links to detailed reference.

### extraction-signals.md

When to extract (from Chapters 2-4):

**Callback Scoring System:**
| Criteria | Score |
|----------|-------|
| Transformer (prepending/normalizing data) | 5/5 |
| Observer (side effects after commit) | 3/5 |
| Invariant (enforcing business rules) | 2/5 |
| Operation (business logic disguised as callback) | 1/5 |

**God Object Identification:**
- Churn × Complexity metrics
- Methods that don't use model data
- Methods with many dependencies

**Concern Extraction Signals:**
- Shared behavior across models
- NOT: code-slicing (splitting model into files)

### anti-patterns.md

Common violations with fixes:

1. **Current in Models** - Replace with explicit parameters
2. **Request Objects in Services** - Extract value objects
3. **Fat Controllers** - Apply specification test
4. **Code-Slicing Concerns** - Use concerns for behavior, not file size
5. **Anemic Models** - Keep domain logic in models
6. **Premature Abstraction** - Wait for patterns to emerge
7. **Service Bag of Objects** - Establish conventions

### specification-test.md

Deep dive on the specification test:
- Philosophy
- Step-by-step process
- Examples for each layer
- Cost consideration (test complexity)

## Integration with Compound Engineering

This skill integrates with existing compound-engineering workflows while also providing standalone capabilities.

### With Compound Engineering

| Workflow | Integration |
|----------|-------------|
| `/plan` | Layered principles guide feature design; pattern references inform approach |
| `/review` | `layered-rails-reviewer` included in review agent pool |
| `/work` | Pattern references available during implementation |

The skill doesn't duplicate compound-engineering's plan/work/review—it extends them.

### Standalone Commands

For users without compound-engineering or wanting quick access:

| Command | Purpose |
|---------|---------|
| `/layers:review` | Focused review from layered principles (no full compound workflow) |
| `/layers:spec-test` | Run specification test on specific files |
| `/layers:analyze` | Full codebase analysis |
| `/layers:analyze:callbacks` | Score callbacks, find extraction candidates |
| `/layers:analyze:gods` | Find potential God objects |

### Reviewer Agent Registration

The `layered-rails-reviewer` agent can be registered with compound-engineering's review workflow:

```yaml
# In compound-engineering config or plugin registration
review_agents:
  - layered-rails-reviewer  # Added to review agent pool
```

When `/review` is invoked, compound-engineering orchestrates multiple review agents. `layered-rails-reviewer` provides layered architecture perspective alongside other reviewers (Kieran, DHH, etc.).

## Gem Recommendations

The skill includes gem recommendations (not prescriptive, but "consider these").

### Gems with Dedicated Reference Files

These gems have standalone reference files in `references/gems/`:

| Gem | Purpose | Reference |
|-----|---------|-----------|
| action_policy | Authorization framework | `gems/action-policy.md` |
| view_component | Component framework | `gems/view-component.md` |
| anyway_config | Typed configuration | `gems/anyway-config.md` |
| active_delivery | Multi-channel notifications | `gems/active-delivery.md` |
| alba | JSON serialization | `gems/alba.md` |
| workflow | State machines | `gems/workflow.md` |
| rubanok | Filter/transformation DSL | `gems/rubanok.md` |
| active_agent | AI agent framework | `gems/active-agent.md` |

### Gems Inlined in Topic References

These gems are documented within their relevant topic files:

| Gem | Topic Reference |
|-----|-----------------|
| dry-initializer, dry-monads | `patterns/service-objects.md` |
| arel-helpers | `patterns/query-objects.md` |
| store_model | `topics/notifications.md` (preferences) |
| phlex, keynote | `topics/view-components.md` |
| typelizer | `patterns/serializers.md` |
| ruby_llm, fast-mcp | `topics/ai-integration.md` |
| yabeda | `topics/instrumentation.md` |
| attractor, callback_hell | `core/extraction-signals.md` |
| database_consistency | `patterns/value-objects.md` (validations) |
| neighbor, pgvector | `topics/ai-integration.md` (RAG) |

---

## Content Sourcing

### Reference Files Mapping

| Reference | Primary Source(s) |
|-----------|-------------------|
| **Core** | |
| architecture-layers.md | Chapter 5: `05-layered-architecture.md` |
| specification-test.md | Chapter 5: `05-layered-architecture.md` (specification test section) |
| extraction-signals.md | Chapter 2: `02-god-objects.md`, Chapter 4: `04-callbacks.md` |
| **Patterns** | |
| service-objects.md | Chapter 5: `05-service-objects.md` |
| query-objects.md | Chapter 6: `06-query-objects.md` |
| form-objects.md | Chapter 8: `08-form-objects.md`, `08-wizard-forms.md` |
| filter-objects.md | Chapter 8: `08-filter-objects.md` |
| presenters.md | Chapter 9: `09-presenters.md` |
| serializers.md | Chapter 9: `09-serializers.md` |
| policy-objects.md | Chapter 10: `10-authorization.md` |
| value-objects.md | Chapter 2: `02-active-record-active-model.md` (composed_of) |
| state-machines.md | Chapter 7: `07-state-machines-workflows.md` |
| concerns.md | Chapter 4: `04-concerns.md` |
| repositories.md | Chapter 6: `06-repositories.md` |
| **Topics** | |
| authorization.md | Chapter 10: `10-authorization.md` |
| notifications.md | Chapter 11: `11-notifications.md`, `11-notification-preferences.md` |
| view-components.md | Chapter 12: `12-view-components.md`, `12-view-components-advanced.md` |
| ai-integration.md | Chapter 13: `13-ai-agents.md`, `13-ai-agents-production.md`, `13-ai-rag.md`, `13-ai-mcp.md` |
| configuration.md | Chapter 14: `14-configuration.md` |
| callbacks.md | Chapter 4: `04-callbacks.md` |
| current-attributes.md | Chapter 4: `04-current-attributes.md` |
| instrumentation.md | Chapter 15: `15-logging.md`, `15-instrumentation.md` |
| **Gems** (8 standalone files) | |
| action-policy.md | Chapter 10 + official docs |
| view-component.md | Chapter 12 + official docs |
| anyway-config.md | Chapter 14 + official docs |
| active-delivery.md | Chapter 11 + official docs |
| alba.md | Chapter 9 + official docs |
| workflow.md | Chapter 7 + official docs |
| rubanok.md | Chapter 8 + official docs |
| active-agent.md | Chapter 13 + official docs |

### From Previous STYLE.md

Rules to incorporate:
- "Use domain language" (Participant vs User, Cloud vs GeneratedImage)
- Model organization order (gems, associations, enums, validations, scopes, callbacks, delegations, methods)
- Namespacing conventions (`Module::ClassName`)
- Extraction thresholds (15+ lines → namespaced class)

## Decisions Made

| Question | Decision |
|----------|----------|
| Skill name | `layered-rails` |
| Reviewer persona | No persona; use "Layered Rails principles" when applicable |
| Technology stack | Include gem recommendations (not "approved" but "consider") |
| Integration | Works as compound-engineering extension + standalone commands |
| Automation level | Mid-to-high |
| Code examples | Inline examples in references |
| Reference granularity | Topic-based + gem-specific files |

## Implementation Phases

### Phase 1: Core Skill (MVP)

**Goal:** Working skill with basic review and analysis capabilities.

1. Create directory structure
2. Create SKILL.md with:
   - Intake menu (analyze, review, plan, implement)
   - Core principles quick reference
   - Pattern catalog overview
   - Command reference
3. Create core references:
   - `references/core/architecture-layers.md`
   - `references/core/specification-test.md`
   - `references/anti-patterns.md`
4. Create reviewer agent:
   - `agents/layered-rails-reviewer.md`
5. Create primary commands:
   - `commands/spec-test.md` (`/layers:spec-test`)
   - `commands/review.md` (`/layers:review`)
6. Test with real Rails codebase

**Deliverables:** Functional skill for basic review and specification test.

### Phase 2: Pattern References

**Goal:** Complete pattern catalog with inline examples.

1. Create pattern references:
   - `references/patterns/service-objects.md`
   - `references/patterns/query-objects.md`
   - `references/patterns/form-objects.md`
   - `references/patterns/filter-objects.md`
   - `references/patterns/presenters.md`
   - `references/patterns/serializers.md`
   - `references/patterns/policy-objects.md`
   - `references/patterns/value-objects.md`
   - `references/patterns/state-machines.md`
   - `references/patterns/concerns.md`
   - `references/patterns/repositories.md`
2. Add extraction signals reference:
   - `references/core/extraction-signals.md`

**Deliverables:** Complete pattern catalog for implementation guidance.

### Phase 3: Topic References

**Goal:** Deep dives on specific topics.

1. Create topic references:
   - `references/topics/authorization.md`
   - `references/topics/notifications.md`
   - `references/topics/view-components.md`
   - `references/topics/ai-integration.md`
   - `references/topics/configuration.md`
   - `references/topics/callbacks.md`
   - `references/topics/current-attributes.md`
   - `references/topics/instrumentation.md`

**Deliverables:** Topic-specific guidance for common Rails concerns.

### Phase 4: Analysis Commands

**Goal:** Automated codebase analysis commands.

1. Create analysis commands:
   - `commands/analyze.md` (`/layers:analyze`)
   - `commands/analyze-callbacks.md` (`/layers:analyze:callbacks`)
   - `commands/analyze-gods.md` (`/layers:analyze:gods`)
2. Integrate with compound-engineering workflows

**Deliverables:** Full suite of automated analysis tools.

### Phase 5: Gem References

**Goal:** Library-specific guidance for 8 key gems.

1. Create gem references:
   - `references/gems/action-policy.md`
   - `references/gems/view-component.md`
   - `references/gems/anyway-config.md`
   - `references/gems/active-delivery.md`
   - `references/gems/alba.md`
   - `references/gems/workflow.md`
   - `references/gems/rubanok.md`
   - `references/gems/active-agent.md`
2. Add refactoring examples:
   - `examples/refactoring-scenarios.md`

**Deliverables:** Library-specific implementation guidance.

## Success Criteria

A well-functioning skill:

**Core Functionality:**
- [ ] Identifies layer violations in code reviews
- [ ] Guides pattern selection for common problems
- [ ] Applies specification test to evaluate responsibilities
- [ ] Detects extraction opportunities (callbacks, concerns, fat controllers)
- [ ] Provides actionable refactoring suggestions with book references

**Integration:**
- [ ] Works as compound-engineering extension (invoked during /review, /plan)
- [ ] Provides standalone commands (/layers:review, /layers:spec-test, /layers:analyze)
- [ ] Mid-to-high automation (minimal prompting for clarification)

**Quality:**
- [ ] Under 500 lines for SKILL.md with progressive disclosure
- [ ] Inline code examples in all references
- [ ] Gem recommendations are "consider" not "must use"
- [ ] References book principles without being preachy

## Next Steps

1. ✅ Get feedback on this plan
2. ✅ Answer open questions
3. Create directory structure
4. **Phase 1:** Write SKILL.md, core references, reviewer agent, primary commands
5. Test with real codebase (your Rails projects)
6. Iterate based on usage
7. **Phase 2-5:** Expand references and commands based on priority

## Open Items

- [ ] Decide on compound-engineering integration specifics (how reviewer is invoked)
- [ ] Identify test Rails codebases for validation
- [ ] Prioritize gem references based on your most-used libraries

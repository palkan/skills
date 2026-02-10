# /layers:analyze

Comprehensive layered architecture analysis of a Rails codebase or specific directory.

## Purpose

Evaluate how well the codebase follows layered architecture principles, identifying:
- Layer violations
- Abstraction opportunities
- God objects
- Callback concerns
- Missing patterns

## Usage

```
/layers:analyze [path]
```

- Without path: Analyzes entire `app/` directory
- With path: Analyzes specific directory (e.g., `app/models`, `app/services`)

## Analysis Process

### 1. Structural Assessment

Map existing code to layers:

```
Presentation Layer:
  - app/controllers/
  - app/views/
  - app/components/
  - app/helpers/
  - app/presenters/

Application Layer:
  - app/services/
  - app/operations/
  - app/policies/
  - app/forms/
  - app/queries/
  - app/deliveries/

Domain Layer:
  - app/models/

Infrastructure Layer:
  - app/mailers/
  - app/jobs/
  - app/channels/
  - app/configs/
```

**Service Layer Structural Assessment** (when `app/services/` exists):

- **Organization check:**
  - Flat vs namespaced? Count top-level files vs files in subdirectories
  - What naming patterns exist? (`*Creator`, `*Updater`, `*Query`, `*Form`, `*Processor`, `*Handler`)
  - Are there groups that suggest dedicated abstractions? (e.g., many query-like services → introduce query objects)

- **"Waiting room" assessment** (see [Service Objects](../skills/layered-rails/references/patterns/service-objects.md)):
  - Services should decompose into specialized patterns as they accumulate
  - A flat `app/services/` with many files is a "bag of random objects" risk
  - Check if services follow consistent conventions (base class, interface, naming)

- **Scoring guidance:**
  - Never label a large service directory (100+ files) as "Strong" or "Excellent" without verifying organization
  - A well-namespaced service layer with clear decomposition patterns can be healthy even at high counts
  - A flat `app/services/` with 200+ files is a red flag regardless of count
  - Produce specific assessments like: "271 services across 15 namespaces — well-organized but consider extracting 23 query-like services to `app/queries/`"

### 2. Layer Violation Detection

Search for common violations:

**Upward Dependencies in Models**

Search for ALL types of upward-layer invocations from models:

```bash
# Mailer/Delivery calls
grep -rn "Mailer\.\|Delivery\.\|deliver_later\|deliver_now" app/models/

# Direct service invocations
grep -rn "Service\.\|Service\.call\|Service\.new" app/models/

# Job enqueuing from models
grep -rn "perform_later\|perform_async\|perform_in\|perform_at" app/models/

# HTTP/API client calls
grep -rn "HTTP\.\|Faraday\.\|RestClient\.\|Net::HTTP\|HTTParty\.\|\.post(\|\.get(" app/models/
```

**Only include in report if violations are found.** Omit this section entirely if no upward dependencies exist in models.

**Current in Models**

Search for `Current\.` in models, then classify each usage:

- **Acceptable patterns** (do not report as violations):
  - AR attribute defaults: `default: -> { Current.user }`, `default: -> { Current.account }`
  - Audit logging: `self.updated_by = Current.user` in `before_save`
  - Context restoration: `Current.set(...)` blocks
  - Overridable default arguments: `def something(user: Current.user)`

- **Concerning patterns** (report as violations):
  - Hardcoded non-overridable access in business logic: `Current.user.admin?`
  - Business logic decisions: `if Current.organization.premium?`
  - Query building: `where(org: Current.organization)`, `scope` using Current
  - Authorization checks: `Current.user.can_do_something?`

```bash
grep -rn "Current\." app/models/
```

**Reporting rules:**
- If only acceptable patterns found → mention briefly: "Current usage follows acceptable patterns (AR defaults, audit logging)"
- If concerning patterns found → report those specifically as violations
- If no Current usage → omit entirely

See [Current Attributes](../skills/layered-rails/references/topics/current-attributes.md) for the full "Where Current IS Appropriate" table.

**Request Objects in Services**
```bash
# VIOLATION: Application layer accessing presentation
grep -r "request\." app/services/
grep -r "params\[" app/services/
```

**Business Logic in Controllers**
```ruby
# VIOLATION: Controllers doing more than coordination
# Look for: complex conditionals, multiple model operations, business rules
```

**Authorization in Models**
```bash
# VIOLATION: Domain layer checking permissions
grep -r "can_.*\?" app/models/
grep -r "\.admin\?" app/models/
```

For each violation found:
1. Trace the call chain (who calls this code?)
2. Find existing orchestrators (services, forms, controllers)
3. Recommend moving side effects to the orchestrator
4. If no orchestrator exists, list options (service, form, controller)

### 3. God Object Identification

Using churn × complexity heuristic:

```bash
# Find most-changed files
git log --format=format: --name-only --since="6 months ago" app/models/ | \
  sort | uniq -c | sort -rn | head -20

# Cross-reference with file size/complexity
wc -l app/models/*.rb | sort -rn | head -20
```

Candidates scoring high on both metrics are god object suspects.

### 4. Callback Analysis

Score all callbacks in models:

| Score | Assessment |
|-------|------------|
| 5/5 | Transformer - keep |
| 4/5 | Maintainer - keep |
| 3/5 | Timestamp - acceptable |
| 2/5 | Background trigger - consider extracting |
| 1/5 | Operation - should extract |

### 5. Coupling Analysis via Specification Test

Apply the [specification test](../skills/layered-rails/references/core/specification-test.md) to the top 3-5 suspicious entities identified during analysis:

**Pick candidates from:**
- Controllers with complex actions (business logic detected in Step 2)
- Jobs with non-trivial logic (more than delegation)
- Large services (high line count or many dependencies)
- Models with mixed-layer responsibilities

**For each candidate:**

1. List every responsibility the entity handles
2. Categorize each responsibility by layer (Presentation / Application / Domain / Infrastructure)
3. Identify misplaced responsibilities — anything outside the entity's primary layer

**Report format:**

```
Entity: OrdersController#create
  - Parse parameters         → Presentation ✓
  - Authenticate user        → Presentation ✓
  - Validate inventory       → Domain ✗ (extract to model)
  - Calculate pricing        → Domain ✗ (extract to model)
  - Send confirmation email  → Infrastructure ✗ (extract to service)
  Recommendation: Extract domain logic to Order model, orchestrate via CreateOrderService
```

Keep this focused — apply to the most suspicious entities only, not exhaustively. Omit this section if no candidates warrant the specification test.

### 6. Concern Health Check

For each concern, verify:
- [ ] Used by multiple models (not single-model organization)
- [ ] Methods are cohesively related
- [ ] No hidden dependencies on including class
- [ ] Doesn't recreate callback problems

### 7. Anti-Pattern Detection

Check for common anti-patterns (see [Anti-Patterns Reference](../skills/layered-rails/references/anti-patterns.md)):

**Anemic Jobs**
```bash
# Find job files with single-line perform methods
grep -l "def perform" app/jobs/*.rb | xargs -I{} sh -c \
  'echo "=== {} ===" && grep -A5 "def perform" {}'
```

Signal: Job's `perform` is single delegation to model method. Fix: Use `active_job-performs` gem.

**Helper HTML Construction**
```bash
# Find helpers building HTML programmatically
grep -r "tag\.\|content_tag" app/helpers/
```

Signal: Heavy `tag.div`, `tag.button` chains. Fix: Extract to ViewComponent.

**Callback Control Flags**
```bash
# Find skip flags in models
grep -r "attr_accessor :skip_" app/models/
grep -r "unless: :skip_" app/models/
```

Signal: Virtual attributes to bypass callbacks. Fix: Extract callbacks to explicit service calls.

For each anti-pattern, reference the specific fix in the anti-patterns documentation.

### 8. Pattern Gap Analysis

Identify missing abstractions:

- **No policies?** Check for authorization in controllers/models
- **No form objects?** Check for complex params handling
- **No query objects?** Check for long scope chains
- **No presenters?** Check for view logic in models

## Reporting Principles

**Conditional reporting:** Only include a section in the report if there are meaningful findings. Do not report "No violations found" for every check — omit empty sections entirely. Focus the report on what matters for this specific codebase.

## Output Format

```markdown
# Layered Architecture Analysis

## Summary
- Overall health: [Good/Fair/Needs Attention/Critical]
- Layer compliance: [percentage]
- God object candidates: [count]
- Callback concerns: [count]
- Anti-patterns detected: [count]

## Layer Violations

### Critical
1. `app/models/user.rb:45` - `Current.user.admin?` used for business logic decision
   - Impact: Domain coupled to request context for authorization
   - Fix: Move to policy object or pass user explicitly through service layer

### Major
...

### Minor
...

## God Object Candidates

| Model | Lines | Churn | Complexity | Recommendation |
|-------|-------|-------|------------|----------------|
| User | 450 | High | High | Extract concerns, services |
| Order | 380 | Medium | High | State machine, form objects |

## Callback Concerns

| File | Callback | Score | Recommendation |
|------|----------|-------|----------------|
| user.rb | after_create :send_welcome | 1/5 | Extract to service |
| post.rb | before_save :update_slug | 5/5 | Keep |

## Anti-Patterns

| Type | Location | Fix |
|------|----------|-----|
| Anemic Job | `NotifyRecipientsJob` | Use `performs` gem |
| Helper HTML | `messages_helper.rb` | Extract to ViewComponent |

See [Anti-Patterns Reference](../skills/layered-rails/references/anti-patterns.md) for details.

## Pattern Recommendations

### Immediate Actions
1. Extract `User` authentication logic to `AuthenticateUser` service
2. Move `Order#can_cancel?` authorization to `OrderPolicy`
3. Replace `Post` callbacks with `PublishPost` service

### Future Improvements
1. Add form objects for multi-model forms
2. Consider query objects for reporting
3. Extract view logic to presenters
```

## Severity Levels

### Critical
- Domain layer using Current for business logic, authorization, or query building
- Circular dependencies between layers
- Business logic in views

### Major
- Heavy callback chains (5+ callbacks)
- God objects (>300 lines, high churn)
- Authorization scattered across layers
- Callback control flags (`skip_*` attributes)

### Minor
- Missing abstractions (could benefit from patterns)
- Concerns used by single model
- Overly complex scopes
- Anemic jobs (single-delegation wrappers)
- Helper HTML construction (candidates for ViewComponents)

## Related Commands

- `/layers:analyze-callbacks` - Deep callback analysis
- `/layers:analyze-gods` - Detailed god object analysis
- `/layers:spec-test` - Apply specification test to specific code
- `/layers:review` - Review specific changes

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

### 2. Layer Violation Detection

Search for common violations:

**Models Triggering Notifications/Deliveries**
```bash
grep -r "Delivery\." app/models/
grep -r "Mailer\." app/models/
grep -r "deliver_later\|deliver_now" app/models/
```

**Current in Models**
```bash
# VIOLATION: Domain accessing request context
grep -r "Current\." app/models/
```

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

### 5. Concern Health Check

For each concern, verify:
- [ ] Used by multiple models (not single-model organization)
- [ ] Methods are cohesively related
- [ ] No hidden dependencies on including class
- [ ] Doesn't recreate callback problems

### 6. Pattern Gap Analysis

Identify missing abstractions:

- **No policies?** Check for authorization in controllers/models
- **No form objects?** Check for complex params handling
- **No query objects?** Check for long scope chains
- **No presenters?** Check for view logic in models

## Output Format

```markdown
# Layered Architecture Analysis

## Summary
- Overall health: [Good/Fair/Needs Attention/Critical]
- Layer compliance: [percentage]
- God object candidates: [count]
- Callback concerns: [count]

## Layer Violations

### Critical
1. `app/models/user.rb:45` - Current.user access in domain layer
   - Impact: Domain coupled to request context
   - Fix: Pass user explicitly through service layer

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
- Domain layer accessing request context (Current, params, request)
- Circular dependencies between layers
- Business logic in views

### Major
- Heavy callback chains (5+ callbacks)
- God objects (>300 lines, high churn)
- Authorization scattered across layers

### Minor
- Missing abstractions (could benefit from patterns)
- Concerns used by single model
- Overly complex scopes

## Related Commands

- `/layers:analyze-callbacks` - Deep callback analysis
- `/layers:analyze-gods` - Detailed god object analysis
- `/layers:spec-test` - Apply specification test to specific code
- `/layers:review` - Review specific changes

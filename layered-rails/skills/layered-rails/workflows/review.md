# Layered Rails Review Workflow

Code review applying layered architecture principles to Rails diffs, files, or branches.

## Contents

- [Philosophy](#philosophy)
- [Process](#process)
- [Review Principles](#review-principles)
- [Review Checklist](#review-checklist)
- [Resolving Violations](#resolving-violations)
- [Reviewing Test Files](#reviewing-test-files)
- [Output Format](#output-format)
- [Severity Levels](#severity-levels)
- [Example Review](#example-review)
- [Related](#related)

## Philosophy

This review evaluates code against the principles from "Layered Design for Ruby on Rails Applications":

- **Favor extraction over complication** — when code grows complex, extract to the appropriate layer
- **Patterns before abstractions** — let code age before extracting; premature abstraction is worse than duplication
- **Services as waiting room** — `app/services` is temporary residence until proper abstractions emerge
- **Domain logic stays in models** — avoid anemic models; services orchestrate, models know business rules
- **Explicit over implicit** — prefer explicit parameters over Current attributes
- **Lower layers never depend on higher layers** — no reverse dependencies

## Process

1. **Identify changed files** (from git diff or provided paths)
2. **Determine layers touched** by the changes
3. **Apply layer boundary checks**
   - Grep for `Current.*` in models
   - Check service parameters for request/params objects
   - Look for business logic in controllers
4. **Run the [specification test](../references/core/specification-test.md)** on key files
5. **Check for extraction signals**
   - Score callbacks
   - Assess concern health
   - Check god-object indicators
6. **Generate review report** with prioritized issues

## Review Principles

### 1. Layer Boundary Enforcement

Check for violations of the four architecture rules:

- **No reverse dependencies** — models don't use Current; services don't accept request objects
- **Abstraction boundaries** — each abstraction belongs to exactly one layer
- **Unidirectional data flow** — data flows top-to-bottom only
- **Minimal connections** — avoid unnecessary coupling between layers

**Flag:**
- `Current.*` usage in models
- Request/params objects passed to services
- Mailers called from model callbacks
- SQL queries in controllers
- Business calculations in views

### 2. Specification Test Application

Evaluate whether code responsibilities match the layer:

- **Controllers** should only handle HTTP concerns (auth, params, response)
- **Services** should orchestrate domain objects, not contain domain logic
- **Models** should contain business rules and domain logic
- **Views** should only format data for display

**Ask:**
- Would testing this require HTTP setup when it shouldn't?
- Is this test verifying the right layer's responsibility?
- Could this logic be tested with a simpler, lower-layer test?

### 3. Extraction Signal Detection

Identify code that should be extracted:

**Callback scoring:**
| Type | Score | Action |
|------|-------|--------|
| Transformer (compute values) | 5/5 | Keep |
| Normalizer (sanitize input) | 4/5 | Keep |
| Utility (counter caches) | 4/5 | Keep |
| Observer (side effects) | 2/5 | Review |
| Operation (business steps) | 1/5 | Extract |

**Concern health:**
- Behavioral concerns (shared across models) → good
- Code-slicing concerns (grouping by artifact type) → extract or inline

**God-object indicators:**
- Many methods (50+)
- High churn (frequently modified)
- Mixed responsibilities (persistence + presentation + notifications)

### 4. Current Attributes Audit

Flag all `Current` usage and evaluate by layer:

- **Controllers:** OK (write location)
- **Services:** review (should it pass explicitly?)
- **Models:** violation (extract to parameter)
- **Jobs:** risk (context will be nil)

### 5. Service Object Critique

Prevent anemic models:

- Does this service contain logic that belongs in the model?
- Is the service just a thin wrapper around model methods?
- Are there established conventions (base class, naming, interface)?

Identify decomposition opportunities:

- Is `app/services` growing unbounded?
- Do services share patterns that could become abstractions?
- Are there 3+ services doing similar things?

### 6. Anemic Job Detection

Flag job classes that just delegate to model methods:

```ruby
# BAD: Anemic job
class NotifyRecipientsJob < ApplicationJob
  def perform(record)
    record.notify_recipients  # Single delegation = anemic
  end
end
```

**Signals:**
- Job's `perform` is single line calling method on argument
- Model has `*_later` method that just calls `SomeJob.perform_later(self)`
- `app/jobs` has many similar thin wrappers

**Recommendation:** Use `active_job-performs` gem:

```ruby
# GOOD: No separate job file
class Post < ApplicationRecord
  performs def notify_recipients
    # Logic here
  end
end
```

### 7. Abstraction Assessment

Evaluate pattern choices:

- Is this the right pattern for the problem?
- Is there a simpler solution?
- Does it follow established conventions?
- Is this premature abstraction?

## Review Checklist

### Layer Violations (Critical)
- [ ] Models don't access Current attributes
- [ ] Services don't accept request/params objects
- [ ] Controllers don't contain business calculations
- [ ] Views don't query database directly (beyond simple associations)
- [ ] Mailers aren't called from model callbacks

### Callback Health (Warning)
- [ ] New callbacks score 4+ on the scale
- [ ] No operation callbacks (business process steps)
- [ ] No callback control flags (`skip_*`, `unless: :flag`)

### Concern Health (Warning)
- [ ] Concerns are behavioral (can be tested in isolation)
- [ ] No code-slicing (grouping by artifact type)
- [ ] Concerns aren't overgrown (50+ lines)

### Service Health (Suggestion)
- [ ] Services follow established conventions
- [ ] Domain logic remains in models (no anemic models)
- [ ] Services aren't just thin wrappers

### Model Health (Suggestion)
- [ ] No god-object indicators (high churn × complexity)
- [ ] Clear separation of concerns
- [ ] Reasonable method count

## Resolving Violations

When identifying a layer violation (e.g., model triggering notification):

### 1. Trace the Call Chain

Find who calls the violating code:
```
Controller/Job → Service → Model (violation here)
```

### 2. Identify Existing Orchestrators

Look for services, forms, or controllers already coordinating this flow. Check:
- `app/services/` for related services
- `app/forms/` for form objects handling this operation
- Controllers that initiate the action

### 3. Recommend Moving to Orchestrator

If an orchestrator exists, recommend moving the side effect there:

```ruby
# BAD: Model triggers notification
class License < ApplicationRecord
  def prolong
    update!(status: :active, expires_at: 1.year.from_now)
    LicenseDelivery.with(license: self).purchased.deliver_later  # Violation
  end
end

# GOOD: Service orchestrates, model stays pure
class StripeEventManager
  def handle_invoice_paid(invoice)
    # ... find license, create payment record ...
    license.prolong
    LicenseDelivery.with(license:).purchased.deliver_later
  end
end

class License < ApplicationRecord
  def prolong
    update!(status: :active, expires_at: 1.year.from_now)
  end
end
```

### 4. No Clear Orchestrator

If no existing orchestrator, list options without being prescriptive:
- Move to controller (if called from a single controller action)
- Create service object (if complex orchestration needed)
- Create form object (if user input involved)

Let the user decide based on their context.

## Reviewing Test Files

When reviewing test files, apply these principles:

### Never Recommend Testing Private Methods via `send`

Private methods are private for a reason — they're implementation details. Never suggest:

```ruby
# BAD — testing private steps via send
processor.send(:parse_json!)
processor.send(:import_board)
processor.send(:import_columns)
```

If private methods need isolated testing, that's a signal the class should be decomposed into smaller public objects. Say that instead.

### Expensive Operations: Combine Assertions Over One-Per-Test Dogma

When a test setup is expensive (e.g., importing hundreds of records from a fixture), running it N times for N single-assertion tests is wasteful. Without RSpec + `before_all` (TestProf), Minitest has no way to share expensive state across tests.

The pragmatic answer: **combine assertions in fewer tests**. This is better than the alternatives (slow suite, or testing privates via `send`):

```ruby
# GOOD — run import once, assert everything
test "import creates board with columns, cards, tags, and comments" do
  processor = TrelloImport::Processor.new(@import)
  processor.import

  # Board
  assert_equal "HR Manager", @import.board.name

  # Columns (only open lists)
  assert_equal 3, @import.board.columns.count
  assert @import.board.columns.exists?(name: "Inbox")

  # Cards
  assert_equal 5, @import.cards_count
  card = @import.board.cards.find_by(title: "First task")
  assert card.published?

  # Tags
  assert_equal 1, Current.account.tags.where(title: "account").count

  # Comments
  assert @import.comments_count > 0
end
```

Keep separate tests only for genuinely independent scenarios (error paths, edge cases with different fixtures).

### Removing Duplicate Tests: Show What Replaces Them

Never recommend simply deleting tests without showing what takes their place. When a higher-layer test duplicates a lower-layer test (e.g., TrelloImport tests duplicating Processor tests), replace the duplicates with a **delegation test** that verifies the lower layer is invoked correctly:

```ruby
# INSTEAD OF deleting these and leaving nothing:
#   "process imports board"
#   "process imports columns"
#   "process imports cards"
#   ...

# REPLACE WITH a delegation test:
test "process delegates to Processor and tracks status" do
  import = TrelloImport.create!(account: Current.account, user: @user, file: uploaded_file)

  mock_processor = Minitest::Mock.new
  mock_processor.expect(:import, nil)
  TrelloImport::Processor.stub(:new, mock_processor) do
    import.process
  end
  mock_processor.verify

  assert import.completed?
  assert_not_nil import.completed_at
end
```

This proves TrelloImport delegates to Processor without re-testing all of Processor's behavior.

## Output Format

Default review output shape:

```markdown
## Layered Rails Review

### Files Reviewed
- path/to/file.rb (Presentation|Application|Domain|Infrastructure)

### Layer Analysis
- **Layers touched:** [list]
- **Data flow:** OK | Violation detected

### Findings

🔴 **Critical: [Issue Type]**
Location: `path/to/file.rb:line`
` ` `ruby
# Problematic code
` ` `
**Problem:** ...
**Fix:** ...

⚠️ **Warning: [Issue Type]**
Location: `path/to/file.rb:line`
**Problem:** ...
**Recommendation:** ...

💡 **Suggestion: [Issue Type]**
[Description with alternative approach]

### Summary

**Good:** [what's working]
**Needs Attention:** [prioritized list]
**Priority:** [what to address first]
```

If there are no findings, say so explicitly and note any residual risks or missing verification.

## Severity Levels

### 🔴 Critical (must fix)
- Layer violation (reverse dependency)
- Current in models used for business logic
- Request objects in services
- Business logic in controllers doing domain calculations

### ⚠️ Warning (should fix)
- Low-scoring callbacks (1-2/5)
- Code-slicing concerns
- Anemic-model risk
- Missing service conventions

### 💡 Suggestion (consider)
- Extraction opportunity
- Pattern alternative
- Convention improvement
- Test layer mismatch

## Example Review

```markdown
## Layered Rails Review

### Files Reviewed
- app/controllers/orders_controller.rb (Presentation)
- app/models/order.rb (Domain)
- app/services/process_order_service.rb (Application)

### Layer Analysis
- **Layers touched:** Presentation, Application, Domain
- **Data flow:** Violation detected

### Findings

🔴 **Critical: Layer Violation**
Location: `app/models/order.rb:45`
` ` `ruby
def complete!
  self.completed_by = Current.user
  save!
end
` ` `
**Problem:** Model depends on Current (presentation context). This will fail silently in background jobs.
**Fix:** Accept user as explicit parameter:
` ` `ruby
def complete!(by:)
  self.completed_by = by
  save!
end
` ` `

⚠️ **Warning: Operation Callback**
Location: `app/models/order.rb:12`
` ` `ruby
after_commit :sync_to_warehouse, on: :update
` ` `
**Problem:** This is a business operation (score 1/5), not a model concern.
**Recommendation:** Move to controller or use event-driven approach with Active Support Notifications.

💡 **Suggestion: Anemic Model Risk**
Location: `app/services/calculate_order_total_service.rb`
**Problem:** This calculation (`items.sum(&:subtotal) * discount_rate`) is domain logic that belongs in the Order model.
**Recommendation:** Move `#calculate_total` to Order model. Services should orchestrate, not contain domain logic.

### Summary

**Good:**
- Clean controller structure
- Proper use of strong parameters

**Needs Attention:**
1. 🔴 Fix Current.user in Order model (will break in background jobs)
2. ⚠️ Move domain logic from service to model
3. ⚠️ Extract warehouse sync callback

**Priority:** Address layer violation first, then refactor service/model boundary.
```

## Related

- [Specification test](../references/core/specification-test.md)
- [Layer violations](../references/anti-patterns/layer-violations.md)
- [Callbacks anti-patterns](../references/anti-patterns/callbacks.md)
- [Service Objects anti-patterns](../references/anti-patterns/service-objects.md)
- [Current attributes](../references/topics/current-attributes.md)

# /layers:review

Standalone code review from layered architecture perspective.

## Usage

```
/layers:review                    # Review uncommitted changes
/layers:review [file_path]        # Review specific file
/layers:review --staged           # Review staged changes
/layers:review --branch main      # Review changes vs branch
```

## Process

1. **Identify changed files** (from git diff or provided paths)
2. **Determine layers touched** by the changes
3. **Apply layer boundary checks**
   - Grep for Current.* in models
   - Check service parameters
   - Look for business logic in controllers
4. **Run specification test** on key files
5. **Check for extraction signals**
   - Score callbacks
   - Assess concern health
   - Check for god object indicators
6. **Generate review report** with prioritized issues

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
- [ ] No callback control flags (skip_*, unless: :flag)

### Concern Health (Warning)
- [ ] Concerns are behavioral (can be tested in isolation)
- [ ] No code-slicing (grouping by artifact type)
- [ ] Concerns aren't overgrown (50+ lines)

### Service Health (Suggestion)
- [ ] Services follow established conventions
- [ ] Domain logic remains in models (no anemic models)
- [ ] Services aren't just thin wrappers

### Model Health (Suggestion)
- [ ] No god object indicators (high churn × complexity)
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
- Move to controller (if called from single controller action)
- Create service object (if complex orchestration needed)
- Create form object (if user input involved)

Let the user decide based on their context.

## Output Format

```markdown
## Layered Rails Review

### Files Reviewed
- app/controllers/orders_controller.rb (Presentation)
- app/models/order.rb (Domain)
- app/services/process_order_service.rb (Application)

### Layer Analysis
- **Layers touched:** Presentation, Application, Domain
- **Data flow:** [OK / Violation detected]

### Issues Found

🔴 **Critical: Layer Violation**
Location: `app/models/order.rb:45`
```ruby
def complete!
  self.completed_by = Current.user
end
```
**Problem:** Model depends on Current (presentation context).
**Fix:** Accept user as explicit parameter:
```ruby
def complete!(by:)
  self.completed_by = by
end
```

⚠️ **Warning: Low-Scoring Callback**
Location: `app/models/order.rb:12`
```ruby
after_commit :sync_to_warehouse
```
**Problem:** Operation callback (score 1/5).
**Recommendation:** Extract to controller, service, or event handler.

⚠️ **Warning: Anemic Model Risk**
Location: `app/services/process_order_service.rb:15-25`
**Problem:** Service contains domain logic (pricing calculations) that belongs in Order model.
**Recommendation:** Move `calculate_total` to Order model.

💡 **Suggestion: Missing Service Convention**
Location: `app/services/process_order_service.rb`
**Problem:** Service doesn't inherit from base class or follow naming convention.
**Recommendation:** Establish `ApplicationService` base class with `.call` interface.

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

## Severity Levels

### 🔴 Critical
Must fix before merge:
- Layer violations (reverse dependencies)
- Current in models
- Request objects in services

### ⚠️ Warning
Should fix or acknowledge:
- Low-scoring callbacks (1-2/5)
- Code-slicing concerns
- Anemic model indicators
- Missing conventions

### 💡 Suggestion
Consider for improvement:
- Extraction opportunities
- Alternative patterns
- Convention improvements

## Integration

This command provides standalone review without requiring compound-engineering.

For full multi-agent review with compound-engineering:
```
/review  # Uses layered-rails-reviewer as part of agent pool
```

## Automation Level

This command runs with mid-to-high automation:

1. **Automatic:** File identification, layer detection, violation scanning
2. **Automatic:** Callback scoring, concern assessment
3. **Automatic:** Issue categorization and prioritization
4. **Automatic:** Fix recommendations with code examples
5. **Manual input needed:** Only for complex architectural decisions

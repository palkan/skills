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

# /layers:analyze-gods

Identify and analyze god objects in the codebase using churn × complexity metrics.

## Purpose

Find models that have grown too large and complex, then provide actionable recommendations for decomposition.

## Usage

```
/layers:analyze-gods [threshold]
```

- Without threshold: Uses default (250 lines)
- With threshold: Custom line count threshold

## God Object Indicators

### Quantitative Signals

| Metric | Warning | Critical |
|--------|---------|----------|
| Lines of code | >250 | >500 |
| Methods | >20 | >40 |
| Associations | >10 | >20 |
| Callbacks | >5 | >10 |
| Concerns included | >5 | >10 |
| Scopes | >10 | >20 |

### Churn Analysis

High change frequency indicates:
- Central to business logic (expected)
- Accumulating unrelated features (problem)
- Frequent bug fixes (complexity debt)

```bash
# Get churn data (commits touching file)
git log --format=format: --name-only --since="6 months ago" -- "*.rb" | \
  grep "app/models" | sort | uniq -c | sort -rn
```

### Complexity Indicators

- Many conditionals (case/if statements)
- Mixed responsibilities (authentication + billing + notifications)
- State-dependent behavior (many boolean checks)
- External API integration mixed with domain logic

## Analysis Process

### 1. Identify Candidates

```ruby
# Find large models
Dir.glob("app/models/**/*.rb").map do |file|
  lines = File.readlines(file).count
  { file: file, lines: lines }
end.select { |f| f[:lines] > 250 }.sort_by { |f| -f[:lines] }
```

### 2. Analyze Each Candidate

For each god object candidate:

1. **Count structural elements**
   - Lines, methods, associations, callbacks, scopes, concerns

2. **Identify responsibility clusters**
   - Group related methods by what they do
   - Look for natural extraction boundaries

3. **Check for layer violations**
   - Presentation logic (formatting, view helpers)
   - Infrastructure concerns (API calls, mailers)
   - Application logic (orchestration, authorization)

4. **Map dependencies**
   - What other models does it touch?
   - What services/jobs reference it?

### 3. Recommend Decomposition

For each cluster of responsibilities, suggest:
- Concern extraction (shared behavior)
- Service extraction (operations)
- Value object extraction (data + behavior)
- Associated object extraction (delegated responsibilities)

## Output Format

```markdown
# God Object Analysis

## Summary
- Models analyzed: 45
- God object candidates: 4
- Critical (>500 lines): 1
- Warning (>250 lines): 3

## Critical: User (623 lines)

### Metrics
| Metric | Value | Status |
|--------|-------|--------|
| Lines | 623 | 🔴 Critical |
| Methods | 47 | 🔴 Critical |
| Associations | 15 | 🟡 Warning |
| Callbacks | 8 | 🟡 Warning |
| Concerns | 6 | 🟡 Warning |
| Scopes | 12 | 🟡 Warning |
| Churn (6mo) | 89 commits | High |

### Responsibility Clusters

**Authentication (lines 45-120)**
- `authenticate`, `valid_password?`, `reset_password!`
- `generate_token`, `verify_token`, `invalidate_sessions`
→ Extract to `Users::Authentication` concern or service

**Profile Management (lines 125-200)**
- `update_profile`, `avatar_url`, `display_name`
- `bio`, `social_links`, `preferences`
→ Extract to `User::Profile` associated object

**Billing (lines 205-320)**
- `subscribe!`, `cancel_subscription!`, `update_payment_method`
- `invoice_history`, `current_plan`, `billing_email`
→ Extract to `User::Billing` associated object or service

**Notifications (lines 325-400)**
- `notify!`, `notification_preferences`, `unread_count`
- `email_notifications?`, `push_notifications?`
→ Extract to `User::NotificationSettings` value object

**Authorization (lines 405-480)**
- `can_access?`, `permissions`, `role_for`
- `admin?`, `moderator?`, `member_of?`
→ Extract to `UserPolicy` (already should be there)

### Recommended Extraction Plan

1. **Immediate**: Extract billing to `User::Billing` using `has_object`
2. **Short-term**: Move notification settings to value object
3. **Medium-term**: Review authentication for service extraction
4. **Ongoing**: Move authorization checks to policies

### Code Example

Before:
```ruby
class User < ApplicationRecord
  # 600+ lines of mixed responsibilities
end
```

After:
```ruby
class User < ApplicationRecord
  include Users::Authentication

  has_object :billing
  has_object :profile

  composed_of :notification_settings,
    class_name: "User::NotificationSettings",
    mapping: [...]

  # ~100 lines of core user logic
end
```

## Warning: Order (380 lines)

### Metrics
| Metric | Value | Status |
|--------|-------|--------|
| Lines | 380 | 🟡 Warning |
| Methods | 28 | 🟡 Warning |
| State methods | 12 | High |
| Callbacks | 6 | 🟡 Warning |

### Responsibility Clusters

**State Management (lines 50-150)**
- Multiple status checks, transitions, validations
→ Extract to state machine (workflow gem)

**Pricing Calculation (lines 155-220)**
- `calculate_subtotal`, `apply_discount`, `tax_amount`, `total`
→ Extract to `Order::Calculator` value object

**Fulfillment (lines 225-300)**
- `ship!`, `deliver!`, `tracking_info`, `estimated_delivery`
→ Extract to `Order::Fulfillment` service or associated object

### Recommended Extraction Plan

1. **Immediate**: Implement state machine for order status
2. **Short-term**: Extract pricing to calculator object
3. **Medium-term**: Consider fulfillment service

## Non-Issues

### Post (280 lines)
- Lines are high but complexity is low
- Single responsibility (content management)
- High churn due to feature additions, not bug fixes
- **Assessment**: Monitor but no action needed

## Extraction Priority Matrix

| Model | Lines | Churn | Complexity | Priority |
|-------|-------|-------|------------|----------|
| User | 623 | High | High | 🔴 Critical |
| Order | 380 | Medium | High | 🟡 High |
| Post | 280 | High | Low | 🟢 Monitor |
| Comment | 260 | Low | Low | 🟢 Low |
```

## Decomposition Strategies

### 1. Concern Extraction
For shared behavior across models:
```ruby
module Sluggable
  extend ActiveSupport::Concern
  # ...
end
```

### 2. Associated Object (has_object)
For delegated responsibilities:
```ruby
class User < ApplicationRecord
  has_object :billing
end

class User::Billing
  # Billing-specific logic
end
```

### 3. Value Object (composed_of)
For data with behavior:
```ruby
class User < ApplicationRecord
  composed_of :address, class_name: "User::Address", mapping: [...]
end
```

### 4. Service Extraction
For operations that span boundaries:
```ruby
class Users::Register
  def call(params)
    # Orchestrate user creation
  end
end
```

### 5. State Machine
For complex state management:
```ruby
class Order < ApplicationRecord
  include Workflow

  workflow do
    state :pending do
      event :confirm, transitions_to: :confirmed
    end
    # ...
  end
end
```

## Related

- [Extraction Signals](/skill/references/core/extraction-signals.md)
- [Service Objects Pattern](/skill/references/patterns/service-objects.md)
- [Concerns Pattern](/skill/references/patterns/concerns.md)
- [Value Objects Pattern](/skill/references/patterns/value-objects.md)

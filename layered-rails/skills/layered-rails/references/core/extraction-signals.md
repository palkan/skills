# Extraction Signals

How to identify code that should be extracted to a different layer or abstraction.

## Callback Scoring System

Rate model callbacks to identify extraction candidates:

| Score | Type | Description | Action |
|-------|------|-------------|--------|
| 5/5 | **Transformer** | Computes/defaults required values | Keep in model |
| 4/5 | **Normalizer** | Sanitizes input data | Keep (prefer `.normalizes` API) |
| 4/5 | **Utility** | Counter caches, cache busting | Keep in model |
| 2/5 | **Observer** | Side effects after commit | Review case-by-case |
| 1/5 | **Operation** | Business process steps | Extract immediately |

### Transformer Callbacks (Keep)

Compute or default required attribute values:

```ruby
class Post < ApplicationRecord
  before_validation :compute_shortname, on: :create
  before_save :set_word_count, if: :content_changed?

  private

  def compute_shortname
    self.short_name ||= title.parameterize
  end

  def set_word_count
    self.word_count = content.split(/\s+/).size
  end
end
```

### Normalizer Callbacks (Keep)

Sanitize user input. Prefer Rails 7.1+ `.normalizes` API:

```ruby
class Post < ApplicationRecord
  normalizes :title, with: -> { _1.strip }
  normalizes :content, with: -> { _1.squish }
end
```

### Utility Callbacks (Keep)

Framework-level utilities like counter caches:

```ruby
class Comment < ApplicationRecord
  belongs_to :post, touch: true, counter_cache: true
end
```

### Operation Callbacks (Extract)

Signs of misplacement:
- Conditions (`unless: :admin?`)
- Collaboration with non-model objects (mailers, API clients)
- Remote peer communication

```ruby
# BAD - Extract these
class User < ApplicationRecord
  after_create :generate_initial_project, unless: :admin?
  after_commit :send_welcome_email, on: :create
  after_commit :sync_with_crm
  after_commit :track_signup_analytics
end
```

**Extraction options:**
1. Move to controller
2. Move to service object
3. Use event-driven approach

```ruby
# GOOD - Event-driven
class User < ApplicationRecord
  after_commit on: :create do
    UserCreatedEvent.publish(user: self)
  end
end

# Subscribers handle side effects
class WelcomeEmailSubscriber
  def user_created(event)
    UserMailer.welcome(event.user).deliver_later
  end
end
```

## God Object Identification

### Churn × Complexity Metric

**Churn** = how often a file changes (indicates ongoing modifications)
**Complexity** = code complexity score (use Flog)

Files high in both are prime refactoring candidates.

```bash
# Calculate churn
git log --format=oneline -- app/models/user.rb | wc -l

# Calculate complexity
flog -s app/models/user.rb

# Find intersection of top 10 by each
```

### Automated Tool

Use [attractor](https://github.com/julianrubisch/attractor):

```bash
attractor report -p app/models
```

### Common God Object Names

Watch for these accumulating responsibilities:
- `User` / `Account`
- `Order` / `Transaction`
- `Project` / `Workspace`
- `Post` / `Article`

### Decomposition Strategies

1. **Extract concerns** for shared behaviors
2. **Extract delegate objects** for complex operations
3. **Extract value objects** for groups of related attributes
4. **Create new models** for distinct concepts

```ruby
# Before: God User model
class User < ApplicationRecord
  # Authentication (20 methods)
  # Profile (15 methods)
  # Notifications (10 methods)
  # Analytics (10 methods)
end

# After: Decomposed
class User < ApplicationRecord
  include User::Authentication
  has_one :profile
  has_one :notification_preferences
end

class User::Authentication
  # Authentication behavior
end

class Profile < ApplicationRecord
  belongs_to :user
end

class NotificationPreferences < ApplicationRecord
  belongs_to :user
end
```

## Concern Health Check

### Good Concerns (Behavioral)

Can be tested in isolation, shared across models:

```ruby
module Publishable
  extend ActiveSupport::Concern

  included do
    scope :published, -> { where.not(published_at: nil) }
    scope :draft, -> { where(published_at: nil) }
  end

  def published? = published_at.present?
  def publish! = update!(published_at: Time.current)
end
```

**Test:** Can you write specs for this concern without instantiating the host model?

### Bad Concerns (Code-Slicing)

Groups code by Rails artifact type, not behavior:

```ruby
# BAD - Just groups contact-related code
module Contactable
  extend ActiveSupport::Concern

  included do
    validates :email, presence: true
    validates :phone, format: { with: PHONE_REGEX }
    before_save :normalize_phone
  end

  def full_contact_info
    "#{email} / #{phone}"
  end
end
```

**Test:** If removing this concern breaks unrelated tests, it's code-slicing.

### Overgrown Concerns

Signs a concern should be extracted:
- 50+ lines
- Multiple responsibilities
- Complex internal state

Extract to:
- **Delegate object** for operations
- **Value object** for attribute groups
- **Separate model** for distinct entity

## Service Object Signals

### When to Extract to Service

Extract from controller when you see:
- Multiple model operations in sequence
- Transaction spanning multiple models
- Complex error handling
- Reusable business operation

### When NOT to Use Services

Don't extract:
- Single model operations (keep in model)
- Simple CRUD (let controller handle)
- Domain logic (belongs in model, not service)

### Anemic Model Warning Signs

Your models might be anemic if:
- Services contain calculations that use only model data
- Models are pure data containers (associations + validations only)
- You have `CalculateXService` for model attributes
- Domain rules live in services, not models

```ruby
# BAD - Anemic
class Order < ApplicationRecord
  # Just associations and validations
end

class CalculateOrderTotalService
  def call(order)
    order.items.sum { |i| i.price * i.quantity }
  end
end

# GOOD - Rich model
class Order < ApplicationRecord
  def total
    items.sum(&:subtotal)
  end
end
```

## Controller Fat Signals

### Extract When You See

- Business calculations (pricing, discounts)
- Multiple model updates
- Complex conditionals based on business rules
- External API calls
- More than 10-15 lines per action

### Keep in Controller

- Parameter parsing
- Authentication/authorization
- Response formatting
- Simple model operations

## Quick Reference

| Signal | Threshold | Action |
|--------|-----------|--------|
| Callback score | ≤ 2/5 | Extract to service/event |
| Model complexity | Flog > 100 | Decompose |
| Model churn | > 30 changes/year | Review for extraction |
| Concern size | > 50 lines | Extract to delegate |
| Controller action | > 15 lines | Extract to service |
| Service with domain logic | Any calculations | Move to model |

## Tools

| Tool | Purpose | Command |
|------|---------|---------|
| [flog](https://github.com/seattlerb/flog) | Complexity scoring | `flog -s app/models/` |
| [attractor](https://github.com/julianrubisch/attractor) | Churn × complexity | `attractor report` |
| [callback_hell](https://github.com/evilmartians/callback_hell) | Callback audit | `bin/rails callback_hell:callbacks[User]` |

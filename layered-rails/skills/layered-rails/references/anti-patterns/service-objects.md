# Service Object Anti-Patterns

Common mistakes when introducing service objects.

## Contents

- Anemic Models
- Bag of Random Objects
- Premature Abstraction

## Anemic Models

**Problem:** All logic moved to services, models become data containers.

```ruby
# BAD - Anemic model
class Order < ApplicationRecord
  # Just associations and validations, no behavior
end

class CalculateOrderTotalService
  def call(order)
    total = order.items.sum { |i| i.price * i.quantity }
    total *= 0.9 if order.customer.vip?
    order.update!(total:)
  end
end

class ApplyDiscountService
  def call(order, code)
    discount = Discount.find_by(code:)
    order.update!(discount_amount: discount.amount)
  end
end
```

**Fix:** Keep domain logic in models. Services orchestrate, models know their business rules.

```ruby
# GOOD
class Order < ApplicationRecord
  def calculate_total
    self.total = items.sum(&:subtotal)
    apply_vip_discount if customer.vip?
  end

  def apply_discount(code)
    discount = Discount.find_by(code:)
    self.discount_amount = discount.amount
  end
end
```

## Bag of Random Objects

**Problem:** No conventions, each service is unique.

```ruby
# BAD - No consistency
class UserRegistration
  def perform(attrs)
    # returns user or nil
  end
end

class OrderProcessor
  def self.process!(order_id)
    # raises on failure
  end
end

class SendNewsletterJob
  def run(newsletter, subscribers)
    # returns count
  end
end
```

**Fix:** Establish conventions.

```ruby
# GOOD - Consistent interface
class ApplicationService
  extend Dry::Initializer
  def self.call(...) = new(...).call
end

class RegisterUserService < ApplicationService
  param :attrs
  def call
    # Returns result object
  end
end

class ProcessOrderService < ApplicationService
  param :order_id
  def call
    # Returns result object
  end
end
```

## Premature Abstraction

**Problem:** Creating abstractions before patterns emerge.

```ruby
# BAD - Over-engineered from day one
class BaseCommand
  include CommandPattern
  include ResultMonad
  include TransactionWrapper
end

class CreateUserCommand < BaseCommand
  # Complex infrastructure for simple operation
end
```

**Fix:** Wait for patterns to emerge. Start simple.

```ruby
# GOOD - Simple first
class CreateUserService
  def self.call(params)
    User.create!(params)
  end
end

# Extract patterns AFTER you see repetition
```

# Service Objects

## Summary

Service objects represent single business operations between controllers and models. They fill the gap in Rails' MVC where neither controllers (inbound layer) nor models (domain layer) are appropriate homes for business logic orchestration.

## When to Use

- Orchestrating multiple domain objects for a use case
- Operations that span multiple models with transaction boundaries
- Complex business logic that doesn't belong in any single model
- Reusable operations called from multiple controllers

## When NOT to Use

- Simple CRUD operations (let controller handle)
- Domain logic (belongs in models)
- Single-model operations (keep in model)

## Key Principles

- **Waiting room metaphor** — services are temporary homes until proper abstractions emerge
- **Establish conventions early** — naming, interface, base class, return values
- **Services orchestrate, models know rules** — don't strip domain logic into services
- **Avoid bag of random objects** — decompose into specialized abstractions as patterns emerge

## Implementation

### Base Class

```ruby
class ApplicationService
  extend Dry::Initializer

  def self.call(...) = new(...).call
end
```

### Example Service

```ruby
class HandleGithubEventService < ApplicationService
  param :event

  def call
    user = User.find_by(gh_id: event.user_id)
    return unless user

    case event
    in GitHubEvent::Issue[action: "opened", title:, body:]
      user.issues.create!(title:, body:)
    in GitHubEvent::PR[action: "opened", title:, body:, branch:]
      user.pull_requests.create!(title:, body:, branch:)
    end
  end
end
```

### Usage

```ruby
# In controller
class GithubCallbacksController < ApplicationController
  def create
    event = GithubEvent.from_request(request)
    HandleGithubEventService.call(event)
    head :ok
  end
end
```

## Conventions to Establish

| Decision | Options |
|----------|---------|
| Naming | `User::HandleGithubEventService` or `HandleGithubEvent` |
| Interface | Callable (`.call` method) |
| Base class | `ApplicationService` with shared utilities |
| Return values | Result objects, monads, or plain values |
| Error handling | Exceptions, result objects, or monads |

## Anti-Patterns

### Anemic Models

All logic moved to services, models become pure data containers:

```ruby
# BAD
class Order < ApplicationRecord
  # Just associations and validations
end

class CalculateOrderTotalService
  def call(order)
    order.items.sum { |i| i.price * i.quantity }
  end
end
```

**Fix:** Keep domain logic in models:

```ruby
# GOOD
class Order < ApplicationRecord
  def total
    items.sum(&:subtotal)
  end
end
```

### Bag of Random Objects

No conventions, each service is unique:

```ruby
# BAD - No consistency
class UserRegistration
  def perform(attrs) # returns user or nil
  end
end

class OrderProcessor
  def self.process!(order_id) # raises on failure
  end
end
```

### Premature Abstraction

Creating service infrastructure before patterns emerge:

```ruby
# BAD - Over-engineered from day one
class BaseCommand
  include CommandPattern
  include ResultMonad
  include TransactionWrapper
end
```

**Fix:** Start simple, extract patterns after you see repetition.

## From Services to Abstractions

As services accumulate, decompose into specialized patterns:

- **Form objects** — user input handling
- **Query objects** — complex queries
- **Policy objects** — authorization
- **Presenter objects** — view logic

## Related Gems

| Gem | Purpose |
|-----|---------|
| dry-initializer | DSL for declaring object parameters |
| dry-monads | Monadic return values for error handling |

# Layer Violations

Cross-layer dependencies that break unidirectional data flow.

## Contents

- Current Attributes in Models
- Request Objects in Services
- Notifications in Models
- Business Logic in Controllers

## Current Attributes in Models

**Problem:** Models depend on presentation-layer context.

```ruby
# BAD
class Post < ApplicationRecord
  def destroy
    self.deleted_by = Current.user  # Hidden dependency!
    super
  end
end
```

**Issues:**
- Background jobs lose Current context (silent bugs)
- Callbacks can overwrite Current mid-iteration
- Hidden dependency makes testing harder
- Violates no-reverse-dependencies rule

**Fix:** Use explicit parameters.

```ruby
# GOOD
class Post < ApplicationRecord
  def destroy_by(user:)
    self.deleted_by = user
    destroy
  end
end
```

## Request Objects in Services

**Problem:** Application layer depends on presentation layer.

```ruby
# BAD
class HandleEventService
  param :request

  def call
    event_type = request.headers["X-Event-Type"]
    payload = JSON.parse(request.body.read)
    # ...
  end
end
```

**Fix:** Extract value object in controller, pass to service.

```ruby
# GOOD
class GithubCallbacksController < ApplicationController
  def create
    event = GithubEvent.from_request(request)
    HandleEventService.call(event:)
  end
end

class HandleEventService
  param :event  # Value object, not request

  def call
    # Work with clean domain object
  end
end
```

## Notifications in Models

**Problem:** Model triggers notifications, crossing into application layer.

```ruby
# BAD
class License < ApplicationRecord
  def prolong
    update!(status: :active, expires_at: 1.year.from_now)
    LicenseDelivery.with(license: self).purchased.deliver_later
  end
end
```

**Issues:**
- Domain layer depends on application layer (reverse dependency)
- Model has side effects beyond state management
- Harder to test model in isolation
- Notification may fire unexpectedly from different call sites

**Fix:** Trace the call chain, move notification to existing orchestrator.

```ruby
# GOOD: Service handles side effects
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

**Resolution process:**
1. Find the caller (controller, service, job)
2. If orchestrator exists → move notification there
3. If no orchestrator → suggest service/form/controller based on context

## Business Logic in Controllers

**Problem:** Presentation layer doing domain work.

```ruby
# BAD
class OrdersController < ApplicationController
  def create
    @order = Order.new(order_params)
    @order.total = @order.items.sum { |i| i.price * i.quantity }
    @order.total *= 0.9 if @order.customer.vip?
    @order.total += calculate_shipping(@order)

    if @order.save
      OrderMailer.confirmation(@order).deliver_later
      redirect_to @order
    else
      render :new
    end
  end
end
```

**Fix:** Move domain logic to model, orchestration to service if needed.

```ruby
# GOOD
class Order < ApplicationRecord
  before_validation :calculate_total

  private

  def calculate_total
    self.total = items.sum(&:subtotal)
    self.total *= 0.9 if customer.vip?
    self.total += shipping_cost
  end
end

class OrdersController < ApplicationController
  def create
    @order = Order.new(order_params)

    if @order.save
      OrderMailer.confirmation(@order).deliver_later
      redirect_to @order
    else
      render :new
    end
  end
end
```

# Replace Implicit State Machine

Replace ad-hoc timestamp checks with an explicit state machine using the `workflow` gem.

## Before

```ruby
class Order < ApplicationRecord
  def status
    return :cancelled if cancelled_at?
    return :delivered if delivered_at?
    return :shipped if shipped_at?
    return :paid if paid_at?
    :pending
  end

  def can_ship?
    paid_at? && !shipped_at? && !cancelled_at?
  end

  def ship!
    return false unless can_ship?
    update!(shipped_at: Time.current)
    OrderMailer.shipped(self).deliver_later
  end
end
```

## After

```ruby
# app/models/order.rb
class Order < ApplicationRecord
  include WorkflowActiverecord

  workflow_column :status

  workflow do
    state :pending do
      event :pay, transitions_to: :paid
      event :cancel, transitions_to: :cancelled
    end

    state :paid do
      event :ship, transitions_to: :shipped
      event :cancel, transitions_to: :cancelled
    end

    state :shipped do
      event :deliver, transitions_to: :delivered
    end

    state :delivered
    state :cancelled
  end

  def ship
    self.shipped_at = Time.current
  end

  def deliver
    self.delivered_at = Time.current
  end

  def cancel
    self.cancelled_at = Time.current
  end
end

# Notifications in service
class Orders::Ship < ApplicationService
  def call(order)
    order.ship!
    OrderMailer.shipped(order).deliver_later
  end
end
```

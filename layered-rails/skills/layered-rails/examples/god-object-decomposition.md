# Extract God Object with Associated Objects

Decompose a sprawling `User` model into focused collaborators using the associated-objects pattern.

## Before

```ruby
class User < ApplicationRecord
  # 500+ lines with multiple responsibilities

  # Authentication
  has_secure_password
  def generate_token; end
  def verify_token; end
  def reset_password!; end

  # Billing
  def subscribe!(plan); end
  def cancel_subscription!; end
  def update_payment_method(token); end
  def invoice_history; end

  # Notifications
  def notify!(message); end
  def notification_preferences; end
  def unread_notifications_count; end
end
```

## After

```ruby
# app/models/user.rb
class User < ApplicationRecord
  has_secure_password

  has_object :billing
  has_object :notification_settings

  # Only core user identity logic
end

# app/models/user/billing.rb
class User::Billing
  attr_reader :user

  def initialize(user)
    @user = user
  end

  def subscribe!(plan)
    Stripe::Subscription.create(customer: stripe_customer_id, items: [{ price: plan.stripe_price_id }])
    user.update!(plan: plan, subscribed_at: Time.current)
  end

  def cancel_subscription!
    Stripe::Subscription.cancel(subscription_id)
    user.update!(plan: nil, subscription_cancelled_at: Time.current)
  end

  def invoice_history
    Stripe::Invoice.list(customer: stripe_customer_id)
  end

  private

  def stripe_customer_id
    user.stripe_customer_id
  end
end

# app/models/user/notification_settings.rb
class User::NotificationSettings
  include ActiveModel::Model
  include ActiveModel::Attributes

  attribute :email_enabled, :boolean, default: true
  attribute :push_enabled, :boolean, default: true
  attribute :digest_frequency, :string, default: "daily"
end
```

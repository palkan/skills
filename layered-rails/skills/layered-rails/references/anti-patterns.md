# Anti-Patterns

Common layered architecture violations and how to fix them.

## Layer Violations

### Current Attributes in Models

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

### Request Objects in Services

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

### Notifications in Models

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

### Business Logic in Controllers

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

## Service Object Anti-Patterns

### Anemic Models

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

### Bag of Random Objects

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

### Premature Abstraction

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

## Callback Anti-Patterns

### Operation Callbacks

**Problem:** Business process steps disguised as callbacks.

```ruby
# BAD
class User < ApplicationRecord
  after_create :generate_initial_project, unless: :admin?
  after_commit :send_welcome_email, on: :create
  after_commit :sync_with_crm
  after_commit :track_signup_analytics
end
```

**Fix:** Extract to controller, service, or events.

```ruby
# GOOD - Controller handles side effects
class UsersController < ApplicationController
  def create
    @user = User.create!(user_params)
    UserMailer.welcome(@user).deliver_later
    CrmSyncJob.perform_later(@user.id)
    AnalyticsService.track_signup(@user)
  end
end

# OR use events
class User < ApplicationRecord
  after_commit on: :create do
    UserCreatedEvent.publish(user: self)
  end
end
```

### Skip Callback Anti-Pattern

**Problem:** `skip_before_action` creates hidden dependencies.

```ruby
# BAD
class ApplicationController < ActionController::Base
  before_action :authenticate_user!
  before_action :set_current_tenant
end

class PublicController < ApplicationController
  skip_before_action :authenticate_user!
  # Now depends on parent's internal callback order
end
```

**Fix:** Use explicit inheritance or composition.

```ruby
# GOOD
class AuthenticatedController < ApplicationController
  before_action :authenticate_user!
end

class PublicController < ApplicationController
  # No authentication needed
end

class DashboardController < AuthenticatedController
  # Inherits authentication
end
```

### Callback Control Flags

**Problem:** Virtual attributes to skip callbacks.

```ruby
# BAD
class User < ApplicationRecord
  attr_accessor :skip_welcome_email, :skip_crm_sync

  after_commit :send_welcome_email, unless: :skip_welcome_email
  after_commit :sync_with_crm, unless: :skip_crm_sync
end

# Usage
user = User.new(params)
user.skip_welcome_email = true
user.save!
```

**Fix:** Extract callbacks, call explicitly when needed.

```ruby
# GOOD
class User < ApplicationRecord
  # No operation callbacks
end

class RegisterUserService
  def call(user_params, send_welcome: true)
    user = User.create!(user_params)
    UserMailer.welcome(user).deliver_later if send_welcome
    user
  end
end
```

## Concern Anti-Patterns

### Code-Slicing Concerns

**Problem:** Splitting model by Rails artifact type, not behavior.

```ruby
# BAD - Just groups related code, not a behavior
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

**Fix:** Keep in model or extract to value object.

```ruby
# GOOD - Behavioral concern (can be tested in isolation)
module Publishable
  extend ActiveSupport::Concern

  included do
    scope :published, -> { where.not(published_at: nil) }
    scope :draft, -> { where(published_at: nil) }
  end

  def published? = published_at.present?

  def publish!
    update!(published_at: Time.current)
  end
end
```

### Overgrown Concerns

**Problem:** Concern has too many responsibilities.

```ruby
# BAD - Too much in one concern
module WithMedia
  extend ActiveSupport::Concern

  included do
    has_many_attached :images
    has_many_attached :videos
    has_one_attached :thumbnail

    after_commit :process_images
    after_commit :generate_thumbnail
    after_commit :transcode_videos
  end

  def images_ready? = # ...
  def videos_ready? = # ...
  def thumbnail_url = # ...
  def processing_status = # ...
  # 50 more methods...
end
```

**Fix:** Extract to delegate object or separate concerns.

```ruby
# GOOD
class Post::MediaProcessor
  def initialize(post)
    @post = post
  end

  def process_all
    process_images
    generate_thumbnail
    transcode_videos
  end

  # ...
end
```

## Helper Anti-Patterns

### HTML Construction in Helpers

**Problem:** Helpers building HTML programmatically instead of providing logic for templates.

```ruby
# BAD: Helper constructs HTML
module MessagesHelper
  def message_tag(message, &)
    tag.div id: dom_id(message),
      class: "message #{"message--emoji" if message.plain_text_body.all_emoji?}",
      data: {
        controller: "reply",
        user_id: message.creator_id,
        message_id: message.id,
        # ... many more data attributes
      }, &
  end
end
```

**Issues:**
- HTML structure hidden in Ruby code, harder to read and modify
- No template preview, harder to collaborate with designers
- Logic and markup tightly coupled
- Testing requires rendering, not unit testable
- Misses ViewComponent benefits (sidecar assets, previews, slots)

**Signal:** Heavy use of `tag.div`, `tag.button`, `tag.span` or complex `content_tag` chains.

**Fix:** Extract to ViewComponent with template.

```ruby
# GOOD: ViewComponent with template
class MessageComponent < ViewComponent::Base
  def initialize(message:)
    @message = message
  end

  def emoji_only?
    @message.plain_text_body.all_emoji?
  end

  def stimulus_data
    {
      controller: "reply",
      user_id: @message.creator_id,
      message_id: @message.id
    }
  end
end
```

```erb
<%# app/components/message_component.html.erb %>
<div id="<%= dom_id(@message) %>"
     class="message <%= "message--emoji" if emoji_only? %>"
     data="<%= stimulus_data.to_json %>">
  <%= content %>
</div>
```

**Rule of thumb:** If a helper method has more than 2-3 `tag.*` calls or builds nested HTML structure, extract to ViewComponent.

## Job Anti-Patterns

### Anemic Jobs

**Problem:** Job classes that just delegate to a single model method.

```ruby
# BAD: Job is just a wrapper
class NotifyRecipientsJob < ApplicationJob
  discard_on ActiveJob::DeserializationError

  def perform(notifiable)
    notifiable.notify_recipients
  end
end

# BAD: Model method just to enqueue job
class Post < ApplicationRecord
  def notify_recipients_later
    NotifyRecipientsJob.perform_later(self)
  end
end
```

**Issues:**
- Boilerplate job files cluttering `app/jobs`
- Two places to maintain (job + model method)
- Job class adds no value beyond async execution
- Makes the jobs folder noisy, hiding complex jobs that need attention

**Signal:** Job's `perform` method is a single line calling a method on the argument.

**Fix:** Use [active_job-performs](https://github.com/kaspth/active_job-performs) gem.

```ruby
# GOOD: Short form (no job options needed)
class Post < ApplicationRecord
  performs def notify_recipients
    # Notification logic
  end
end

# Usage
post.notify_recipients_later
```

This generates:
- `Post::NotifyRecipientsJob` automatically
- `notify_recipients_later` instance method
- `notify_recipients_later_bulk` class method (Rails 7.1+)

**With options:**
```ruby
class Post < ApplicationRecord
  performs :notify_recipients,
           queue_as: :notifications,
           discard_on: ActiveRecord::RecordNotFound

  def notify_recipients
    # ...
  end
end
```

**When to keep separate job class:**
- Job has complex logic beyond single method call
- Job processes multiple records with custom batching
- Job needs extensive retry/error handling configuration
- Job is triggered from multiple unrelated models

See [active_job-performs gem reference](gems/active-job-performs.md) for full documentation.

## Testing Anti-Patterns

### Testing Wrong Layer

**Problem:** Controller tests verify business logic.

```ruby
# BAD
describe OrdersController do
  it "applies VIP discount" do
    post :create, params: { items: [...] }
    expect(Order.last.total).to eq(90)  # Testing domain logic!
  end
end
```

**Fix:** Test business logic in model specs.

```ruby
# GOOD
describe Order do
  it "applies VIP discount" do
    order = build(:order, customer: vip_customer)
    order.calculate_total
    expect(order.total).to eq(90)
  end
end

describe OrdersController do
  it "creates order and redirects" do
    post :create, params: { items: [...] }
    expect(response).to redirect_to(Order.last)
  end
end
```

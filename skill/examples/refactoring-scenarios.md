# Refactoring Scenarios

Common refactoring patterns for improving layered architecture.

## Scenario 1: Extract Callbacks to Service

### Before

```ruby
class User < ApplicationRecord
  after_create :send_welcome_email
  after_create :create_default_workspace
  after_create :notify_admin
  after_create :track_signup

  private

  def send_welcome_email
    UserMailer.welcome(self).deliver_later
  end

  def create_default_workspace
    workspaces.create!(name: "My Workspace")
  end

  def notify_admin
    AdminMailer.new_user(self).deliver_later
  end

  def track_signup
    Analytics.track("user_signed_up", user_id: id)
  end
end
```

### After

```ruby
# app/models/user.rb
class User < ApplicationRecord
  before_validation :normalize_email

  private

  def normalize_email
    self.email = email&.downcase&.strip
  end
end

# app/services/users/create.rb
class Users::Create < ApplicationService
  def call(params)
    user = User.create!(params)

    UserMailer.welcome(user).deliver_later
    user.workspaces.create!(name: "My Workspace")
    AdminMailer.new_user(user).deliver_later
    Analytics.track("user_signed_up", user_id: user.id)

    user
  end
end

# app/controllers/users_controller.rb
class UsersController < ApplicationController
  def create
    @user = Users::Create.call(user_params)
    redirect_to @user, notice: "Welcome!"
  rescue ActiveRecord::RecordInvalid => e
    @user = e.record
    render :new, status: :unprocessable_entity
  end
end
```

---

## Scenario 2: Extract Authorization to Policy

### Before

```ruby
class PostsController < ApplicationController
  def update
    @post = Post.find(params[:id])

    # Authorization scattered in controller
    unless current_user.admin? || @post.author == current_user
      redirect_to posts_path, alert: "Not authorized"
      return
    end

    @post.update!(post_params)
    redirect_to @post
  end

  def destroy
    @post = Post.find(params[:id])

    # Duplicated logic
    unless current_user.admin?
      redirect_to posts_path, alert: "Not authorized"
      return
    end

    @post.destroy!
    redirect_to posts_path
  end
end
```

### After

```ruby
# app/policies/post_policy.rb
class PostPolicy < ApplicationPolicy
  def update?
    owner? || admin?
  end

  def destroy?
    admin?
  end

  private

  def owner?
    record.author_id == user.id
  end

  def admin?
    user.admin?
  end
end

# app/controllers/posts_controller.rb
class PostsController < ApplicationController
  def update
    @post = Post.find(params[:id])
    authorize! @post

    @post.update!(post_params)
    redirect_to @post
  end

  def destroy
    @post = Post.find(params[:id])
    authorize! @post

    @post.destroy!
    redirect_to posts_path
  end
end
```

---

## Scenario 3: Extract Query Logic to Query Object

### Before

```ruby
class ReportsController < ApplicationController
  def sales
    @orders = Order
      .joins(:customer, :line_items)
      .where(status: :completed)
      .where(created_at: params[:start_date]..params[:end_date])
      .where(customers: { region: params[:region] }) if params[:region].present?
      .group("DATE(orders.created_at)")
      .select(
        "DATE(orders.created_at) as date",
        "COUNT(DISTINCT orders.id) as order_count",
        "SUM(line_items.quantity * line_items.price) as revenue"
      )
      .order("date DESC")
  end
end
```

### After

```ruby
# app/queries/sales_report_query.rb
class SalesReportQuery < ApplicationQuery
  relation { Order.joins(:customer, :line_items).where(status: :completed) }

  def by_date_range(start_date, end_date)
    relation.where(created_at: start_date..end_date)
  end

  def by_region(region)
    return relation if region.blank?
    relation.where(customers: { region: region })
  end

  def daily_summary
    relation
      .group("DATE(orders.created_at)")
      .select(
        "DATE(orders.created_at) as date",
        "COUNT(DISTINCT orders.id) as order_count",
        "SUM(line_items.quantity * line_items.price) as revenue"
      )
      .order("date DESC")
  end
end

# app/controllers/reports_controller.rb
class ReportsController < ApplicationController
  def sales
    @orders = SalesReportQuery.new
      .by_date_range(params[:start_date], params[:end_date])
      .by_region(params[:region])
      .daily_summary
  end
end
```

---

## Scenario 4: Extract Current from Model

### Before

```ruby
class Post < ApplicationRecord
  belongs_to :author, class_name: "User"

  before_validation :set_author, on: :create

  def can_edit?
    author == Current.user || Current.user&.admin?
  end

  private

  def set_author
    self.author = Current.user
  end
end
```

### After

```ruby
# app/models/post.rb
class Post < ApplicationRecord
  belongs_to :author, class_name: "User"
  # No Current access - domain is context-agnostic
end

# app/policies/post_policy.rb
class PostPolicy < ApplicationPolicy
  def edit?
    owner? || admin?
  end

  private

  def owner?
    record.author_id == user.id
  end

  def admin?
    user.admin?
  end
end

# app/controllers/posts_controller.rb
class PostsController < ApplicationController
  def create
    @post = current_user.posts.build(post_params)

    if @post.save
      redirect_to @post
    else
      render :new, status: :unprocessable_entity
    end
  end
end
```

---

## Scenario 5: Extract God Object with Associated Objects

### Before

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

### After

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

---

## Scenario 6: Replace Implicit State Machine

### Before

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

### After

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

---

## Scenario 7: Extract View Logic to Presenter

### Before

```erb
<%# app/views/users/show.html.erb %>
<div class="profile">
  <span class="badge <%= user.status == 'active' ? 'badge-success' : user.status == 'pending' ? 'badge-warning' : 'badge-secondary' %>">
    <%= user.status.titleize %>
  </span>

  <h1>
    <%= user.name.squish.split(/\s/).then { |parts| parts[0..-2].map { _1[0] + "." }.join + parts.last } %>
  </h1>

  <p>Member since <%= user.created_at.strftime("%B %Y") %></p>
</div>
```

### After

```ruby
# app/presenters/user_presenter.rb
class UserPresenter < SimpleDelegator
  def status_badge_class
    case status
    when "active" then "badge-success"
    when "pending" then "badge-warning"
    else "badge-secondary"
    end
  end

  def short_name
    name.squish.split(/\s/).then do |parts|
      parts[0..-2].map { _1[0] + "." }.join + parts.last
    end
  end

  def member_since
    created_at.strftime("%B %Y")
  end
end
```

```erb
<%# app/views/users/show.html.erb %>
<% present(@user) do |user| %>
  <div class="profile">
    <span class="badge <%= user.status_badge_class %>">
      <%= user.status.titleize %>
    </span>

    <h1><%= user.short_name %></h1>

    <p>Member since <%= user.member_since %></p>
  </div>
<% end %>
```

---

## Scenario 8: Form Object for Complex Input

### Before

```ruby
class RegistrationsController < ApplicationController
  def create
    @user = User.new(user_params)
    @user.profile = Profile.new(profile_params)

    if @user.email.end_with?("@company.com")
      @user.role = :employee
      @user.team = Team.find_by(department: profile_params[:department])
    end

    if @user.save
      UserMailer.welcome(@user).deliver_later
      redirect_to dashboard_path
    else
      render :new, status: :unprocessable_entity
    end
  end

  private

  def user_params
    params.require(:user).permit(:email, :password, :name)
  end

  def profile_params
    params.require(:profile).permit(:bio, :department, :avatar)
  end
end
```

### After

```ruby
# app/forms/registration_form.rb
class RegistrationForm < ApplicationForm
  attribute :email, :string
  attribute :password, :string
  attribute :name, :string
  attribute :bio, :string
  attribute :department, :string
  attribute :avatar

  validates :email, :password, :name, presence: true
  validates :email, format: { with: URI::MailTo::EMAIL_REGEXP }
  validates :password, length: { minimum: 8 }

  def save
    return false unless valid?

    ApplicationRecord.transaction do
      create_user
      create_profile
      assign_team if company_email?
    end

    true
  rescue ActiveRecord::RecordInvalid => e
    errors.merge!(e.record.errors)
    false
  end

  attr_reader :user

  private

  def create_user
    @user = User.create!(
      email: email,
      password: password,
      name: name,
      role: company_email? ? :employee : :member
    )
  end

  def create_profile
    @user.create_profile!(bio: bio, department: department, avatar: avatar)
  end

  def assign_team
    @user.update!(team: Team.find_by(department: department))
  end

  def company_email?
    email.end_with?("@company.com")
  end
end

# app/controllers/registrations_controller.rb
class RegistrationsController < ApplicationController
  def create
    @form = RegistrationForm.new(registration_params)

    if @form.save
      UserMailer.welcome(@form.user).deliver_later
      redirect_to dashboard_path
    else
      render :new, status: :unprocessable_entity
    end
  end

  private

  def registration_params
    params.require(:registration).permit(:email, :password, :name, :bio, :department, :avatar)
  end
end
```

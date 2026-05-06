# Extract Callbacks to Service

Move multi-step user-creation side effects out of `after_create` callbacks into an explicit service.

## Before

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

## After

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

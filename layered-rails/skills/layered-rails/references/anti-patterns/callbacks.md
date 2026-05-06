# Callback Anti-Patterns

Misuses of Active Record callbacks that signal a layering problem.

## Contents

- Operation Callbacks
- Skip Callback Anti-Pattern
- Callback Control Flags

## Operation Callbacks

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

## Skip Callback Anti-Pattern

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

## Callback Control Flags

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

# Current Attributes

## Summary

`Current` is Rails' built-in thread-local storage for request-scoped context like current user, tenant, or request metadata. It enables implicit context passing but must be used carefully to avoid coupling layers.

## Layer Placement

```
┌─────────────────────────────────────────┐
│ Presentation Layer                      │
│  └─ Sets Current values in controllers  │
├─────────────────────────────────────────┤
│ Application Layer                       │
│  └─ May read Current (sparingly)        │
├─────────────────────────────────────────┤
│ Domain Layer                            │
│  └─ Should NOT access Current           │
└─────────────────────────────────────────┘
```

## Key Principles

- **Set at entry points** — controllers, jobs, middleware
- **Read sparingly** — prefer explicit parameters
- **Never in models** — domain layer must be Current-agnostic
- **Reset automatically** — Rails clears between requests

## Implementation

### Basic Current Class

```ruby
# app/models/current.rb
class Current < ActiveSupport::CurrentAttributes
  attribute :user, :request_id, :tenant

  resets { Time.zone = nil }

  def user=(user)
    super
    Time.zone = user&.time_zone
  end
end
```

### Setting in Controllers

```ruby
class ApplicationController < ActionController::Base
  before_action :set_current_attributes

  private

  def set_current_attributes
    Current.user = current_user
    Current.request_id = request.uuid
  end
end
```

### Multi-Tenancy with Current

```ruby
class Current < ActiveSupport::CurrentAttributes
  attribute :tenant

  def tenant=(tenant)
    super
    ActsAsTenant.current_tenant = tenant if defined?(ActsAsTenant)
  end
end

class ApplicationController < ActionController::Base
  before_action :set_tenant

  private

  def set_tenant
    Current.tenant = Tenant.find_by!(subdomain: request.subdomain)
  end
end
```

### In Background Jobs

```ruby
class ApplicationJob < ActiveJob::Base
  around_perform do |job, block|
    Current.set(
      user: job.arguments.first[:current_user],
      tenant: job.arguments.first[:current_tenant]
    ) do
      block.call
    end
  end
end

# Enqueue with context
ProcessOrderJob.perform_later(
  order: order,
  current_user: Current.user,
  current_tenant: Current.tenant
)
```

## Acceptable Uses

### Audit Logging

```ruby
class ApplicationRecord < ActiveRecord::Base
  before_save :set_audit_user

  private

  def set_audit_user
    self.updated_by = Current.user if respond_to?(:updated_by=)
    self.created_by = Current.user if respond_to?(:created_by=) && new_record?
  end
end
```

### Request Logging

```ruby
class ApplicationController < ActionController::Base
  around_action :tag_logs

  private

  def tag_logs
    Rails.logger.tagged(
      "user:#{Current.user&.id}",
      "request:#{Current.request_id}"
    ) { yield }
  end
end
```

### Time Zone

```ruby
class Current < ActiveSupport::CurrentAttributes
  attribute :user

  def user=(user)
    super
    Time.zone = user&.time_zone || "UTC"
  end
end
```

## Anti-Patterns

### Current in Models (Domain Layer)

```ruby
# BAD: Model accesses Current
class Post < ApplicationRecord
  belongs_to :author, class_name: "User"

  before_validation :set_author, on: :create

  def set_author
    self.author = Current.user  # Domain knows about request context!
  end
end

# GOOD: Explicit association
class Post < ApplicationRecord
  belongs_to :author, class_name: "User"
end

# Set in controller
class PostsController < ApplicationController
  def create
    @post = current_user.posts.build(post_params)
    # ...
  end
end
```

### Current for Business Logic

```ruby
# BAD: Business decisions based on Current
class Post < ApplicationRecord
  def can_publish?
    Current.user&.admin? || author == Current.user
  end
end

# GOOD: Pass context explicitly or use policies
class PostPolicy < ApplicationPolicy
  def publish?
    user.admin? || record.author == user
  end
end
```

### Current in Service Objects

```ruby
# BAD: Service implicitly depends on Current
class PublishPost
  def call(post)
    return unless Current.user&.can_publish?(post)  # Hidden dependency!
    post.publish!
  end
end

# GOOD: Explicit parameters
class PublishPost
  def call(post, by:)
    return unless PostPolicy.new(by, post).publish?
    post.publish!
  end
end

# Usage
PublishPost.new.call(post, by: current_user)
```

### Testing Difficulties

```ruby
# BAD: Tests must set Current
RSpec.describe Post do
  before { Current.user = create(:user) }  # Setup for every test!

  it "sets author" do
    post = Post.create!(title: "Test")
    expect(post.author).to eq(Current.user)
  end
end

# GOOD: Explicit association, no Current needed
RSpec.describe Post do
  it "belongs to author" do
    user = create(:user)
    post = user.posts.create!(title: "Test")
    expect(post.author).to eq(user)
  end
end
```

## Where Current IS Appropriate

| Use Case | Appropriate? | Notes |
|----------|--------------|-------|
| Audit trails | ✅ | Infrastructure concern |
| Request logging | ✅ | Infrastructure concern |
| Time zone | ✅ | Presentation concern |
| Locale | ✅ | Presentation concern |
| Multi-tenancy | ⚠️ | Use dedicated gems |
| Authorization | ❌ | Use policies |
| Business logic | ❌ | Pass explicitly |
| Model behavior | ❌ | Domain should be agnostic |

## Testing with Current

```ruby
# Use around block to ensure cleanup
RSpec.describe "request with current user" do
  around do |example|
    Current.set(user: create(:user)) { example.run }
  end

  it "logs with user context" do
    # Current.user available here
  end
end

# Or mock at boundaries
RSpec.describe PublishPost do
  let(:user) { create(:user) }
  let(:post) { create(:post, author: user) }

  it "publishes when authorized" do
    # No Current needed - explicit params
    result = described_class.new.call(post, by: user)
    expect(result).to be_success
  end
end
```

## Current vs Explicit Parameters

| Approach | Pros | Cons |
|----------|------|------|
| Current | Less boilerplate, automatic propagation | Hidden dependencies, testing complexity |
| Explicit | Clear dependencies, easy testing | More verbose, must pass through layers |

**Recommendation**: Default to explicit parameters. Use Current only for cross-cutting infrastructure concerns (logging, audit, time zone).

## Related

- [Anti-Patterns: Current in Models](../anti-patterns.md#current-in-models)

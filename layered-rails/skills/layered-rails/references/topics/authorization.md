# Authorization

## Summary

Authorization determines what authenticated users can do. It belongs in the application layer as policy objects, enforced at presentation layer entry points, never leaking into domain models.

## Layer Placement

```
┌─────────────────────────────────────────┐
│ Presentation Layer                      │
│  └─ Enforcement (authorize! calls)      │
├─────────────────────────────────────────┤
│ Application Layer                       │
│  └─ Policy Objects (rules live here)    │
├─────────────────────────────────────────┤
│ Domain Layer                            │
│  └─ Models operate in authorized context│
└─────────────────────────────────────────┘
```

## Key Principles

- **Single enforcement point** — authorize in controllers, nowhere else
- **Policies are application layer** — bridge between presentation and domain
- **Models are agnostic** — domain doesn't know about permissions
- **Scoping over checking** — load only accessible records when possible
- **Minimal rules** — `show?` for visibility, `manage?` for modifications
- **Composition over complexity** — delegate to other policies via `allowed_to?`

## Implementation with Action Policy

### Basic Policy

```ruby
class PostPolicy < ApplicationPolicy
  def show?
    true  # Public
  end

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
```

### Rule Design

Keep rules minimal and consistent:

| Rule | Purpose |
|------|---------|
| `show?` | Visibility — who can see this resource |
| `manage?` | Management — fallback for update?, destroy?, etc. |
| `create?` | Creation — often delegates to parent's manage? |
| `index?` | Listing — often same as show? or delegates to parent |

**Custom rules** are appropriate for domain operations (`transfer?`, `cancel?`) and parent policy groupings (`manage_billing?`). If a custom rule maps to a full controller with its own views, consider a dedicated resource instead.

### Controller Enforcement

```ruby
class PostsController < ApplicationController
  def show
    @post = Post.find(params[:id])
    authorize! @post
  end

  def update
    @post = Post.find(params[:id])
    authorize! @post

    if @post.update(post_params)
      redirect_to @post
    else
      render :edit, status: :unprocessable_entity
    end
  end
end
```

### Scoping-Based Authorization

Prefer loading only accessible records:

```ruby
class PostsController < ApplicationController
  def index
    @posts = authorized_scope(Post.all)
  end

  def destroy
    @post = authorized_scope(Post.all, as: :destroyable).find(params[:id])
    @post.destroy!
    redirect_to posts_path
  end
end

class PostPolicy < ApplicationPolicy
  # Default scope for index
  relation_scope do |scope|
    if user.admin?
      scope.all
    else
      scope.where(author: user).or(scope.published)
    end
  end

  # Named scope for specific actions
  relation_scope(:destroyable) do |scope|
    user.admin? ? scope.all : scope.where(author: user)
  end
end
```

### View Authorization

```erb
<% @posts.each do |post| %>
  <article>
    <h2><%= post.title %></h2>

    <% if allowed_to?(:update?, post) %>
      <%= link_to "Edit", edit_post_path(post) %>
    <% end %>

    <% if allowed_to?(:destroy?, post) %>
      <%= button_to "Delete", post, method: :delete %>
    <% end %>
  </article>
<% end %>
```

### Role-Based Access Control (RBAC)

```ruby
class User < ApplicationRecord
  ROLES = %w[reader editor admin].freeze
  enum :role, ROLES.zip(ROLES).to_h

  PERMISSIONS = {
    reader: %i[read],
    editor: %i[read create update],
    admin: %i[read create update delete manage_users]
  }.freeze

  def permission?(name)
    PERMISSIONS.fetch(role.to_sym, []).include?(name)
  end
end

class ApplicationPolicy < ActionPolicy::Base
  def permission?(name)
    user.permission?(name)
  end
end

class PostPolicy < ApplicationPolicy
  def update?
    permission?(:update) && (owner? || permission?(:manage_users))
  end
end
```

### Attribute-Based Access Control (ABAC)

```ruby
class DocumentPolicy < ApplicationPolicy
  def view?
    return true if record.public?
    return true if user.department == record.department
    return true if record.shared_with?(user)
    false
  end

  def edit?
    return false if record.locked?
    return true if record.owner == user
    return true if user.manager_of?(record.owner)
    false
  end
end
```

## Error Handling

Return 404 for visibility failures (don't leak resource existence), 403 for permission failures:

```ruby
module Authorization
  extend ActiveSupport::Concern

  included do
    rescue_from ActionPolicy::Unauthorized, with: :handle_unauthorized
  end

  private

  def handle_unauthorized(exception)
    if exception.rule == :show?
      raise ActiveRecord::RecordNotFound  # 404 - don't leak existence
    else
      head :forbidden  # 403 - record exists but action denied
    end
  end
end
```

## Anti-Patterns

### Authorization in Models

```ruby
# BAD: Domain layer knows about permissions
class Post < ApplicationRecord
  def editable_by?(user)
    author == user || user.admin?
  end
end

# GOOD: Keep in policy
class PostPolicy < ApplicationPolicy
  def update?
    owner? || admin?
  end
end
```

### Multiple Enforcement Points

```ruby
# BAD: Authorization in controller AND service
class PostsController < ApplicationController
  def publish
    authorize! @post, to: :publish?
    PublishService.call(@post, current_user)  # Checks again!
  end
end

class PublishService
  def call(post, user)
    raise unless PostPolicy.new(user, post).publish?  # Duplicate!
    post.publish!
  end
end

# GOOD: Single enforcement point
class PostsController < ApplicationController
  def publish
    authorize! @post, to: :publish?
    @post.publish!
  end
end
```

### Implicit Authorization

```ruby
# BAD: Authorization hidden in scope
class PostsController < ApplicationController
  def index
    @posts = current_user.posts  # Implicitly authorized
  end
end

# GOOD: Explicit authorization
class PostsController < ApplicationController
  def index
    @posts = authorized_scope(Post.all)
  end
end
```

## Testing

### Policy Unit Tests

```ruby
# RSpec
RSpec.describe PostPolicy do
  let(:user) { create(:user) }
  let(:admin) { create(:user, :admin) }
  let(:post) { create(:post) }

  describe "#update?" do
    it "allows owner" do
      post = create(:post, author: user)
      expect(PostPolicy.new(user, post).update?).to be true
    end

    it "allows admin" do
      expect(PostPolicy.new(admin, post).update?).to be true
    end

    it "denies others" do
      expect(PostPolicy.new(user, post).update?).to be false
    end
  end
end

# Minitest
class BoardPolicyTest < ActiveSupport::TestCase
  test "board creator can manage" do
    policy = BoardPolicy.new(@board, user: users(:david), account: @account)
    assert policy.apply(:manage?)
  end

  test "create uses board context" do
    policy = WebhookPolicy.new(board: @board, user: users(:david), account: @account)
    assert policy.apply(:create?)
  end
end
```

### Controller Authorization Tests

```ruby
# RSpec
RSpec.describe PostsController do
  include ActionPolicy::TestHelper

  describe "PUT #update" do
    it "authorizes the action" do
      post = create(:post)

      expect {
        put :update, params: { id: post.id, post: { title: "New" } }
      }.to be_authorized_to(:update?, post)
    end
  end
end

# Minitest
class PostsControllerTest < ActionDispatch::IntegrationTest
  include ActionPolicy::TestHelper

  test "update authorizes" do
    assert_authorized_to(:update?, posts(:one)) do
      put post_path(posts(:one)), params: { post: { title: "New" } }
    end
  end
end
```

## N+1 Authorization

```erb
<%# BAD: N policy checks %>
<% @posts.each do |post| %>
  <% if allowed_to?(:update?, post) %>
    <%= link_to "Edit", edit_post_path(post) %>
  <% end %>
<% end %>
```

Solutions:

1. **Preload required data** for policy checks
2. **Cache authorization** results
3. **Use scoping** instead of per-record checks

```ruby
# Preload in controller
class PostsController < ApplicationController
  def index
    @posts = Post.includes(:author).all
    @editable_ids = authorized_scope(Post.all, as: :editable).pluck(:id).to_set
  end
end

# In view
<% if @editable_ids.include?(post.id) %>
```

## Related

- [Policy Objects Pattern](../patterns/policy-objects.md)
- [Action Policy Gem](../gems/action-policy.md)

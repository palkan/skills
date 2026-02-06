# Action Policy

Authorization framework for Ruby and Rails applications.

**GitHub**: https://github.com/palkan/action_policy
**Layer**: Application

## Installation

```ruby
# Gemfile
gem "action_policy"

# Generate policy
rails generate action_policy:policy Post
```

## Basic Usage

### Define Policy

```ruby
class PostPolicy < ApplicationPolicy
  def show?
    true
  end

  def update?
    owner? || user.admin?
  end

  def destroy?
    user.admin?
  end

  private

  def owner?
    record.author_id == user.id
  end
end
```

### Controller Integration

```ruby
class PostsController < ApplicationController
  def show
    @post = Post.find(params[:id])
    authorize! @post
  end

  def update
    @post = Post.find(params[:id])
    authorize! @post

    @post.update!(post_params)
    redirect_to @post
  end
end
```

### View Integration

```erb
<% if allowed_to?(:update?, @post) %>
  <%= link_to "Edit", edit_post_path(@post) %>
<% end %>
```

## Scoping

Load only authorized records:

```ruby
class PostsController < ApplicationController
  def index
    @posts = authorized_scope(Post.all)
  end

  def destroy
    @post = authorized_scope(Post.all, as: :destroyable).find(params[:id])
    @post.destroy!
  end
end

class PostPolicy < ApplicationPolicy
  # Default scope for index
  relation_scope do |scope|
    if user.admin?
      scope.all
    else
      scope.published.or(scope.where(author: user))
    end
  end

  # Named scope
  relation_scope(:destroyable) do |scope|
    user.admin? ? scope.all : scope.where(author: user)
  end
end
```

## Rule Aliases

```ruby
class PostPolicy < ApplicationPolicy
  def manage?
    owner? || user.admin?
  end

  # Alias multiple rules to manage?
  alias_rule :create?, :update?, :destroy?, to: :manage?
end
```

## Minimal CRUD Rules

Keep policies small. Most policies need only two rules:

```ruby
class BoardPolicy < ApplicationPolicy
  def show?
    # Visibility - who can see this resource
    record.all_access? || has_access?
  end

  def manage?
    # Management - who can modify this resource
    board_admin?
  end

  # update?, edit?, destroy? automatically fall back to manage?
end
```

Action Policy provides:
- **Default rule:** `manage?` as fallback for undefined rules
- **Default alias:** `new? -> create?`

### When Custom Rules Make Sense

Custom rules are appropriate for:

**Domain operations** beyond CRUD:
```ruby
class AccountPolicy < ApplicationPolicy
  def transfer?
    owner? && record.transferable?
  end

  def cancel?
    owner? || admin?
  end
end

class ReportPolicy < ApplicationPolicy
  def show_sources?
    allowed_to?(:show?) && user.researcher?
  end
end
```

**Parent policy groupings** for related resources:
```ruby
class OrganizationPolicy < ApplicationPolicy
  def manage_billing?
    owner? || billing_admin?
  end

  def manage_members?
    owner? || admin?
  end
end

# Used across multiple controllers
authorize! @organization, to: :manage_billing?
```

### When to Consider New Resources

If a custom rule maps directly to a controller action with its own views and routes, consider a dedicated resource:

```ruby
# If you have:
# POST /cards/:id/archive
# GET /cards/:id/archive (confirmation page)
# DELETE /cards/:id/archive (unarchive)

# Consider: Cards::ArchivesController with ArchivePolicy
# Instead of: CardPolicy#can_archive?, #can_unarchive?
```

The goal is clarity, not strict adherence to patterns.

## Reason Tracking with `check?`

Use `check?` instead of direct predicate calls to track failure reasons:

```ruby
class AccountPolicy < ApplicationPolicy
  def manage?
    check?(:admin?)  # Tracks "admin?" as failure reason
  end

  def destroy?
    check?(:owner?)  # Tracks "owner?" as failure reason
  end
end
```

This enables debugging authorization failures:
```ruby
policy = AccountPolicy.new(user, account)
policy.apply(:manage?)
policy.result.reasons  #=> { admin?: false }
```

## Policy Composition

Delegate to other policies for nested authorization:

```ruby
class CommentPolicy < ApplicationPolicy
  authorize :card, optional: true

  def create?
    allowed_to?(:show?, card)  # Delegates to CardPolicy
  end

  def show?
    allowed_to?(:show?, record.card)  # Uses record's association
  end

  def manage?
    allowed_to?(:show?) && check?(:creator?)  # Combines both
  end
end
```

## Pre-Checks

Run before every rule:

```ruby
class ApplicationPolicy < ActionPolicy::Base
  pre_check :allow_admins

  private

  def allow_admins
    allow! if user.admin?
  end
end
```

## Authorization Context

For `create?` and `index?` rules where `record` isn't available, use authorization contexts:

```ruby
class WebhookPolicy < ApplicationPolicy
  authorize :board, optional: true  # optional: only needed for create?/index?

  def index?
    allowed_to?(:manage?, board)  # Uses context
  end

  def create?
    allowed_to?(:manage?, board)  # Uses context
  end

  def show?
    allowed_to?(:manage?, record.board)  # Uses record
  end
end
```

Register contexts via controller concerns:

```ruby
module BoardScoped
  extend ActiveSupport::Concern

  included do
    before_action :set_board
    authorize :board, through: -> { @board }
  end

  private

  def set_board
    @board = Current.account.boards.find_by!(slug: params[:board_id])
    authorize! @board, to: :show?
  end
end

class WebhooksController < ApplicationController
  include BoardScoped

  def index
    authorize!  # Uses WebhookPolicy with board context
    @webhooks = @board.webhooks
  end
end
```

## Error Handling

Return 404 for visibility failures (don't leak existence), 403 for permission failures:

```ruby
module Authorization
  extend ActiveSupport::Concern

  included do
    rescue_from ActionPolicy::Unauthorized, with: :handle_unauthorized
  end

  private

  def handle_unauthorized(exception)
    if exception.rule == :show?
      raise ActiveRecord::RecordNotFound  # 404
    else
      head :forbidden  # 403
    end
  end
end
```

## Gotchas

### View Context Syntax

Context must use `context:` hash:

```ruby
# Wrong
allowed_to?(:create?, Webhook, board: @board)

# Correct
allowed_to?(:create?, Webhook, context: {board: @board})
```

### Optional Contexts

Mark context as `optional: true` when only needed for some rules:

```ruby
authorize :board, optional: true  # Required for create?, not show?
```

## Testing

### Policy Unit Tests

```ruby
# RSpec
RSpec.describe PostPolicy do
  let(:user) { create(:user) }
  let(:post) { create(:post) }

  describe "#update?" do
    it "allows owner" do
      post = create(:post, author: user)
      expect(described_class.new(user, post).update?).to be true
    end

    it "denies non-owner" do
      expect(described_class.new(user, post).update?).to be false
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
    # Pass context as named argument, no record
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

  it "authorizes update" do
    expect {
      put :update, params: { id: post.id, post: { title: "New" } }
    }.to be_authorized_to(:update?, post)
  end
end

# Minitest
class WebhooksControllerTest < ActionDispatch::IntegrationTest
  include ActionPolicy::TestHelper

  test "index authorizes" do
    assert_authorized_to(:index?, Webhook) do
      get board_webhooks_path(boards(:writebook))
    end
  end

  test "show authorizes specific record" do
    webhook = webhooks(:active)
    assert_authorized_to(:show?, webhook) do
      get board_webhook_path(webhook.board, webhook)
    end
  end
end
```

## Related

- [Policy Objects Pattern](../patterns/policy-objects.md)
- [Authorization Topic](../topics/authorization.md)

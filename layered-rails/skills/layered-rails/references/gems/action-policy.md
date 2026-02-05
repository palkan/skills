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

Pass additional context:

```ruby
class PostPolicy < ApplicationPolicy
  authorize :account

  def publish?
    account.publishing_enabled? && owner?
  end
end

# In controller
authorize! @post, context: { account: current_account }
```

## Testing

```ruby
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

# Test enforcement
RSpec.describe PostsController do
  include ActionPolicy::TestHelper

  it "authorizes update" do
    expect {
      put :update, params: { id: post.id, post: { title: "New" } }
    }.to be_authorized_to(:update?, post)
  end
end
```

## Related

- [Policy Objects Pattern](../patterns/policy-objects.md)
- [Authorization Topic](../topics/authorization.md)

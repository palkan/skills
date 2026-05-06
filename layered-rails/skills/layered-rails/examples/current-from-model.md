# Extract Current from Model

Remove `Current.user` access from a domain model by moving authorization to a policy and ownership to the controller.

## Before

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

## After

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

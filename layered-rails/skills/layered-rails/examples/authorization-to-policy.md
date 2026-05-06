# Extract Authorization to Policy

Replace duplicated controller-side authorization checks with a policy object.

## Before

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

## After

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

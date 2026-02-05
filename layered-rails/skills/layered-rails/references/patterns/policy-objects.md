# Policy Objects

## Summary

Policy objects encapsulate authorization rules, determining whether a user can perform specific actions on resources. They belong to the application layer, sitting between presentation (enforcement) and domain (entities).

## When to Use

- Authorization logic beyond simple ownership checks
- Role-based or attribute-based access control
- Reusable authorization rules across controllers
- Testing authorization independently from controllers

## When NOT to Use

- Simple ownership checks (`post.user_id == current_user.id`)
- Authentication (who is this user?)

## Key Principles

- **Separate from authentication** — authentication identifies, authorization permits
- **Keep in services layer** — policies are application-layer abstractions
- **Never leak to domain** — models live in already-authorized context
- **Predicate interface** — methods return true/false
- **Convention-based lookup** — `PostPolicy` for `Post` model

## Implementation

### Plain Ruby Policy

```ruby
class BookPolicy
  attr_reader :user, :book

  def initialize(user, book)
    @user = user
    @book = book
  end

  def view?
    true
  end

  def destroy?
    user.permission?(:manage_all_books) || (
      user.permission?(:manage_books) &&
      book.dept == user.dept
    )
  end
end
```

### Usage in Controller

```ruby
class BooksController < ApplicationController
  def destroy
    book = Book.find(params[:id])

    if BookPolicy.new(current_user, book).destroy?
      book.destroy!
      redirect_to books_path, notice: "Removed"
    else
      redirect_to books_path, alert: "No access"
    end
  end
end
```

### With Action Policy (Recommended)

```ruby
class ApplicationPolicy < ActionPolicy::Base
  # Helper to access user permissions
  def permission?(name)
    user.permission?(name)
  end
end

class BookPolicy < ApplicationPolicy
  def view?
    true
  end

  def manage?
    permission?(:manage_all_books) || (
      permission?(:manage_books) &&
      record.dept == user.dept
    )
  end

  # Alias CRUD actions to manage?
  alias_rule :create?, :update?, :destroy?, to: :manage?
end
```

### Controller with `authorize!`

```ruby
class BooksController < ApplicationController
  def destroy
    book = Book.find(params[:id])
    authorize! book  # Infers BookPolicy#destroy?

    book.destroy!
    redirect_to books_path, notice: "Removed"
  end
end
```

## Authorization in Views

```erb
<% @books.each do |book| %>
  <li>
    <%= book.name %>
    <% if allowed_to?(:destroy?, book) %>
      <%= button_to "Delete", book, method: :delete %>
    <% end %>
  </li>
<% end %>
```

## Roles and Permissions

### Role-Based (RBAC)

```ruby
class User < ApplicationRecord
  enum :role, {regular: 0, admin: 1, librarian: 2}

  PERMISSIONS = {
    regular: %i[browse_catalogue borrow_books],
    librarian: %i[browse_catalogue borrow_books manage_books],
    admin: %i[browse_catalogue borrow_books manage_books manage_librarians]
  }.freeze

  def permission?(name)
    PERMISSIONS.fetch(role.to_sym, []).include?(name)
  end
end
```

### Attribute-Based (ABAC)

Any attribute can influence access:

```ruby
class BookPolicy < ApplicationPolicy
  def destroy?
    return true if permission?(:manage_all_books)
    return false unless permission?(:manage_books)

    # Attribute-based: department must match
    record.dept == user.dept
  end
end
```

## Scoping-Based Authorization

Combine data loading with authorization:

```ruby
class BooksController < ApplicationController
  def destroy
    # Only loads books the user can destroy
    book = authorized_scope(Book.all, as: :destroyable).find(params[:id])
    book.destroy!
    redirect_to books_path
  end
end

class BookPolicy < ApplicationPolicy
  relation_scope(:destroyable) do |scope|
    next scope.all if permission?(:manage_all_books)
    next scope.where(dept: user.dept) if permission?(:manage_books)
    scope.none
  end
end
```

## N+1 Authorization Problem

```erb
<% @posts.each do |post| %>
  <% if allowed_to?(:publish?, post) %>  <%# N checks! %>
    <%= button_to "Publish", ... %>
  <% end %>
<% end %>
```

**Solutions:**
- Preload data needed by policy rules
- Cache authorization results
- Use scoping-based authorization

## Testing

Test policy rules separately from enforcement:

```ruby
# Test policy rules
RSpec.describe BookPolicy do
  let(:user) { build(:user, role: :librarian, dept: "fiction") }
  let(:book) { build(:book, dept: "fiction") }
  let(:policy) { described_class.new(user, book) }

  describe "#destroy?" do
    it "allows librarians to destroy books in their department" do
      expect(policy.destroy?).to be true
    end

    it "denies librarians from other departments" do
      book.dept = "non-fiction"
      expect(policy.destroy?).to be false
    end
  end
end

# Test enforcement
RSpec.describe BooksController do
  include ActionPolicy::TestHelper

  it "authorizes destroy" do
    assert_authorized_to(:destroy?, book) do
      delete book_path(book)
    end
  end
end
```

## Anti-Patterns

### Authorization in Models

```ruby
# BAD
class Book < ApplicationRecord
  def destroyable_by?(user)
    user.admin? || user.dept == dept
  end
end

# GOOD: Keep in policy
class BookPolicy < ApplicationPolicy
  def destroy?
    # ...
  end
end
```

### Mixed Enforcement Layers

```ruby
# BAD: Authorization in both controller AND service
class BooksController
  def destroy
    authorize! @book  # Here...
    BookService.destroy(@book, current_user)
  end
end

class BookService
  def destroy(book, user)
    raise unless user.can_destroy?(book)  # ...and here!
  end
end

# GOOD: Single enforcement point
class BooksController
  def destroy
    authorize! @book
    @book.destroy!
  end
end
```

## Related Gems

| Gem | Purpose |
|-----|---------|
| action_policy | Authorization framework with policies |

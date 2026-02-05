# Presenters

## Summary

Presenters encapsulate representation logic for views. They bridge models and the view layer, extracting UI-specific formatting, CSS classes, and display logic from domain objects.

## When to Use

- View-specific formatting (dates, names, statuses)
- CSS class generation based on state
- Combining data from multiple models for display
- Logic that's only needed in views

## When NOT to Use

- Domain logic (belongs in models)
- Data transformation for APIs (use serializers)
- Simple attribute access

## Key Principles

- **Presentation layer** — never leak presenters to lower layers
- **Explicit interface (closed)** vs **delegation (open)** — choose based on isolation needs
- **One presenter per view context** — avoid god presenters
- **Test presenters independently** — no full request cycle needed

## Implementation

### Closed Presenter (Explicit Interface)

Best for strict isolation:

```ruby
class UserPresenter
  delegate :id, :to_model, to: :user

  private attr_reader :user

  def initialize(user)
    @user = user
  end

  def short_name
    user.name.squish.split(/\s/).then do |parts|
      parts[0..-2].map { _1[0] + "." }.join + parts.last
    end
  end

  def status_badge_class
    case user.status
    when "active" then "badge-success"
    when "pending" then "badge-warning"
    else "badge-secondary"
    end
  end

  def member_since
    user.created_at.strftime("%B %Y")
  end
end
```

### Open Presenter (Decorator)

Delegates all methods, adds presentation logic:

```ruby
class UserPresenter < SimpleDelegator
  def short_name
    name.squish.split(/\s/).then do |parts|
      parts[0..-2].map { _1[0] + "." }.join + parts.last
    end
  end

  def status_badge_class
    case status
    when "active" then "badge-success"
    when "pending" then "badge-warning"
    else "badge-secondary"
    end
  end
end
```

### Multi-Model Presenter

For composite UI elements:

```ruby
class User::BookPresenter < SimpleDelegator
  private attr_reader :book_read

  delegate :read?, :read_at, :score, to: :book_read

  def initialize(book, book_read)
    super(book)
    @book_read = book_read
  end

  def progress_icon
    read? ? "fa-circle-check" : "fa-clock"
  end

  def score_class
    case score
    when 0..2 then "text-red-600"
    when 3...4 then "text-yellow-600"
    when 4.. then "text-green-600"
    end
  end
end
```

### Presenter Helper

```ruby
module ApplicationHelper
  def present(obj, with: nil)
    presenter_class = with || "#{obj.class.name}Presenter".constantize
    presenter = presenter_class.new(obj)
    block_given? ? yield(presenter) : presenter
  end
end
```

### Usage in Views

```erb
<% present(@user) do |p| %>
  <span class="<%= p.status_badge_class %>">
    <%= p.short_name %>
  </span>
  <small>Member since <%= p.member_since %></small>
<% end %>
```

## With Keynote (Library)

```ruby
class UserPresenter < Keynote::Presenter
  presents :user

  def short_name
    user.name.squish.split(/\s/).then do |parts|
      parts[0..-2].map { _1[0] + "." }.join + parts.last
    end
  end

  # Access view helpers directly
  def avatar
    image_tag(user.avatar_url, class: "avatar")
  end
end
```

## Anti-Patterns

### Representation Logic in Models

```ruby
# BAD
class User < ApplicationRecord
  def status_badge_class
    case status
    when "active" then "badge-success"
    # ...
    end
  end
end

# GOOD: Move to presenter
class UserPresenter
  def status_badge_class
    # ...
  end
end
```

### Leaking Decorators

```ruby
# BAD: Creating presenter in controller, passing to service
def create
  @user = UserPresenter.new(User.find(params[:id]))
  SomeService.call(@user)  # Presenter leaked to application layer!
end

# GOOD: Present only in views
def show
  @user = User.find(params[:id])
end

# In view
<% present(@user) do |p| %>
  ...
<% end %>
```

### Global Helpers with Prefixes

```ruby
# BAD: Polluting helper namespace
module UsersHelper
  def user_short_name(user)
    # ...
  end

  def user_status_badge(user)
    # ...
  end
end

# GOOD: Encapsulate in presenter
class UserPresenter
  def short_name
  def status_badge_class
end
```

## Testing

```ruby
RSpec.describe UserPresenter do
  let(:user) { build(:user, name: "John Michael Doe", status: "active") }
  let(:presenter) { described_class.new(user) }

  describe "#short_name" do
    it "abbreviates middle names" do
      expect(presenter.short_name).to eq("J.M.Doe")
    end
  end

  describe "#status_badge_class" do
    it "returns success class for active users" do
      expect(presenter.status_badge_class).to eq("badge-success")
    end
  end
end
```

## Related Gems

| Gem | Purpose |
|-----|---------|
| keynote | Presenters with caching and view helpers |

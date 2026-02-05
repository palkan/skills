# ViewComponent

Framework for building reusable, testable view components.

**GitHub**: https://github.com/viewcomponent/view_component
**Layer**: Presentation

## Installation

```ruby
# Gemfile
gem "view_component"

# Generate component
rails generate component UserAvatar user size
```

## Basic Usage

### Define Component

```ruby
# app/components/user_avatar_component.rb
class UserAvatarComponent < ViewComponent::Base
  def initialize(user:, size: :medium)
    @user = user
    @size = size
  end

  private

  def size_class
    case @size
    when :small then "w-8 h-8"
    when :medium then "w-12 h-12"
    when :large then "w-16 h-16"
    end
  end
end
```

```erb
<%# app/components/user_avatar_component.html.erb %>
<div class="avatar <%= size_class %>">
  <% if @user.avatar.attached? %>
    <%= image_tag @user.avatar, class: "rounded-full" %>
  <% else %>
    <span class="avatar-initials"><%= @user.initials %></span>
  <% end %>
</div>
```

### Render Component

```erb
<%= render(UserAvatarComponent.new(user: @user, size: :large)) %>
```

## Slots

### Single Slot

```ruby
class CardComponent < ViewComponent::Base
  renders_one :header
  renders_one :footer
end
```

```erb
<%# Template %>
<div class="card">
  <% if header? %>
    <header><%= header %></header>
  <% end %>

  <div class="card-body"><%= content %></div>

  <% if footer? %>
    <footer><%= footer %></footer>
  <% end %>
</div>
```

```erb
<%# Usage %>
<%= render(CardComponent.new) do |card| %>
  <% card.with_header { "Title" } %>
  <p>Body content</p>
  <% card.with_footer { "Footer text" } %>
<% end %>
```

### Multiple Slots

```ruby
class ListComponent < ViewComponent::Base
  renders_many :items, ItemComponent

  class ItemComponent < ViewComponent::Base
    def initialize(title:)
      @title = title
    end
  end
end
```

## Collections

```ruby
class PostComponent < ViewComponent::Base
  with_collection_parameter :post

  def initialize(post:)
    @post = post
  end
end

# Render collection
<%= render(PostComponent.with_collection(@posts)) %>
```

## Inline Components

```ruby
class StatusBadgeComponent < ViewComponent::Base
  def initialize(status:)
    @status = status
  end

  def call
    content_tag :span, @status.titleize, class: "badge #{badge_class}"
  end

  private

  def badge_class
    case @status.to_sym
    when :active then "badge-success"
    when :pending then "badge-warning"
    else "badge-secondary"
    end
  end
end
```

## Stimulus Integration

```ruby
class DropdownComponent < ViewComponent::Base
  def initialize(label:)
    @label = label
  end
end
```

```erb
<div data-controller="dropdown">
  <button data-action="dropdown#toggle"><%= @label %></button>
  <div data-dropdown-target="menu" class="hidden">
    <%= content %>
  </div>
</div>
```

## Previews

```ruby
# test/components/previews/user_avatar_component_preview.rb
class UserAvatarComponentPreview < ViewComponent::Preview
  def small
    render(UserAvatarComponent.new(user: User.first, size: :small))
  end

  def medium
    render(UserAvatarComponent.new(user: User.first, size: :medium))
  end

  def large
    render(UserAvatarComponent.new(user: User.first, size: :large))
  end
end
```

Access at: `/rails/view_components/user_avatar_component/small`

## Testing

```ruby
RSpec.describe UserAvatarComponent, type: :component do
  it "renders avatar for user with image" do
    user = create(:user, :with_avatar)
    render_inline(described_class.new(user: user))

    expect(page).to have_css("img.rounded-full")
  end

  it "renders initials without image" do
    user = build(:user, name: "John Doe")
    render_inline(described_class.new(user: user))

    expect(page).to have_css(".avatar-initials", text: "JD")
  end

  it "applies size class" do
    user = build(:user)
    render_inline(described_class.new(user: user, size: :large))

    expect(page).to have_css(".w-16.h-16")
  end
end
```

## Related

- [View Components Topic](../topics/view-components.md)
- [Presenters Pattern](../patterns/presenters.md)

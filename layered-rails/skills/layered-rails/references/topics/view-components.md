# View Components

## Summary

View components are Ruby objects that encapsulate view logic, replacing complex partials with testable, reusable units. They bridge the presentation layer's need for logic with proper object-oriented design.

## Layer Placement

```
┌─────────────────────────────────────────┐
│ Presentation Layer                      │
│  ├─ Views (ERB/HTML)                    │
│  ├─ ViewComponents (logic + template)   │
│  └─ Presenters (view-specific logic)    │
└─────────────────────────────────────────┘
```

## When to Use

- Partials with complex logic
- Reusable UI elements across views
- Components needing isolated testing
- Preview/documentation requirements

## When NOT to Use

- Simple static markup (use partials)
- One-off display logic (use helpers)
- Data transformation (use presenters/serializers)

## Key Principles

- **Single responsibility** — one component, one purpose
- **Explicit interface** — typed inputs, no magic
- **Isolated testing** — unit test without full request
- **Composition** — build complex UIs from simple components

## Implementation

### Basic Component

```ruby
# app/components/user_avatar_component.rb
class UserAvatarComponent < ViewComponent::Base
  def initialize(user:, size: :medium)
    @user = user
    @size = size
  end

  def call
    if @user.avatar.attached?
      image_tag @user.avatar.variant(resize_to_limit: dimensions),
                class: css_class, alt: @user.name
    else
      content_tag :div, initials, class: "#{css_class} avatar-placeholder"
    end
  end

  private

  def initials
    @user.name.split.map(&:first).join.upcase[0, 2]
  end

  def dimensions
    case @size
    when :small then [32, 32]
    when :medium then [64, 64]
    when :large then [128, 128]
    end
  end

  def css_class
    "avatar avatar-#{@size}"
  end
end
```

### Component with Template

```ruby
# app/components/card_component.rb
class CardComponent < ViewComponent::Base
  renders_one :header
  renders_one :footer
  renders_many :actions

  def initialize(variant: :default)
    @variant = variant
  end
end
```

```erb
<%# app/components/card_component.html.erb %>
<article class="card card-<%= @variant %>">
  <% if header? %>
    <header class="card-header"><%= header %></header>
  <% end %>

  <div class="card-body">
    <%= content %>
  </div>

  <% if actions? %>
    <div class="card-actions">
      <% actions.each do |action| %>
        <%= action %>
      <% end %>
    </div>
  <% end %>

  <% if footer? %>
    <footer class="card-footer"><%= footer %></footer>
  <% end %>
</article>
```

### Usage in Views

```erb
<%= render(CardComponent.new(variant: :primary)) do |card| %>
  <% card.with_header { "Post Details" } %>

  <h2><%= @post.title %></h2>
  <p><%= @post.excerpt %></p>

  <% card.with_action do %>
    <%= link_to "Read more", @post, class: "btn" %>
  <% end %>

  <% card.with_action do %>
    <%= link_to "Share", share_path(@post), class: "btn btn-secondary" %>
  <% end %>

  <% card.with_footer { "Published #{time_ago_in_words(@post.published_at)} ago" } %>
<% end %>
```

### Component with Slots and Polymorphism

```ruby
class AlertComponent < ViewComponent::Base
  VARIANTS = {
    info: { icon: "info-circle", class: "alert-info" },
    success: { icon: "check-circle", class: "alert-success" },
    warning: { icon: "exclamation-triangle", class: "alert-warning" },
    error: { icon: "x-circle", class: "alert-error" }
  }.freeze

  renders_one :actions

  def initialize(variant: :info, dismissible: false)
    @variant = variant
    @dismissible = dismissible
  end

  def variant_config
    VARIANTS.fetch(@variant)
  end

  def dismissible?
    @dismissible
  end
end
```

### Component Composition

```ruby
class PostListComponent < ViewComponent::Base
  def initialize(posts:)
    @posts = posts
  end
end
```

```erb
<%# app/components/post_list_component.html.erb %>
<div class="post-list">
  <% @posts.each do |post| %>
    <%= render(PostCardComponent.new(post: post)) %>
  <% end %>
</div>
```

## Testing Components

```ruby
RSpec.describe UserAvatarComponent, type: :component do
  let(:user) { build(:user, name: "John Doe") }

  it "renders avatar image when attached" do
    user.avatar.attach(io: file_fixture("avatar.png").open, filename: "avatar.png")

    render_inline(described_class.new(user: user))

    expect(page).to have_css("img.avatar")
  end

  it "renders initials when no avatar" do
    render_inline(described_class.new(user: user))

    expect(page).to have_css(".avatar-placeholder", text: "JD")
  end

  it "applies size class" do
    render_inline(described_class.new(user: user, size: :large))

    expect(page).to have_css(".avatar-large")
  end
end
```

### Preview Components

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

  def without_avatar
    user = User.new(name: "Preview User")
    render(UserAvatarComponent.new(user: user))
  end
end
```

## Component Patterns

### Collection Component

```ruby
class PostListComponent < ViewComponent::Base
  include ViewComponent::Collection

  def initialize(post:)
    @post = post
  end
end

# Usage
<%= render(PostListComponent.with_collection(@posts)) %>
```

### Inline Component

```ruby
class StatusBadgeComponent < ViewComponent::Base
  STATUS_CLASSES = {
    draft: "badge-secondary",
    published: "badge-success",
    archived: "badge-muted"
  }.freeze

  def initialize(status:)
    @status = status.to_sym
  end

  def call
    content_tag :span, @status.to_s.titleize,
                class: "badge #{STATUS_CLASSES[@status]}"
  end
end
```

### Stimulus Integration

```ruby
class DropdownComponent < ViewComponent::Base
  def initialize(label:)
    @label = label
  end
end
```

```erb
<div data-controller="dropdown">
  <button data-action="dropdown#toggle">
    <%= @label %>
  </button>

  <div data-dropdown-target="menu" class="hidden">
    <%= content %>
  </div>
</div>
```

## Extraction Signals

### From Helpers

Extract helpers to ViewComponents when you see:

| Signal | Example | Action |
|--------|---------|--------|
| Heavy `tag.*` usage | `tag.div`, `tag.button` chains | Extract to component with template |
| Complex data attributes | `data: { controller: ..., action: ... }` | Component encapsulates Stimulus wiring |
| Conditional CSS classes | `class: "foo #{bar if baz}"` | Component method for class logic |
| Nested structure | Helper yielding to blocks with wrappers | Component with slots |
| Error handling in render | `rescue` in helper methods | Component with proper error boundaries |

**Before (Helper):**
```ruby
def message_area_tag(room, &)
  tag.div id: "message-area", class: "message-area", data: {
    controller: "messages presence drop-target",
    action: [ messages_actions, drop_target_actions, presence_actions ].join(" "),
    messages_page_url_value: room_messages_url(room)
  }, &
end
```

**After (ViewComponent):**
```ruby
class MessageAreaComponent < ViewComponent::Base
  def initialize(room:)
    @room = room
  end
end
```

```erb
<div id="message-area"
     class="message-area"
     data-controller="messages presence drop-target"
     data-action="<%= stimulus_actions %>"
     data-messages-page-url-value="<%= room_messages_url(@room) %>">
  <%= content %>
</div>
```

### From Presenters

Extract presenters to ViewComponents when:
- Presenter has a `render` method returning HTML
- Presenter accepts `context: self` for helper access
- Presenter builds complex markup via `content_tag` or `tag.*`

**Signal:** `SomePresentation.new(..., context: self).render`

This pattern indicates the presenter is doing component work without component benefits.

## Anti-Patterns

### Data Fetching in Components

```ruby
# BAD: Component fetches its own data
class RecentPostsComponent < ViewComponent::Base
  def initialize; end

  def posts
    @posts ||= Post.recent.limit(5)
  end
end

# GOOD: Data passed from controller
class RecentPostsComponent < ViewComponent::Base
  def initialize(posts:)
    @posts = posts
  end
end
```

### Business Logic in Components

```ruby
# BAD: Authorization in component
class PostActionsComponent < ViewComponent::Base
  def initialize(post:, user:)
    @post = post
    @user = user
  end

  def can_edit?
    @user.admin? || @post.author == @user  # Business logic!
  end
end

# GOOD: Receive authorization result
class PostActionsComponent < ViewComponent::Base
  def initialize(post:, can_edit:, can_delete:)
    @post = post
    @can_edit = can_edit
    @can_delete = can_delete
  end
end

# In controller/view
<%= render(PostActionsComponent.new(
  post: post,
  can_edit: allowed_to?(:update?, post),
  can_delete: allowed_to?(:destroy?, post)
)) %>
```

### God Components

```ruby
# BAD: Component does too much
class PostComponent < ViewComponent::Base
  # Renders post, comments, author, likes, shares, related posts...
end

# GOOD: Compose from smaller components
<%= render(PostHeaderComponent.new(post: @post)) %>
<%= render(PostBodyComponent.new(post: @post)) %>
<%= render(PostActionsComponent.new(post: @post, ...)) %>
<%= render(CommentsListComponent.new(comments: @post.comments)) %>
```

## File Organization

```
app/components/
├── application_component.rb
├── alert_component.rb
├── alert_component.html.erb
├── card_component.rb
├── card_component.html.erb
├── posts/
│   ├── card_component.rb
│   ├── card_component.html.erb
│   ├── list_component.rb
│   └── list_component.html.erb
└── users/
    ├── avatar_component.rb
    └── profile_card_component.rb
```

## Related

- [ViewComponent Gem](../gems/view-component.md)
- [Presenters Pattern](../patterns/presenters.md)

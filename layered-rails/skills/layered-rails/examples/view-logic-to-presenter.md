# Extract View Logic to Presenter

Move complex view computations out of templates into a presenter wrapping the model.

## Before

```erb
<%# app/views/users/show.html.erb %>
<div class="profile">
  <span class="badge <%= user.status == 'active' ? 'badge-success' : user.status == 'pending' ? 'badge-warning' : 'badge-secondary' %>">
    <%= user.status.titleize %>
  </span>

  <h1>
    <%= user.name.squish.split(/\s/).then { |parts| parts[0..-2].map { _1[0] + "." }.join + parts.last } %>
  </h1>

  <p>Member since <%= user.created_at.strftime("%B %Y") %></p>
</div>
```

## After

```ruby
# app/presenters/user_presenter.rb
class UserPresenter < SimpleDelegator
  def status_badge_class
    case status
    when "active" then "badge-success"
    when "pending" then "badge-warning"
    else "badge-secondary"
    end
  end

  def short_name
    name.squish.split(/\s/).then do |parts|
      parts[0..-2].map { _1[0] + "." }.join + parts.last
    end
  end

  def member_since
    created_at.strftime("%B %Y")
  end
end
```

```erb
<%# app/views/users/show.html.erb %>
<% present(@user) do |user| %>
  <div class="profile">
    <span class="badge <%= user.status_badge_class %>">
      <%= user.status.titleize %>
    </span>

    <h1><%= user.short_name %></h1>

    <p>Member since <%= user.member_since %></p>
  </div>
<% end %>
```

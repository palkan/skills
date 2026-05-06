# Helper Anti-Patterns

Helpers doing work that belongs in templates or components.

## HTML Construction in Helpers

**Problem:** Helpers building HTML programmatically instead of providing logic for templates.

```ruby
# BAD: Helper constructs HTML
module MessagesHelper
  def message_tag(message, &)
    tag.div id: dom_id(message),
      class: "message #{"message--emoji" if message.plain_text_body.all_emoji?}",
      data: {
        controller: "reply",
        user_id: message.creator_id,
        message_id: message.id,
        # ... many more data attributes
      }, &
  end
end
```

**Issues:**
- HTML structure hidden in Ruby code, harder to read and modify
- No template preview, harder to collaborate with designers
- Logic and markup tightly coupled
- Testing requires rendering, not unit testable
- Misses ViewComponent benefits (sidecar assets, previews, slots)

**Signal:** Heavy use of `tag.div`, `tag.button`, `tag.span` or complex `content_tag` chains.

**Fix:** Extract to ViewComponent with template.

```ruby
# GOOD: ViewComponent with template
class MessageComponent < ViewComponent::Base
  def initialize(message:)
    @message = message
  end

  def emoji_only?
    @message.plain_text_body.all_emoji?
  end

  def stimulus_data
    {
      controller: "reply",
      user_id: @message.creator_id,
      message_id: @message.id
    }
  end
end
```

```erb
<%# app/components/message_component.html.erb %>
<div id="<%= dom_id(@message) %>"
     class="message <%= "message--emoji" if emoji_only? %>"
     data="<%= stimulus_data.to_json %>">
  <%= content %>
</div>
```

**Rule of thumb:** If a helper method has more than 2-3 `tag.*` calls or builds nested HTML structure, extract to ViewComponent.

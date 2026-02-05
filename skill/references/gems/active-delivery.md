# Active Delivery

Abstraction layer over delivery mechanisms (email, push, SMS, etc.).

**GitHub**: https://github.com/palkan/active_delivery
**Layer**: Application (delivery classes) / Infrastructure (notifiers)

## Installation

```ruby
# Gemfile
gem "active_delivery"

# Generate delivery
rails generate delivery Posts
```

## Basic Usage

### Define Delivery

```ruby
# app/deliveries/posts_delivery.rb
class PostsDelivery < ApplicationDelivery
  deliver_by :mailer

  def published(post)
    params(post: post, author: post.author)
  end

  def commented(post, comment)
    params(post: post, comment: comment, author: post.author)
  end
end
```

### Define Mailer

```ruby
# app/mailers/posts_mailer.rb
class PostsMailer < ApplicationMailer
  def published
    @post = params[:post]
    @author = params[:author]

    mail(to: @author.email, subject: "Your post is published!")
  end

  def commented
    @post = params[:post]
    @comment = params[:comment]

    mail(to: params[:author].email, subject: "New comment on your post")
  end
end
```

### Trigger Delivery

```ruby
# Deliver later (async)
PostsDelivery.with(post: post).published.deliver_later

# Deliver now (sync)
PostsDelivery.with(post: post).published.deliver_now
```

## Multiple Channels

```ruby
class PostsDelivery < ApplicationDelivery
  deliver_by :mailer
  deliver_by :push, to: PushNotifier
  deliver_by :slack, to: SlackNotifier

  def published(post)
    params(post: post, author: post.author)
  end
end

# Push notifier
class PushNotifier < AbstractNotifier::Base
  self.driver = PushDriver.new

  def published
    notification(
      user: params[:author],
      title: "Post Published",
      body: "Your post '#{params[:post].title}' is now live!"
    )
  end
end

# Slack notifier
class SlackNotifier < AbstractNotifier::Base
  self.driver = SlackDriver.new

  def published
    notification(
      channel: "#content",
      text: "New post: #{params[:post].title}"
    )
  end
end
```

## Conditional Delivery

```ruby
class PostsDelivery < ApplicationDelivery
  deliver_by :mailer
  deliver_by :push, if: :push_enabled?
  deliver_by :slack, if: -> { params[:post].featured? }

  private

  def push_enabled?
    params[:author]&.push_notifications_enabled?
  end
end
```

## User Preferences

```ruby
class ApplicationDelivery < ActiveDelivery::Base
  deliver_by :mailer, if: :email_enabled?
  deliver_by :push, if: :push_enabled?

  private

  def recipient
    params[:user] || params[:recipient] || params[:author]
  end

  def email_enabled?
    recipient&.email_notifications?
  end

  def push_enabled?
    recipient&.push_notifications?
  end
end
```

## Custom Delivery Lines

```ruby
# Webhook delivery
class WebhookLine < ActiveDelivery::Lines::Base
  def resolve_class(name)
    "#{name}Webhook".safe_constantize
  end

  def notify(handler, mid, **options)
    handler.public_send(mid)&.deliver
  end
end

ActiveDelivery::Base.register_line :webhook, WebhookLine

class PostsDelivery < ApplicationDelivery
  deliver_by :webhook
end

class PostsWebhook
  def published
    # Send webhook
  end
end
```

## Testing

```ruby
RSpec.describe PostsDelivery do
  let(:post) { create(:post) }

  describe "#published" do
    it "delivers email" do
      expect {
        described_class.with(post: post).published.deliver_now
      }.to have_delivered_to(PostsMailer, :published)
    end

    it "delivers push notification when enabled" do
      post.author.update!(push_notifications: true)

      expect {
        described_class.with(post: post).published.deliver_now
      }.to have_delivered_to(PushNotifier, :published)
    end

    it "skips push when disabled" do
      post.author.update!(push_notifications: false)

      expect {
        described_class.with(post: post).published.deliver_now
      }.not_to have_delivered_to(PushNotifier, :published)
    end
  end
end
```

## Inline Mode (Development)

```ruby
# config/environments/development.rb
config.active_delivery.deliver_later_queue_adapter = :inline
```

## Related

- [Notifications Topic](../topics/notifications.md)

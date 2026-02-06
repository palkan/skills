# Notifications

## Summary

Notifications deliver messages through multiple channels (email, SMS, push, in-app). Active Delivery provides a layer of abstraction over delivery mechanisms, making notifications a first-class domain concept.

## Layer Placement

```
┌─────────────────────────────────────────┐
│ Application Layer                       │
│  └─ Delivery classes (what to send)     │
├─────────────────────────────────────────┤
│ Infrastructure Layer                    │
│  └─ Mailers, SMS adapters (how to send) │
└─────────────────────────────────────────┘
```

## Key Principles

- **Delivery abstraction** — separate what from how
- **Channel-agnostic** — same notification, multiple delivery methods
- **Testable** — verify notifications without infrastructure
- **Configurable** — enable/disable channels per notification type

## Implementation with Active Delivery

### Basic Setup

```ruby
# Delivery class (application layer)
class PostsDelivery < ApplicationDelivery
  # Automatically routes to PostsMailer and other lines
  deliver_by :mailer
  deliver_by :slack, to: SlackNotifier

  def published(post)
    # Params available to all delivery lines
    params(post: post, author: post.author)
  end
end

# Mailer (infrastructure layer)
class PostsMailer < ApplicationMailer
  def published
    @post = params[:post]
    @author = params[:author]

    mail(
      to: @author.email,
      subject: "Your post '#{@post.title}' is now live!"
    )
  end
end

# Slack notifier (infrastructure layer)
class SlackNotifier < AbstractNotifier::Base
  self.driver = SlackDriver.new

  def published
    @post = params[:post]

    notification(
      channel: "#content",
      text: "New post published: #{@post.title}"
    )
  end
end
```

### Triggering Notifications

```ruby
# In service or callback
class PublishPost
  def call(post)
    post.publish!
    PostsDelivery.with(post: post).published.deliver_later
  end
end

# Or inline delivery
PostsDelivery.with(post: post).published.deliver_now
```

### Conditional Delivery

```ruby
class PostsDelivery < ApplicationDelivery
  deliver_by :mailer
  deliver_by :slack, if: -> { params[:post].featured? }
  deliver_by :push, unless: -> { params[:author].push_disabled? }

  def published(post)
    params(post: post, author: post.author)
  end
end
```

### User Preferences

```ruby
class ApplicationDelivery < ActiveDelivery::Base
  deliver_by :mailer, if: :email_enabled?
  deliver_by :push, if: :push_enabled?
  deliver_by :sms, if: :sms_enabled?

  private

  def email_enabled?
    recipient&.notification_settings&.email_enabled?
  end

  def push_enabled?
    recipient&.notification_settings&.push_enabled?
  end

  def sms_enabled?
    recipient&.notification_settings&.sms_enabled?
  end

  def recipient
    params[:user] || params[:recipient]
  end
end
```

### Testing Deliveries

```ruby
RSpec.describe PostsDelivery do
  let(:post) { create(:post) }

  describe "#published" do
    it "sends email notification" do
      expect {
        described_class.with(post: post).published.deliver_now
      }.to have_delivered_to(PostsMailer, :published)
    end

    it "sends slack notification for featured posts" do
      post = create(:post, :featured)

      expect {
        described_class.with(post: post).published.deliver_now
      }.to have_delivered_to(SlackNotifier, :published)
    end
  end
end
```

## Without Active Delivery

### Service-Based Approach

```ruby
class NotifyPostPublished
  def initialize(post)
    @post = post
  end

  def call
    send_email
    send_push if post.author.push_enabled?
    send_slack if post.featured?
  end

  private

  attr_reader :post

  def send_email
    PostsMailer.published(post).deliver_later
  end

  def send_push
    PushService.deliver(
      user: post.author,
      title: "Post Published",
      body: "Your post '#{post.title}' is now live!"
    )
  end

  def send_slack
    SlackService.post(
      channel: "#content",
      text: "New featured post: #{post.title}"
    )
  end
end

# Usage
NotifyPostPublished.new(post).call
```

## Triggering from Workflows

When notifications are tied to state transitions, standalone workflows are an ideal place to trigger them via `after_transition` callbacks. This keeps models free of notification logic while centralizing state-related side effects.

See [Triggering Deliveries from Workflows](../patterns/state-machines.md#triggering-deliveries-from-workflows) for implementation details.

## Anti-Patterns

### Notifications in Models

```ruby
# BAD: Domain layer sending notifications
class Post < ApplicationRecord
  after_update :notify_if_published

  private

  def notify_if_published
    return unless saved_change_to_published_at?
    PostsMailer.published(self).deliver_later
  end
end

# GOOD: Notifications from application layer
class PublishPost
  def call(post)
    post.publish!
    PostsDelivery.with(post: post).published.deliver_later
  end
end
```

### Mailer Knows Too Much

```ruby
# BAD: Mailer with business logic
class PostsMailer < ApplicationMailer
  def published(post)
    @post = post

    if post.featured?
      notify_editors(post)
    end

    mail(to: post.author.email, subject: subject_for(post))
  end

  private

  def notify_editors(post)
    # More business logic in mailer!
  end
end

# GOOD: Mailer only formats and sends
class PostsMailer < ApplicationMailer
  def published
    @post = params[:post]
    mail(to: @post.author.email, subject: "Post published!")
  end
end

# Business logic in delivery or service
class PostsDelivery < ApplicationDelivery
  deliver_by :mailer
  deliver_by :editor_mailer, if: -> { params[:post].featured? }
end
```

### Inline Notification Logic

```ruby
# BAD: Scattered notification logic
class PostsController < ApplicationController
  def publish
    @post.publish!
    PostsMailer.published(@post).deliver_later
    SlackService.post(channel: "#content", text: "...")
    PushService.deliver(user: @post.author, ...)
  end
end

# GOOD: Encapsulated in delivery
class PostsController < ApplicationController
  def publish
    @post.publish!
    PostsDelivery.with(post: @post).published.deliver_later
  end
end
```

## Delivery Patterns

### Batch Notifications

```ruby
class DigestDelivery < ApplicationDelivery
  def daily_digest(user, posts)
    return if posts.empty?
    params(user: user, posts: posts)
  end
end

# Scheduled job
class DailyDigestJob < ApplicationJob
  def perform
    User.digest_enabled.find_each do |user|
      posts = user.unread_posts.where(created_at: 1.day.ago..)
      DigestDelivery.with(user: user, posts: posts).daily_digest.deliver_later
    end
  end
end
```

### Notification Objects

```ruby
class Notification < ApplicationRecord
  belongs_to :user
  belongs_to :notifiable, polymorphic: true

  scope :unread, -> { where(read_at: nil) }

  def mark_read!
    touch(:read_at)
  end
end

class PostsDelivery < ApplicationDelivery
  deliver_by :mailer
  deliver_by :database, to: DatabaseNotifier

  def published(post)
    params(post: post, user: post.author)
  end
end

class DatabaseNotifier < AbstractNotifier::Base
  def published
    Notification.create!(
      user: params[:user],
      notifiable: params[:post],
      kind: "post_published",
      data: { title: params[:post].title }
    )
  end
end
```

## Related

- [Active Delivery Gem](../gems/active-delivery.md)
- [Callbacks Topic](./callbacks.md)

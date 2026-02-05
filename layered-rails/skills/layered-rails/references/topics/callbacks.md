# Callbacks

## Summary

Callbacks are hooks into object lifecycle events. While Rails provides extensive callback support, overuse leads to tangled dependencies and hidden behavior. Use callbacks judiciously, preferring explicit operations.

## Callback Scoring System

Rate callbacks on a 5-point scale:

| Score | Type | Description | Example |
|-------|------|-------------|---------|
| 5/5 | Transformer | Pure data transformation | `before_validation :normalize_email` |
| 4/5 | Maintainer | Internal consistency | `before_save :update_cached_count` |
| 3/5 | Timestamp | Set time-based attributes | `before_create :set_published_at` |
| 2/5 | Background trigger | Enqueue async work | `after_commit :enqueue_indexing` |
| 1/5 | Operation | Synchronous side effects | `after_create :send_welcome_email` |

**Rule**: Avoid callbacks scoring below 3/5. Extract to explicit service objects.

## Good Callbacks (4-5/5)

### Transformers

```ruby
class User < ApplicationRecord
  before_validation :normalize_email
  before_validation :strip_whitespace

  private

  def normalize_email
    self.email = email&.downcase&.strip
  end

  def strip_whitespace
    self.name = name&.strip
  end
end
```

### Maintainers

```ruby
class Post < ApplicationRecord
  has_many :comments

  before_save :update_comments_count, if: :comments_changed?

  private

  def update_comments_count
    self.comments_count = comments.count
  end
end
```

### Safe Timestamps

```ruby
class Article < ApplicationRecord
  before_create :set_published_at, if: -> { published? && published_at.blank? }

  private

  def set_published_at
    self.published_at = Time.current
  end
end
```

## Problematic Callbacks (1-2/5)

### Background Triggers (2/5)

```ruby
# Acceptable but consider explicit service
class Post < ApplicationRecord
  after_commit :enqueue_indexing, on: [:create, :update]

  private

  def enqueue_indexing
    IndexPostJob.perform_later(id)
  end
end
```

### Operations (1/5) — Extract These

```ruby
# BAD: Synchronous side effects in callback
class User < ApplicationRecord
  after_create :send_welcome_email
  after_create :create_default_workspace
  after_create :notify_admin
  after_create :track_signup

  private

  def send_welcome_email
    UserMailer.welcome(self).deliver_later
  end

  def create_default_workspace
    workspaces.create!(name: "My Workspace")
  end

  def notify_admin
    AdminNotifier.new_signup(self)
  end

  def track_signup
    Analytics.track("user_signed_up", user_id: id)
  end
end

# GOOD: Explicit service object
class CreateUser
  def call(params)
    user = User.create!(params)

    UserMailer.welcome(user).deliver_later
    user.workspaces.create!(name: "My Workspace")
    AdminNotifier.new_signup(user)
    Analytics.track("user_signed_up", user_id: user.id)

    user
  end
end
```

## Callback Anti-Patterns

### Conditional Complexity

```ruby
# BAD: Complex conditions in callbacks
class Order < ApplicationRecord
  after_save :process_completion

  private

  def process_completion
    return unless saved_change_to_status?
    return unless status == "completed"
    return if processed_at.present?

    # This logic is hard to follow and test
    update_inventory
    charge_payment
    send_confirmation
    notify_warehouse
  end
end

# GOOD: Explicit state transition
class CompleteOrder
  def call(order)
    order.transaction do
      order.update!(status: "completed", processed_at: Time.current)
      update_inventory(order)
      charge_payment(order)
    end

    send_confirmation(order)
    notify_warehouse(order)
  end
end
```

### Callback Chains

```ruby
# BAD: Callbacks triggering other callbacks
class Post < ApplicationRecord
  after_save :update_author_stats

  def update_author_stats
    author.update!(posts_count: author.posts.count)
    # This triggers Author callbacks!
  end
end

class Author < ApplicationRecord
  after_save :recalculate_ranking
  # And so on...
end

# GOOD: Counter cache or explicit service
class Post < ApplicationRecord
  belongs_to :author, counter_cache: true
end
```

### Testing Difficulties

```ruby
# BAD: Can't create User without side effects
class User < ApplicationRecord
  after_create :send_welcome_email
end

# Test must deal with email sending
user = User.create!(name: "Test")  # Email sent!

# GOOD: Service allows isolated testing
class CreateUser
  def call(params)
    User.create!(params).tap do |user|
      UserMailer.welcome(user).deliver_later
    end
  end
end

# Test model in isolation
user = User.create!(name: "Test")  # No side effects
```

### Skip Callback Temptation

```ruby
# BAD: Need to skip callbacks = smell
User.skip_callback(:create, :after, :send_welcome_email)
user = User.create!(attributes)
User.set_callback(:create, :after, :send_welcome_email)

# GOOD: Callbacks don't need skipping
user = User.create!(attributes)
# Side effects in separate service when needed
```

## When Callbacks ARE Appropriate

1. **Data normalization** — cleaning input before save
2. **Derived attributes** — calculating values from other attributes
3. **Internal state consistency** — keeping model internally valid
4. **Soft deletes** — setting timestamps on destroy

```ruby
class Document < ApplicationRecord
  # All appropriate callbacks
  before_validation :normalize_filename
  before_save :update_word_count
  before_destroy :set_deleted_at, prepend: true

  private

  def normalize_filename
    self.filename = filename&.parameterize
  end

  def update_word_count
    self.word_count = content&.split&.size || 0
  end

  def set_deleted_at
    update!(deleted_at: Time.current)
    throw(:abort)  # Prevent actual deletion
  end
end
```

## Callback to Service Extraction

Before (callbacks):

```ruby
class Article < ApplicationRecord
  after_create :notify_subscribers
  after_update :sync_to_search, if: :published?
  after_destroy :cleanup_attachments
end
```

After (services):

```ruby
class Article < ApplicationRecord
  # Only data-focused callbacks
  before_validation :normalize_slug
end

# In controller
class ArticlesController < ApplicationController
  def create
    @article = CreateArticle.call(article_params)
    redirect_to @article
  end

  def update
    @article = UpdateArticle.call(@article, article_params)
    redirect_to @article
  end

  def destroy
    DestroyArticle.call(@article)
    redirect_to articles_path
  end
end
```

## Testing Callback-Light Models

```ruby
RSpec.describe User do
  # Easy to test: no side effects
  describe "email normalization" do
    it "downcases email" do
      user = User.new(email: "TEST@EXAMPLE.COM")
      user.valid?
      expect(user.email).to eq("test@example.com")
    end
  end
end

RSpec.describe CreateUser do
  # Test side effects explicitly
  it "sends welcome email" do
    expect {
      described_class.call(user_params)
    }.to have_enqueued_mail(UserMailer, :welcome)
  end
end
```

## Related

- [Service Objects Pattern](../patterns/service-objects.md)
- [Extraction Signals](../core/extraction-signals.md)

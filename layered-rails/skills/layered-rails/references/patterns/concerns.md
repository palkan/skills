# Concerns

## Summary

Concerns are Ruby modules with `ActiveSupport::Concern` that extend model capabilities. They're Rails' built-in mechanism for composition, but require discipline to avoid becoming a dumping ground for unrelated code.

## When to Use

- Shared behavior across multiple models
- Cohesive feature sets (soft delete, auditing, slugging)
- Interface extraction (common protocol for different models)
- Reducing model file size while maintaining cohesion

## When NOT to Use

- Single-model "organization" (hiding complexity)
- Unrelated methods grouped together
- Callbacks that should be explicit operations
- As a substitute for proper abstractions

## Key Principles

- **Cohesion over organization** — concerns group related behavior, not random methods
- **Explicit dependencies** — document what the including class must provide
- **Test concerns independently** — don't rely on specific model setup
- **Prefer composition** — consider service objects before concerns

## Concern Health Check

Signs of healthy concerns:

```ruby
# GOOD: Cohesive, single responsibility
module Sluggable
  extend ActiveSupport::Concern

  included do
    before_validation :generate_slug, if: :should_generate_slug?
  end

  def to_param
    slug
  end

  private

  def generate_slug
    self.slug = title.parameterize
  end

  def should_generate_slug?
    slug.blank? && title.present?
  end
end
```

Signs of unhealthy concerns:

```ruby
# BAD: Kitchen sink concern
module PostExtensions
  extend ActiveSupport::Concern

  included do
    has_many :comments
    has_many :likes
    belongs_to :author

    scope :published, -> { where(published: true) }
    scope :recent, -> { order(created_at: :desc) }

    validates :title, presence: true
    validates :body, length: { minimum: 100 }

    after_create :notify_followers
    after_update :sync_to_search
  end

  def word_count
    body.split.size
  end

  def reading_time
    (word_count / 200.0).ceil
  end

  def notify_followers
    # ...
  end

  def sync_to_search
    # ...
  end
end
```

## Implementation

### Basic Concern

```ruby
module SoftDeletable
  extend ActiveSupport::Concern

  included do
    scope :kept, -> { where(deleted_at: nil) }
    scope :deleted, -> { where.not(deleted_at: nil) }

    default_scope { kept }
  end

  def soft_delete
    update!(deleted_at: Time.current)
  end

  def restore
    update!(deleted_at: nil)
  end

  def deleted?
    deleted_at.present?
  end
end
```

### Concern with Configuration

```ruby
module Auditable
  extend ActiveSupport::Concern

  included do
    has_many :audit_logs, as: :auditable, dependent: :destroy

    class_attribute :audited_attributes, default: []
  end

  class_methods do
    def audit(*attributes)
      self.audited_attributes = attributes
      after_update :create_audit_log, if: :audited_changes?
    end
  end

  private

  def audited_changes?
    (saved_changes.keys.map(&:to_sym) & audited_attributes).any?
  end

  def create_audit_log
    audit_logs.create!(
      changes: saved_changes.slice(*audited_attributes.map(&:to_s)),
      user: Current.user
    )
  end
end

# Usage
class Post < ApplicationRecord
  include Auditable
  audit :title, :body, :status
end
```

### Concern with Required Interface

```ruby
module Publishable
  extend ActiveSupport::Concern

  # Document required interface
  # Including class must have:
  # - published_at: datetime column
  # - author: association

  included do
    scope :published, -> { where.not(published_at: nil) }
    scope :draft, -> { where(published_at: nil) }
  end

  def publish!
    transaction do
      update!(published_at: Time.current)
      notify_author
    end
  end

  def published?
    published_at.present?
  end

  private

  def notify_author
    PublicationMailer.published(self).deliver_later
  end
end
```

### Interface Extraction

```ruby
# Multiple models share common interface
module Searchable
  extend ActiveSupport::Concern

  class_methods do
    def searchable_attributes(*attrs)
      @searchable_attributes = attrs
    end

    def search(query)
      return all if query.blank?

      conditions = @searchable_attributes.map do |attr|
        arel_table[attr].matches("%#{query}%")
      end

      where(conditions.reduce(:or))
    end
  end
end

class Post < ApplicationRecord
  include Searchable
  searchable_attributes :title, :body
end

class User < ApplicationRecord
  include Searchable
  searchable_attributes :name, :email
end
```

## Concern vs Other Patterns

| Need | Pattern |
|------|---------|
| Shared query logic | Query object |
| Cross-cutting callbacks | Service object |
| State-dependent behavior | State machine |
| External API integration | Service object |
| Shared validations | Concern (carefully) |
| Shared associations | Concern |

## Testing Concerns

```ruby
RSpec.describe SoftDeletable do
  # Use anonymous class to test concern in isolation
  let(:model_class) do
    Class.new(ApplicationRecord) do
      self.table_name = "posts"
      include SoftDeletable
    end
  end

  let(:record) { model_class.create!(title: "Test") }

  describe "#soft_delete" do
    it "sets deleted_at timestamp" do
      expect { record.soft_delete }
        .to change { record.deleted_at }
        .from(nil)
    end
  end

  describe ".kept scope" do
    it "excludes soft-deleted records" do
      record.soft_delete
      expect(model_class.kept).not_to include(record)
    end
  end
end
```

## Anti-Patterns

### Single-Model Concerns

```ruby
# BAD: Concern used by only one model
module PostCallbacks
  extend ActiveSupport::Concern

  included do
    after_create :do_thing_1
    after_update :do_thing_2
    after_destroy :do_thing_3
  end
end

class Post < ApplicationRecord
  include PostCallbacks  # Only used here!
end

# GOOD: Keep in model or extract to service
class Post < ApplicationRecord
  after_create :do_thing_1
  # Or use service objects for complex operations
end
```

### Dependency Hiding

```ruby
# BAD: Concern hides critical dependencies
module Notifiable
  extend ActiveSupport::Concern

  included do
    after_create :send_notifications
  end

  def send_notifications
    NotificationService.new(self).deliver_all
  end
end

# Problem: Including Notifiable silently adds callback
# GOOD: Make dependency explicit
class Post < ApplicationRecord
  after_create -> { PostNotifications.new(self).deliver }
end
```

### Concern Chains

```ruby
# BAD: Concerns depending on other concerns
module A
  extend ActiveSupport::Concern
  included do
    include B  # Implicit dependency
  end
end

# GOOD: Explicit includes in model
class Post < ApplicationRecord
  include B
  include A
end
```

## File Organization

```
app/models/
├── concerns/
│   ├── auditable.rb
│   ├── publishable.rb
│   ├── searchable.rb
│   └── soft_deletable.rb
├── post.rb
└── user.rb
```

## Concern Checklist

Before creating a concern, verify:

- [ ] Will multiple models use this?
- [ ] Are all methods cohesively related?
- [ ] Is the interface documented?
- [ ] Could this be a service object instead?
- [ ] Are callbacks necessary or hiding complexity?

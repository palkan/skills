# Concern Anti-Patterns

Misuses of `ActiveSupport::Concern` that hide structural problems.

## Code-Slicing Concerns

**Problem:** Splitting model by Rails artifact type, not behavior.

```ruby
# BAD - Just groups related code, not a behavior
module Contactable
  extend ActiveSupport::Concern

  included do
    validates :email, presence: true
    validates :phone, format: { with: PHONE_REGEX }
    before_save :normalize_phone
  end

  def full_contact_info
    "#{email} / #{phone}"
  end
end
```

**Test:** If removing this concern breaks unrelated tests, it's code-slicing.

**Fix:** Keep in model or extract to value object.

```ruby
# GOOD - Behavioral concern (can be tested in isolation)
module Publishable
  extend ActiveSupport::Concern

  included do
    scope :published, -> { where.not(published_at: nil) }
    scope :draft, -> { where(published_at: nil) }
  end

  def published? = published_at.present?

  def publish!
    update!(published_at: Time.current)
  end
end
```

## Overgrown Concerns

**Problem:** Concern has too many responsibilities.

```ruby
# BAD - Too much in one concern
module WithMedia
  extend ActiveSupport::Concern

  included do
    has_many_attached :images
    has_many_attached :videos
    has_one_attached :thumbnail

    after_commit :process_images
    after_commit :generate_thumbnail
    after_commit :transcode_videos
  end

  def images_ready? = # ...
  def videos_ready? = # ...
  def thumbnail_url = # ...
  def processing_status = # ...
  # 50 more methods...
end
```

**Fix:** Extract to delegate object or separate concerns.

```ruby
# GOOD
class Post::MediaProcessor
  def initialize(post)
    @post = post
  end

  def process_all
    process_images
    generate_thumbnail
    transcode_videos
  end

  # ...
end
```

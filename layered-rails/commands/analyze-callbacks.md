# /layers:analyze-callbacks

Deep analysis of Active Record callbacks in the codebase.

## Purpose

Audit callbacks using the scoring system, identifying candidates for extraction to explicit service objects.

## Usage

```
/layers:analyze-callbacks [path]
```

- Without path: Analyzes all models in `app/models/`
- With path: Analyzes specific file or directory

## Callback Scoring System

### 5/5 - Transformer (Keep)
Pure data transformation on the same object.

```ruby
before_validation :normalize_email

def normalize_email
  self.email = email&.downcase&.strip
end
```

### 4/5 - Maintainer (Keep)
Maintains internal object consistency.

```ruby
before_save :update_cached_count

def update_cached_count
  self.comments_count = comments.size
end
```

### 3/5 - Timestamp (Acceptable)
Sets time-based attributes.

```ruby
before_create :set_published_at, if: :published?

def set_published_at
  self.published_at ||= Time.current
end
```

### 2/5 - Background Trigger (Consider Extracting)
Enqueues background work.

```ruby
after_commit :enqueue_indexing

def enqueue_indexing
  IndexRecordJob.perform_later(self)
end
```

### 1/5 - Operation (Extract)
Synchronous side effects, external communication.

```ruby
after_create :send_welcome_email     # External communication
after_create :create_default_records # Creates other records
after_save :notify_followers         # Side effects
after_update :sync_to_external_api   # External API calls
```

## Analysis Process

### 1. Find All Callbacks

```ruby
# Search patterns
CALLBACK_PATTERNS = %w[
  before_validation after_validation
  before_save after_save around_save
  before_create after_create around_create
  before_update after_update around_update
  before_destroy after_destroy around_destroy
  after_commit after_rollback
  after_touch after_find after_initialize
]
```

### 2. Score Each Callback

For each callback found:
1. Read the callback method body
2. Classify by what it does
3. Assign score
4. Note extraction recommendation

### 3. Identify Callback Chains

Look for models with multiple related callbacks:

```ruby
# WARNING: Callback chain detected
after_create :create_profile
after_create :send_welcome_email
after_create :notify_admin
after_create :track_signup
after_create :create_default_settings
```

### 4. Check for Skip Patterns

Search for callback skipping (indicates design smell):

```ruby
# RED FLAG: Callbacks being skipped
User.skip_callback(:create, :after, :send_email)
record.save(validate: false)
```

## Output Format

```markdown
# Callback Analysis Report

## Summary
- Total callbacks: 47
- Score 5/5 (keep): 12
- Score 4/5 (keep): 8
- Score 3/5 (acceptable): 5
- Score 2/5 (consider): 7
- Score 1/5 (extract): 15

## By Model

### User (app/models/user.rb)
| Line | Callback | Method | Score | Action |
|------|----------|--------|-------|--------|
| 15 | before_validation | normalize_email | 5/5 | Keep |
| 16 | before_validation | strip_whitespace | 5/5 | Keep |
| 18 | after_create | send_welcome_email | 1/5 | Extract |
| 19 | after_create | create_profile | 1/5 | Extract |
| 20 | after_create | notify_admin | 1/5 | Extract |

**Recommendation**: Create `CreateUser` service to handle registration flow.

### Order (app/models/order.rb)
| Line | Callback | Method | Score | Action |
|------|----------|--------|-------|--------|
| 22 | before_save | calculate_totals | 4/5 | Keep |
| 25 | after_save | update_inventory | 1/5 | Extract |
| 26 | after_save | charge_payment | 1/5 | Extract |
| 27 | after_commit | send_confirmation | 2/5 | Consider |

**Recommendation**: Create `CompleteOrder` service for post-save operations.

## Callback Chains

### User Registration Chain
```
after_create :send_welcome_email
after_create :create_profile
after_create :create_default_workspace
after_create :notify_admin
after_create :track_signup_analytics
```

**Recommendation**: Extract to `Users::Create` service:
```ruby
class Users::Create < ApplicationService
  def call(params)
    user = User.create!(params)

    UserMailer.welcome(user).deliver_later
    user.create_profile!
    user.workspaces.create!(name: "Default")
    AdminNotifier.new_signup(user)
    Analytics.track("signup", user_id: user.id)

    user
  end
end
```

## Skip Callback Usage

Found 3 instances of callback skipping:

1. `spec/models/user_spec.rb:45` - Test setup
2. `app/services/bulk_import.rb:78` - Bulk operation
3. `lib/tasks/migrate.rake:23` - Data migration

**Assessment**: Skip usage in tests is acceptable. Production code skipping suggests callback design issues.

## Extraction Priority

### High Priority (Extract Now)
1. **User** - 5 operation callbacks, clear service extraction
2. **Order** - Payment and inventory callbacks

### Medium Priority (Plan Extraction)
1. **Post** - Publication and notification callbacks
2. **Comment** - Notification callbacks

### Low Priority (Monitor)
1. **Profile** - Single background job callback
```

## Extraction Patterns

### Before: Callback Chain
```ruby
class User < ApplicationRecord
  after_create :send_welcome_email
  after_create :create_profile
  after_create :notify_admin

  private

  def send_welcome_email
    UserMailer.welcome(self).deliver_later
  end

  def create_profile
    Profile.create!(user: self)
  end

  def notify_admin
    AdminMailer.new_user(self).deliver_later
  end
end
```

### After: Service Object
```ruby
class User < ApplicationRecord
  # Only data transformations remain
  before_validation :normalize_email
end

class CreateUser < ApplicationService
  def call(params)
    user = User.create!(params)

    UserMailer.welcome(user).deliver_later
    Profile.create!(user: user)
    AdminMailer.new_user(user).deliver_later

    user
  end
end
```

## Related

- [Callbacks Topic](/skill/references/topics/callbacks.md)
- [Service Objects Pattern](/skill/references/patterns/service-objects.md)
- [Extraction Signals](/skill/references/core/extraction-signals.md)

# active_job-performs

Eliminate boilerplate job classes by declaring background methods directly on models.

**Repository:** [kaspth/active_job-performs](https://github.com/kaspth/active_job-performs)

## When to Use

Use when you have **anemic jobs** - job classes that just call a single method on a model:

```ruby
# BAD: Anemic job
class NotifyRecipientsJob < ApplicationJob
  def perform(notifiable)
    notifiable.notify_recipients
  end
end

# BAD: Model method just to enqueue job
class Post < ApplicationRecord
  def notify_recipients_later
    NotifyRecipientsJob.perform_later(self)
  end
end
```

## The Pattern

Replace anemic jobs with `performs`:

```ruby
# GOOD: Short form (no job options needed)
class Post < ApplicationRecord
  performs def notify_recipients
    # Notification logic
  end
end

# Usage
post.notify_recipients_later
```

This generates:
- `Post::NotifyRecipientsJob` (automatically)
- `notify_recipients_later` instance method
- `notify_recipients_later_bulk` class method (Rails 7.1+)

### When to Use Short vs Long Form

**Short form** - when no job configuration needed:
```ruby
performs def sync_with_provider
  # Simple async execution
end
```

**Long form** - when job options are required:
```ruby
performs :sync_with_provider, queue_as: :critical, discard_on: ApiError

def sync_with_provider
  # ...
end
```

## Detection Signals

**Anemic job indicators:**
- Job's `perform` method is a single line calling a method on the argument
- Model has `*_later` method that just calls `SomeJob.perform_later(self)`
- Job class has no logic beyond delegation
- Job folder has many similar thin wrapper jobs

## Configuration

### Job Options

```ruby
class Post < ApplicationRecord
  performs :publish,
           queue_as: :critical,
           discard_on: ActiveRecord::RecordNotFound do
    retry_on TimeoutError, wait: :polynomially_longer
  end

  def publish
    # ...
  end
end
```

### Delayed Execution

```ruby
class Post < ApplicationRecord
  performs :social_boost, wait: 5.minutes
  performs :publish, wait_until: -> post { Date.tomorrow.noon }

  def social_boost; end
  def publish; end
end
```

### Private Methods

```ruby
class Post < ApplicationRecord
  performs :sync_to_warehouse

  private

  def sync_to_warehouse
    # Only accessible via sync_to_warehouse_later
  end
end
```

### Method Suffixes

```ruby
class Post < ApplicationRecord
  performs :publish!   # Creates publish_later!
  performs :dangerous? # Creates dangerous_later?
end
```

## Application-Wide Patterns

Define common async operations in `ApplicationRecord`:

```ruby
class ApplicationRecord < ActiveRecord::Base
  self.abstract_class = true

  performs :destroy, queue_as: "active_record.destroy"
end

# Any model can now use:
post.destroy_later
```

## When NOT to Use

Keep separate job classes when:
- Job has complex logic beyond calling one method
- Job processes multiple records with custom batching
- Job needs to be triggered from multiple models
- Job has extensive retry/error handling configuration

## Migration Path

1. Identify anemic jobs (single method delegation)
2. Add `performs :method_name` to the model
3. Replace `SomeJob.perform_later(record)` with `record.method_name_later`
4. Delete the job file
5. Delete any `*_later` wrapper methods

## Layer Placement

The `performs` declaration belongs in the **Domain Layer** (model), keeping the async execution detail close to the domain logic it executes.

## Related

- [Callbacks Topic](../topics/callbacks.md) - When to use callbacks vs explicit `_later` calls
- [Service Objects](../patterns/service-objects.md) - For complex multi-step operations

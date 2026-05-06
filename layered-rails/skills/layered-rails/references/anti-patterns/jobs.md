# Job Anti-Patterns

Background-job classes that add boilerplate without value.

## Anemic Jobs

**Problem:** Job classes that just delegate to a single model method.

```ruby
# BAD: Job is just a wrapper
class NotifyRecipientsJob < ApplicationJob
  discard_on ActiveJob::DeserializationError

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

**Issues:**
- Boilerplate job files cluttering `app/jobs`
- Two places to maintain (job + model method)
- Job class adds no value beyond async execution
- Makes the jobs folder noisy, hiding complex jobs that need attention

**Signal:** Job's `perform` method is a single line calling a method on the argument.

**Fix:** Use the [active_job-performs](https://github.com/kaspth/active_job-performs) gem.

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
- `Post::NotifyRecipientsJob` automatically
- `notify_recipients_later` instance method
- `notify_recipients_later_bulk` class method (Rails 7.1+)

**With options:**
```ruby
class Post < ApplicationRecord
  performs :notify_recipients,
           queue_as: :notifications,
           discard_on: ActiveRecord::RecordNotFound

  def notify_recipients
    # ...
  end
end
```

**When to keep separate job class:**
- Job has complex logic beyond single method call
- Job processes multiple records with custom batching
- Job needs extensive retry/error handling configuration
- Job is triggered from multiple unrelated models

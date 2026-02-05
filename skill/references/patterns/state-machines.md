# State Machines

## Summary

State machines describe possible states, transitions between them, and triggering events. They make implicit state logic explicit and centralized, preventing scattered conditional logic across the codebase.

## When to Use

- Multiple related boolean/timestamp attributes tracking state
- Complex conditional logic based on object state
- State-dependent behavior
- Audit trail requirements

## When NOT to Use

- Linear progressions (just use enum)
- Simple two-state flags
- Before patterns emerge (premature)

## Key Principles

- **Identify implicit state machines** — scattered booleans/timestamps often hide state
- **Prefer events over direct transitions** — `order.submit!` not `order.status = :submitted`
- **Extract when not central** — standalone workflow for secondary state
- **Guards and callbacks sparingly** — don't recreate callback problems

## Identifying Implicit State Machines

Signs of hidden state:

```ruby
# Multiple related attributes
class Post < ApplicationRecord
  # submitted_at, reviewed_at, published_at, archived_at
  # is_draft, is_approved, is_hidden
end

# Scattered conditionals
def can_publish?
  submitted_at.present? && reviewed_at.present? && !is_hidden
end

def publish!
  return unless can_publish?
  update!(published_at: Time.current)
  notify_subscribers if !was_published_before
end
```

## Implementation

### With Enum (Simple)

```ruby
class Post < ApplicationRecord
  enum :state, {
    draft: 0,
    submitted: 1,
    approved: 2,
    rejected: 3,
    published: 4,
    archived: 5
  }
end
```

### Pattern Matching Transitions

```ruby
class Post < ApplicationRecord
  enum :state, %w[draft submitted approved rejected published archived].index_by(&:itself)

  def trigger(event)
    with_lock do
      case [state.to_sym, event.to_sym]
      in [:draft, :submit]
        update!(state: :submitted, submitted_at: Time.current)
      in [:submitted, :approve]
        update!(state: :approved, reviewed_at: Time.current)
      in [:submitted, :reject]
        update!(state: :rejected, reviewed_at: Time.current)
      in [:approved | :archived, :publish]
        update!(state: :published, published_at: Time.current, archived_at: nil)
      in [:published, :archive]
        update!(state: :archived, archived_at: Time.current)
      else
        false
      end
    end
  end
end

# Usage
post.trigger(:submit)
post.trigger(:approve)
post.trigger(:publish)
```

### With Workflow Gem

```ruby
class Post < ApplicationRecord
  include WorkflowActiverecord
  workflow_column :state

  workflow do
    state :draft do
      event :submit, transitions_to: :submitted
      event :publish, transitions_to: :published,
        if: proc { user.karma >= MIN_TRUSTED_KARMA }
    end

    state :submitted do
      event :reject, transitions_to: :rejected
      event :approve, transitions_to: :approved
      event :revise, transitions_to: :draft
    end

    state :approved do
      event :publish, transitions_to: :published
    end

    state :published do
      event :archive, transitions_to: :archived
    end

    state :archived do
      event :publish, transitions_to: :published
    end
  end

  # Transition callbacks
  def publish
    touch :published_at
  end

  def archive
    touch :archived_at
  end
end

# Usage
post.submit!
post.can_approve?  #=> true
post.approve!
post.current_state.events  #=> [:publish]
```

### Standalone Workflow

When state machine isn't central to the model:

```ruby
class Post::PublicationWorkflow
  include Workflow

  private attr_reader :post

  def initialize(post)
    @post = post
    @state = post.publication_state
  end

  workflow do
    state :draft do
      event :submit, transitions_to: :submitted
    end
    # ...
  end

  def persist_workflow_state(new_state)
    post.update!(publication_state: new_state)
  end

  # Transition callbacks
  def publish
    post.touch :published_at
  end
end

class Post < ApplicationRecord
  def publication_workflow
    @publication_workflow ||= PublicationWorkflow.new(self)
  end

  delegate :submit!, :approve!, :publish!, to: :publication_workflow
end
```

## Events Over Direct Transitions

```ruby
# BAD: Direct state assignment
post.update!(state: :published)

# GOOD: Event-driven
post.publish!

# Why? Events:
# - Validate transition is allowed
# - Run callbacks
# - Provide audit trail
# - Decouple layers
```

## Transition Guards

```ruby
workflow do
  state :draft do
    event :publish, transitions_to: :published,
      if: :publishable?
  end
end

def publishable?
  body.present? && title.present?
end
```

## Transition Callbacks

```ruby
workflow do
  state :submitted do
    event :approve, transitions_to: :approved
  end
end

# Called on transition
def approve
  self.reviewed_at = Time.current
  self.reviewed_by = Current.user
end

# Or use after_transition
after_transition to: :approved do
  ApprovalNotification.deliver_later(self)
end
```

## Anti-Patterns

### Implicit State Machines

```ruby
# BAD: State scattered across attributes
class Order < ApplicationRecord
  def status
    return :cancelled if cancelled_at?
    return :shipped if shipped_at?
    return :paid if paid_at?
    :pending
  end
end

# GOOD: Explicit state
class Order < ApplicationRecord
  enum :status, {pending: 0, paid: 1, shipped: 2, cancelled: 3}
end
```

### Phantom Transitions

```ruby
# BAD: publish -> publish triggers side effects
post.publish!  # Sends notifications
post.publish!  # Sends again!

# GOOD: Guard against no-op transitions
def publish!
  return false if published?
  # ...
end
```

### Excessive Guards

```ruby
# BAD: Guard recreates business logic
event :approve, transitions_to: :approved,
  if: proc { user.admin? && !flagged? && reviewed_by_two_people? }

# GOOD: Keep guards simple, logic in methods
event :approve, transitions_to: :approved, if: :approvable?

def approvable?
  ApprovalPolicy.new(Current.user, self).allowed?
end
```

## Related Gems

| Gem | Purpose |
|-----|---------|
| workflow | Finite-state machine with introspection |
| workflow-activerecord | Active Record integration |
| active_record-associated_object | `has_object` for attaching workflows |

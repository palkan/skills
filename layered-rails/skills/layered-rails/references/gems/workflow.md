# Workflow

Finite state machine implementation for Ruby.

**GitHub**: https://github.com/geekq/workflow
**Layer**: Domain

## Installation

```ruby
# Gemfile
gem "workflow"
gem "workflow-activerecord"  # For Active Record integration
```

## Basic Usage

### Define State Machine

```ruby
class Post < ApplicationRecord
  include WorkflowActiverecord

  workflow_column :status

  workflow do
    state :draft do
      event :submit, transitions_to: :pending_review
    end

    state :pending_review do
      event :approve, transitions_to: :approved
      event :reject, transitions_to: :rejected
      event :request_changes, transitions_to: :draft
    end

    state :approved do
      event :publish, transitions_to: :published
      event :archive, transitions_to: :archived
    end

    state :rejected do
      event :revise, transitions_to: :draft
    end

    state :published do
      event :archive, transitions_to: :archived
      event :unpublish, transitions_to: :draft
    end

    state :archived do
      event :restore, transitions_to: :draft
    end
  end
end
```

### Trigger Transitions

```ruby
post = Post.create!(title: "My Post")
post.draft?  #=> true

post.submit!
post.pending_review?  #=> true

post.approve!
post.approved?  #=> true

post.publish!
post.published?  #=> true
```

### Check Available Events

```ruby
post.current_state.events
#=> [:submit]

post.can_submit?  #=> true
post.can_approve? #=> false
```

## Transition Callbacks

```ruby
class Post < ApplicationRecord
  include WorkflowActiverecord

  workflow do
    state :draft do
      event :submit, transitions_to: :pending_review
    end

    state :pending_review do
      event :approve, transitions_to: :approved
    end

    state :approved do
      event :publish, transitions_to: :published
    end
  end

  # Called when event fires
  def submit
    self.submitted_at = Time.current
  end

  def approve
    self.approved_at = Time.current
    self.approved_by = Current.user
  end

  def publish
    self.published_at = Time.current
  end
end
```

## Transition Guards

```ruby
class Post < ApplicationRecord
  include WorkflowActiverecord

  workflow do
    state :draft do
      event :submit, transitions_to: :pending_review,
        if: :submittable?
    end

    state :pending_review do
      event :approve, transitions_to: :approved,
        if: proc { Current.user&.admin? }
    end
  end

  private

  def submittable?
    title.present? && body.present?
  end
end
```

## State-Dependent Behavior

```ruby
class Post < ApplicationRecord
  include WorkflowActiverecord

  workflow do
    state :draft
    state :published
    state :archived
  end

  def editable?
    draft?
  end

  def visible?
    published?
  end

  def restorable?
    archived?
  end
end
```

## Standalone Workflow

When state machine isn't central to the model:

```ruby
class Post::PublicationWorkflow
  include Workflow

  private attr_reader :post

  def initialize(post)
    @post = post
    @state = post.publication_status
  end

  workflow do
    state :draft do
      event :submit, transitions_to: :submitted
    end

    state :submitted do
      event :approve, transitions_to: :approved
      event :reject, transitions_to: :rejected
    end

    state :approved do
      event :publish, transitions_to: :published
    end

    state :published do
      event :archive, transitions_to: :archived
    end
  end

  def persist_workflow_state(new_state)
    post.update!(publication_status: new_state)
  end

  def publish
    post.touch(:published_at)
  end
end

# Usage
class Post < ApplicationRecord
  def publication_workflow
    @publication_workflow ||= PublicationWorkflow.new(self)
  end

  delegate :submit!, :approve!, :publish!, to: :publication_workflow
end
```

## After Transition Hooks

```ruby
class Order < ApplicationRecord
  include WorkflowActiverecord

  workflow do
    state :pending do
      event :confirm, transitions_to: :confirmed
    end

    state :confirmed do
      event :ship, transitions_to: :shipped
    end

    state :shipped do
      event :deliver, transitions_to: :delivered
    end
  end

  # Runs after any transition
  def on_transition(from, to, event, *args)
    AuditLog.create!(
      record: self,
      from_state: from,
      to_state: to,
      event: event
    )
  end
end
```

## Querying by State

```ruby
# Workflow adds scopes for each state
Post.with_draft_status
Post.with_published_status

# Or use enum-style queries if using enum column
Post.where(status: :draft)
```

## Testing

```ruby
RSpec.describe Post do
  describe "workflow" do
    it "starts in draft state" do
      post = Post.new
      expect(post).to be_draft
    end

    it "transitions from draft to pending_review" do
      post = create(:post, :draft)

      expect { post.submit! }
        .to change { post.status }
        .from("draft").to("pending_review")
    end

    it "guards against invalid submissions" do
      post = create(:post, title: nil)

      expect { post.submit! }.to raise_error(Workflow::NoTransitionAllowed)
    end
  end
end
```

## Related

- [State Machines Pattern](../patterns/state-machines.md)

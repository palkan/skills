# Form Objects

## Summary

Form objects handle specific user interactions involving data submission. They belong to the presentation layer and are useful when the form doesn't map 1:1 to a model — creating multiple records, updating virtual attributes, or handling complex validation contexts.

## When to Use

- Multi-model forms (creating/updating multiple records)
- Model-less forms (feedback, search, settings)
- Context-specific validations (publish vs draft)
- Complex form logic that doesn't belong in models

## When NOT to Use

- Simple single-model CRUD (use model directly)
- Duplicating model validations

## Key Principles

- **Presentation layer abstraction** — handles UI concerns, not domain logic
- **Use when N ≠ 1** — forms that create/update zero, multiple, or virtual resources
- **Build on Active Model** — validations, attributes, Action View compatibility
- **Callbacks for decomposition** — `after_save` (in transaction), `after_commit` (after)
- **Don't duplicate validations** — delegate to models and merge errors

## Implementation

### Base Class

```ruby
class ApplicationForm
  include ActiveModel::API
  include ActiveModel::Attributes

  define_callbacks :save, only: :after
  define_callbacks :commit, only: :after

  class << self
    def after_save(...) = set_callback(:save, :after, ...)
    def after_commit(...) = set_callback(:commit, :after, ...)

    def model_name
      @model_name ||= ActiveModel::Name.new(nil, nil, name.sub(/Form$/, ""))
    end
  end

  delegate :model_name, to: :class

  def save
    return false unless valid?

    with_transaction do
      AfterCommitEverywhere.after_commit { run_callbacks(:commit) }
      run_callbacks(:save) { submit! }
    end
  end

  private

  def with_transaction(&) = ApplicationRecord.transaction(&)
  def submit! = raise NotImplementedError
end
```

### Context-Specific Form

```ruby
class InvitationForm < ApplicationForm
  attribute :email
  attribute :send_copy, :boolean

  attr_accessor :sender

  validates :email, presence: true, format: {with: URI::MailTo::EMAIL_REGEXP}

  after_commit :deliver_invitation
  after_commit :deliver_invitation_copy, if: :send_copy

  private

  def submit!
    @user = User.create!(email:, status: :invited)
  end

  def deliver_invitation
    UserMailer.invite(@user).deliver_later
  end

  def deliver_invitation_copy
    UserMailer.invite_copy(sender, @user).deliver_later if sender
  end
end
```

### Multi-Model Form

```ruby
class RegistrationForm < ApplicationForm
  attribute :name
  attribute :email
  attribute :project_name
  attribute :should_create_project, :boolean

  validates :project_name, presence: true, if: :should_create_project
  validate :user_is_valid

  attr_reader :user

  after_save :create_initial_project, if: :should_create_project

  def initialize(...)
    super
    @user = User.new(email:, name:)
  end

  private

  def submit!
    user.save!
  end

  def create_initial_project
    user.projects.create!(name: project_name)
  end

  def user_is_valid
    return if user.valid?
    user.errors.each do |error|
      errors.add(error.attribute, error.message)
    end
  end
end
```

### Model-less Form

```ruby
class FeedbackForm < ApplicationForm
  attribute :message
  attribute :email
  attribute :category

  validates :message, presence: true, length: {minimum: 10}
  validates :email, presence: true

  after_commit :deliver_feedback

  private

  def submit!
    # No model to save
    true
  end

  def deliver_feedback
    FeedbackMailer.new_feedback(email:, message:, category:).deliver_later
  end
end
```

## Usage in Controllers

```ruby
class InvitationsController < ApplicationController
  def new
    @form = InvitationForm.new
  end

  def create
    @form = InvitationForm.new
    @form.sender = current_user

    if @form.from(params[:invitation]).save
      redirect_to invitations_path, notice: "Invitation sent"
    else
      render :new, status: :unprocessable_entity
    end
  end
end
```

## Wizard Forms (Multi-Step)

Use state machines for complex multi-step forms:

```ruby
class OnboardingForm < ApplicationForm
  include Workflow

  workflow do
    state :profile do
      event :next, transitions_to: :preferences
    end
    state :preferences do
      event :next, transitions_to: :confirmation
      event :back, transitions_to: :profile
    end
    state :confirmation do
      event :back, transitions_to: :preferences
    end
  end

  # Validate only current step
  validates :name, presence: true, if: :profile?
  validates :email, presence: true, if: :profile?
  validates :theme, presence: true, if: :preferences?

  def submit!
    return true unless confirmation?
    User.create!(attributes.except(:workflow_state))
  end
end
```

## Anti-Patterns

### Duplicating Model Validations

```ruby
# BAD
class UserForm < ApplicationForm
  validates :email, presence: true, uniqueness: true  # Duplicates User validation
end

# GOOD
class UserForm < ApplicationForm
  validate :user_is_valid

  def user_is_valid
    return if user.valid?
    user.errors.each { |e| errors.add(e.attribute, e.message) }
  end
end
```

### UI Logic in Model Callbacks

```ruby
# BAD: Model callback for UI-specific behavior
class User < ApplicationRecord
  after_create :send_welcome_email, if: :from_registration_form?
end

# GOOD: Form handles UI-specific side effects
class RegistrationForm < ApplicationForm
  after_commit :send_welcome_email
end
```

## Related Gems

| Gem | Purpose |
|-----|---------|
| after_commit_everywhere | `after_commit` callbacks outside Active Record |

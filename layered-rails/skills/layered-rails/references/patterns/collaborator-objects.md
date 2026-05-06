# Collaborator Objects

## Contents

- Summary
- When to Use
- When NOT to Use
- Key Principles
- Implementation
- Comparison With Other Patterns
- Anti-Patterns

## Summary

A collaborator object is a small, focused class that owns a slice of behavior tightly coupled to a primary model. It lives alongside the model, takes the model (or a piece of its data) as input, and exposes a narrow interface. The classic shape is a **delegate object**: a separate class — sometimes a separate Active Record table — that the primary model delegates a coherent group of attributes and methods to.

A collaborator is **not** a service object. Services orchestrate operations across the application. Collaborators stay inside the Domain layer; they exist to keep the primary model from accumulating unrelated responsibilities.

## When to Use

- A model has a coherent slice of behavior that doesn't justify a full sibling model but bloats the primary class (contact information, profile metadata, billing details).
- Multiple models share the slice (polymorphic delegates work well here).
- The slice has its own validations, normalizations, or formatting rules that don't belong on the parent.
- A behavioral concern has grown beyond a single mixin's reasonable size and would be clearer as a typed object.

## When NOT to Use

- The slice is just data with no behavior — use a value object instead.
- The slice is a unit of work (creating, sending, syncing) — use a service object.
- The slice is reusable across heterogeneous models with no per-instance state — a concern is fine.
- The slice has its own identity and lifecycle — promote it to a sibling model.

## Key Principles

- **One primary association.** A collaborator is created for and owned by a single model (or polymorphic owner). It does not stand alone.
- **Narrow interface.** The collaborator exposes a focused set of methods — what its slice of behavior provides — not the full Active Record API.
- **Domain-layer only.** A collaborator stays inside the Domain layer. It does not call mailers, jobs, services, or external APIs. If it needs to, it's a service in disguise.
- **Delegate from the parent.** The parent model uses `delegate :method, to: :collaborator` (or a concern that does the same) so callers can keep using the parent's existing API while the implementation moves.

## Implementation

### Polymorphic Delegate (Active Record)

The contact-information example: a `User` had grown phone-number, country-code, social-account, and visibility validations and normalizations that all clustered around contacting a person. Extracting them into `ContactInformation` keeps the user model focused on identity and authentication.

```ruby
class ContactInformation < ApplicationRecord
  belongs_to :contactable, polymorphic: true

  SOCIAL_ACCOUNTS = %i[facebook twitter tiktok].freeze
  store_accessor :social_accounts, *SOCIAL_ACCOUNTS, suffix: :social_id

  validates :phone_number, allow_blank: true, phone: {types: :mobile}
  validates :country_code, inclusion: Country.codes

  normalizes :phone_number, with: -> { Phonelib.parse(it).e164 }

  def region
    Country[country_code].region
  end

  def phone_number_visible?
    contact_info_visible && phone_number_visible
  end
end

module Contactable
  extend ActiveSupport::Concern

  included do
    has_one :contact_information, as: :contactable, dependent: :destroy

    delegate :phone_number, :region, to: :contact_information
  end
end

class User < ApplicationRecord
  include Contactable
end
```

Callers keep using `user.phone_number` and `user.region` — the delegate is invisible at the call site.

### Plain Ruby Delegate

A collaborator does not have to be an Active Record model. When the slice does not need persistence, a plain Ruby object that takes the parent in its constructor is enough.

```ruby
class User
  class Greeter
    def initialize(user)
      @user = user
    end

    def hello
      "Hello, #{@user.name}!"
    end

    def goodbye
      "See you later, #{@user.name}."
    end
  end

  def greeter
    @greeter ||= Greeter.new(self)
  end

  delegate :hello, :goodbye, to: :greeter
end

user.hello    #=> "Hello, Alice!"
user.goodbye  #=> "See you later, Alice."
```

### Delegate Replacing a Mixed Concern

When a concern accumulates unrelated behavior — validation rules, query helpers, formatting — splitting it into a typed delegate (or several) makes ownership clear.

```ruby
# Before: User concern is a junk drawer
module Contactable
  extend ActiveSupport::Concern

  included do
    validates :phone_number, ...
    normalizes :phone_number, ...
  end

  def region = ...
  def phone_number_visible? = ...
  def social_links = ...
  def primary_channel = ...
end

# After: contact information owns its own type
class ContactInformation < ApplicationRecord
  validates :phone_number, ...
  normalizes :phone_number, ...

  def region = ...
  def phone_number_visible? = ...
  def social_links = ...
  def primary_channel = ...
end

module Contactable
  extend ActiveSupport::Concern

  included do
    has_one :contact_information, as: :contactable
    delegate :region, :phone_number_visible?, :social_links, :primary_channel,
      to: :contact_information
  end
end
```

The `Contactable` concern shrinks to a one-liner association + delegate. The behavior moves to a class that names what it represents.

## Comparison With Other Patterns

| Pattern | Owns | Has behavior? | Has identity? | Layer |
|---|---|---|---|---|
| **Value object** | A bundle of attributes | Yes (pure) | No | Domain |
| **Collaborator / delegate object** | A slice of one model's behavior | Yes (and possibly state) | Optional (polymorphic AR has its own row) | Domain |
| **Service object** | A unit of work | Yes (orchestration) | No (transient) | Application |
| **Sibling model** | A first-class concept | Yes | Yes (own primary key) | Domain |
| **Concern** | A reusable behavior across models | Yes (mixed in) | No | Domain |

The collaborator/delegate sits between value objects and sibling models: it has more behavior than a value object and less independent identity than a sibling model. It is the right tool when a slice of a model wants its own type but does not want to be its own entity.

## Anti-Patterns

### Cross-Layer Delegate

```ruby
# BAD — crosses into Infrastructure
class User::Notifier
  def initialize(user) = @user = user

  def notify(event)
    NotifierMailer.send(@user, event).deliver_later
    SlackClient.post(@user.slack_id, event)
  end
end

class User < ApplicationRecord
  delegate :notify, to: :notifier
  def notifier = @notifier ||= Notifier.new(self)
end
```

Calling mailers, jobs, or external APIs from a delegate makes it an application service in domain clothing. Move it to `app/services/` or to the dedicated notification layer.

### Anemic Delegate

```ruby
# BAD — just a struct of attribute readers
class User::Profile
  def initialize(user) = @user = user
  def first_name = @user.first_name
  def last_name = @user.last_name
end
```

If the delegate has no behavior of its own, it is paperwork. Either inline the methods on the parent, or promote to a value object if the attributes deserve their own type.

### Delegate That Knows About Callers

A collaborator should not branch on who called it (`if controller_context.user.admin?`). It owns a slice of one model's behavior; cross-cutting context belongs in the calling layer.

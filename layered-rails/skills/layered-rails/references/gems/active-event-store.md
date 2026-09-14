# Active Event Store

Rails Event Store with conventions and transparent Rails integration.

**GitHub**: https://github.com/palkan/active_event_store
**Layer**: Domain (event classes) / Application (subscribers) / Infrastructure (the store)

## Contents

- Installation
- Describing Events
- Publishing Events
- Subscribing to Events
- Conventions
- Testing
- When to Use
- Event-Driven Is Not Event Sourcing

## Installation

```ruby
# Gemfile
gem "active_event_store", "~> 1.0"
```

Set up the data model through Rails Event Store:

```bash
rails generate rails_event_store_active_record:migration
rails db:migrate
```

Requires Ruby >= 2.6, Rails >= 6.0, RailsEventStore >= 2.1.

## Describing Events

Events are classes that declare their payload. Keep them in `app/events/`.

```ruby
class ProfileCompleted < ActiveEventStore::Event
  # Optional. Defaults to `name.underscore.gsub('/', '.')`.
  # Set explicitly only to keep an identifier stable across a class rename.
  self.identifier = "profile_completed"

  attributes :user_id

  # Available to sync subscribers only, so they need not reload the record.
  # Not persisted.
  sync_attributes :user
end
```

Events serialize to JSON, so `attributes` holds simple field types only: numbers, strings, booleans. Every event also carries `event_id`, `type` and `metadata`.

Name events in the past tense, describing what happened: `ProfileCompleted`, `OrderPaid`.

## Publishing Events

```ruby
event = ProfileCompleted.new(user_id: user.id)

# With metadata
event = ProfileCompleted.new(user_id: user.id, metadata: {ip: request.remote_ip})

ActiveEventStore.publish(event)
```

The event is stored and propagated to subscribers.

## Subscribing to Events

Declare subscriptions in an initializer, inside the load hook so the store is ready:

```ruby
ActiveSupport.on_load :active_event_store do |store|
  # Async by default: a background job enqueued after the current
  # transaction commits.
  store.subscribe MyEventHandler, to: ProfileCreated

  # Sync: runs inside `publish`.
  store.subscribe MyEventHandler, to: ProfileCreated, sync: true

  # Delayed. `wait:`/`wait_until:` pass through to Active Job's `.set`.
  store.subscribe MyEventHandler, to: ProfileCreated, wait: 10.minutes

  # Anonymous handlers must be sync.
  store.subscribe(to: ProfileCreated, sync: true) { |event| ... }

  # Convention: the event is inferred from the subscriber's name.
  store.subscribe OnProfileCreated::DoThat
end
```

A subscriber is any callable that takes the event as its single argument.

Async subscribers need Active Job loaded.

## Conventions

| Thing | Location |
|---|---|
| Event classes | `app/events/` |
| Subscribers | `app/subscribers/on_<event_type>/<subscriber>.rb` |

Subscribers being enqueued only after commit is the property that makes this a safe replacement for `after_commit` side effects: a rolled-back transaction publishes nothing.

## Testing

Include `ActiveEventStore::TestHelpers` in Minitest tests.

```ruby
# Minitest: a subscriber is enqueued
def test_subscribed
  event = MyEvent.new(some: "data")
  assert_async_event_subscriber_enqueued(MySubscriberService, event: event) do
    ActiveEventStore.publish event
  end
end

# Minitest: an event is published
assert_event_published(ProfileCreated, with: {user_id: user.id}) { subject }
```

RSpec equivalents are `have_enqueued_async_subscriber_for` and `have_published_event`, both block expectations.

**Async subscribers are enqueued only after the transaction commits**, so a test asserting enqueue needs `self.use_transactional_fixtures = false` in that test class.

## When to Use

Reach for this when extracting operation callbacks (score 1-2 in the Callback Scoring System) that are *communication with remote peers* rather than context-sensitive steps of one process:

- Analytics tracking
- CRM and third-party sync
- Cross-domain reactions where the publisher should not know the subscriber

Context-sensitive operations that belong to one process (for example, generating a starter project during registration) are better extracted to a service object, not an event.

Do not reach for it when a plain method call in the same unit of work would do. An event whose only subscriber lives in the same context adds indirection without decoupling anything.

## Event-Driven Is Not Event Sourcing

They are separate ideas and are easy to conflate:

- **Event-driven architecture** is about *communication* between components: publishers, subscribers, a bus. This gem.
- **Event sourcing** is about *persistence*: the object's state is stored as a stream of modifications rather than a single value, so past states can be reconstructed.

Using this gem does not make an application event-sourced, and it does not need to be.

## Related

`downstream` (https://github.com/palkan/downstream) is the twin gem, with the same listener and event abstractions over an in-memory broker by default. Choose it when durability is not required.

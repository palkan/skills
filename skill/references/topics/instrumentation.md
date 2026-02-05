# Instrumentation

## Summary

Instrumentation provides visibility into application behavior through logging, metrics, and tracing. It's an infrastructure concern that should be non-invasive to domain logic.

## Layer Placement

```
┌─────────────────────────────────────────┐
│ Infrastructure Layer                    │
│  └─ Instrumentation subscribers         │
│  └─ Log formatters                      │
│  └─ Metrics collectors                  │
└─────────────────────────────────────────┘
```

## Key Principles

- **Non-invasive** — domain code shouldn't know about instrumentation
- **Event-driven** — use Rails instrumentation, not inline logging
- **Structured** — use tagged/structured logging
- **Centralized** — configure in initializers, not throughout code

## Rails Instrumentation API

### Subscribe to Events

```ruby
# config/initializers/instrumentation.rb
ActiveSupport::Notifications.subscribe("process_action.action_controller") do |event|
  Rails.logger.info({
    event: event.name,
    controller: event.payload[:controller],
    action: event.payload[:action],
    status: event.payload[:status],
    duration_ms: event.duration.round(2)
  }.to_json)
end
```

### Custom Events

```ruby
# Instrument custom operations
class ProcessPayment
  def call(order)
    ActiveSupport::Notifications.instrument(
      "process.payment",
      order_id: order.id,
      amount: order.total
    ) do
      gateway.charge(order)
    end
  end
end

# Subscribe elsewhere
ActiveSupport::Notifications.subscribe("process.payment") do |event|
  Metrics.histogram(
    "payment.duration",
    event.duration,
    tags: { status: event.payload[:status] }
  )
end
```

### LogSubscriber Pattern

```ruby
# app/subscribers/payment_log_subscriber.rb
class PaymentLogSubscriber < ActiveSupport::LogSubscriber
  def process(event)
    info do
      "Payment processed: order=#{event.payload[:order_id]} " \
      "amount=#{event.payload[:amount]} " \
      "duration=#{event.duration.round(2)}ms"
    end
  end

  def refund(event)
    info { "Payment refunded: #{event.payload[:order_id]}" }
  end
end

PaymentLogSubscriber.attach_to :payment
```

## Structured Logging

### Tagged Logging

```ruby
class ApplicationController < ActionController::Base
  around_action :tag_logs

  private

  def tag_logs
    Rails.logger.tagged(
      "request_id:#{request.uuid}",
      "user:#{current_user&.id}"
    ) { yield }
  end
end
```

### JSON Logging

```ruby
# config/environments/production.rb
config.log_formatter = proc do |severity, time, progname, msg|
  {
    severity: severity,
    time: time.iso8601,
    progname: progname,
    message: msg
  }.to_json + "\n"
end
```

### Semantic Logger

```ruby
# Gemfile
gem "semantic_logger"

# config/application.rb
config.semantic_logger.application = "myapp"
config.semantic_logger.environment = Rails.env

# Usage
class PaymentService
  include SemanticLogger::Loggable

  def process(order)
    logger.info("Processing payment", order_id: order.id, amount: order.total)
    # ...
    logger.info("Payment complete", order_id: order.id, status: :success)
  rescue => e
    logger.error("Payment failed", order_id: order.id, error: e.message)
    raise
  end
end
```

## Metrics

### StatsD Integration

```ruby
# config/initializers/metrics.rb
$statsd = Datadog::Statsd.new("localhost", 8125)

ActiveSupport::Notifications.subscribe(/\.action_controller$/) do |event|
  $statsd.distribution(
    "rails.request.duration",
    event.duration,
    tags: [
      "controller:#{event.payload[:controller]}",
      "action:#{event.payload[:action]}",
      "status:#{event.payload[:status]}"
    ]
  )
end
```

### Custom Metrics

```ruby
# Non-invasive metrics collection
class MetricsSubscriber
  def self.subscribe!
    ActiveSupport::Notifications.subscribe("create.user") do |event|
      $statsd.increment("users.created")
    end

    ActiveSupport::Notifications.subscribe("process.payment") do |event|
      $statsd.distribution(
        "payments.duration",
        event.duration,
        tags: ["status:#{event.payload[:status]}"]
      )

      if event.payload[:status] == :success
        $statsd.increment("payments.success")
      else
        $statsd.increment("payments.failure")
      end
    end
  end
end
```

## Service Instrumentation

### Instrumented Base Class

```ruby
class ApplicationService
  include ActiveSupport::Callbacks
  define_callbacks :call

  set_callback :call, :around, :instrument

  def call(...)
    run_callbacks(:call) { perform(...) }
  end

  private

  def perform(...)
    raise NotImplementedError
  end

  def instrument
    ActiveSupport::Notifications.instrument(
      "call.#{self.class.name.underscore}",
      service: self.class.name
    ) { yield }
  end
end

class ProcessPayment < ApplicationService
  def perform(order)
    # Implementation
  end
end

# Automatic instrumentation events:
# "call.process_payment"
```

### Manual Instrumentation

```ruby
class ImportData
  def call(file)
    result = nil

    ActiveSupport::Notifications.instrument("import.data", file: file.name) do |payload|
      result = process_file(file)
      payload[:records_count] = result.count
      payload[:status] = :success
    rescue => e
      payload[:status] = :failure
      payload[:error] = e.message
      raise
    end

    result
  end
end
```

## Anti-Patterns

### Logging in Domain Models

```ruby
# BAD: Model knows about logging
class Order < ApplicationRecord
  after_create do
    Rails.logger.info("Order created: #{id}")
  end
end

# GOOD: Subscribe to model events
ActiveSupport::Notifications.subscribe("sql.active_record") do |event|
  # Log SQL if needed
end

# Or use LogSubscriber for custom events
class OrderLogSubscriber < ActiveSupport::LogSubscriber
  def create(event)
    info { "Order created: #{event.payload[:order_id]}" }
  end
end
```

### Metrics Scattered in Code

```ruby
# BAD: Metrics inline with business logic
class ProcessPayment
  def call(order)
    $statsd.increment("payment.attempts")

    result = gateway.charge(order)

    if result.success?
      $statsd.increment("payment.success")
    else
      $statsd.increment("payment.failure")
    end

    result
  end
end

# GOOD: Separate instrumentation from logic
class ProcessPayment
  def call(order)
    ActiveSupport::Notifications.instrument("process.payment", order_id: order.id) do |payload|
      result = gateway.charge(order)
      payload[:status] = result.success? ? :success : :failure
      result
    end
  end
end

# Metrics collected via subscriber
```

### Verbose Debug Logging

```ruby
# BAD: Excessive logging cluttering code
def process(items)
  Rails.logger.debug("Starting process with #{items.count} items")
  items.each_with_index do |item, i|
    Rails.logger.debug("Processing item #{i}: #{item.inspect}")
    result = transform(item)
    Rails.logger.debug("Item #{i} transformed: #{result.inspect}")
  end
  Rails.logger.debug("Process complete")
end

# GOOD: Single instrumented event
def process(items)
  ActiveSupport::Notifications.instrument("process.batch", count: items.count) do
    items.map { |item| transform(item) }
  end
end
```

## Testing Instrumentation

```ruby
RSpec.describe ProcessPayment do
  it "instruments the operation" do
    events = []
    callback = ->(event) { events << event }

    ActiveSupport::Notifications.subscribed(callback, "process.payment") do
      described_class.new.call(order)
    end

    expect(events.size).to eq(1)
    expect(events.first.payload[:order_id]).to eq(order.id)
    expect(events.first.payload[:status]).to eq(:success)
  end
end
```

## Performance Considerations

```ruby
# Use lazy evaluation for expensive log messages
Rails.logger.debug { "Expensive: #{expensive_calculation}" }

# Batch metrics
$statsd.batch do |batch|
  batch.increment("foo")
  batch.gauge("bar", 100)
end

# Sample high-volume events
ActiveSupport::Notifications.subscribe("sql.active_record") do |event|
  next unless rand < 0.1  # 10% sample
  # Process event
end
```

## Related

- [Callbacks Topic](./callbacks.md)
- [Configuration Topic](./configuration.md)

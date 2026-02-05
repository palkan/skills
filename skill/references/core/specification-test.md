# The Specification Test

## Principle

> If the specification of an object describes features beyond the primary responsibility of its abstraction layer, such features should be extracted into lower layers.

The specification test helps identify code that belongs in a different layer by examining what tests would verify.

## How to Apply

1. **Write test structure** (contexts/describes) without implementation
2. **Examine what the tests verify**
3. **Ask:** Does this test verify the object's primary responsibility?

If a test verifies something outside the layer's primary concern, that code should be extracted.

## Layer Responsibilities

| Layer | Primary Responsibility | Tests Should Verify |
|-------|------------------------|---------------------|
| Presentation (Controller) | HTTP handling | Authentication, authorization, response codes, redirects |
| Application (Service) | Use-case orchestration | Correct domain objects called, transaction boundaries |
| Domain (Model) | Business rules | Validations, state transitions, calculations |
| Infrastructure | Technical implementation | Data persistence, API calls |

## Example: Controller Specification

```ruby
describe "/callbacks/github" do
  context "when signature is missing"      # ✓ Authentication (controller responsibility)
  context "when signature is invalid"      # ✓ Authentication (controller responsibility)
  context "when event is pull_request"     # ✗ Business logic (extract to lower layer)
  context "when event is issue"            # ✗ Business logic (extract to lower layer)
  context "when user is not found"         # ✗ Business logic (extract to lower layer)
end
```

The business logic tests indicate code that should move to the application or domain layer.

**After extraction:**

```ruby
# Controller spec - only HTTP concerns
describe "/callbacks/github" do
  context "when signature is missing"
  context "when signature is invalid"
  context "when signature is valid"
end

# Service spec - business logic
describe HandleGithubEventService do
  context "when event is pull_request"
  context "when event is issue"
  context "when user is not found"
end
```

## Example: Service Specification

```ruby
describe ProcessOrderService do
  context "when order is valid"           # ✓ Orchestration
  context "when payment fails"            # ✓ Error handling
  context "when inventory check fails"    # ✓ Error handling
  context "when discount > 50%"           # ✗ Business rule (move to model)
  context "when order total < minimum"    # ✗ Business rule (move to model)
end
```

Discount and minimum order rules are domain logic—they belong in the Order model.

## Example: Model Specification

```ruby
describe Order do
  context "validations"                   # ✓ Business rules
  context "#calculate_total"              # ✓ Domain calculation
  context "#apply_discount"               # ✓ Domain logic
  context "when sending confirmation"     # ✗ Presentation concern (extract)
  context "when syncing to warehouse"     # ✗ Infrastructure concern (extract)
end
```

Notification and external sync are not domain responsibilities.

## Cost Consideration

Higher-layer tests are:
- **Harder to write** (more context setup)
- **Slower to execute** (HTTP requests, full stack)
- **More brittle** (depend on more components)

Moving logic to lower layers enables faster, simpler, more focused tests.

| Test Type | Speed | Setup Complexity | Brittleness |
|-----------|-------|------------------|-------------|
| Model/unit | Fast | Low | Low |
| Service | Medium | Medium | Medium |
| Controller/request | Slow | High | High |
| System/integration | Slowest | Highest | Highest |

## Applying the Test

### Step 1: List Responsibilities

For the code you're examining, list every responsibility it handles.

Example for `OrdersController#create`:
- Parse order parameters
- Authenticate user
- Authorize order creation
- Validate inventory
- Calculate pricing
- Apply discounts
- Create order record
- Send confirmation email
- Sync to warehouse API
- Return JSON response

### Step 2: Categorize by Layer

| Responsibility | Layer | Belongs in Controller? |
|----------------|-------|------------------------|
| Parse parameters | Presentation | ✓ Yes |
| Authenticate user | Presentation | ✓ Yes |
| Authorize creation | Application | ✓ Yes (or policy) |
| Validate inventory | Domain | ✗ No |
| Calculate pricing | Domain | ✗ No |
| Apply discounts | Domain | ✗ No |
| Create record | Domain | ✗ No |
| Send email | Presentation | ✗ No (not controller's job) |
| Sync to API | Infrastructure | ✗ No |
| Return JSON | Presentation | ✓ Yes |

### Step 3: Extract

Move misplaced responsibilities to appropriate layers:

```ruby
# Controller - only HTTP concerns
class OrdersController < ApplicationController
  def create
    result = CreateOrderService.call(
      params: order_params,
      user: current_user
    )

    if result.success?
      render json: OrderSerializer.new(result.order)
    else
      render json: { errors: result.errors }, status: :unprocessable_entity
    end
  end
end

# Service - orchestration
class CreateOrderService
  def call
    order = Order.new(params)
    order.customer = user

    return failure(order.errors) unless order.valid?

    order.save!
    OrderMailer.confirmation(order).deliver_later
    WarehouseSyncJob.perform_later(order.id)

    success(order)
  end
end

# Model - domain logic
class Order < ApplicationRecord
  def valid?
    validate_inventory
    calculate_pricing
    apply_discounts
    super
  end
end
```

## Quick Reference

**Controller should test:**
- HTTP status codes
- Redirects
- Authentication/authorization
- Parameter handling
- Response format

**Controller should NOT test:**
- Business rules
- Calculations
- State transitions
- External service behavior

**Service should test:**
- Correct objects orchestrated
- Transaction success/failure
- Error handling

**Service should NOT test:**
- Domain validation rules
- Business calculations
- HTTP concerns

**Model should test:**
- Validations
- Business rules
- Calculations
- State transitions

**Model should NOT test:**
- HTTP concerns
- Notification delivery
- External API calls

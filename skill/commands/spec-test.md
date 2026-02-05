# /layers:spec-test

Run the specification test on files to evaluate layer responsibility alignment.

## Usage

```
/layers:spec-test [file_path]
/layers:spec-test app/controllers/orders_controller.rb
/layers:spec-test app/services/
```

## Process

1. **Read target file(s)**
2. **Identify architecture layer** (Presentation, Application, Domain, Infrastructure)
3. **List all responsibilities** the code handles
4. **Evaluate each responsibility** against layer's primary concern
5. **Flag misplaced responsibilities** with suggested extraction targets
6. **Generate report** with recommendations

## Layer Primary Responsibilities

| Layer | Primary Concern | Should Handle | Should NOT Handle |
|-------|-----------------|---------------|-------------------|
| Presentation (Controller) | HTTP handling | Auth, params, response codes, redirects | Business logic, calculations |
| Application (Service) | Use-case orchestration | Coordinating domain objects, transactions | Domain rules, HTTP concerns |
| Domain (Model) | Business rules | Validations, calculations, state transitions | Notifications, HTTP, external APIs |
| Infrastructure | Technical implementation | Persistence, external communication | Business rules |

## Output Format

```markdown
## Specification Test: [FileName]

**Layer:** [Identified layer]
**Primary Responsibility:** [Layer's primary concern]

### Responsibility Analysis

| Responsibility | Belongs Here? | Suggested Location |
|----------------|---------------|-------------------|
| [responsibility 1] | ✓ | - |
| [responsibility 2] | ✗ | [target layer/abstraction] |

### Extraction Recommendations

1. **[Responsibility]** → Extract to [target]
   - Current location: `file:line`
   - Suggested pattern: [Service/Model/etc.]
   - Example:
   ```ruby
   # Before (in controller)
   total = items.sum { |i| i.price * i.quantity }

   # After (in model)
   def calculate_total
     items.sum(&:subtotal)
   end
   ```

### Test Implications

Moving these responsibilities would:
- Enable [X] unit tests instead of [Y] integration tests
- Reduce test setup complexity for [responsibility]
- Improve test speed by [explanation]
```

## Example

Input: `app/controllers/orders_controller.rb`

```ruby
class OrdersController < ApplicationController
  def create
    @order = Order.new(order_params)
    @order.customer = current_user

    # Calculate total with discounts
    @order.total = @order.items.sum { |i| i.price * i.quantity }
    @order.total *= 0.9 if @order.customer.vip?
    @order.total += calculate_shipping(@order)

    if @order.save
      # Send notifications
      OrderMailer.confirmation(@order).deliver_later
      SlackNotifier.order_created(@order)

      # Sync to external system
      WarehouseApi.create_order(@order.to_warehouse_format)

      redirect_to @order, notice: "Order created"
    else
      render :new
    end
  end

  private

  def calculate_shipping(order)
    # Complex shipping calculation
    base = 10
    base += 5 if order.items.sum(&:weight) > 10
    base += 10 if order.express_shipping?
    base
  end
end
```

Output:

```markdown
## Specification Test: OrdersController

**Layer:** Presentation
**Primary Responsibility:** HTTP request/response handling

### Responsibility Analysis

| Responsibility | Belongs Here? | Suggested Location |
|----------------|---------------|-------------------|
| Parse order_params | ✓ | - |
| Set current_user | ✓ | - |
| Calculate item totals | ✗ | Domain (Order model) |
| Apply VIP discount | ✗ | Domain (Order model) |
| Calculate shipping | ✗ | Domain (Order model or ShippingCalculator) |
| Save order | ✓ | - |
| Send confirmation email | ⚠️ | Application (Service) or keep but simplify |
| Send Slack notification | ✗ | Application (Service or NotificationService) |
| Sync to warehouse | ✗ | Application (Job or Service) |
| Redirect on success | ✓ | - |
| Render form on failure | ✓ | - |

### Extraction Recommendations

1. **Pricing calculations** → Extract to Order model
   - Current location: `orders_controller.rb:7-10`
   - Suggested pattern: Model method with callback
   ```ruby
   # In Order model
   before_validation :calculate_total

   def calculate_total
     self.total = items.sum(&:subtotal)
     self.total *= 0.9 if customer.vip?
     self.total += shipping_cost
   end
   ```

2. **Shipping calculation** → Extract to Order model or dedicated calculator
   - Current location: `orders_controller.rb:25-31`
   - Suggested pattern: Model method or Value object
   ```ruby
   # In Order model
   def shipping_cost
     ShippingCalculator.new(self).calculate
   end
   ```

3. **External notifications** → Extract to service or job
   - Current location: `orders_controller.rb:14-15`
   - Suggested pattern: After-action notification
   ```ruby
   # Option 1: Simple service
   OrderNotificationService.call(@order)

   # Option 2: Event-driven
   # Model publishes event, subscribers handle notifications
   ```

4. **Warehouse sync** → Extract to background job
   - Current location: `orders_controller.rb:18`
   - Suggested pattern: Background job
   ```ruby
   WarehouseSyncJob.perform_later(@order.id)
   ```

### Test Implications

Moving these responsibilities would:
- Enable 4 unit tests (model) instead of 4 request tests
- Remove HTTP setup for pricing/shipping tests
- Allow testing warehouse sync without full request cycle
- Estimated test speedup: 10x for extracted logic
```

## Automation Level

This command runs with mid-to-high automation:

1. **Automatic:** Layer identification, responsibility listing
2. **Automatic:** Categorization against layer concerns
3. **Automatic:** Extraction recommendations with code examples
4. **Manual input needed:** Only for ambiguous cases or when multiple valid approaches exist

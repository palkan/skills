# /layers:spec-test

Run the specification test on files to evaluate layer responsibility alignment.

The specification test works by generating a **test skeleton** — the describe/context structure that would be needed to fully test the code. This skeleton makes layer violations immediately visible: if you see `context "when HTTP response fails"` inside a domain model spec, something is wrong.

## Usage

```
/layers:spec-test [file_path]
/layers:spec-test app/controllers/orders_controller.rb
/layers:spec-test app/services/
```

## Process

1. **Read target file(s)**
2. **Identify architecture layer** (Presentation, Application, Domain, Infrastructure)
3. **Generate test skeleton** — describe/context blocks covering all code paths, annotated with ✓/⚠️/✗ markers
4. **Search for existing tests** — look for corresponding spec/test files; if found, annotate the actual test structure
5. **Recommend extractions** — concrete suggestions for misplaced responsibilities

## Layer Primary Responsibilities

| Layer | Primary Concern | Should Handle | Should NOT Handle |
|-------|-----------------|---------------|-------------------|
| Presentation (Controller) | HTTP handling | Auth, params, response codes, redirects | Business logic, calculations |
| Application (Service) | Use-case orchestration | Coordinating domain objects, transactions | Domain rules, HTTP concerns |
| Domain (Model) | Business rules | Validations, calculations, state transitions | Notifications, HTTP, external APIs |
| Infrastructure | Technical implementation | Persistence, external communication | Business rules |

## Output Format

```markdown
# Specification Test: [FileName]

**Layer:** [Identified layer]
**Primary Responsibility:** [Layer's primary concern]

## Test Skeleton

Generate the describe/context structure that would be needed to fully test this code.

**Skip configuration — only describe behavior:**
- Do NOT include associations, simple validations, enums, or other declarative
  configuration. Tests for `belongs_to :account` or `enum :status` are rarely
  useful and clutter the skeleton. Only include validations if they contain
  non-trivial logic (custom validators, conditional rules, cross-field checks).
- Focus on public methods and their behavioral edge cases.

**Authorization methods** (e.g., `accessible_to?`, `can_edit?`, policy-like checks):
- Flag as ⚠️ by default. In projects with a dedicated authorization layer
  (Action Policy, Pundit, etc.), these belong in policy objects, not models.
- Only mark ✓ if the project clearly has no authorization abstraction and
  keeps access rules in models by convention.

Every context must be annotated:

- ✓ — belongs in this layer
- ⚠️ — borderline, could stay but signals a design smell
- ✗ — does NOT belong in this layer (layer violation)

` ` `ruby
describe ClassName do
  describe "#method_name" do
    context "when [scenario]"           # ✓ [Layer concern]
    context "when [scenario]"           # ✗ [Wrong layer] — [brief why]
  end
end
` ` `

After the skeleton, add a short summary: how many contexts total, how many ✓, ⚠️, ✗.

## Existing Test Analysis

Search for existing test files for the target code. Use the project's test
framework conventions:

- RSpec: `spec/` directory, `_spec.rb` suffix
- Minitest: `test/` directory, `_test.rb` suffix

If tests exist:

1. Show the **actual** describe/context structure (extracted from the file)
2. Annotate each context with ✓/⚠️/✗ markers (same as the skeleton)
3. Highlight **symptoms of layer violations** in the test code:
   - Heavy mocking/stubbing of external services inside a model spec
   - Complex setup (factory chains, request stubs) for what should be simple unit tests
   - Callback bypass workarounds (`update_columns`, `skip_callbacks`) in test setup
   - Tests that are slow/brittle because they test across layer boundaries

If no tests exist, state that and note what the skeleton above reveals about testability.

## Extraction Recommendations

For each ✗ or ⚠️ item:

1. **[Responsibility]** → Extract to [target]
   - Current location: `file:line_range`
   - Suggested pattern: [pattern name]
   - Brief code sketch (keep short)
   - **Test impact:** Show how tests change after extraction. The key benefit:
     the original object's test can now mock/stub the extracted component and
     only verify it was invoked with the right input — all the ✗ contexts
     move to the extracted component's own test. Show both sides: what the
     original test becomes (simpler, mocking the extraction) and what the new
     test covers (the moved logic, tested in isolation).
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
# Specification Test: OrdersController

**Layer:** Presentation
**Primary Responsibility:** HTTP request/response handling

## Test Skeleton

` ` `ruby
describe "POST /orders" do
  # --- HTTP / Auth ---
  context "when user is not authenticated"          # ✓ Presentation — access control
  context "when user is authenticated" do           # ✓ Presentation — access control
    context "when order params are valid" do         # ✓ Presentation — param handling
      it "creates an order and redirects"            # ✓ Presentation — response

      # --- Pricing (domain logic leaked into controller) ---
      context "when customer is VIP" do
        it "applies 10% discount"                    # ✗ Domain — pricing rule
      end
      context "when customer is not VIP" do
        it "charges full price"                      # ✗ Domain — pricing rule
      end

      # --- Shipping (domain logic leaked into controller) ---
      context "when items weigh over 10" do
        it "adds weight surcharge"                   # ✗ Domain — shipping calculation
      end
      context "when express shipping selected" do
        it "adds express surcharge"                  # ✗ Domain — shipping calculation
      end

      # --- Notifications (application concern leaked into controller) ---
      it "sends confirmation email"                  # ✗ Application — notification orchestration
      it "sends Slack notification"                  # ✗ Application — notification orchestration

      # --- External sync (infrastructure leaked into controller) ---
      it "syncs order to warehouse API"              # ✗ Infrastructure — external API call
    end

    context "when order params are invalid" do
      it "renders the form with errors"              # ✓ Presentation — error response
    end
  end
end
` ` `

**Summary:** 12 test contexts — 4 ✓, 0 ⚠️, 8 ✗
Only 33% of what this controller needs testing actually belongs in the controller.

## Existing Test Analysis

Found: `spec/requests/orders_spec.rb`

` ` `ruby
describe "POST /orders" do
  context "when params are valid" do                 # ✓ Presentation
    it "creates the order"                           # ✓ Presentation
    it "applies VIP discount"                        # ✗ Domain — pricing rule tested via HTTP roundtrip
    it "calculates shipping for heavy items"         # ✗ Domain — requires factory setup for weight
  end
  context "when params are invalid" do               # ✓ Presentation
    it "returns 422"                                 # ✓ Presentation
  end
end
` ` `

**Symptoms visible in existing tests:**
- VIP discount test requires creating a user with `vip: true` + items with specific prices — heavy setup for a pricing rule
- Shipping test creates items with specific weights — testing domain math through an HTTP request
- No tests for Slack/warehouse sync — likely untested because setup is too complex at this layer

## Extraction Recommendations

1. **Pricing + shipping** → Order model
   - Current location: `orders_controller.rb:7-10, 25-31`
   - Pattern: Model calculation with before_validation callback
   ` ` `ruby
   # Order model
   before_validation :calculate_total

   def calculate_total
     self.total = items.sum(&:subtotal)
     self.total *= 0.9 if customer.vip?
     self.total += ShippingCalculator.new(self).cost
   end
   ` ` `
   - **Test impact:** Controller test no longer needs VIP/shipping contexts — just verify the order is saved and response is correct. All pricing/shipping edge cases move to a fast model unit test:
   ` ` `ruby
   # Controller test (after) — no pricing concerns
   describe "POST /orders" do
     it "creates the order and redirects" # ✓ no VIP setup, no weight setup
   end

   # Model test (new) — isolated, fast
   describe Order, "#calculate_total" do
     context "when customer is VIP"
     context "when items weigh over 10"
     context "when express shipping selected"
   end
   ` ` `

2. **Notifications + warehouse sync** → Application layer / background job
   - Current location: `orders_controller.rb:14-18`
   - Pattern: Active Delivery + background job
   - **Test impact:** Controller test verifies the delivery/job was enqueued, not that Slack/email/warehouse actually received anything:
   ` ` `ruby
   # Controller test (after) — mock the side effects
   it "enqueues order notifications" do
     assert_enqueued_with(job: OrderDelivery) { post orders_path, ... }
   end

   # Delivery test (new) — isolated
   describe OrderDelivery do
     it "sends confirmation email"
     it "sends Slack notification"
   end
   ` ` `
```

## Automation Level

This command runs with mid-to-high automation:

1. **Automatic:** Layer identification, test skeleton generation, annotation
2. **Automatic:** Search for existing tests, structure extraction, symptom analysis
3. **Automatic:** Extraction recommendations with code sketches
4. **Manual input needed:** Only for ambiguous cases or when multiple valid approaches exist

# Testing Anti-Patterns

Tests that verify the wrong layer's responsibilities.

## Testing Wrong Layer

**Problem:** Controller tests verify business logic.

```ruby
# BAD
describe OrdersController do
  it "applies VIP discount" do
    post :create, params: { items: [...] }
    expect(Order.last.total).to eq(90)  # Testing domain logic!
  end
end
```

**Fix:** Test business logic in model specs.

```ruby
# GOOD
describe Order do
  it "applies VIP discount" do
    order = build(:order, customer: vip_customer)
    order.calculate_total
    expect(order.total).to eq(90)
  end
end

describe OrdersController do
  it "creates order and redirects" do
    post :create, params: { items: [...] }
    expect(response).to redirect_to(Order.last)
  end
end
```

# Extract Query Logic to Query Object

Pull a long Active Record chain out of a controller into a composable query object.

## Before

```ruby
class ReportsController < ApplicationController
  def sales
    @orders = Order
      .joins(:customer, :line_items)
      .where(status: :completed)
      .where(created_at: params[:start_date]..params[:end_date])
      .where(customers: { region: params[:region] }) if params[:region].present?
      .group("DATE(orders.created_at)")
      .select(
        "DATE(orders.created_at) as date",
        "COUNT(DISTINCT orders.id) as order_count",
        "SUM(line_items.quantity * line_items.price) as revenue"
      )
      .order("date DESC")
  end
end
```

## After

```ruby
# app/queries/sales_report_query.rb
class SalesReportQuery < ApplicationQuery
  relation { Order.joins(:customer, :line_items).where(status: :completed) }

  def by_date_range(start_date, end_date)
    relation.where(created_at: start_date..end_date)
  end

  def by_region(region)
    return relation if region.blank?
    relation.where(customers: { region: region })
  end

  def daily_summary
    relation
      .group("DATE(orders.created_at)")
      .select(
        "DATE(orders.created_at) as date",
        "COUNT(DISTINCT orders.id) as order_count",
        "SUM(line_items.quantity * line_items.price) as revenue"
      )
      .order("date DESC")
  end
end

# app/controllers/reports_controller.rb
class ReportsController < ApplicationController
  def sales
    @orders = SalesReportQuery.new
      .by_date_range(params[:start_date], params[:end_date])
      .by_region(params[:region])
      .daily_summary
  end
end
```

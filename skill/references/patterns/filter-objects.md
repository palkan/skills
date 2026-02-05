# Filter Objects

## Summary

Filter objects transform datasets based on user-provided parameters. They belong to the presentation layer, consuming request parameters and applying transformations to domain collections.

## When to Use

- Request parameter filtering/transformation
- Search interfaces with multiple optional filters
- Sorting and pagination logic
- Parameter sanitization before domain layer

## When NOT to Use

- Domain-specific queries (use query objects)
- Form submissions (use form objects)

## Key Principles

- **Presentation layer** — consumes user input, not domain logic
- **One filter per interface** — avoid universal filter objects
- **Can use query objects internally** — filters orchestrate, queries implement
- **Declarative over imperative** — use DSL for common patterns

## Implementation

### With Rubanok (Recommended)

```ruby
class ApplicationFilter < Rubanok::Processor
  class << self
    alias filter call
  end
end

class ProjectsFilter < ApplicationFilter
  TYPES = %w[draft published].freeze
  SORT_FIELDS = %w[id name started_at].freeze
  SORT_ORDERS = %w[asc desc].freeze

  map :type_filter do |type_filter:|
    next raw.none unless TYPES.include?(type_filter)
    raw.where(status: type_filter)
  end

  match :time_filter do
    having "future" do
      raw.future
    end
    having "past" do
      raw.past
    end
  end

  map :sort_by, :sort_order do |sort_by: "started_at", sort_order: "desc"|
    next raw unless SORT_FIELDS.include?(sort_by) &&
                    SORT_ORDERS.include?(sort_order)
    raw.order(sort_by => sort_order)
  end

  map :q do |q:|
    raw.where(Project.arel_table[:name].matches("%#{q}%"))
  end
end
```

### Usage

```ruby
# Direct usage
projects = ProjectsFilter.filter(Project.all, params)

# Convention-based
class ApplicationRecord < ActiveRecord::Base
  def self.filter_by(params, with: nil)
    filter_class = with || "#{name.pluralize}Filter".constantize
    filter_class.filter(all, params)
  end
end

# In controller
def index
  @projects = Project.filter_by(params)
end
```

### Plain Ruby Implementation

```ruby
class ProjectsFilter
  ALLOWED_SORT_FIELDS = %w[name created_at].freeze

  def initialize(relation, params)
    @relation = relation
    @params = params
  end

  def filter
    result = @relation
    result = filter_by_status(result)
    result = filter_by_search(result)
    result = apply_sorting(result)
    result
  end

  private

  def filter_by_status(relation)
    return relation unless @params[:status].present?
    relation.where(status: @params[:status])
  end

  def filter_by_search(relation)
    return relation unless @params[:q].present?
    relation.where("name ILIKE ?", "%#{@params[:q]}%")
  end

  def apply_sorting(relation)
    field = @params[:sort_by]
    return relation unless ALLOWED_SORT_FIELDS.include?(field)
    relation.order(field => @params[:sort_order] || :asc)
  end
end
```

## Filter vs Query Object

| Aspect | Filter Object | Query Object |
|--------|---------------|--------------|
| Layer | Presentation | Domain |
| Input | Request params | Domain values |
| Purpose | UI filtering | Reusable queries |
| Location | `app/filters/` | `app/queries/` |

```ruby
# Filter object (presentation) uses query object (domain)
class PostsFilter < ApplicationFilter
  map :trending do |trending:|
    next raw unless trending == "true"
    Post::TrendingQuery.new(raw).resolve
  end
end
```

## Anti-Patterns

### Universal Filter Object

```ruby
# BAD: One filter for all interfaces
class UniversalFilter
  def filter(relation, params)
    # Handles every possible filter for every model
  end
end
```

**Fix:** Create interface-specific filters:

```ruby
# GOOD
class Admin::UsersFilter < ApplicationFilter
  # Admin-specific filters
end

class Api::V1::UsersFilter < ApplicationFilter
  # API-specific filters
end
```

### Filtering in Controller

```ruby
# BAD
def index
  @projects = Project.all
  @projects = @projects.where(status: params[:status]) if params[:status]
  @projects = @projects.where("name LIKE ?", "%#{params[:q]}%") if params[:q]
  # ...
end

# GOOD
def index
  @projects = Project.filter_by(params)
end
```

## Security Considerations

Always whitelist allowed values:

```ruby
class ProjectsFilter < ApplicationFilter
  ALLOWED_STATUSES = %w[draft published].freeze

  map :status do |status:|
    next raw unless ALLOWED_STATUSES.include?(status)
    raw.where(status:)
  end
end
```

## Related Gems

| Gem | Purpose |
|-----|---------|
| rubanok | Parameter-based transformation pipelines |
| has_scope | DSL to glue scopes to controller params |
| filterameter | Declarative filter DSL |

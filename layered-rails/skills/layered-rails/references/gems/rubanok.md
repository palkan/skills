# Rubanok

Transform controller params into database queries.

**GitHub**: https://github.com/palkan/rubanok
**Layer**: Presentation/Application boundary

## Installation

```ruby
# Gemfile
gem "rubanok"
```

## Basic Usage

### Define Processor

```ruby
class PostsProcessor < Rubanok::Processor
  # Simple equality match
  map :status

  # With transformation
  map :author_id do |author_id:|
    raw.where(author_id: author_id)
  end

  # Search
  map :q do |q:|
    raw.where("title ILIKE ?", "%#{q}%")
  end

  # Sorting
  map :sort do |sort:|
    field, dir = sort.split("_")
    raw.order(field => dir)
  end
end
```

### Controller Integration

```ruby
class PostsController < ApplicationController
  def index
    @posts = rubanok_process(Post.all, params)
    # Or with explicit processor
    @posts = rubanok_process(Post.all, params, with: PostsProcessor)
  end
end
```

## Matching Rules

### Simple Match

```ruby
class PostsProcessor < Rubanok::Processor
  # Maps params[:status] to where(status: value)
  map :status

  # With alias
  map :state, to: :status
end
```

### Custom Mapping

```ruby
class PostsProcessor < Rubanok::Processor
  map :published do |published:|
    if published == "true"
      raw.where.not(published_at: nil)
    else
      raw.where(published_at: nil)
    end
  end
end
```

### Multiple Params

```ruby
class PostsProcessor < Rubanok::Processor
  map :min_date, :max_date do |min_date: nil, max_date: nil|
    scope = raw
    scope = scope.where("created_at >= ?", min_date) if min_date
    scope = scope.where("created_at <= ?", max_date) if max_date
    scope
  end
end
```

## Matching with `match`

```ruby
class PostsProcessor < Rubanok::Processor
  # Match specific values
  match :order, ->(dir) { dir.in?(%w[asc desc]) } do |order:|
    raw.order(created_at: order)
  end

  # Match with type checking
  match :page, ->(v) { v.to_i.positive? } do |page:|
    raw.page(page.to_i)
  end
end
```

## Fail Strategy

```ruby
class PostsProcessor < Rubanok::Processor
  # Raise on invalid params
  fail_when :status, ->(v) { !Post.statuses.key?(v) }

  # Or custom handling
  match :status, ->(v) { Post.statuses.key?(v) } do |status:|
    raw.where(status: status)
  end
end
```

## Nested Params

```ruby
class PostsProcessor < Rubanok::Processor
  nested :filter do
    map :status
    map :author_id
  end
end

# Processes params[:filter][:status], params[:filter][:author_id]
```

## Sorting

```ruby
class PostsProcessor < Rubanok::Processor
  SORTABLE_FIELDS = %w[title created_at views_count].freeze

  map :sort_by, :sort_order do |sort_by: "created_at", sort_order: "desc"|
    field = SORTABLE_FIELDS.include?(sort_by) ? sort_by : "created_at"
    dir = sort_order == "asc" ? :asc : :desc
    raw.order(field => dir)
  end
end
```

## Pagination

```ruby
class PostsProcessor < Rubanok::Processor
  DEFAULT_PER_PAGE = 20
  MAX_PER_PAGE = 100

  map :page, :per_page do |page: 1, per_page: DEFAULT_PER_PAGE|
    page = [page.to_i, 1].max
    per_page = [[per_page.to_i, 1].max, MAX_PER_PAGE].min

    raw.offset((page - 1) * per_page).limit(per_page)
  end
end
```

## With Form Object

```ruby
class PostsFilterForm
  include ActiveModel::Model
  include ActiveModel::Attributes

  attribute :status, :string
  attribute :author_id, :integer
  attribute :q, :string
  attribute :sort_by, :string, default: "created_at"
  attribute :sort_order, :string, default: "desc"

  validates :status, inclusion: { in: Post.statuses.keys }, allow_blank: true
end

class PostsController < ApplicationController
  def index
    @filter = PostsFilterForm.new(filter_params)

    if @filter.valid?
      @posts = rubanok_process(Post.all, @filter.attributes)
    else
      @posts = Post.none
    end
  end

  private

  def filter_params
    params.fetch(:filter, {}).permit(:status, :author_id, :q, :sort_by, :sort_order)
  end
end
```

## Testing

```ruby
RSpec.describe PostsProcessor do
  let(:scope) { Post.all }

  describe "status filter" do
    it "filters by status" do
      result = described_class.call(scope, status: "published")

      expect(result.to_sql).to include("status")
    end
  end

  describe "search" do
    it "searches by title" do
      result = described_class.call(scope, q: "ruby")

      expect(result.to_sql).to include("ILIKE")
    end
  end

  describe "sorting" do
    it "sorts by field" do
      result = described_class.call(scope, sort: "title_asc")

      expect(result.to_sql).to include("ORDER BY")
    end
  end
end
```

## Related

- [Filter Objects Pattern](../patterns/filter-objects.md)
- [Query Objects Pattern](../patterns/query-objects.md)

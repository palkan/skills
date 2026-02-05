# Repositories

## Summary

Repositories encapsulate complex data access patterns, providing a clean interface between domain logic and persistence. In Rails, they complement Active Record rather than replacing it, handling cross-model queries and external data sources.

## When to Use

- Complex queries spanning multiple models
- Data aggregation from multiple sources
- External data source integration
- Caching layers for expensive queries
- Read model optimization (CQRS-lite)

## When NOT to Use

- Simple single-model queries (use scopes)
- CRUD operations (use Active Record directly)
- Before query complexity justifies abstraction

## Key Principles

- **Complement Active Record** — don't fight Rails conventions
- **Encapsulate complexity** — hide multi-model joins and aggregations
- **Return domain objects** — not raw hashes or database results
- **Single responsibility** — one repository per aggregate or read concern

## Implementation

### Basic Repository

```ruby
class PostRepository
  def featured_with_stats
    Post
      .published
      .joins(:comments, :likes)
      .select(
        "posts.*",
        "COUNT(DISTINCT comments.id) AS comments_count",
        "COUNT(DISTINCT likes.id) AS likes_count"
      )
      .group("posts.id")
      .order(likes_count: :desc)
      .limit(10)
  end

  def by_author_with_engagement(author)
    Post
      .where(author: author)
      .includes(:comments, :likes)
      .order(created_at: :desc)
  end
end

# Usage
repository = PostRepository.new
@featured = repository.featured_with_stats
```

### Repository with Caching

```ruby
class DashboardRepository
  def initialize(user)
    @user = user
  end

  def stats
    Rails.cache.fetch(cache_key, expires_in: 5.minutes) do
      {
        total_posts: user_posts.count,
        published_posts: user_posts.published.count,
        total_views: total_views,
        engagement_rate: calculate_engagement
      }
    end
  end

  private

  attr_reader :user

  def cache_key
    "dashboard/#{user.id}/#{user.updated_at.to_i}"
  end

  def user_posts
    @user_posts ||= Post.where(author: user)
  end

  def total_views
    user_posts.sum(:views_count)
  end

  def calculate_engagement
    return 0 if total_views.zero?
    (Comment.where(post: user_posts).count.to_f / total_views * 100).round(2)
  end
end
```

### Multi-Source Repository

```ruby
class UserActivityRepository
  def initialize(user)
    @user = user
  end

  def recent_activity
    activities = []
    activities.concat(recent_posts)
    activities.concat(recent_comments)
    activities.concat(recent_likes)
    activities.sort_by(&:created_at).reverse.first(20)
  end

  private

  attr_reader :user

  def recent_posts
    user.posts.recent.limit(10).map do |post|
      Activity.new(
        type: :post,
        record: post,
        created_at: post.created_at,
        description: "Published '#{post.title}'"
      )
    end
  end

  def recent_comments
    user.comments.recent.limit(10).map do |comment|
      Activity.new(
        type: :comment,
        record: comment,
        created_at: comment.created_at,
        description: "Commented on '#{comment.post.title}'"
      )
    end
  end

  def recent_likes
    user.likes.recent.includes(:post).limit(10).map do |like|
      Activity.new(
        type: :like,
        record: like,
        created_at: like.created_at,
        description: "Liked '#{like.post.title}'"
      )
    end
  end

  Activity = Data.define(:type, :record, :created_at, :description)
end
```

### Read Model Repository

For complex reporting or dashboards:

```ruby
class AnalyticsRepository
  def post_performance(date_range:)
    Post
      .where(published_at: date_range)
      .joins("LEFT JOIN comments ON comments.post_id = posts.id")
      .joins("LEFT JOIN likes ON likes.post_id = posts.id")
      .group("DATE(posts.published_at)")
      .select(
        "DATE(posts.published_at) AS date",
        "COUNT(DISTINCT posts.id) AS posts_count",
        "COUNT(DISTINCT comments.id) AS comments_count",
        "COUNT(DISTINCT likes.id) AS likes_count",
        "SUM(posts.views_count) AS total_views"
      )
      .order(:date)
      .map { |row| PerformanceData.new(row.attributes.symbolize_keys) }
  end

  PerformanceData = Data.define(:date, :posts_count, :comments_count, :likes_count, :total_views) do
    def engagement_rate
      return 0 if total_views.zero?
      ((comments_count + likes_count).to_f / total_views * 100).round(2)
    end
  end
end
```

### External Data Integration

```ruby
class BookRepository
  def initialize(api_client: GoogleBooksAPI.new)
    @api_client = api_client
  end

  def find_with_external_data(isbn)
    book = Book.find_by!(isbn: isbn)
    external_data = fetch_external_data(isbn)

    BookWithMetadata.new(
      book: book,
      cover_url: external_data[:cover],
      description: external_data[:description],
      rating: external_data[:average_rating]
    )
  end

  def search(query)
    # Combine local and external results
    local_results = Book.search(query).limit(10)
    external_results = api_client.search(query)

    merge_results(local_results, external_results)
  end

  private

  attr_reader :api_client

  def fetch_external_data(isbn)
    Rails.cache.fetch("book_external/#{isbn}", expires_in: 1.day) do
      api_client.fetch(isbn)
    end
  end

  def merge_results(local, external)
    # Prefer local, supplement with external
    local_isbns = local.pluck(:isbn)
    unique_external = external.reject { |e| local_isbns.include?(e[:isbn]) }

    local.to_a + unique_external.first(5).map { |data| Book.new(data) }
  end

  BookWithMetadata = Data.define(:book, :cover_url, :description, :rating) do
    delegate_missing_to :book
  end
end
```

## Repository vs Query Object

| Repository | Query Object |
|------------|--------------|
| Multiple related queries | Single query concern |
| Cross-model aggregation | Single-model filtering |
| External data integration | Database queries only |
| Caching strategies | Composable query logic |
| Read model concerns | Reusable query fragments |

```ruby
# Query Object: single composable query
class PublishedPostsQuery < ApplicationQuery
  relation { Post.published }

  def by_author(author) = relation.where(author:)
  def recent = relation.order(published_at: :desc)
end

# Repository: aggregates multiple concerns
class PostRepository
  def featured_posts
    # Uses multiple queries, caching, maybe external data
  end
end
```

## Testing

```ruby
RSpec.describe DashboardRepository do
  let(:user) { create(:user) }
  let(:repository) { described_class.new(user) }

  describe "#stats" do
    before do
      create_list(:post, 3, author: user, status: :published)
      create_list(:post, 2, author: user, status: :draft)
    end

    it "returns correct post counts" do
      stats = repository.stats

      expect(stats[:total_posts]).to eq(5)
      expect(stats[:published_posts]).to eq(3)
    end

    it "caches results" do
      expect(Rails.cache).to receive(:fetch).and_call_original

      2.times { repository.stats }
    end
  end
end
```

## Anti-Patterns

### Thin Repository Wrapper

```ruby
# BAD: No value added over Active Record
class PostRepository
  def find(id)
    Post.find(id)
  end

  def all
    Post.all
  end

  def create(params)
    Post.create(params)
  end
end

# GOOD: Just use Active Record directly
Post.find(id)
```

### Repository with Business Logic

```ruby
# BAD: Business logic in repository
class PostRepository
  def publish(post)
    post.update!(published_at: Time.current)
    NotificationService.notify_subscribers(post)
    AnalyticsService.track_publication(post)
  end
end

# GOOD: Repository for data access, service for operations
class PostRepository
  def published_with_stats
    # Complex query
  end
end

class PublishPost
  def call(post)
    post.publish!
    # Side effects
  end
end
```

## File Organization

```
app/
├── models/
│   └── post.rb
├── queries/
│   └── published_posts_query.rb
└── repositories/
    ├── dashboard_repository.rb
    ├── analytics_repository.rb
    └── post_repository.rb
```

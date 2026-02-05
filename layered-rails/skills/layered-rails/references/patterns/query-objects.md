# Query Objects

## Summary

Query objects encapsulate complex, context-specific database queries. They separate persistence concerns from domain models and provide reusable, testable query logic.

## When to Use

- Complex queries with multiple JOINs or subqueries
- Context-specific queries (not general model scopes)
- Queries reused across multiple controllers/services
- Queries that need parameterization

## When NOT to Use

- Simple queries (use model scopes)
- Single-condition filters (use atomic scopes)

## Key Principles

- **Atomic scopes in models** — simple, single-condition scopes stay in models
- **Complex queries in query objects** — multi-condition, context-specific queries
- **Use Arel for reusability** — avoid SQL string stitching
- **Convention-based discovery** — `Model::SomeQuery` resolves to model automatically

## Implementation

### Base Class

```ruby
class ApplicationQuery
  class << self
    def resolve(...) = new.resolve(...)
    alias_method :call, :resolve

    def query_model
      name.sub(/::[^\:]+$/, "").safe_constantize
    end
  end

  private attr_reader :relation

  def initialize(relation = self.class.query_model&.all)
    @relation = relation
  end

  def resolve(...) = relation
end
```

### Example Query Object

```ruby
class User::WithBookmarkedPostsQuery < ApplicationQuery
  def resolve(period: :previous_week)
    bookmarked_posts = build_bookmarked_posts_scope(period)
    relation.with(bookmarked_posts:).joins(:bookmarked_posts)
  end

  private

  def build_bookmarked_posts_scope(period)
    Post.public_send(period)
        .where.associated(:bookmarks)
        .select(:user_id).distinct
  end
end
```

### Usage

```ruby
# Default relation (User.all)
User::WithBookmarkedPostsQuery.resolve

# Custom base relation
User::WithBookmarkedPostsQuery.new(account.users).resolve(period: :this_month)

# Or with call alias
User::WithBookmarkedPostsQuery.call(period: :previous_week)
```

## Atomic vs Complex Scopes

### Atomic Scopes (Keep in Model)

Single condition, composable:

```ruby
class Post < ApplicationRecord
  scope :published, -> { where.not(published_at: nil) }
  scope :recent, -> { where(created_at: 1.week.ago..) }
  scope :by_author, ->(user) { where(user:) }
end

# Compose them
Post.published.recent.by_author(user)
```

### Complex Scopes (Extract to Query Object)

Multiple conditions, context-specific:

```ruby
# BAD: Complex scope in model
class Post < ApplicationRecord
  scope :trending, -> {
    joins(:views, :comments)
      .where(views: {created_at: 1.day.ago..})
      .group(:id)
      .having("COUNT(views.id) > 100")
      .order("COUNT(comments.id) DESC")
  }
end

# GOOD: Query object
class Post::TrendingQuery < ApplicationQuery
  def resolve(min_views: 100, period: 1.day.ago..)
    relation
      .joins(:views, :comments)
      .where(views: {created_at: period})
      .group(:id)
      .having("COUNT(views.id) > ?", min_views)
      .order("COUNT(comments.id) DESC")
  end
end
```

## Using Arel

For reusable, composable query fragments:

```ruby
class Post::SearchQuery < ApplicationQuery
  def resolve(query:)
    relation.where(
      Post.arel_table[:title].matches("%#{query}%")
        .or(Post.arel_table[:body].matches("%#{query}%"))
    )
  end
end
```

## Attaching Query Objects as Scopes

```ruby
class ApplicationRecord < ActiveRecord::Base
  def self.query(query_class, ...)
    query_class.new(all).resolve(...)
  end
end

# Usage
Post.query(Post::TrendingQuery, min_views: 50)
```

## Anti-Patterns

### Over-Scoping

Scopes that include other scopes, causing conflicts:

```ruby
# BAD: Scopes with implicit ordering
scope :recent, -> { order(created_at: :desc) }
scope :popular, -> { order(views_count: :desc) }

Post.recent.popular  # Which order wins?
```

### Context-Free Queries in Models

General queries that are actually context-specific:

```ruby
# BAD: This is really "admin dashboard search"
class User < ApplicationRecord
  scope :search, ->(q) {
    joins(:posts, :comments)
      .where("users.name LIKE ?", "%#{q}%")
      .or(where("posts.title LIKE ?", "%#{q}%"))
  }
end

# GOOD: Context-specific query object
class Admin::UserSearchQuery < ApplicationQuery
  # ...
end
```

## Related Gems

| Gem | Purpose |
|-----|---------|
| arel-helpers | Reduce Arel boilerplate for complex JOINs |

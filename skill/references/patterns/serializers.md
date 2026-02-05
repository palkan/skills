# Serializers

## Summary

Serializers are specialized presenters for API responses. They form a dedicated abstraction layer between models and the external API contract, providing consistent JSON formatting and the ability to generate TypeScript types.

## When to Use

- API responses beyond simple JSON
- Multiple JSON formats for different contexts
- TypeScript frontend integration
- Versioned APIs

## When NOT to Use

- Simple `render json: @model`
- Internal data transformation

## Key Principles

- **Don't override `#as_json`** — couples model to API representation
- **Convention-based lookup** — `PostSerializer` for `Post` model
- **One serializer per context** — different serializers for list vs detail
- **Generate TypeScript types** — keep frontend in sync

## Implementation

### Plain Ruby Serializer

```ruby
class UserSerializer < SimpleDelegator
  def as_json(...)
    {id:, short_name:, email:}
  end

  def short_name
    name.squish.split(/\s/).then do |parts|
      parts[0..-2].map { _1[0] + "." }.join + parts.last
    end
  end
end

class PostSerializer < SimpleDelegator
  def as_json(...)
    {
      id:,
      title:,
      is_draft: draft?,
      user: UserSerializer.new(user)
    }
  end
end
```

### Alba Serializer (Recommended)

```ruby
class ApplicationSerializer
  include Alba::Resource
  include Rails.application.routes.url_helpers
end

class UserSerializer < ApplicationSerializer
  attributes :id, :email

  attribute :short_name do |user|
    user.name.squish.split(/\s/).then do |parts|
      parts[0..-2].map { _1[0] + "." }.join + parts.last
    end
  end
end

class PostSerializer < ApplicationSerializer
  attributes :id, :title
  attribute :is_draft, &:draft?
  attribute :url do |post|
    post_url(post)
  end

  one :user
  many :comments
end
```

### Usage

```ruby
# Single object
render json: PostSerializer.new(post)

# Collection
render json: PostSerializer.new(posts)

# With root key
render json: {post: PostSerializer.new(post)}
```

### Convention-Based Lookup

```ruby
class ApplicationController < ActionController::API
  private

  def serialize(obj, with: nil)
    serializer = with || infer_serializer(obj)
    serializer.new(obj)
  end

  def infer_serializer(obj)
    model = obj.respond_to?(:model) ? obj.model : obj.class
    "#{model.name}Serializer".constantize
  end
end

# Usage
render json: serialize(@post)
render json: serialize(@post, with: Post::DetailSerializer)
```

### Context-Specific Serializers

```ruby
# List view (minimal)
class Post::ListSerializer < ApplicationSerializer
  attributes :id, :title, :published_at
end

# Detail view (full)
class Post::DetailSerializer < ApplicationSerializer
  attributes :id, :title, :body, :published_at
  one :user
  many :comments
end

# Admin view
class Admin::PostSerializer < ApplicationSerializer
  attributes :id, :title, :body, :status, :created_at, :updated_at
  one :user
  attribute :edit_url do |post|
    admin_post_url(post)
  end
end
```

### TypeScript Generation

```ruby
class ApplicationSerializer
  include Alba::Resource
  include Typelizer::DSL
end

class PostSerializer < ApplicationSerializer
  typelize_from Post
  typelize is_draft: "boolean"

  attributes :id, :title
  attribute :is_draft, &:draft?
  one :user
end
```

Generated TypeScript:

```typescript
interface Post {
  id: number;
  title: string;
  is_draft: boolean;
  user: User;
}
```

## Anti-Patterns

### Overriding `#as_json` in Models

```ruby
# BAD
class Post < ApplicationRecord
  def as_json(options = {})
    super(options.merge(
      only: [:id, :title],
      methods: [:is_draft],
      include: {user: {only: [:id, :name]}}
    ))
  end
end

# GOOD: Use serializer
class PostSerializer < ApplicationSerializer
  attributes :id, :title
  attribute :is_draft, &:draft?
  one :user
end
```

### Multiple Formats Without Serializers

```ruby
# BAD
def show
  respond_to do |format|
    format.json { render json: @post.as_json(include: :user) }
    format.xml { render xml: @post.to_xml(include: :user) }
  end
end

# GOOD
def show
  respond_to do |format|
    format.json { render json: PostSerializer.new(@post) }
  end
end
```

## Testing

```ruby
RSpec.describe PostSerializer do
  let(:post) { create(:post, title: "Hello", draft: true) }
  let(:serialized) { described_class.new(post).as_json }

  it "includes expected attributes" do
    expect(serialized).to include(
      id: post.id,
      title: "Hello",
      is_draft: true
    )
  end

  it "includes nested user" do
    expect(serialized[:user]).to include(
      id: post.user.id
    )
  end
end
```

## Related Gems

| Gem | Purpose |
|-----|---------|
| alba | Fast JSON serialization with DSL |
| typelizer | Generate TypeScript from serializers |

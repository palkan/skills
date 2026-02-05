# Alba

Fast JSON serialization with a clean DSL.

**GitHub**: https://github.com/okuramasafumi/alba
**Layer**: Presentation (API layer)

## Installation

```ruby
# Gemfile
gem "alba"
```

## Basic Usage

### Define Serializer

```ruby
class UserSerializer
  include Alba::Resource

  attributes :id, :email

  attribute :full_name do |user|
    "#{user.first_name} #{user.last_name}"
  end
end
```

### Serialize

```ruby
user = User.find(1)
UserSerializer.new(user).serialize
# => '{"id":1,"email":"user@example.com","full_name":"John Doe"}'

# Collection
users = User.all
UserSerializer.new(users).serialize
# => '[{"id":1,...},{"id":2,...}]'
```

### In Controller

```ruby
class UsersController < ApplicationController
  def show
    user = User.find(params[:id])
    render json: UserSerializer.new(user)
  end

  def index
    users = User.all
    render json: UserSerializer.new(users)
  end
end
```

## Associations

```ruby
class PostSerializer
  include Alba::Resource

  attributes :id, :title, :body

  # Nested serializer
  one :author, resource: UserSerializer

  # Collection
  many :comments, resource: CommentSerializer

  # Inline definition
  many :tags do
    attributes :id, :name
  end
end
```

## Conditional Attributes

```ruby
class UserSerializer
  include Alba::Resource

  attributes :id, :name, :email

  # Conditional attribute
  attribute :admin_notes, if: proc { |user, context|
    context[:current_user]&.admin?
  }

  # Method-based condition
  attribute :phone, if: :show_phone?

  def show_phone?(user)
    user.phone_public?
  end
end

# Pass context
UserSerializer.new(user, params: { current_user: current_user }).serialize
```

## Computed Attributes

```ruby
class PostSerializer
  include Alba::Resource

  attributes :id, :title

  attribute :is_published do |post|
    post.published_at.present?
  end

  attribute :reading_time do |post|
    (post.body.split.size / 200.0).ceil
  end

  attribute :url do |post|
    Rails.application.routes.url_helpers.post_url(post)
  end
end
```

## Root Key

```ruby
class UserSerializer
  include Alba::Resource

  root_key :user, :users  # singular, plural

  attributes :id, :name
end

UserSerializer.new(user).serialize
# => '{"user":{"id":1,"name":"John"}}'

UserSerializer.new(users).serialize
# => '{"users":[{"id":1,"name":"John"},...]}'
```

## Base Serializer

```ruby
class ApplicationSerializer
  include Alba::Resource
  include Rails.application.routes.url_helpers

  # Common configuration
  transform_keys :lower_camel

  # Helper available to all serializers
  def current_time
    Time.current.iso8601
  end
end

class UserSerializer < ApplicationSerializer
  attributes :id, :name

  attribute :serialized_at do
    current_time
  end
end
```

## Key Transformation

```ruby
class UserSerializer
  include Alba::Resource

  # Transform all keys
  transform_keys :lower_camel  # firstName
  transform_keys :dash         # first-name

  attributes :first_name, :last_name  # becomes firstName, lastName
end
```

## TypeScript Generation

With typelizer:

```ruby
# Gemfile
gem "typelizer"

class ApplicationSerializer
  include Alba::Resource
  include Typelizer::DSL
end

class UserSerializer < ApplicationSerializer
  typelize_from User

  attributes :id, :email
  attribute :is_admin, &:admin?
end
```

Generated TypeScript:

```typescript
interface User {
  id: number;
  email: string;
  is_admin: boolean;
}
```

## Performance Tips

```ruby
# Use select to avoid loading unused columns
users = User.select(:id, :name, :email)
UserSerializer.new(users).serialize

# Preload associations
posts = Post.includes(:author, :comments)
PostSerializer.new(posts).serialize
```

## Testing

```ruby
RSpec.describe UserSerializer do
  let(:user) { create(:user, first_name: "John", last_name: "Doe") }
  let(:serialized) { JSON.parse(described_class.new(user).serialize) }

  it "includes expected attributes" do
    expect(serialized).to include(
      "id" => user.id,
      "email" => user.email,
      "full_name" => "John Doe"
    )
  end
end
```

## Related

- [Serializers Pattern](../patterns/serializers.md)

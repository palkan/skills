# Value Objects

## Summary

Value objects encapsulate domain concepts that are defined by their attributes rather than identity. They're immutable, comparable by value, and often created from multiple database columns or JSON stores.

## When to Use

- Domain concepts like Money, Address, Coordinates
- Groups of related attributes that travel together
- Attributes with behavior (formatting, validation, comparison)
- JSON/JSONB column wrappers with validation

## When NOT to Use

- Entities with identity (use models)
- Simple scalar values without behavior

## Key Principles

- **Immutable** — value objects don't change after creation
- **Equality by value** — two objects with same attributes are equal
- **No identity** — no `id` field, not persisted directly
- **Self-contained** — all behavior related to the concept

## Implementation

### Using Data Class

```ruby
class MediaType < Data.define(:content_type)
  SVG_TYPES = %w[image/svg image/svg+xml].freeze
  FONT_TYPES = %w[font/otf font/ttf font/woff font/woff2].freeze

  include Comparable

  def <=>(other)
    content_type <=> other.content_type
  end

  def video?
    content_type.start_with?("video")
  end

  def image?
    content_type.start_with?("image")
  end

  def svg?
    SVG_TYPES.include?(content_type)
  end

  def font?
    FONT_TYPES.include?(content_type)
  end
end

# Usage
media_type = MediaType.new("image/png")
media_type.image?  #=> true
media_type.video?  #=> false
```

### Usage in Models

```ruby
module WithMedia
  extend ActiveSupport::Concern

  included do
    has_one_attached :media
  end

  def media_type
    return unless media&.content_type
    MediaType.new(media.content_type)
  end
end

class Post < ApplicationRecord
  include WithMedia
end

post.media_type.video?
```

### With `composed_of` (Multiple Columns)

```ruby
class User::Address
  include ActiveModel::API
  include ActiveModel::Attributes

  attribute :country
  attribute :city
  attribute :street
  attribute :zip

  def full_address
    [street, city, zip, country].compact.join(", ")
  end
end

class User < ApplicationRecord
  composed_of :address,
    class_name: "User::Address",
    mapping: [
      %w[address_country country],
      %w[address_city city],
      %w[address_street street],
      %w[address_zip zip]
    ],
    constructor: proc { |country, city, street, zip|
      User::Address.new(country:, city:, street:, zip:)
    }
end

# Usage
user = User.create!(
  address_country: "UK",
  address_city: "Birmingham",
  address_street: "Livery St",
  address_zip: "B32PB"
)
user.address.full_address  #=> "Livery St, Birmingham, B32PB, UK"
user.address.zip  #=> "B32PB"
```

### With JSON Store

```ruby
class User < ApplicationRecord
  store :address, coder: JSON

  def address
    @address ||= User::Address.new(super || {})
  end

  validate do |record|
    next if address.valid?
    record.errors.add(:address, "is invalid")
  end
end

class User::Address
  include ActiveModel::API
  include ActiveModel::Attributes

  attribute :country
  attribute :city
  attribute :street
  attribute :zip

  validates :country, :zip, presence: true
end

# Usage
user = User.create!(address: {country: "USA", city: "Bronx", zip: "10463"})
user.address.country  #=> "USA"
```

### With store_model Gem

```ruby
class AddressModel
  include StoreModel::Model

  attribute :country, :string
  attribute :city, :string
  attribute :street, :string
  attribute :zip, :string

  validates :country, :zip, presence: true
end

class User < ApplicationRecord
  attribute :address, AddressModel.to_type
  validates :address, store_model: true
end
```

## Money Example

```ruby
class Money < Data.define(:amount_cents, :currency)
  CURRENCIES = %w[USD EUR GBP].freeze

  def initialize(amount_cents:, currency: "USD")
    raise ArgumentError unless CURRENCIES.include?(currency)
    super
  end

  def to_s
    format("%.2f %s", amount_cents / 100.0, currency)
  end

  def +(other)
    raise ArgumentError unless currency == other.currency
    Money.new(amount_cents: amount_cents + other.amount_cents, currency:)
  end

  def *(multiplier)
    Money.new(amount_cents: (amount_cents * multiplier).round, currency:)
  end
end

# Usage
price = Money.new(amount_cents: 1999, currency: "USD")
price.to_s  #=> "19.99 USD"
price * 2   #=> Money(amount_cents: 3998, currency: "USD")
```

## Anti-Patterns

### Mutable Value Objects

```ruby
# BAD
class Address
  attr_accessor :city, :street  # Mutable!
end

# GOOD: Use Data class (immutable)
class Address < Data.define(:city, :street)
end
```

### Value Objects With Side Effects

```ruby
# BAD
class Coordinates < Data.define(:lat, :lng)
  def save_to_cache!
    Rails.cache.write("coords", self)
  end
end

# GOOD: Value objects are pure
class Coordinates < Data.define(:lat, :lng)
  def distance_to(other)
    # Pure calculation
  end
end
```

## Performance Note

Active Model objects are slower than plain Ruby Data/Struct (~4-13x), but only optimize when profiling shows it's a bottleneck. The benefits of Active Model integration (validations, attributes API) usually outweigh the overhead.

## Related Gems

| Gem | Purpose |
|-----|---------|
| store_model | Active Model for JSON store attributes |
| frozen_record | Query static YAML/JSON like Active Record |

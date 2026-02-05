# Anyway Config

Configuration management with typed attributes and multiple sources.

**GitHub**: https://github.com/palkan/anyway_config
**Layer**: Infrastructure

## Installation

```ruby
# Gemfile
gem "anyway_config"

# Generate config
rails generate anyway:config stripe
```

## Basic Usage

### Define Config

```ruby
# app/configs/stripe_config.rb
class StripeConfig < Anyway::Config
  attr_config :api_key,
              :webhook_secret,
              :publishable_key,
              currency: "usd"

  required :api_key, :webhook_secret
end
```

### YAML Source

```yaml
# config/stripe.yml
default:
  currency: usd

development:
  api_key: sk_test_xxx
  webhook_secret: whsec_xxx
  publishable_key: pk_test_xxx

production:
  api_key: <%= ENV["STRIPE_API_KEY"] %>
  webhook_secret: <%= ENV["STRIPE_WEBHOOK_SECRET"] %>
  publishable_key: <%= ENV["STRIPE_PUBLISHABLE_KEY"] %>
```

### Access Config

```ruby
StripeConfig.new.api_key
# Or with singleton pattern
StripeConfig.api_key
```

## Base Config Class

```ruby
# app/configs/application_config.rb
class ApplicationConfig < Anyway::Config
  class << self
    def instance
      @instance ||= new
    end

    delegate_missing_to :instance
  end
end

class StripeConfig < ApplicationConfig
  # ...
end

# Usage
StripeConfig.api_key
```

## Nested Configuration

```ruby
class EmailConfig < ApplicationConfig
  attr_config :from_address,
              :reply_to,
              smtp: {
                host: "localhost",
                port: 25,
                username: nil,
                password: nil
              }
end

# Access
EmailConfig.smtp.host
EmailConfig.smtp.port
```

## Type Coercion

```ruby
class AppConfig < ApplicationConfig
  attr_config :port,
              :debug,
              :allowed_hosts

  coerce_types port: :integer,
               debug: :boolean,
               allowed_hosts: { type: :string, array: true }
end
```

## Validation

```ruby
class DatabaseConfig < ApplicationConfig
  attr_config :host, :port, :pool_size

  required :host

  on_load do
    raise_validation_error("port must be positive") if port && port <= 0
    raise_validation_error("pool_size must be positive") if pool_size <= 0
  end
end
```

## Environment Sources (Priority)

1. **Environment variables** (highest)
   - `STRIPE_API_KEY`, `STRIPE_CURRENCY`

2. **Local files** (gitignored)
   - `config/stripe.local.yml`

3. **Environment YAML**
   - `config/stripe.yml` (under environment key)

4. **Default values** (lowest)
   - `attr_config currency: "usd"`

```ruby
# Override via ENV
STRIPE_CURRENCY=eur rails console
StripeConfig.currency  #=> "eur"
```

## Local Overrides

```yaml
# config/stripe.local.yml (gitignored)
api_key: sk_test_local_override
```

## Testing

```ruby
RSpec.describe PaymentService do
  let(:config) do
    StripeConfig.new(
      api_key: "test_key",
      webhook_secret: "test_secret",
      currency: "eur"
    )
  end

  it "uses configured currency" do
    service = described_class.new(config: config)
    # ...
  end
end

# Or with environment override
RSpec.describe "with config" do
  around do |example|
    with_env("STRIPE_CURRENCY" => "gbp") { example.run }
  end

  it "uses environment value" do
    expect(StripeConfig.new.currency).to eq("gbp")
  end
end
```

## Rails Credentials

```ruby
class SecretsConfig < ApplicationConfig
  attr_config :secret_key_base,
              :api_credentials

  # Load from Rails credentials
  def values
    Rails.application.credentials.to_h
  end
end
```

## Related

- [Configuration Topic](../topics/configuration.md)

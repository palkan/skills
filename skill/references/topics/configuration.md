# Configuration

## Summary

Configuration management extracts settings from code into structured, environment-aware objects. Anyway Config provides type-safe, validated configuration with multiple source support.

## Layer Placement

```
┌─────────────────────────────────────────┐
│ Infrastructure Layer                    │
│  └─ Configuration classes               │
│  └─ Environment variables               │
│  └─ YAML files                          │
└─────────────────────────────────────────┘
```

## Key Principles

- **Explicit over implicit** — typed config classes, not scattered ENV reads
- **Fail fast** — validate configuration at boot
- **Environment-aware** — different values per environment
- **Testable** — override config in tests

## Implementation with Anyway Config

### Basic Configuration

```ruby
# app/configs/stripe_config.rb
class StripeConfig < ApplicationConfig
  attr_config :api_key,
              :webhook_secret,
              :publishable_key,
              currency: "usd",
              connect_enabled: false

  required :api_key, :webhook_secret
end

# config/stripe.yml
default:
  currency: usd
  connect_enabled: false

development:
  api_key: sk_test_xxx
  webhook_secret: whsec_xxx
  publishable_key: pk_test_xxx

production:
  api_key: <%= ENV["STRIPE_API_KEY"] %>
  webhook_secret: <%= ENV["STRIPE_WEBHOOK_SECRET"] %>
  publishable_key: <%= ENV["STRIPE_PUBLISHABLE_KEY"] %>
  connect_enabled: true
```

### Application Config Base

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
```

### Usage

```ruby
# Direct access
StripeConfig.api_key
StripeConfig.currency

# In services
class PaymentProcessor
  def initialize(config: StripeConfig.instance)
    @config = config
  end

  def process(amount)
    Stripe::Charge.create(
      amount: amount,
      currency: config.currency,
      api_key: config.api_key
    )
  end

  private

  attr_reader :config
end
```

### Nested Configuration

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

  required :from_address
end

# Access nested values
EmailConfig.smtp.host
EmailConfig.smtp.port
```

### Feature Flags via Config

```ruby
class FeaturesConfig < ApplicationConfig
  attr_config dark_mode: false,
              ai_summaries: false,
              new_editor: false,
              beta_features: []

  def enabled?(feature)
    return beta_features.include?(feature.to_s) if respond_to?(feature)
    public_send(feature)
  end
end

# Usage
if FeaturesConfig.enabled?(:ai_summaries)
  SummarizeArticleJob.perform_later(article.id)
end
```

### Validation

```ruby
class DatabaseConfig < ApplicationConfig
  attr_config :host, :port, :database, :username, :password,
              pool_size: 5,
              timeout: 5000

  required :host, :database

  on_load do
    raise_validation_error("pool_size must be positive") if pool_size <= 0
    raise_validation_error("timeout must be positive") if timeout <= 0
  end
end
```

### Environment-Specific Behavior

```ruby
class AppConfig < ApplicationConfig
  attr_config :base_url,
              :asset_host,
              force_ssl: false,
              log_level: "info"

  on_load do
    self.force_ssl = true if Rails.env.production?
    self.log_level = "debug" if Rails.env.development?
  end
end
```

## Without Anyway Config

### Simple Config Class

```ruby
class AppSettings
  include Singleton

  def initialize
    @settings = load_settings
    validate!
  end

  def stripe_api_key
    @settings.dig(:stripe, :api_key) || ENV["STRIPE_API_KEY"]
  end

  def stripe_currency
    @settings.dig(:stripe, :currency) || "usd"
  end

  private

  def load_settings
    path = Rails.root.join("config", "settings.yml")
    return {} unless path.exist?

    YAML.load_file(path, aliases: true)[Rails.env] || {}
  end

  def validate!
    raise "STRIPE_API_KEY required" if stripe_api_key.blank?
  end
end

# Usage
AppSettings.instance.stripe_api_key
```

### Rails Credentials Integration

```ruby
class CredentialsConfig < ApplicationConfig
  # Values from config/credentials.yml.enc
  attr_config :secret_key,
              :api_credentials

  coerce_types secret_key: :string

  # Load from Rails credentials
  def values
    Rails.application.credentials.to_h
  end
end
```

## Testing Configuration

```ruby
RSpec.describe PaymentProcessor do
  let(:config) do
    StripeConfig.new(
      api_key: "test_key",
      webhook_secret: "test_secret",
      currency: "eur"
    )
  end

  let(:processor) { described_class.new(config: config) }

  it "uses configured currency" do
    expect(Stripe::Charge).to receive(:create)
      .with(hash_including(currency: "eur"))

    processor.process(1000)
  end
end

# Or use Anyway Config test helpers
RSpec.describe "with config override" do
  around do |example|
    with_env("STRIPE_CURRENCY" => "gbp") do
      example.run
    end
  end

  it "uses environment variable" do
    expect(StripeConfig.currency).to eq("gbp")
  end
end
```

## Anti-Patterns

### Scattered ENV Access

```ruby
# BAD: ENV scattered throughout codebase
class PaymentService
  def process
    Stripe.api_key = ENV["STRIPE_API_KEY"]
    Stripe::Charge.create(currency: ENV["STRIPE_CURRENCY"] || "usd")
  end
end

class WebhookHandler
  def verify(payload, signature)
    Stripe::Webhook.construct_event(
      payload, signature, ENV["STRIPE_WEBHOOK_SECRET"]
    )
  end
end

# GOOD: Centralized configuration
class PaymentService
  def process
    Stripe::Charge.create(
      currency: StripeConfig.currency,
      api_key: StripeConfig.api_key
    )
  end
end
```

### Unvalidated Configuration

```ruby
# BAD: No validation, fails at runtime
def send_email
  smtp = Net::SMTP.new(ENV["SMTP_HOST"], ENV["SMTP_PORT"].to_i)
  # Fails if ENV vars missing
end

# GOOD: Validate at boot
class SmtpConfig < ApplicationConfig
  attr_config :host, :port
  required :host, :port

  on_load do
    raise_validation_error("port must be integer") unless port.is_a?(Integer)
  end
end
```

### Mutable Configuration

```ruby
# BAD: Config modified at runtime
class AppConfig
  class << self
    attr_accessor :api_key  # Mutable!
  end
end

AppConfig.api_key = "changed"  # Dangerous!

# GOOD: Frozen configuration
class AppConfig < ApplicationConfig
  attr_config :api_key

  on_load do
    freeze
  end
end
```

## File Organization

```
app/configs/
├── application_config.rb
├── database_config.rb
├── email_config.rb
├── features_config.rb
└── stripe_config.rb

config/
├── database.yml
├── email.yml
├── features.yml
└── stripe.yml
```

## Configuration Sources (Priority)

1. Environment variables (highest)
2. Local config files (config/*.local.yml)
3. Environment-specific YAML
4. Default values in class

```ruby
# Order of precedence:
# 1. STRIPE_API_KEY env var
# 2. config/stripe.local.yml (gitignored)
# 3. config/stripe.yml[environment]
# 4. attr_config default value
```

## Related

- [Anyway Config Gem](../gems/anyway-config.md)

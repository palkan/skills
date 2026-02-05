# AI Integration

## Summary

AI features (LLM calls, embeddings, agents) should be treated as infrastructure concerns, wrapped in abstractions that keep domain logic AI-agnostic. This enables testing, provider switching, and graceful degradation.

## Layer Placement

```
┌─────────────────────────────────────────┐
│ Application Layer                       │
│  └─ AI-powered services (orchestration) │
├─────────────────────────────────────────┤
│ Domain Layer                            │
│  └─ Models (AI-agnostic)                │
├─────────────────────────────────────────┤
│ Infrastructure Layer                    │
│  └─ LLM clients, embedding services     │
└─────────────────────────────────────────┘
```

## Key Principles

- **Wrap external APIs** — don't scatter LLM calls throughout code
- **Domain-first design** — model the problem, then add AI
- **Testable without AI** — mock infrastructure, test logic
- **Graceful degradation** — handle API failures, rate limits

## Implementation with Active Agent

### Basic Agent

```ruby
# app/agents/application_agent.rb
class ApplicationAgent < ActiveAgent::Base
  # Default configuration
end

# app/agents/content_summarizer_agent.rb
class ContentSummarizerAgent < ApplicationAgent
  def summarize(text, max_length: 200)
    prompt "Summarize the following text in #{max_length} characters or less:\n\n#{text}"
  end
end

# Usage
summary = ContentSummarizerAgent.new.summarize(article.body)
```

### Agent with Tools

```ruby
class ResearchAgent < ApplicationAgent
  tool :search_web, description: "Search the web for information" do |query|
    WebSearchService.search(query)
  end

  tool :read_url, description: "Read content from a URL" do |url|
    UrlReaderService.read(url)
  end

  def research(topic)
    prompt <<~PROMPT
      Research the topic: #{topic}

      Use the available tools to gather information, then provide a comprehensive summary.
    PROMPT
  end
end
```

### Service Layer Integration

```ruby
class SummarizeArticle
  def initialize(article, agent: ContentSummarizerAgent.new)
    @article = article
    @agent = agent
  end

  def call
    return existing_summary if article.summary.present?

    summary = agent.summarize(article.body)
    article.update!(summary: summary, summarized_at: Time.current)
    summary
  rescue ActiveAgent::Error => e
    Rails.logger.error("AI summarization failed: #{e.message}")
    fallback_summary
  end

  private

  attr_reader :article, :agent

  def existing_summary
    article.summary
  end

  def fallback_summary
    article.body.truncate(200)
  end
end
```

## Without Active Agent

### Wrapped LLM Client

```ruby
# app/services/llm_client.rb
class LLMClient
  def initialize(provider: Rails.configuration.llm_provider)
    @provider = provider
    @client = build_client(provider)
  end

  def complete(prompt, **options)
    response = client.chat(
      model: options[:model] || default_model,
      messages: [{ role: "user", content: prompt }],
      **options.except(:model)
    )
    response.dig("choices", 0, "message", "content")
  rescue StandardError => e
    handle_error(e)
  end

  private

  attr_reader :provider, :client

  def build_client(provider)
    case provider
    when :openai then OpenAI::Client.new
    when :anthropic then Anthropic::Client.new
    else raise ArgumentError, "Unknown provider: #{provider}"
    end
  end

  def default_model
    case provider
    when :openai then "gpt-4"
    when :anthropic then "claude-3-sonnet"
    end
  end

  def handle_error(error)
    Rails.logger.error("LLM error: #{error.message}")
    raise LLMError, error.message
  end

  class LLMError < StandardError; end
end
```

### AI-Powered Service

```ruby
class ClassifyContent
  CATEGORIES = %w[technology business sports entertainment science].freeze

  def initialize(llm: LLMClient.new)
    @llm = llm
  end

  def call(content)
    response = llm.complete(classification_prompt(content))
    parse_category(response)
  end

  private

  attr_reader :llm

  def classification_prompt(content)
    <<~PROMPT
      Classify the following content into exactly one of these categories:
      #{CATEGORIES.join(", ")}

      Content: #{content.truncate(1000)}

      Respond with only the category name, nothing else.
    PROMPT
  end

  def parse_category(response)
    category = response.strip.downcase
    CATEGORIES.include?(category) ? category : "uncategorized"
  end
end
```

## Embeddings and Vector Search

```ruby
class EmbeddingService
  def initialize(client: OpenAI::Client.new)
    @client = client
  end

  def embed(text)
    response = client.embeddings(
      model: "text-embedding-3-small",
      input: text
    )
    response.dig("data", 0, "embedding")
  end

  def embed_batch(texts)
    response = client.embeddings(
      model: "text-embedding-3-small",
      input: texts
    )
    response["data"].map { |d| d["embedding"] }
  end
end

class SemanticSearch
  def initialize(embedding_service: EmbeddingService.new)
    @embedding_service = embedding_service
  end

  def search(query, scope: Article.all, limit: 10)
    query_embedding = embedding_service.embed(query)

    scope
      .where.not(embedding: nil)
      .order(Arel.sql("embedding <-> '#{query_embedding}'"))
      .limit(limit)
  end
end
```

## Testing AI Features

```ruby
RSpec.describe SummarizeArticle do
  let(:article) { create(:article, body: "Long article content...") }

  describe "#call" do
    it "generates and saves summary" do
      mock_agent = instance_double(ContentSummarizerAgent)
      allow(mock_agent).to receive(:summarize).and_return("Brief summary")

      service = described_class.new(article, agent: mock_agent)
      result = service.call

      expect(result).to eq("Brief summary")
      expect(article.reload.summary).to eq("Brief summary")
    end

    it "returns existing summary without API call" do
      article.update!(summary: "Existing summary")
      mock_agent = instance_double(ContentSummarizerAgent)

      service = described_class.new(article, agent: mock_agent)
      result = service.call

      expect(result).to eq("Existing summary")
      expect(mock_agent).not_to have_received(:summarize)
    end

    it "falls back on API error" do
      mock_agent = instance_double(ContentSummarizerAgent)
      allow(mock_agent).to receive(:summarize).and_raise(ActiveAgent::Error)

      service = described_class.new(article, agent: mock_agent)
      result = service.call

      expect(result).to eq(article.body.truncate(200))
    end
  end
end
```

## Anti-Patterns

### LLM Calls in Models

```ruby
# BAD: Domain layer depends on AI
class Article < ApplicationRecord
  def generate_summary
    response = OpenAI::Client.new.chat(...)
    update!(summary: response)
  end
end

# GOOD: AI in application/infrastructure layer
class SummarizeArticle
  def call(article)
    summary = agent.summarize(article.body)
    article.update!(summary: summary)
  end
end
```

### Unhandled AI Failures

```ruby
# BAD: No error handling
def classify(content)
  llm.complete("Classify: #{content}")
end

# GOOD: Handle failures gracefully
def classify(content)
  llm.complete("Classify: #{content}")
rescue LLMClient::LLMError => e
  Rails.logger.warn("Classification failed: #{e.message}")
  "uncategorized"  # Sensible default
end
```

### Prompt Strings Everywhere

```ruby
# BAD: Prompts scattered in code
def summarize(text)
  llm.complete("Summarize this: #{text}")
end

def classify(text)
  llm.complete("Classify this into categories: #{text}")
end

# GOOD: Centralized prompt management
class Prompts
  def self.summarize(text, max_length:)
    <<~PROMPT
      Summarize the following in #{max_length} characters:
      #{text}
    PROMPT
  end
end
```

## Background Processing

```ruby
class SummarizeArticleJob < ApplicationJob
  retry_on ActiveAgent::RateLimitError, wait: :polynomially_longer, attempts: 5
  discard_on ActiveAgent::InvalidRequestError

  def perform(article_id)
    article = Article.find(article_id)
    SummarizeArticle.new(article).call
  end
end

# Trigger asynchronously
class ArticlesController < ApplicationController
  def create
    @article = Article.create!(article_params)
    SummarizeArticleJob.perform_later(@article.id)
    redirect_to @article
  end
end
```

## Related

- [Active Agent Gem](../gems/active-agent.md)
- [Service Objects Pattern](../patterns/service-objects.md)

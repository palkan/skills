# Active Agent

Framework for building AI agents in Rails applications.

**GitHub**: https://github.com/activeagents/activeagent
**Layer**: Infrastructure (LLM calls) / Application (orchestration)

## Installation

```ruby
# Gemfile
gem "activeagent"
```

## Basic Usage

### Define Agent

```ruby
# app/agents/application_agent.rb
class ApplicationAgent < ActiveAgent::Base
  # Default provider configuration
end

# app/agents/summarizer_agent.rb
class SummarizerAgent < ApplicationAgent
  def summarize(text, max_length: 200)
    prompt <<~PROMPT
      Summarize the following text in #{max_length} characters or less.
      Maintain the key points and tone.

      Text:
      #{text}
    PROMPT
  end
end
```

### Use Agent

```ruby
agent = SummarizerAgent.new
summary = agent.summarize(article.body, max_length: 150)
```

## Agents with Tools

```ruby
class ResearchAgent < ApplicationAgent
  tool :search_web,
       description: "Search the web for information" do |query|
    WebSearchService.search(query).map do |result|
      { title: result.title, url: result.url, snippet: result.snippet }
    end
  end

  tool :read_url,
       description: "Read and extract content from a URL" do |url|
    UrlReaderService.read(url)
  end

  tool :save_note,
       description: "Save a research note" do |title, content|
    ResearchNote.create!(title: title, content: content)
    "Note saved: #{title}"
  end

  def research(topic)
    prompt <<~PROMPT
      Research the topic: #{topic}

      Use the search_web tool to find relevant information.
      Use read_url to get more details from promising results.
      Use save_note to record important findings.

      Provide a comprehensive summary of your research.
    PROMPT
  end
end
```

## System Prompts

```ruby
class CustomerSupportAgent < ApplicationAgent
  system_prompt <<~PROMPT
    You are a helpful customer support agent for Acme Corp.
    Be polite, professional, and helpful.
    If you don't know something, say so honestly.
    Never make up information about products or policies.
  PROMPT

  def respond(customer_message, context: {})
    prompt <<~PROMPT
      Customer: #{customer_message}

      Context:
      - Customer name: #{context[:customer_name]}
      - Account type: #{context[:account_type]}
      - Previous interactions: #{context[:interaction_count]}

      Respond helpfully to the customer's message.
    PROMPT
  end
end
```

## Structured Output

```ruby
class ClassifierAgent < ApplicationAgent
  def classify(content)
    response = prompt <<~PROMPT
      Classify the following content into one of these categories:
      - technology
      - business
      - entertainment
      - sports
      - science

      Also provide a confidence score from 0 to 1.

      Content: #{content}

      Respond in JSON format:
      {"category": "...", "confidence": 0.XX}
    PROMPT

    JSON.parse(response)
  end
end
```

## Service Integration

```ruby
class SummarizeArticle
  def initialize(agent: SummarizerAgent.new)
    @agent = agent
  end

  def call(article)
    return article.summary if article.summary.present?

    summary = agent.summarize(article.body)
    article.update!(summary: summary, summarized_at: Time.current)
    summary
  rescue ActiveAgent::Error => e
    Rails.logger.error("Summarization failed: #{e.message}")
    article.body.truncate(200)  # Fallback
  end

  private

  attr_reader :agent
end
```

## Background Processing

```ruby
class SummarizeArticleJob < ApplicationJob
  retry_on ActiveAgent::RateLimitError,
           wait: :polynomially_longer,
           attempts: 5

  discard_on ActiveAgent::InvalidRequestError

  def perform(article_id)
    article = Article.find(article_id)
    SummarizeArticle.new.call(article)
  end
end
```

## Configuration

```ruby
# config/initializers/active_agent.rb
ActiveAgent.configure do |config|
  config.default_provider = :anthropic
  config.default_model = "claude-3-sonnet"

  config.providers[:anthropic] = {
    api_key: Rails.application.credentials.anthropic_api_key
  }

  config.providers[:openai] = {
    api_key: Rails.application.credentials.openai_api_key
  }
end
```

## Testing

```ruby
RSpec.describe SummarizeArticle do
  let(:article) { create(:article, body: "Long article content...") }

  describe "#call" do
    it "generates and saves summary" do
      mock_agent = instance_double(SummarizerAgent)
      allow(mock_agent).to receive(:summarize).and_return("Brief summary")

      service = described_class.new(agent: mock_agent)
      result = service.call(article)

      expect(result).to eq("Brief summary")
      expect(article.reload.summary).to eq("Brief summary")
    end

    it "handles API errors gracefully" do
      mock_agent = instance_double(SummarizerAgent)
      allow(mock_agent).to receive(:summarize)
        .and_raise(ActiveAgent::RateLimitError)

      service = described_class.new(agent: mock_agent)
      result = service.call(article)

      expect(result).to eq(article.body.truncate(200))
    end
  end
end

RSpec.describe ResearchAgent do
  describe "#research" do
    it "uses tools to gather information" do
      agent = described_class.new

      # Mock tool responses
      allow(WebSearchService).to receive(:search)
        .and_return([{ title: "Result", url: "http://...", snippet: "..." }])

      result = agent.research("Ruby on Rails best practices")

      expect(result).to be_present
    end
  end
end
```

## Error Handling

```ruby
class AIService
  def call(prompt)
    agent.prompt(prompt)
  rescue ActiveAgent::RateLimitError
    # Retry after delay
    sleep(60)
    retry
  rescue ActiveAgent::InvalidRequestError => e
    # Log and return fallback
    Rails.logger.error("Invalid AI request: #{e.message}")
    nil
  rescue ActiveAgent::AuthenticationError
    # Critical - alert ops
    Rails.logger.fatal("AI authentication failed")
    raise
  end
end
```

## Related

- [AI Integration Topic](../topics/ai-integration.md)
- [Service Objects Pattern](../patterns/service-objects.md)

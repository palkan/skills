# /layered-rails:analyze-services

Deep audit of the Application layer (`app/services/` and service-like classes elsewhere) against Chapter 5 of *Layered Design for Ruby on Rails Applications*.

## Purpose

Answer one question: **is the service layer healthy, and if not, what should change?**

This is a focused complement to `/layered-rails:analyze`. Where the parent command surveys the whole codebase, this one zeroes in on services and the surrounding application layer, applying the book's "waiting room" heuristic and the layer-architecture rules to produce concrete, actionable recommendations.

## Usage

```
/layered-rails:analyze-services [path]
```

- Without path: analyzes the current Rails app (`./app/`).
- With path: treats the given directory as the Rails app root.

## Core Idea

> `app/services/` is a waiting room for code. Until a corresponding abstraction (train) arrives, code can sit there. But space is limited—don't overcrowd.

Two failure modes are equally bad:

1. **Bag of random objects** — a sprawling `app/services/` with no shared conventions, where each file is a unique snowflake.
2. **Anemic models** — services that strip business logic out of models, turning the domain layer into a data container.

The healthy state is **specialization**: as patterns emerge in the waiting room, they get promoted to dedicated abstractions (forms, queries, policies, presenters, deliveries, …) with their own conventions and base classes. A small `app/services/` with rich `app/{forms,queries,policies,deliveries,...}/` is the target.

This command measures how far the codebase is from that state and what should move next.

## How This Report Justifies Recommendations

Design principles alone don't move teams. **Every recommendation in the output must be backed by concrete, observable consequences** — focus on what the *current* shape costs and what the *promoted* shape gives back.

The two engines of justification are:

1. **Tests** — every change to the service layer changes the test layer. The report must describe what spec setup looks like *now*, what shared helpers/matchers/idioms become available *after* the change, and what the **specification test** (Chapter 5) reveals about each candidate. A spec that describes responsibilities outside its layer's primary concern is itself the proof a refactor is needed.
2. **Concrete current pain** — slow specs, repeated stubs, brittle assertions, layer leakages, duplicate coverage between service and model specs, unclear failure messages. These are observable; the report must point at examples in the codebase, not generic descriptions.

Recommendations stated as bare design principles ("services should be cohesive", "models should be rich") are insufficient and should be rewritten in terms of one or both of the above.

## Step 1 — Waiting-Room Gate

Compute four numbers from the codebase root:

```bash
# Count and LOC of services
service_count=$(find app/services -name "*.rb" -type f 2>/dev/null | wc -l)
service_loc=$(find app/services -name "*.rb" -type f 2>/dev/null | xargs wc -l 2>/dev/null | tail -1 | awk '{print $1}')
app_loc=$(find app -name "*.rb" -type f 2>/dev/null | xargs wc -l 2>/dev/null | tail -1 | awk '{print $1}')
service_share=$(echo "scale=3; ${service_loc:-0} / $app_loc" | bc)
```

**Skip the service-side analysis if `service_count < 10` OR `service_share < 0.10`.** Always run Steps 10 (target-architecture signals) and 11 (service-like classes in `app/models/`) regardless.

When the gate fires, the report's verdict line says so explicitly and offers no recommendations for `app/services/` — only for `app/models/`.

## Step 2 — Convention Strength

The **single most diagnostic property** of a service layer. Without conventions, the count doesn't matter — the codebase has a "bag of random objects" regardless of size.

Sample 30–60 service files (or all of them when small). For each axis, classify and compute the dominant percentage.

| Axis | What to look for | Strong (≥80%) | Mixed | Weak (<50%) |
|---|---|---|---|---|
| Base class | `class X < ApplicationService` (or `BaseService`, `ApplicationOperation`, `ApplicationCommand`) | One base used widely | Two or three competing | No shared base |
| Call interface | Method named `call`, `perform`, `run`, `process`, `execute` | One verb dominates | Mixed | No discoverable contract |
| Parameter style | Positional args, kwargs, `dry-initializer` `param`/`option`, `attr_accessor` + `initialize` | One style | Two | Free-for-all |
| Naming suffix | `*Service` suffix vs. no suffix — **the codebase must pick one** | One shape (≥90%) | One shape 70–90% | <70% (mixed) |
| Naming form | Verb-first (`CreateUser`), noun-first (`UserCreator`), or other | One form (≥70%) | Two | Random |
| Return value | Plain values, `Result`/`Success`/`Failure`, `Dry::Monads`, exceptions only | One approach (≥70%) | Two | Caller can't predict |

Search recipes:

```bash
# Base class adoption
grep -rE "class \w+ < (ApplicationService|BaseService|ApplicationOperation|ApplicationCommand)" app/services/ | wc -l

# Call interface verb distribution
grep -rE "^\s*def (call|perform|run|process|execute)\b" app/services/ | \
  sed -E 's/.*def ([a-z]+).*/\1/' | sort | uniq -c | sort -rn

# dry-initializer / param style
grep -rlE "extend Dry::Initializer|^\s*(param|option) :" app/services/ | wc -l

# Result / monad usage
grep -rlE "include Dry::Monads|Success\(|Failure\(" app/services/ | wc -l

# Naming suffix consistency
total=$(find app/services -name "*.rb" -type f | wc -l)
suffix_count=$(find app/services -name "*_service.rb" -type f | wc -l)
non_suffix=$((total - suffix_count))
echo "*Service suffix: $suffix_count / $total ; no suffix: $non_suffix"
```

### Naming suffix consistency — flag the deviating minority

The `*Service` suffix is binary: **a healthy codebase picks one rule and applies it to every file**. Either every service is named `CreateUserService` (suffix style) or every service is named `CreateUser` (folder-as-convention style). What you don't want is **both styles in the same directory** — that's an unspoken inconsistency readers have to learn case-by-case.

Apply this rule strictly:

| Suffix-style share | Verdict | Action |
|---|---|---|
| ≥95% | Strong (suffix convention) | None |
| ≤5% | Strong (no-suffix convention) | None |
| 5–95% | **Inconsistent** — flag explicitly | List the files in the **minority** style; the team must rename them to match the majority |

Always show the minority list when in the inconsistent band — that's the actionable bit. Don't summarize as "Mixed naming" without naming the offenders.

The suffix choice itself is also a maturity signal. Codebases with mature decomposition tend to *drop* the suffix (`License::CreateForm`, not `License::CreateFormService`) because folder location is the convention. If the audit finds `*Service` everywhere *and* zero promoted specializations (`app/forms/` etc. are missing), services and forms/queries/policies haven't yet differentiated — note that in the report.

### Testing impact of conventions

Convention strength is testing infrastructure in disguise. Translate each axis into observable test consequences in the report:

- **Base class.** Without a shared base class, RSpec/Minitest cannot have a single `before(:each) { stub_service(...) }` helper or a `support/services.rb` shared example. Each service spec stubs in its own way. **Verify** by spot-checking 3–5 service specs and quoting an example of repeated boilerplate that a base class would eliminate.
- **Call interface.** When everyone uses `.call`, callers can be stubbed uniformly (`allow(MyService).to receive(:call)`). When `.perform`/`.run`/`.process` are mixed, every test must remember the right verb. Cite the deviating files.
- **Naming.** Verb-first naming (`CreateUser`) makes the spec read as a sentence (`describe CreateUser do ... it "creates a user when valid" ...`); reading the spec list shows the system's *behaviors*. Suffix or noun-first naming (`UserCreator`, `CreateUserService`) requires the reader to translate into actions. More importantly, **shared examples (`it_behaves_like`) only line up cleanly when a cluster of services share a name shape** — mixed naming blocks generic test idioms across a cluster.
- **Parameter style.** A consistent style (`dry-initializer`, kwargs, etc.) lets specs reuse a single factory pattern. Mixed styles force each spec to re-learn the constructor.
- **Return value.** When return shape is uniform, assertions are uniform: `expect(result).to be_success` vs. `expect(result).not_to be_nil` vs. `expect { ... }.not_to raise_error`. Mixed shapes mean every spec has to remember which discipline this service uses.

In the report's Conventions section, **for any axis that scores below the Strong threshold, name a concrete test consequence with a file/line citation**, not just the percentage.

## Step 3 — Organization Shape

Walk `app/services/` once:

```bash
top_level=$(find app/services -maxdepth 1 -name "*.rb" -type f | wc -l)
total=$(find app/services -name "*.rb" -type f | wc -l)
ls -d app/services/*/ 2>/dev/null  # subdirectories
```

Compute:
- top-level files vs files in subdirs (ratio)
- mean and max namespace depth
- the largest sub-namespaces by file count

### Flags

| Flag | Trigger | Meaning |
|---|---|---|
| Flat sprawl | >30 top-level files OR >50% of services at the top level | Group under sub-namespaces |
| Mega-namespace | Any subdirectory holding ≥15% of all services | Likely a hidden bounded context worth promoting |
| Generic-named subdir smell | `utils/`, `helpers/`, `lib/`, `misc/`, `common/`, `shared/` with mixed contents | Bag-of-random-objects sub-symptom |

### Subdir naming nuance

Not every non-domain subdir is a smell. Distinguish:

| Pattern | Verdict | Example |
|---|---|---|
| Domain-named | Healthy at any depth | `app/services/billing/`, `app/services/onboarding/users/` |
| Specialization-named | Healthy when contents match the name | `app/services/processors/`, `app/services/queries/`, `app/services/deploy_services/` |
| Generic-named with mixed contents | Smell | `app/services/utils/` containing unrelated logic |
| **Vendor-named top-level folder** | Smell — names infrastructure, not a concept | `app/temporal/`, `app/sidekiq/`, `app/redis/` |
| Vendor-named *sub*-folder under a concept-named parent | Healthy | `app/clients/stripe/`, `app/workflows/temporal/<workflow>` |

### Vendor-named top-level folders — explicit rule

A subdirectory of `app/` (or of `app/services/`) named after an infrastructure vendor or library, rather than a concept, hides the architectural role behind a brand name. Examples to flag and how to fix:

- `app/temporal/` → rename to `app/workflows/` and introduce `ApplicationWorkflow`. Temporal.io becomes an implementation detail of the base class, not the folder name.
- `app/sidekiq/` → rename to `app/jobs/` or `app/workers/` per the codebase's existing convention.
- `app/services/aws_client/`, `app/services/redis/` → fold into `app/clients/<vendor>/` (where `app/clients/` is the role) or rename to a domain concept.

The rule: **a top-level `app/<x>/` folder names a layer or a concept, never a vendor.** Vendor-specific implementations live one level deeper, under a concept-named parent. Organization reflects what the code *is*, not what tool it talks to.

A **specialization sub-namespace under `app/services/` is a perfectly fine alternative** to a top-level `app/<specialization>/` folder — see Step 4.

## Step 4 — Specialization Clusters

The most actionable section. Tokenize each service basename and group by trailing/leading verb-noun pattern. A cluster is significant when **≥5 names share the pattern OR the pattern covers ≥10% of services**.

```bash
find app/services -name "*.rb" -type f | xargs -n1 basename -s .rb | \
  sed -E 's/^(.+_)?([a-z]+)$/\2/' | sort | uniq -c | sort -rn | head -20
```

| Trailing pattern (case-insensitive) | Wants to be (the layer/abstraction) | Example libraries (any one is fine) | Reference |
|---|---|---|---|
| `Query`, `Finder`, `Search`, `Filter`, `Lookup` | Query / Filter layer | hand-rolled POROs, `rubanok`, `ransack`-backed objects | `references/patterns/query-objects.md`, `filter-objects.md` |
| `Form`, `Builder`, `Wrapper`, `Input` | Form-object layer | `ActiveModel::Model` POROs, `dry-validation`, `reform` | `references/patterns/form-objects.md` |
| `Policy`, `Authorizer`, `Permission`, `Access` | Authorization layer | `action_policy`, `pundit`, `cancancan`, hand-rolled policies | `references/patterns/policy-objects.md` |
| `Presenter`, `Decorator`, `View`, `Renderer` | View / presentation layer | `view_component`, `phlex`, `draper`, hand-rolled presenters | `references/patterns/presenters.md` |
| `Notifier`, `Notification`, `Mailer`, `Delivery` | Notification / delivery layer | `active_delivery`, `noticed`, hand-rolled delivery POROs over ActionMailer + others | `references/topics/notifications.md` |
| `Importer`, `Exporter`, `Sync`, `Webhook`, `Handler`, `Listener` | Background-processing / event-handling layer | ActiveJob with `active_job-performs`, Sidekiq workers, `karafka` for events | `references/anti-patterns.md` (anemic jobs) |
| `Manager`, `Coordinator`, `Orchestrator` (no domain word) | Suspect god service — inspect | n/a | `/layered-rails:analyze-gods` |
| `Serializer`, `Marshaller` | API serialization layer | `alba`, `panko`, `ams`, `jbuilder` | `references/patterns/serializers.md` |

The middle column lists the **abstraction layer** the cluster wants to become. The right column lists **example libraries** — *any one* satisfies the recommendation; the team picks based on existing dependencies and preferences. A cluster's report section mentions the layer first, names 2+ library options, and uses one as a short illustrative example. It does not declare a winner.

### For each cluster, justify promotion with concrete evidence

Generic design reasoning ("extract these to query objects because that's the pattern") is **not enough**. Every cluster section must answer four concrete questions in order:

**1. Current pain — observable problems**

Sample 2–3 services in the cluster and read their source + spec. Cite specific examples of:
- Repeated stubbing or setup boilerplate across cluster specs (quote a snippet).
- Slow specs that load the controller stack or full DB fixtures where focused tests would suffice.
- Brittle assertions tied to internal implementation rather than behavior.
- Duplicate coverage between the service spec and the underlying model/component spec.
- Layer leakage in tests (`request`/`params` doubles in service specs).

**2. Specification-test verdict**

Examine the cluster's spec `describe`/`context` blocks. If those contexts describe something **outside** the cluster's true responsibility, the specification test (Chapter 5) is telling you the wrong responsibility lives in this layer. Quote 1–2 actual `describe`/`context` lines as proof:

- `*Query` service spec asserting SQL/scope shape → that is a query-object spec.
- `*Form` service spec asserting validation messages and error states → that is a form-object spec under ActiveModel semantics.
- `*Notifier`/`*Sender` service spec stubbing mailer + Slack + webhook → that is a delivery spec with channel matchers.
- `*Detector`/`*Calculator` spec asserting branch coverage on inputs → that is a value-object/method-object spec.
- `*Sync`/`*Webhook`/`*Handler` spec setting `perform_enqueued_jobs` and asserting side effects → that is a job spec.

**3. Test idioms unlocked by promotion (the concrete payoff)**

State which framework matchers/helpers/shared examples become available, and **point at one current spec each one would replace**:

| Layer | Test idioms unlocked (typical for this kind of layer) | Replaces |
|---|---|---|
| Form-object layer | ActiveModel-style matchers (`be_valid`, `have_error_on`); shared *context* for setup | Hand-rolled validation assertions; manual error-message checks |
| Query layer | Custom matcher on the shared base (e.g., `be_a_query_returning(...)`); pure relation assertions | Repeated AR fixture setup; controller-stack tests for what is really a scope |
| Authorization layer | Permit/forbid matchers (most authorization gems ship them); rule-level specs | `expect(response).to be_forbidden` integration tests; scattered authorization assertions |
| Notification / delivery layer | Has-been-delivered / enqueue matchers (most notification libraries ship them); per-channel isolated specs | Per-channel stubbing; brittle multi-channel assertions |
| Background-processing / event-handling layer | `have_enqueued_job(...)`-style matchers; job-level assertions | Service specs that assert side effects through stubbed jobs |
| View / presentation layer | Render-into-page matchers (`render_inline`, `page.has_css?`, rspec-html-matchers) | Helper specs that build HTML strings; render-string tests |
| API serialization layer | Snapshot or structural matchers; isolated payload asserts | Controller specs re-verifying payload structure |

The matchers listed are **typical for the layer** — concrete syntax depends on the chosen library. Idioms become available through that library's matchers and shared *contexts*, never through blanket shared examples across heterogeneous services. `it_behaves_like` is only justified within a single specialization where the contract is uniform (e.g., across all policy rules in the chosen authorization gem).

**4. Specification clarity after promotion**

In one sentence, state the single responsibility the new abstraction's spec describes (e.g., "the form spec describes validation rules and persistence on save; nothing else"). This is the litmus that the refactor actually moved the right code.

**5. Library-agnostic recommendation**

Each cluster section ends with a **library-neutral recommendation**: "Extract a `<layer-name>`. Libraries like `<libA>`, `<libB>`, `<libC>` are well-fit options; the team picks based on existing dependencies." Do not declare one library "the right choice" unless the codebase already commits to it.

If a sketch with a specific library would be useful as a follow-up, surface it in the report's **Next Steps** section — don't inline a "Want me to sketch this?" prompt in the cluster body. The cluster section is for the recommendation; Next Steps is for the elaboration offers.

This rule applies to **every** cluster recommendation in the report and to the Top 3 Actions. The command's job is to point at the right *layer*; the team picks the *library*.

### Placement guidance — don't push one answer

The report mentions both placement options for every cluster, and lets the user decide:

- **Nest under `app/services/<specialization>/`** (e.g., `app/services/queries/`) — minimal change, no autoload edits, scopes naming inside the existing folder.
- **Promote to a top-level folder** (e.g., `app/queries/`) — signals first-class abstraction. Right when the abstraction is **common, recognizable, framework-blessed** (`app/policies/` is the canonical example; `app/forms/`, `app/presenters/`, `app/queries/` are well-precedented).

The team gets to choose. The command does **not** push everyone toward `app/<specialization>/`.

### Wrong-abstraction caution

Chapter 5's specialization-cluster threshold (≥5 names or ≥10%) is a **prompt to inspect**, not a mandate to extract. A wrong abstraction is worse than duplication. For each detected cluster the report must apply this guardrail:

- **Tiny cluster (5–7 files) with low structural similarity** → recommend "wait — keep duplication until the shape is unmistakable". Surface the cluster, but do not push promotion. Cite which two files in the cluster look least alike to make the point concrete.
- **Cluster of any size where the candidates differ in dependency depth (e.g., some take a single AR model, others orchestrate jobs/mailers/external APIs)** → splitting may produce a smaller, real cluster plus orphans. Prefer extracting only the cohesive subset.
- **Mature cluster (≥8 files) with uniform shape** → promotion is a clear win.

The bias is against premature extraction. State this explicitly in the cluster section when the count is borderline.

## Step 5 — Naming Smells and Alternative Forms

This step asks a question the structural cluster analysis doesn't: **should this individual service exist at all?** Three mechanical checks plus two layer-bound suggestions for refactoring it away.

The checks are diagnostic prompts, not violations. Each finding pairs the smell with a concrete refactor suggestion that respects the layer rules — never just "this is bad".

### 5.1 Naming smells

#### `-er` suffix

Class names ending in `-er` (`Manager`, `Processor`, `Creator`, `Sender`, `Exchanger`, `Transferrer`, `Getter`, `Fetcher`, `Updater`, `Mover`, `Cleaner`, `Resolver`) often signal a *procedure-carrier* rather than a real abstraction — the class exists only to hold a verb.

```bash
grep -rohE "^\s*class \w+(Manager|Processor|Creator|Sender|Exchanger|Transferrer|Getter|Fetcher|Updater|Mover|Cleaner|Resolver)\b" app/services/ | head
```

Caveat: some `-er` suffixes name legitimate framework-blessed roles — `Notifier`, `Validator`, `Serializer`, `Presenter`, `Decorator`, `Renderer`, `Formatter`, `Builder` (when it builds a real object), `Controller` itself. Treat those as healthy; flag only the procedure-carrier flavors above.

Output the suspect `-er` classes as a list, then run §5.2 and §5.3 against them.

#### Tautological method/class pair

When the class name's verb-form root and the action method name say the same thing (`IpnProcessor#process_ipn`, `ReportGenerator#generate_report`, `OrderManager#manage_order`, `EmailSender#send_email`, `LinkBuilder#build_link`), the class adds nothing the method couldn't on its own.

```bash
# Heuristic: extract the verb root from the class (Processor→process, Generator→generate, ...)
# and check if the action method name is "<verb>_<noun>" or "<verb>".
grep -rEnH "^\s*class \w+(Processor|Generator|Manager|Sender|Builder|Creator|Maker|Doer|Runner|Executor|Performer)\b" app/services/ | head
# Then for each, check the def line:
#   class IpnProcessor < BaseService; ...; def process_ipn(...) ; end
# Tautology: process_ipn ⊃ "process" ⊃ Processor.
```

Implementation: for each detected suspect class `<X><Suffix>`, check if there is a `def <verb>_<x_lowercase>`, `def <verb><X>` or `def <verb>` where `<verb>` matches the suffix root. If yes, flag.

#### Ubiquitous-language test

A domain service should use terminology from the business glossary. Heuristic: extract the head noun of the class name (drop verb prefixes and trailing role-words like `Service`/`Form`/`Query`) and check whether it appears in `app/models/`, `db/schema.rb`, or `config/locales/`. If absent, the class names an invented concept.

```bash
# For class FooBarSender — head noun is "FooBar". Check models/schema.
class_name="FooBar"
file_form="$(ruby -e "puts ARGV[0].gsub(/(.)([A-Z])/, \"\\\\1_\\\\2\").downcase" "$class_name")"
[ -f "app/models/${file_form}.rb" ] && echo "model exists" || echo "no model"
grep -rE "create_table .${file_form}" db/schema.rb 2>/dev/null
```

Findings here are weak signals on their own; combine with the `-er` smell or tautology smell to identify candidates worth refactoring.

### 5.2 "Could this be a method on the domain object?" — bound by layer rules

The "find the domain object first" check, made architecturally precise. A service qualifies as a domain-method candidate **only if its body stays inside the Domain layer**:

- Takes one primary domain object (`ApplicationRecord` model) as input. Other inputs are value objects or simple scalars.
- Body uses only Domain-layer operations on that model and its associations: AR persistence, value-object math, state transitions, validations, scope queries.
- Body does **not** call mailers, jobs, services, HTTP/API clients, `Current.*`, `request`, `params`, file/storage APIs.
- The operation is a domain rule, invariant, calculation, or state transition — not orchestration.

```bash
# Candidate detection: services with exactly one `param` whose name matches an AR model.
grep -rEnH "^\s*param :([a-z_]+)\s*$" app/services/ | head
# Then check the body for cross-layer calls:
#   - mailer/job: \w+(Mailer|Job)\.|\.deliver_(now|later)|\.perform_(now|later|async|in)
#   - other services: \w+Service\.call|\w+\.call(\(|$)
#   - HTTP/API: HTTP\.|Faraday|Net::HTTP|RestClient|HTTParty
#   - Current/request: Current\.|request\.|params\[
```

**If the candidate is fully clean** → recommend moving the body to a method on the model. Concrete wording: *"Move `XxxService#call` to `Xxx#verb_form` — body is pure domain."*

**If the candidate is *almost* clean** (one infrastructure side-effect, e.g., a single `deliver_later` or `perform_later`) → recommend the **layered split**: extract the pure body as a model method, keep the side-effect in a thin orchestrating service that calls the new method then triggers the side-effect. Do not collapse cross-layer code onto the model — that turns anemic models into god models, which is just a different layer violation.

### 5.3 "Could this be a module function?" — bound by layer rules

The "if it walks like a procedure, write it as a procedure" check, made architecturally precise. A service qualifies as a module-function candidate **only if the procedure stays inside one layer**:

- Stateless: no instance variables, no inheritance from `BaseService`/`ApplicationService`, no constructor state beyond inputs that are immediately consumed.
- Single public method.
- Body operates within one layer only — Domain (math on value objects), Infrastructure (HTTP/parser without domain models), Presentation (formatting already-rendered values). No layer-crossing.

```bash
# Candidate detection: small, stateless services
find app/services -name "*.rb" -type f -exec sh -c '
  lc=$(wc -l < "$1")
  defs=$(grep -cE "^\s*def " "$1")
  has_state=$(grep -cE "@\w+|param :|option :" "$1")
  if [ "$lc" -le 30 ] && [ "$defs" -le 2 ] && [ "$has_state" -eq 0 ]; then
    echo "$lc $1"
  fi
' _ {} \; | sort -n | head
```

For each candidate, name the layer it belongs to and the resulting placement:

- **Domain-only utility** → `app/models/concerns/<name>.rb` or a domain module under `app/models/<concept>.rb`.
- **Infrastructure-only utility** → `app/lib/` or `lib/`.
- **Presentation-only utility** → `app/helpers/` or a presenter namespace.

If the body crosses layers (e.g., reads a model and enqueues a job), the service stays a class even when stateless — **the class form makes the orchestration visible at the call site, which is what Chapter 5 requires**. Don't recommend module-conversion for cross-layer code, even when the structural conditions otherwise look right.

These are **suggestions**, not violations — teams that committed to `.call` everywhere are making a defensible convention-strength tradeoff (uniform stubbing, uniform interface). The command names the candidates and lets the team choose.

## Step 6 — Implicit-Workflow Detection

When service A calls services B, C, D from inside its `call`, the workflow has no explicit owner — business logic forms invisible paths through services that share data implicitly. The service folder accumulates a "junk drawer" of orchestrators with no named workflow.

```bash
# Cross-service edges: services that call other services (heuristic)
grep -rEnH "(\b[A-Z][A-Za-z]+Service)\.call|(\b[A-Z][A-Za-z]+(::[A-Z][A-Za-z]+)*)\.call\b" app/services/ \
  | grep -vE "^[^:]+:\d+:\s*#" \
  | head -30
```

Build a rough call graph (caller file → callee class). Findings to surface:

- **Chains of length ≥3** (A → B → C). State the chain explicitly. Recommend: introduce a named orchestrator that owns the workflow — typically a form (`ApplicationForm`), an operation (`ApplicationOperation`), or a saga-like service that names what is happening (`AcceptInvitation`, not the chain `EmailSender → InvitationCreator → MembershipUpdater`).
- **Hub services** with high fan-in or fan-out (called by ≥5 services, or calling ≥5 services). High fan-in suggests a missing domain abstraction; high fan-out suggests an undeclared workflow.
- **Cycles** between services (rare but worth flagging). Always a layer-architecture problem.

Workflow-level test win: a named orchestrator's spec describes the workflow steps (one responsibility); the previously implicit chain becomes an explicit, testable narrative.

## Step 7 — Layer-Hygiene Violations

Targeted greps in `app/services/`. Report only sections with findings.

```bash
# Presentation-layer dependencies
grep -rnE "(^|[^_])request\.|params\[|session\[|cookies\[|headers\[|request_id|request_ip" app/services/ \
  | grep -vE "^\s*#"

# Controller machinery
grep -rnE "flash\[|render |redirect_to|helpers\." app/services/

# Current.* — apply the same accept/concern split as /layered-rails:analyze
grep -rn "Current\." app/services/
```

For `Current.*`, classify each usage:

- **Acceptable:** AR-style attribute defaults (`default: -> { Current.user }`), audit trails (`self.created_by = Current.user` in a callback-like helper), explicit context-restoration blocks (`Current.set(...)`), overridable kwargs (`def call(user: Current.user)`).
- **Concerning:** business-decision branching (`Current.organization.premium?`), authorization (`Current.user.admin?`), query scoping (`where(org: Current.organization)`), anywhere the call site can't override.

Reference: `references/topics/current-attributes.md`.

### Sinkhole detection

A service that just delegates to a single model method adds no value — the book calls this an "architecture sinkhole".

Heuristic: file ≤20 LOC AND the action method has ≤3 statements AND every statement targets the same single model. Surface 3–5 examples; don't list every case.

```bash
# Candidates: small files
find app/services -name "*.rb" -type f -exec sh -c '
  lc=$(wc -l < "$1")
  if [ "$lc" -le 20 ]; then echo "$lc $1"; fi
' _ {} \; | sort -n | head -20
```

## Step 8 — Test & Specification Audit

The single dedicated section that gathers the test-side picture. Many cluster-level test points are already raised in Step 4; this step characterizes **the codebase as a whole** and surfaces issues that don't fit a single cluster.

### 8.1 Test convention discovery

Look at `spec/services/` (or `test/services/`) and answer:

- **Coverage** — what fraction of services have a corresponding spec? (Many services with no spec is itself a finding.)
- **Test support helpers** — does `spec/support/` define **shared contexts** (e.g., `shared_context "with current account"`) and **custom matchers** (e.g., `expect(query).to be_a_query_returning(...)`) that match the codebase's specializations? Their presence/absence is the signal.
- **Stubbing style** — do specs uniformly use `instance_double` / `class_double` / `allow(...).to receive`? Or is there a mix?
- **Interface stubbing** — when caller specs stub services, do they all stub the same verb (e.g., `.call`)? If not, that's a downstream effect of a weak call-interface convention.
- **Result discipline** — do specs check return shape uniformly (`be_success`, `be_present`, exception-based)? Mixed shapes mean callers can't generalize.

```bash
# Coverage
spec_files=$(find spec/services -name "*_spec.rb" 2>/dev/null | wc -l)
test_files=$(find test/services -name "*_test.rb" 2>/dev/null | wc -l)
service_files=$(find app/services -name "*.rb" -type f | wc -l)
echo "service files: $service_files | specs: $spec_files | tests: $test_files"

# Shared contexts and custom matchers (NOT shared examples)
ls spec/support 2>/dev/null
grep -rE "shared_context|RSpec::Matchers\.define|Minitest::Spec::DSL" spec/support 2>/dev/null | head

# Stub-call-verb distribution
grep -rohE "\.to receive\(:\w+\)" spec/services 2>/dev/null | sort | uniq -c | sort -rn | head
```

**Important — what to recommend, what not to recommend:**

- **Shared *contexts*** (`shared_context "with current account" do let(:account) { ... } end`) are appropriate — they collect setup, used in conjunction with concrete examples.
- **Custom matchers / assertions** are appropriate for true specializations (queries, deliveries, policies) where the abstraction has a uniform contract — e.g., `be_a_query_returning(...)`, `permit(user, record)`, `have_delivered_to(...)`.
- **Focused `before` setup** that leans on a base class (e.g., `BaseService` providing `transaction`/`fail_with!`) is appropriate.
- **Shared *examples* across heterogeneous services are NOT appropriate** and the report must not recommend them. Shared examples are only justified when the abstractions truly share a contract (e.g., `it_behaves_like "an action policy rule"` across policy specs because every policy implements the same rule shape). Across mixed services they hide differences and produce coupled, brittle tests.

### 8.2 Specification-test sweep

For 5–8 representative services (mix of cluster-detected and standalone), open the spec and read the `describe`/`context` block names. Classify each context by what it actually verifies:

- **Orchestration** (correct collaborators called, transaction boundaries) — appropriate for a service.
- **Domain rule** (validations, business rules, state transitions) — should live in a model spec.
- **Presentation/HTTP** (params parsing, response codes, redirects) — should live in a controller/request spec.
- **Side-effect plumbing** (mailer/job calls counted, Slack stubbed) — usually wants a delivery or job spec.

In the report, list the services whose specs are dominated by non-orchestration concerns. Each such case is a concrete refactor target that produces an immediate test-quality win.

### 8.3 Test smells that justify refactors

The following patterns are observable test smells that the report should surface explicitly when they occur. Each smell is a *concrete* problem (not a principled one):

| Smell | How to detect | What it signals |
|---|---|---|
| Heavy controller-stack setup in service specs | `request_spec_helper` / `type: :request` / `Rack::Test` imports | Service is doing presentation work; tests are slow and brittle |
| Repeated mailer/job/Slack stubbing across cluster | Same `allow(MyMailer)…` block in 5+ specs | Cluster wants to be a delivery — promotion gives `have_delivered_to` matchers |
| `let(:request) { double(...) }` in service specs | grep | Service accepts a request — fix the layer leak first |
| Duplicate model-rule coverage | The same validation tested in `<Service>_spec` and `<Model>_spec` | Domain logic is in services AND model — usually a cue that the service is doing the model's job |
| Unparameterized stubbing of own services (`.with` missing) | `allow(SomeService).to receive(:call).and_return(true)` | Call interface non-uniform OR service does too many things to constrain inputs |
| No specs at all in the cluster | Coverage check | The cluster's responsibility is unclear enough that nobody knew what to test — a *strong* promotion signal |

For each smell encountered, name the cluster or files; do not list smells that don't apply.

### 8.4 Stating the test win for each recommendation

Every recommendation in the report (under **Top 3 Actions** and **Recommendations**) must include a one-line **Test win** indicating what specifically improves: faster specs, fewer stubs, framework matchers gained, duplicate coverage removed, layer leak closed. If no test win is identifiable, the recommendation is design-only — call that out so the user can weigh it accordingly.

## Step 9 — Anemic-Model Risk

The inverse failure mode. For each model heavily referenced from `app/services/`:

```bash
# Top models referenced from services (rough mention count)
grep -rohE "[A-Z][A-Za-z]+(::[A-Z][A-Za-z]+)*" app/services/ | sort | uniq -c | sort -rn | head -30
# (Filter to names that match files in app/models/.)
```

For each top model:

1. Open `app/models/<model>.rb`.
2. Count **substantive method definitions** — exclude:
   - DSL declarations (`belongs_to`, `has_many`, `validates`, `scope`, `enum`, `normalizes`, `delegate`, `attr_*`, `composed_of`).
   - Single-line aliases / accessors / pure delegations (`def name = first_name`).
3. **Flag as anemic** if ≥10 services touch the model AND the substantive method count is fewer than 3.

For each anemic model, surface one concrete service example whose body manipulates the model's attributes — that's the domain logic that escaped the model.

## Step 10 — Target Architecture Signals (positive markers)

Promoted specializations are healthy signals. Report them as a **strength**, not silence them.

| Folder to check | Base class | Healthy when |
|---|---|---|
| `app/forms/` | `ApplicationForm` | ≥80% inherit it |
| `app/queries/` | `ApplicationQuery` (or simple POROs) | folder exists with ≥3 files |
| `app/policies/` | `ApplicationPolicy` | base class present |
| `app/deliveries/`, `app/notifiers/` | `ApplicationDelivery`, `ApplicationNotifier` | base class(es) per channel |
| `app/presenters/`, `app/ui/`, `app/components/` | `ApplicationComponent`, `ApplicationPresenter` | base class present |
| `app/operations/` | `ApplicationOperation` | base class present |

```bash
for folder in forms queries policies deliveries notifiers presenters ui components operations; do
  count=$(find "app/$folder" -name "*.rb" 2>/dev/null | wc -l)
  if [ "$count" -gt 0 ]; then
    base=$(grep -rEh "^class Application\w+" "app/$folder" 2>/dev/null | head -1)
    echo "$folder: $count files | $base"
  fi
done
```

### Architecture tier verdict

| Tier | Condition |
|---|---|
| **Mature decomposition** | `app/services/` is small (passes the gate) AND ≥3 specialization folders exist |
| **Mixed** | Some specializations promoted, others still in services |
| **Pre-decomposition** | `app/services/` is large AND zero specialization folders |

In a "Mature decomposition" report, the recommendations should suggest at most fine-tuning — not refactoring. Celebrate the state.

## Step 11 — Service-Like Classes in `app/models/` (split: domain vs application)

The Domain layer is allowed to contain service-shaped classes — Chapter 6 of *Layered Design* names this the **domain services** sub-layer. Query objects, calculators, resolvers, and other pure domain operations that don't naturally fit on a single AR model legitimately live under `app/models/`. The rule is **what crosses layer boundaries**, not what shape the class has.

So step 11 surfaces service-like classes in `app/models/` and **classifies each as domain or application**. The two categories get different recommendations:

- **Domain service** → stays in `app/models/`. Recommend: shape the abstraction with a suffix convention (`*_query.rb`, `*_calculator.rb`, `*_resolver.rb`), a per-shape base class (`ApplicationQuery`, `ApplicationCalculator`, `ApplicationResolver`), and a clear placement (per-model namespace `app/models/<model>/<thing>_query.rb` or a flat `app/queries/`/`app/calculators/`).
- **Application service** → move to `app/services/` (or to the appropriate specialized layer if a cluster is large enough — forms, deliveries, etc.).

### Detection

```bash
# Non-AR classes in app/models with action interfaces
for f in $(find app/models -name "*.rb" -type f); do
  if ! grep -qE "< (ApplicationRecord|ActiveRecord::Base|ApplicationCachedRecord)" "$f"; then
    if grep -qE "^\s*def (call|perform|run|process|execute|import|sync|export|resolve|score|value)\b" "$f"; then
      echo "non-AR action class: $f"
    fi
  fi
done

# Service-like names in app/models
find app/models -name "*.rb" | grep -E "(_service|_command|_sync|_importer|_exporter|_processor|_handler|_notifier|_calculator|_builder|_resolver|_query|_finder)\.rb$"
```

### Classification rule (the layered test)

For each candidate, read the file and ask: **what is the purpose of this class — does it derive information from domain data, or does it orchestrate a side effect that escapes the Domain layer?** The classification is about *purpose* (what role the class plays in the architecture), not just about which method calls appear in its body.

#### Mechanical signals — direct cross-layer calls

A candidate is clearly **application-layer** if **any** of these appear directly in the body:

- Calls a mailer, job, or another service (`*Mailer\.`, `\.deliver_(now|later)`, `\.perform_(now|later|async|in)`, `\w+Service\.call`).
- Calls a third-party SDK / HTTP client (`Stripe::`, `OpenAI::`, `Slack::`, `AWS::`, `Twilio::`, `HTTP\.`, `Faraday`, `Net::HTTP`, `RestClient`, `HTTParty`).
- Reads `Current.*` for business decisions, or accepts `request`/`params`.
- Performs file/storage operations (`File.write`, `Tempfile`, `ActiveStorage::Blob`).

#### Conceptual signal — the purpose test

A candidate can also be application-layer **even when none of the mechanical signals fire** — when its purpose is to orchestrate a pipeline whose ultimate effect leaves the Domain. The most common example is a notifier:

```ruby
class Notifier::SomethingNotifier < Notifier
  def recipients = ...
  def creator = ...
end

class Notifier
  def notify
    recipients.each { Notification.create!(user: _1, source:, creator:) }
  end
end
```

The body only does `Notification.create!` — pure AR persistence — and the regex says "domain". But the `Notification` records exist *solely* to trigger emails / push / Slack delivery (somewhere downstream — typically a job consuming the new records, or an `after_commit` on `Notification` itself). The notifier's *purpose* is "send a notification when X happens", which is by definition application-level orchestration of side effects. **It is an application service, not a domain service**, regardless of where the file lives.

Apply the purpose test by asking:

1. **Does this class exist to coordinate side effects** (notifications, jobs, deliveries, integrations, state transitions that have outward-facing consequences)? → application.
2. **Does this class exist to derive information from domain data** (calculate a value, find records matching a rule, compute state from associations, transform a value object)? → domain.

Other cases that pass the regex but are conceptually application-layer:

- Classes that create AR records whose lifecycle triggers `after_commit` jobs / mailers further down — the persistence call is the trigger; the purpose is the trigger.
- Classes that update an attribute that another model's callback responds to (a state-change notifier in disguise).
- Classes that wrap a multi-step domain mutation that, taken together, defines a use case (e.g., `Account::Activate` setting `activated_at` and `welcome_sent_at` and creating an `AuditEvent` record).

Other cases that pass the regex but are conceptually domain-layer:

- Pure calculators / value-object builders that happen to use `ActiveStorage::Blob` to read attached data (the storage read is reading domain state, not orchestrating delivery).

#### Name signals — corroborating

Name signals are weak evidence on their own; combine with the mechanical or purpose test:

- `*_calculator`, `*_query`, `*_finder`, `*_resolver`, `*_score`, `*_metric` — typically domain.
- `*_notifier`, `*_sync`, `*_importer`, `*_exporter`, `*_handler`, `*_observer`, `*_creator` (when it triggers downstream effects) — typically application *even if the body looks pure* (apply the purpose test).
- `*_builder` — depends on what's being built (a value object → domain; an AR record + side effects → application).
- `*_dispatcher`, `*_router`, `*_publisher`, `*_emitter` — orchestration vocabulary, almost always application.

The takeaway: **purpose first, regex second.** A regex match without a purpose match is a false positive (e.g., `Insights::MetricsApi` named `*Api` but composing pure JSON); a purpose match without a regex match is the more dangerous case (e.g., a notifier with only `create!` in its body).

### Reporting format

Split the findings into two lists. For each list, surface counts, sample files, and a layer-shaped recommendation:

#### Domain-service candidates (stay in `app/models/`, add specialization)
For each cluster (calculators, queries, resolvers, …):
- Count and example files.
- Suggested suffix and base class (e.g., `*_calculator.rb` → `ApplicationCalculator`).
- Common machinery the base class can hoist (see "Looking for shared machinery" below).
- Placement options: per-model namespace (`app/models/<model>/`) vs dedicated top-level folder (`app/queries/`, `app/calculators/`).
- Reference: `references/patterns/query-objects.md` (Chapter 6) for the canonical shape.

#### Application-service candidates (move to `app/services/`)
- Count and example files.
- The cross-layer call(s) that disqualify them from the Domain.
- Same per-cluster grouping if patterns emerge.
- Recommendation: introduce `app/services/` with a base class — never recommend a bare file move (see "Recommend a layer with machinery, not just a folder" below).

### When the codebase intentionally has no `app/services/`

Some codebases keep all logic in `app/models/`, concerns, and jobs by design — the "Rails Way" / models-first idiom often associated with the 37signals/Basecamp tradition. The audit must recognize this as a deliberate architectural stance, not a defect, **and** call out the trade-offs honestly.

**When to recognize the stance** (signals):
- `app/services/` is absent and `app/models/` has deeply nested namespaces (`account/data_transfer/`, `signup/`, `notifier/`, …) holding non-AR action classes.
- Behavioral concerns (`Notifiable`, `Eventable`, `Searchable`) carry side-effect callbacks (e.g., `after_create_commit :notify_recipients_later`).
- ActiveJob is the substitute for explicit application services (`*Job` files do orchestration that other codebases would put in services).
- `Current` (custom `ActiveSupport::CurrentAttributes`) is used liberally for tenancy / user context.
- Style guides reference the "Rails Way" / 37signals tradition.

**Verdict for these codebases:** The architecture-tier line should say **"Mature decomposition (models-first variant)"** — same maturity as a codebase with `app/forms/`, `app/queries/`, `app/policies/`, just expressed differently. The waiting room is intentionally absent.

**But the report must list the structural risks the team has accepted.** These are observable problems that grow with codebase size; surface them whenever the stance is recognized:

1. **Layer-leak detection is harder.** When `app/services/` exists, `grep request app/services/` finds presentation-in-application leaks instantly. With no folder boundary, the same code hides in `app/models/<concept>/operation.rb` indefinitely. Recommend: an explicit lint rule (e.g., RuboCop custom cop, or a CI grep) that forbids `request`/`params`/`Current.*` for business decisions in non-AR classes under `app/models/`.

2. **Specification test gets blurrier.** Model specs end up testing orchestration behavior (jobs enqueued, callbacks fired, notifications dispatched). Find this by sampling 5–10 model specs and checking whether `describe`/`context` blocks describe domain rules vs. side-effect dispatch. When the latter dominates, the test layer is doing service-spec work disguised as model specs.

3. **Callback proliferation.** When models are the only home, side effects accumulate as `after_*_commit` callbacks. Run `/layered-rails:analyze-callbacks` for the codebase; expect more 1/5–2/5 callbacks than in service-having codebases. Watch for callback chains on the same event (`after_create_commit :notify_recipients_later, :update_search_index, :enqueue_audit_log`).

4. **Concerns become a junk drawer.** When a behavior doesn't fit on one model and isn't allowed to be a service, it goes into a concern. Today's behavioral concerns (`Notifiable`, `Eventable`, `Searchable`) may grow into multi-purpose concerns over time. Watch concern growth: a concern over 100 LOC or with mixed responsibilities is a signal.

5. **Job classes attract scope creep.** Jobs become the only home for cross-model orchestration. As the app grows, individual job files grow branching logic (`if user.admin?` … `else` …). Run `/layered-rails:analyze-gods` over `app/jobs/` periodically.

6. **Domain-method overloading (the "fat model" risk).** Without an application layer, large models accumulate methods that are arguably orchestration (`User#sign_up_and_invite_team`, `Account#provision_with_default_data`). Hard to tell domain rule from orchestration when both are instance methods.

7. **`Current` reliance.** Models-first apps lean on `Current` attributes for tenancy/user context across models and concerns. Each `Current.*` read is a hidden dependency on execution context — a layer leak. Mitigate by keeping `Current` usage to the AR-default / audit-trail uses listed in `references/topics/current-attributes.md`; avoid `Current.user.admin?` for business decisions.

8. **Observability gaps.** With no application layer, instrumenting "every business operation" requires hooks scattered across callbacks/jobs/concerns. There's no single place to add request-tracing or event-sourcing. Mitigate with consistent `ActiveSupport::Notifications` instrumentation in jobs and a small `audit/` model namespace.

9. **Onboarding cost.** Contributors trained on layered architecture (forms, queries, services, presenters) have to unlearn and rediscover where things live. Document the stance in `AGENTS.md` / `STYLE.md` so the convention is explicit.

10. **Refactoring loss-aversion.** When a real service-shaped need eventually appears (an integration with a complex external API; a multi-step workflow that doesn't fit any single model), introducing `app/services/` retroactively is awkward — the existing convention pulls reflexively for the model folder. Decide ahead of time when the pull threshold is crossed (e.g., "we'll add a service folder if a single operation needs >3 models + 1 external API + 1 mailer").

The recommendations for these codebases are usually **observations to preserve** plus **risks to monitor** — not refactors. The audit's role is to make the trade-offs visible, not to push the team off their stance.

### Recommend a layer with machinery, not just a folder

A bare file move ("create `app/services/` and move 139 files into it") is not a strong recommendation. The justification for introducing a layer must come from **shared machinery the abstraction can hoist** — that's what makes the layer earn its keep, not visibility.

Before recommending the introduction of `app/services/` (or `app/queries/`, `app/calculators/`, etc.), inspect 3–5 candidate files and identify common patterns that could factor into the base class:

| Common pattern across candidates | Goes into the base class |
|---|---|
| Repeated `ActiveRecord::Base.transaction do ... end` blocks | `transaction` delegate; or wrap `call` in a transaction option |
| Repeated `Rails.logger.info("[X] ...")` instrumentation | A logger helper, or `instrument` block via `ActiveSupport::Notifications` |
| Repeated `raise SomeError, msg` patterns | A `fail_with!(message)` helper that raises a uniform error type |
| Common parameter shapes (e.g., everyone takes a `current_user` and a record) | A typed initializer (`extend Dry::Initializer` with `option :current_user`) |
| Repeated success/failure return shape | A `Result`/monad return convention |
| Repeated `ActiveRecord::Base.lease_connection.query(...)` for raw SQL | A SQL-execution helper |
| Repeated `transaction { yield; after_commit { ... } }` for callbacks | An `after_commit` helper (à la `AfterCommitEverywhere`) |

```bash
# Survey common patterns across candidates
candidates=$(grep -rl "extend Callable\|extend Memoizable" app/models 2>/dev/null | head -10)
for f in $candidates; do
  echo "=== $f ==="
  grep -E "transaction|Rails.logger|raise |ActiveSupport::Notifications|after_commit" "$f" | head -3
done
```

The recommendation phrasing then becomes concrete, not visibility-based:

> **Introduce `ApplicationService` with a shared transaction wrapper, a `fail_with!` error helper, and `instrument` blocks.** The 139 candidates currently re-implement these in 47 different ways — a base class that hoists them removes ~120 LOC of duplicated boilerplate, makes errors uniform across the layer (single rescue point at the controller), and makes specs uniform via a single shared context. Then migrate the 139 candidates to inherit from it.

If sampling reveals **no** common machinery worth hoisting, **don't recommend a base class for its own sake**. The layer can use POROs that follow a naming convention only — but say so explicitly: "Each candidate is a unique procedure; the win is namespace/suffix consistency, not shared machinery."

## Reporting Principles

- **Conditional sections.** Do not include a section if there are no findings. No "✅ No issues found" filler.
- **Concrete evidence over generic advice.** Cite specific files, line numbers, and percentages. "Mixed parameter style (dry-initializer 64%, kwargs 28%, positional 8%)" beats "establish parameter conventions".
- **No vague recommendations.** Every recommendation must be specific enough to act on without further interpretation. "Add a CI guard" without showing the rule pattern, "introduce a base class" without surveying the machinery to hoist, "consolidate test frameworks" without naming files — drop these entirely rather than including them. A vague item dilutes the concrete ones around it. If the analysis can't get specific (data missing, scope too large, etc.), say so explicitly instead of waving at it.
- **Findings vs. recommendations are structurally separated.** Findings (observations: counts, leaks, smells, hub services, dependency facts) live under a single `## Findings` section. Recommendations (concrete next moves) live under `## Recommendations` and `## Top 3 Actions`. The two never share a paragraph. Each recommendation cross-references the finding(s) it rests on.
- **Don't push placement.** For every cluster, mention both nesting (`app/services/queries/`) and promotion (`app/queries/`); let the user decide.
- **Recommend the abstraction layer, not the library.** The report says "extract a notification layer", not "use ActiveDelivery". When a concrete library is helpful for illustration, list 2+ alternatives and mark one as the example used to make the suggestion tangible. The user picks the implementation; the command picks the layer. Sketch-with-X follow-ups go in the **Next Steps** section, not inline in the recommendation.
- **Tests are first-class evidence.** Every cluster, every recommendation, every convention finding must connect to a test consequence — current pain (slow specs, repeated stubs, layer leakage) and/or future affordance (matchers, shared contexts, focused setup). A recommendation without a test win must be flagged as design-only.
- **The specification test is the headline diagnostic.** When a spec's contexts describe responsibilities outside its layer, that's the most concrete signal a refactor is justified. Quote actual `describe`/`context` lines as proof.
- **Shared examples across heterogeneous services are out of scope.** Recommend shared *contexts* and custom matchers tied to specific specializations; never blanket `it_behaves_like "a service"`.

### What the report body must NOT contain

- **No author name-drops.** End users do not know who Swett, Avdi, Fowler, Metz, Evans, DHH, etc. are. Do not write "by Swett's rule", "the Avdi smell", "per Fowler's anemic-domain-model anti-pattern", "Sandi Metz says". State the rule directly. If the source matters, it goes in the "Read more" section at the end.
- **No bare chapter-number references.** Do not write "per Chapter 5", "Chapter 6's domain services", "the book recommends". Either state the rule directly without attribution, or include the source in "Read more".
- **No buzzwords without explanation.** "DDD ubiquitous language" → "the name comes from the business glossary". "Specification test" is a defined concept the report uses; that's fine, but explain the first time it appears.

### Optional tail: "Read more"

When the report leans on specific external sources to justify rules, include a short "Read more" section listing them. When only general principles were applied, **omit the section entirely** — don't pad with the canonical book + two blog posts as a default.

If included, format as a short list with one-line context per link:

```markdown
## Read more

- *Layered Design for Ruby on Rails Applications* — chapters 5 (Service Objects) and 6 (Query Objects / Domain Services). [Packt](https://www.packtpub.com/...)
- "Service Objects" — case against service-shaped procedures. [avdi.codes/service-objects](https://avdi.codes/service-objects/)
```

## Output Format

The report opens with **TL;DR** and **Top 3 Actions**. A reader who reads only the first half-page must walk away knowing what to do. Below them, **Findings** (observations) and **Recommendations** (concrete next moves) live in separate top-level sections — never mixed in the same paragraph. Follow-up prompts go under **Next Steps**, not inline.

```markdown
# Service Object Analysis — <project name>

## TL;DR

A single sentence stating the next move — concrete enough that the team could start work on it tomorrow. No prefix ("Monday move:", "Headline:", etc.) — just the statement. Example:

> Extract a delivery layer for `pb_slack/messages/*Formatter` — the single highest-leverage move; closes the layer leak and unlocks per-channel test isolation.

Then a one-paragraph diagnosis: tier verdict, key strengths, key gaps, the forces at play. No actions — state-of-the-world only. Example:

> The codebase has a strong `BaseService` foundation and clean `def call` discipline. The gaps are surface-level: one cluster of 4 formatter services that wants to be a delivery layer, 13 outlier files that break the no-suffix naming convention, and 2 layer-hygiene leaks reading `request`. No structural rewrite needed.

## Top 3 Actions

Numbered. Each action: one-line *what* + one-line *why* (test win + design win). Recommendations name the **layer**, not the library; library options are listed separately. Each action cross-references the Findings section it rests on.

1. **Extract a notification / delivery layer for `pb_slack/messages/*Formatter`.**
   *Why:* 8 specs lose their `Slack::Web::Client` stubs (test win); message-rendering moves out of `app/services/` and tests use channel-isolated matchers (design win). See Findings → Test & Specification, Recommendations → Specialization clusters.
   *Library options:* `active_delivery`, `noticed`, or hand-rolled delivery POROs over `ActionMailer` + Slack — pick based on existing dependencies. Sketch on request — see Next Steps.
2. **Rename the 13 outlier `*_service.rb` files in `pb_discord/` / `pb_slack/` / `sendgrid/`.**
   *Why:* removes the only naming-convention deviation; spec file names align too (test win); convention becomes strong everywhere (design win). See Findings → Conventions.
3. **Fix two layer-hygiene leaks (`token_fetcher.rb`, `license_pdf_generator.rb`).**
   *Why:* specs drop `double('request')` and `params['…']` shapes (test win); presentation parsing returns to the controller (design win). See Findings → Layer-Hygiene.

---

## Findings

Pure observations about the codebase. No recommendations live in this section — those are gathered under **Recommendations** below. Hub services, fan-in lists, and similar diagnostic data are findings only; they don't require a recommendation to be worth surfacing.

### Verdict
- Services: N files, L LOC (X% of app/)
- Architecture tier: **Mature decomposition** | Mixed | **Pre-decomposition** | Waiting room
- Promoted specializations: forms ✓ | queries ✓ | policies ✓ | deliveries ✗ | presenters ✗
- Convention strength: Strong | Mixed | Weak ("bag of random objects")
- Organization: Healthy | Sprawling | Bag of random objects
- Test convention strength: Strong | Mixed | Weak (spec coverage X%, no shared contexts/matchers, ...)
- Naming smells: K services flagged
- Implicit workflows: J chains of length ≥3
- Specialization opportunities: K clusters
- Layer-hygiene issues: M
- Anemic-model risk: P models
- Service-like models: Q files

### Waiting Room (only when under threshold)
N services (X% of app/) — the waiting-room model fits at this size. No service-layer analysis performed.

### Conventions
- Base class: `ApplicationService` — 73% of services
- Call interface: `.call` 81%, `.perform` 12%, mixed remainder
- Parameter style: `dry-initializer` 64%, kwargs 28%
- Naming suffix: 13 / 288 services (4.5%) use `*Service` suffix — **inconsistent**. Minority files:
  - `app/services/users/auth/token_fetcher_service.rb`
  - `app/services/pb_discord/init_service.rb`
  - … (full list)
- Naming form: verb-first dominant
- Return values: plain values 80%, Result objects 15%, exceptions 5%

### Organization
- 47 top-level files, 12 namespaces (max depth 3)
- `Billing/` (domain) — 38 files (15% of services); healthy concentration.
- `Utils/` (generic) — 22 files of unrelated logic; bag-of-random-objects sub-symptom.
- `Processors/` (specialization) — 9 files, all share `process` interface; healthy specialization sub-namespace.

### Layer-Hygiene

**Presentation deps**
- `app/services/foo/handle_event.rb:12` — accepts `request`

**Current usage (concerning)**
- `app/services/billing/charge.rb:8` — `Current.user.admin?` in business logic

**Sinkhole services**
- `app/services/posts/find.rb` — single `Post.find(id)` call

### Implicit Workflows

**Chains of length ≥3**
- `EmailSender → InvitationCreator → MembershipUpdater` (`app/services/users/invite_team_member.rb` → …)

**Hub services (high fan-in)**
- `OrganizationService` — called by 11 other services
- `Assets::UpdateTags.call` — called by 11 services

(Pure findings: high fan-in is data, not a TODO. Inspect for missing domain abstractions before acting.)

### Service-Like Classes in `app/models/`
Split: domain vs application (purpose test applied).

**Domain-service candidates (in `app/models/`, well-placed)**
- 23 calculators (`*_calculator.rb`) — pure domain math on AR data.
- 8 resolvers (`*_resolver.rb`) — pure lookup/strategy.

**Application-service candidates (placed in `app/models/`, but cross layer boundaries)**
- `app/models/inventory_sync.rb` — defines `.call`, body invokes `WarehouseMailer.update.deliver_later` and `ReindexJob.perform_later`. Crosses into Infrastructure.
- 5 `*_observer.rb` files in `app/models/event_stream/` — dispatch jobs and notifications.

### Test & Specification

**Coverage and conventions**
- 213 / 288 services have a corresponding spec (74%). 75 services unspec'd.
- No reusable test support: no shared *contexts* under `spec/support/`, no custom matchers, no per-cluster setup helpers.
- Stub-verb distribution: `.to receive(:call)` 412 / `.to receive(:perform)` 38 / `.to receive(:run)` 11.

**Specification-test sweep (representative services)**
- `app/services/users/auth/token_fetcher_spec.rb` — contexts include `when Authorization header is missing`, `when token is expired`. Both are presentation concerns.
- `app/services/license_pdf_generator_spec.rb` — contexts include `when params['client_email'] is missing`. Presentation parsing.
- `app/services/payments/cancel_subscription_spec.rb` — contexts describe `when subscription is active`, `when subscription is past_due`. Domain-rule contexts; belong on the model.

**Test smells**
- Heavy stubbing of own services: `allow(SomeService).to receive(:call)` without `.with(...)` constraints — 47 occurrences.
- Repeated mailer/Slack stubs in `pb_slack/`: 11 specs contain the same `allow(Slack::Web::Client)…` block.

### Anemic-Model Risk
- `Order` — 23 services touch this model, 1 substantive method. Example: `app/services/orders/calculate_total.rb` computes `items.sum(...)`.

---

## Recommendations

Concrete next moves. Each rests on findings above; cross-references included. If a recommendation can't be made specific (e.g., "add a CI guard" without showing the rule pattern), it doesn't appear here — drop it rather than wave at it.

### Specialization clusters

#### `*Query` / `*Finder` cluster (14 services) — extract a query layer
*Findings cited:* Conventions (no shared base for queries), Test & Specification (repeated `before { create_list(:user, 5) }` in 9 cluster specs).

- **Current pain:** `spec/services/users/active_query_spec.rb:12–34` re-creates 5 user fixtures and stubs `Current.organization` to test what is essentially `User.where(active: true)`. The same `before { create_list(:user, 5, ...) }` block appears in 9 of the 14 cluster specs.
- **Specification-test verdict:** specs describe `it "excludes archived" do; expect(call).to match_array([active_user]); end` — "which records are returned" is a query-object responsibility.
- **Test idioms unlocked:** pure relation assertions; a custom matcher `be_a_query_returning([...])` defined once on the shared base standardizes assertions across all 14 specs.
- **Specification clarity after:** the query spec describes the SQL/scope shape it produces — one responsibility.
- **Recommendation:** extract a query layer. Implementations: hand-rolled POROs over `ActiveRecord::Relation`, the `rubanok` gem for parameter-driven scoping, or `ransack`-backed filter objects.
- **Placement (your call):** nest under `app/services/queries/` (minimal) or promote to `app/queries/` (first-class).

#### `*Sync` / `*Webhook` cluster (8 services) — extract a background-processing / event-handling layer
*Findings cited:* Test & Specification (specs use `perform_enqueued_jobs` and stub Slack + mailer).

- **Current pain:** specs stub Slack + mailer to verify side effects — equivalent to a job spec but routed through a service stack.
- **Specification-test verdict:** contexts read `'when payload has new commits'` / `'when payload is malformed'` — those are job-handling contexts.
- **Test idioms unlocked:** `have_enqueued_job(...)` matchers; retry/backoff specs at job level.
- **Recommendation:** extract a background-processing / event-handling layer. Implementations: `ActiveJob` with `active_job-performs` for thin job wrappers, plain `Sidekiq::Worker` classes, or `karafka` for a true event bus.
- **Placement:** nest under `app/services/handlers/` or promote to `app/jobs/<concept>/`.

### Naming refactors

**`-er` suffix candidates (5)**
- `app/services/billing/charge_processor.rb`, `…/email_sender.rb`, …
- These names signal procedure-carriers. Inspect each for the next two checks.

**Tautological method/class pair (2)**
- `app/services/ipn_processor.rb` — `IpnProcessor#process_ipn`. Inline as a module function or a method on the model the IPN affects.
- `app/services/report_generator.rb` — `ReportGenerator#generate_report`. Same pattern.

**Domain-method candidates (3)**
- `app/services/orders/calculate_total.rb` — body is `order.items.sum(&:subtotal)`. **No cross-layer calls.** Move to `Order#total`.
- `app/services/users/anonymize.rb` — body updates `user` attributes only. Move to `User#anonymize!`.
- `app/services/posts/publish_with_notification.rb` — body sets `published_at` *and* calls `PostMailer`. Layered split: keep the mailer call here; move `published_at` setting to `Post#publish!`.

**Module-function candidates (4)**
- `app/services/string_humanizer.rb` — pure string transform, single layer (Domain). Move to `app/lib/strings/humanize.rb`.
- `app/services/markdown/safe_render.rb` — Presentation-only. Move to `app/helpers/markdown_helper.rb`.

These are *suggestions*; teams committed to `.call` everywhere may keep them as classes.

### Domain-service shaping (in `app/models/`)
*Findings cited:* Service-Like Classes / Domain-service candidates.

- 23 calculators (`*_calculator.rb`) — introduce `ApplicationCalculator` hoisting `memoize :value` and a logger helper. Place at `app/models/<model>/<name>_calculator.rb` or a dedicated `app/calculators/` if reused across models.
- 8 resolvers (`*_resolver.rb`) — introduce `ApplicationResolver`, or fold into `ApplicationQuery` if they all return relations.

### Application-service extraction (out of `app/models/`)
*Findings cited:* Service-Like Classes / Application-service candidates.

- Introduce `ApplicationService` with a shared transaction wrapper and `fail_with!` helper — the 11 candidates re-implement these patterns 4 different ways today. Migrate the application candidates after the base class exists.

### Other recommendations

- **Establish a single return-value convention.** Currently plain values (80%) coexist with `Result` objects (15%). Pick one. *Test win:* `expect(result).to be_success` becomes uniform across callers.
- **Restore `Order` domain methods.** 23 services touch `Order` while the model has 1 substantive method. Move `items.sum`-style logic onto `Order`. *Test win:* duplicated rule coverage between `Order_spec` and `*OrderService_spec` collapses.

---

## Next Steps

Follow-up prompts you can run when ready to dig deeper. Include only items that follow from actual findings or recommendations above — don't pad.

- **Sketch `ApplicationService`** based on the surveyed machinery (shared transaction wrapper, `fail_with!`, instrumentation hooks). Run: *"Sketch ApplicationService for the application-layer candidates."*
- **Compare query-layer libraries** for the 14 `*Query`/`*Finder` cluster — hand-rolled POROs vs `rubanok` vs `ransack`-backed objects. Run: *"Sketch the query layer with rubanok"* (or another).
- **Compare delivery-layer libraries** for the `pb_slack/messages/*Formatter` cluster. Run: *"Sketch the delivery layer with active_delivery."*
- **Drill into the `Order` anemic model.** Run `/layered-rails:analyze-gods app/models/order.rb` (yes, the anemic case is also a target — most "anemic" models hide either domain logic in services or god behavior elsewhere).
```

## Related

- [Service Objects Pattern](../skills/layered-rails/references/patterns/service-objects.md)
- [Anti-Patterns: Bag of Random Objects, Anemic Models, Premature Abstraction](../skills/layered-rails/references/anti-patterns.md)
- [Specification Test](../skills/layered-rails/references/core/specification-test.md)
- [Current Attributes](../skills/layered-rails/references/topics/current-attributes.md)
- [`/layered-rails:analyze`](./analyze.md) — full codebase architecture analysis
- [`/layered-rails:analyze-gods`](./analyze-gods.md) — god-object decomposition
- [`/layered-rails:analyze-callbacks`](./analyze-callbacks.md) — callback scoring

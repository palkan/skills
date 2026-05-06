---
lint-skip:
  - rule: reference.length
    reason: "Comprehensive multi-phase service-layer audit; the three phases (discovery, clusters, cross-cutting) are sequential and benefit from being read together. Splitting them fragments the methodology."
---

# Service-Layer Audit Workflow

Deep audit of the Application layer (`app/services/` and service-like classes elsewhere) against Chapter 5 of *Layered Design for Ruby on Rails Applications*.

## Contents

- [Purpose](#purpose)
- [Core Idea](#core-idea)
- [How This Report Justifies Recommendations](#how-this-report-justifies-recommendations)
- [Phase 1 — Discovery](#phase-1--discovery-what-does-this-codebase-have-and-what-does-it-call-a-service)
- [Phase 2 — Clusters](#phase-2--clusters-promote-up-or-demote-down)
- [Phase 3 — Cross-cutting findings](#phase-3--cross-cutting-findings-the-codebase-insights-supply)
- [Reporting Principles](#reporting-principles)
- [Read more](#read-more)
- [Output Format](#output-format)
- [Related](#related)

## Purpose

Answer one question: **is the service layer healthy, and if not, what concrete proposals would shape it?**

This is a focused complement to the architecture-analysis workflow. Where the parent workflow surveys the whole codebase and emits a **brief** service-layer summary (tier, convention strength, top 3 cluster headlines, smell counts), this workflow produces the **full** report — empirical mirror, per-cluster proposal blocks with contracts and test wins, classification rules, cross-cutting findings. Run the architecture-analysis workflow first for the wide view; run this one when the brief surfaces something worth resolving.

## Core Idea

> `app/services/` is a waiting room for code. Until a corresponding abstraction (train) arrives, code can sit there. But space is limited—don't overcrowd.

Two failure modes are equally bad:

1. **Bag of random objects** — a sprawling `app/services/` with no shared conventions, where each file is a unique snowflake.
2. **Anemic models** — services that strip business logic out of models, turning the domain layer into a data container.

The healthy state is **specialization**: as patterns emerge in the waiting room, they get promoted to dedicated abstractions (forms, queries, policies, presenters, deliveries, …) with their own conventions and base classes. A small `app/services/` with rich `app/{forms,queries,policies,deliveries,...}/` is the target.

This command measures how far the codebase is from that state — and proposes, per cluster, the **next abstraction's interface, machinery, and what writing a new instance of it will feel like**.

## How This Report Justifies Recommendations

Design principles alone don't move teams. **Every recommendation in the output must be backed by concrete, observable consequences** — focus on what the *current* shape costs and what the *promoted* (or demoted) shape gives back.

The two engines of justification are:

1. **Tests** — every change to the service layer changes the test layer. The report must describe what spec setup looks like *now*, what shared helpers/matchers/idioms become available *after* the change, and what the **specification test** reveals about each candidate. A spec that describes responsibilities outside its layer's primary concern is itself the proof a refactor is needed.
2. **Concrete current pain** — slow specs, repeated stubs, brittle assertions, layer leakages, duplicate coverage between service and model specs, unclear failure messages. These are observable; the report must point at examples in the codebase, not generic descriptions.

Recommendations stated as bare design principles ("services should be cohesive", "models should be rich") are insufficient and should be rewritten in terms of one or both of the above.

The command is organized into three phases. **Phase 1 — Discovery** answers "what exists and what does this codebase call a service". **Phase 2 — Clusters** turns each detected cluster into a concrete proposal (promote up or demote down). **Phase 3 — Cross-cutting findings** surfaces everything that doesn't belong inside a cluster.

---

## Phase 1 — Discovery: "What does this codebase have, and what does it call a service?"

### 1.1 Waiting-Room Gate

Compute four numbers from the codebase root:

```bash
# Count and LOC of services
service_count=$(find app/services -name "*.rb" -type f 2>/dev/null | wc -l)
service_loc=$(find app/services -name "*.rb" -type f 2>/dev/null | xargs wc -l 2>/dev/null | tail -1 | awk '{print $1}')
app_loc=$(find app -name "*.rb" -type f 2>/dev/null | xargs wc -l 2>/dev/null | tail -1 | awk '{print $1}')
service_share=$(echo "scale=3; ${service_loc:-0} / $app_loc" | bc)
```

**Skip the cluster analysis (Phase 2 and Phase 3.1 — Convention Strength) if `service_count < 10` OR `service_share < 0.10`.** Always run Phase 1.3 (hidden services in `app/models/`) and the Phase 3 sections that scan models regardless.

When the gate fires, the report's verdict line says so explicitly and offers no recommendations for `app/services/` — only for `app/models/`.

### 1.2 How This Codebase Defines a Service Object — the empirical mirror

**This is the foundation for every later proposal.** Sample 5–10 representative service files internally and synthesize the project's own implicit design pattern. The point is to make the team's *unspoken* convention visible at a glance — and to anchor every per-cluster contract suggestion in Phase 2.3 to what already exists.

Sample broadly: pick the most-recently-modified files, the largest files, and a few short ones. For each, note class shape, call interface, parameter style, return shape, naming, and side-effect surface — internally, as background for the synthesis.

**The output is exactly one sentence — no code, no numbers, no percentages.** It states the *inferred design pattern* in plain prose, the way you'd answer the question "what's a service in this codebase?" to a new contributor over coffee. Save the supporting metric bullets for Phase 3.1 (Convention Strength) — that's where the *deviation* report lives.

**Always give a definition — even if the only honest one is ironic.** A statement like *"not defined"* or *"no convention"* is not a definition; it's a refusal to name what's there. The mirror's job is to name the design pattern that has emerged from the team's actual choices, however weak. For a codebase with zero shared shape, the honest definition is a Service Object as a *random Ruby object placed under `app/services/`* — that's still a definition (the only convention is the folder), and naming it lands the diagnosis in a way "not yet defined" cannot.

Examples of the right register:

> **In this project, a Service Object is:** a callable class wrapping a single domain operation, with a uniform `#call` entry point and side effects expressed as explicit job or mailer calls.

> **In this project, a Service Object is:** a class that adopts the `Callable` mixin to expose a uniform `.call` entry point, with no shared base or machinery — so each service decides its own discipline beyond the entry-point shape.

> **In this project, a Service Object is:** any Ruby object placed under `app/services/` — every file is its own shape.

That last phrasing — *"any Ruby object placed under `app/services/`"* — *is* the (ironic) definition for "bag of random objects" codebases. The folder is the only convention, and naming that as the convention is more useful to the reader than any percentage table.

The mirror feeds Phase 3.1 (the *deviation* report, where the numbers live) and every Phase 2.3 cluster proposal (which builds on or breaks from the existing convention).

### 1.3 Hidden Services in `app/models/`

The Domain layer is allowed to contain service-shaped classes — Chapter 6 of *Layered Design* names this the **domain services** sub-layer. Query objects, calculators, resolvers, and other pure domain operations that don't naturally fit on a single AR model legitimately live under `app/models/`. The rule is **what crosses layer boundaries**, not what shape the class has.

Surface service-like classes in `app/models/` and **classify each as domain or application** using the purpose test (defined in Phase 2.2). The two categories feed different Phase 2 cluster directions:

- **Domain candidates** stay in `app/models/`. They flow into Phase 2 as **demote-down** clusters — the proposal shapes them with a suffix convention and a per-shape base class, kept inside the Domain layer.
- **Application candidates** are layer leaks. They flow into Phase 2 as **promote-up** clusters — the proposal moves them to `app/services/` (or the appropriate specialized layer if a cluster is large enough — forms, deliveries, importers, etc.).

#### Detection

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

The classification rule (purpose first, regex second) is defined once in Phase 2.2 and applied here.

### Decision gate after Phase 1

- If `app/services/` is small/absent (the gate fired), the empirical mirror finds no coherent convention because there is nothing to sample, **and** the `app/models/` scan finds no application-layer leaks **and** no demote-able clusters → emit a short **"Mature decomposition"** or **"Mature decomposition (models-first variant)"** report and stop. (anycable-saaqs and fizzy follow this path.)
- Otherwise → proceed to Phase 2.

#### Models-first stance recognition

Some codebases keep all logic in `app/models/`, concerns, and jobs by design. Recognize this as a deliberate architectural choice, not a defect, and call out the trade-offs honestly.

**Signals:**
- `app/services/` is absent and `app/models/` has deeply nested namespaces (`account/data_transfer/`, `signup/`, `notifier/`, …) holding non-AR action classes.
- Behavioral concerns (`Notifiable`, `Eventable`, `Searchable`) carry side-effect callbacks (e.g., `after_create_commit :notify_recipients_later`).
- ActiveJob is the substitute for explicit application services (`*Job` files do orchestration that other codebases would put in services).
- A custom `ActiveSupport::CurrentAttributes` is used liberally for tenancy / user context.

**Verdict:** the architecture-tier line says **"Mature decomposition (models-first variant)"** — same maturity as a codebase with `app/forms/`, `app/queries/`, `app/policies/`, just expressed differently. The waiting room is intentionally absent.

**Risks the team has accepted** (list when the stance is recognized; observable problems that grow with codebase size):

1. **Layer-leak detection is harder.** With no folder boundary, leaks hide in `app/models/<concept>/operation.rb` indefinitely. Recommend an explicit lint rule that forbids `request`/`params`/`Current.*` for business decisions in non-AR classes under `app/models/`.
2. **Specification test gets blurrier.** Model specs end up testing orchestration behavior. Sample 5–10 model specs and check whether `describe`/`context` blocks describe domain rules vs. side-effect dispatch.
3. **Callback proliferation.** Side effects accumulate as `after_*_commit` callbacks. Run the callback-analysis workflow.
4. **Concerns become a junk drawer.** Watch concerns crossing 100 LOC or with mixed responsibilities.
5. **Job classes attract scope creep.** Run the god-object analysis workflow over `app/jobs/` periodically.
6. **Domain-method overloading on large models** (`User#sign_up_and_invite_team`, `Account#provision_with_default_data`).
7. **`Current` reliance for cross-model context.** Each `Current.*` read is a hidden dependency on execution context.
8. **Observability gaps** — no single place to instrument every business operation.
9. **Onboarding cost** — contributors trained on layered architecture have to unlearn.
10. **Refactoring loss-aversion** — introducing `app/services/` retroactively is awkward; decide ahead of time when the threshold is crossed.

The recommendations for these codebases are usually **observations to preserve** plus **risks to monitor** — not refactors. The audit's role is to make the trade-offs visible, not to push the team off their stance.

---

## Phase 2 — Clusters: promote up *or* demote down

Goal: for every detected cluster, produce a **proposal** — the layer/abstraction it should become and what that change concretely looks like.

### 2.1 Cluster Detection

Tokenize each service basename and group by trailing/leading verb-noun pattern. A cluster is significant when **≥5 names share the pattern OR the pattern covers ≥10% of services**.

```bash
find app/services -name "*.rb" -type f | xargs -n1 basename -s .rb | \
  sed -E 's/^(.+_)?([a-z]+)$/\2/' | sort | uniq -c | sort -rn | head -20
```

**Cluster sources:**
- Suffix/prefix groupings inside `app/services/` (`*Query`, `*Form`, `*Notifier`, `*Importer`, `*Sync`, …).
- Application-layer candidates surfaced from `app/models/` in Phase 1.3.
- Cross-folder candidates (e.g., service-shaped files in `app/lib/`).

#### 2.1.1 Suffix/prefix clustering is a hypothesis, not a verdict

Naming is a *first-pass grouping signal*, not the answer. Before proposing a shared base for any cluster, **sample-read 3–5 bodies** and check shape homogeneity along the axes that matter for the proposed abstraction: constructor arity, side-effect surface, return value, channel count. If shapes diverge, report the divergence honestly — sub-cluster or split rather than force a uniform base. A cluster of "things named the same" that *do* different things is not a cluster.

#### 2.1.2 Cluster smells — name the diagnosis before naming the fix

Many name-based clusters are not really clusters of "things to consolidate" — they're symptoms of a different problem. Surface these patterns with the right diagnosis so the proposal targets the underlying cause:

**(a) Verb-prefix cluster smell.** When ≥3 cluster members share a verb prefix (`Send*`, `Create*`, `Award*`, `Notify*`, `Process*`, `Generate*`, `Build*`, `Apply*`, `Update*`, `Remove*`, `Sync*`, `Import*`, `Export*`, `Calculate*`, `Compute*`):

- The prefix names an *action*, not a *concept*. Each member is defined as "a thing that does X" rather than "a kind of Y."
- The action almost always belongs to a single service (or base class) consuming the members; the members themselves should be nouns naming the concepts they represent.
- The fix: rename members to noun-only, often combined with relocation to `app/models/<concept>/`. Do **not** recommend "move the verb to a suffix" — that preserves the confusion. Drop the verb from the per-member name entirely; the verb lives once, in the consuming service or base class.
- If the cluster contains a member named after the bare verb (e.g., a base class with the same name as the prefix), that's a strong tell the verb is the cluster's operation and the prefixed members are nouns that should stand alone.
- When this smell fires, also check directory-level naming: if ≥30 top-level files use verb-first naming, surface as a **directory-level finding** ("verb-first filenames scatter related concepts alphabetically — consider namespace grouping by concept").

**(b) Action-axis grouping.** When the cluster takes the form of parallel namespaces each containing single-action classes (`<X>::Add`, `<X>::Remove` repeated per `<X>`):

- **Regroup by bounded concept.** One multi-action service per concept exposing `#add`, `#remove`, etc. The file name says the concept; the method name says the action.
- **Surface the latent-bug risk.** Action-axis copy-paste hides bugs in the shared shape — copy-paste artifacts invisible from the class names alone.
- Do not propose flattening into action-parameterized classes — that's the dedup that misses.

**(c) Folder-level mixing of different responsibilities.** When a folder contains both delivery-shaped classes (notifiers, mailers, messengers) **and** record-management operations (`Remove*`, `Cleanup*`, `Update*`, `Purge*`), flag the **mixing** as a sub-finding. Different responsibilities, identical surface — split first; destination of the operations is a secondary choice.

**(d) Non-class files in `app/services/`.** During sampling, look at top-level non-class files: `module Foo; def self.x; end; end`-shaped files with no AR/HTTP/job calls and `Hash`-returning methods are **presenters/serializers**. Surface as a dedicated finding ("presenter/serializer living in services/") with the destination layer (`app/serializers/` or `app/decorators/`).

**(e) Thin-wrapper cluster — missing cross-cutting abstraction.** When a cluster of services all follow the pattern `<trivial domain operation> + <same cross-cutting side effect>`, the recommendation should target the **cross-cutting concern** (extract a reusable abstraction for the side effect), not the cluster shape (consolidate N services into 1). The cluster dissolves as a consequence — each service was only a wrapper because the side effect had no reusable home. Name this diagnosis as **"missing cross-cutting abstraction"** rather than "verb-prefix cluster" or "consolidation target."

The tell: each service body is ≤30 LOC, the domain operation is one AR call, and the remaining lines are identical boilerplate for the same side effect (event dispatch, audit logging, webhook delivery, protocol distribution). The services aren't N pieces of application logic — they're N copies of one infrastructure pattern that nobody named.

Distinguish from (a): verb-prefix clusters have members that should be renamed to nouns and consumed by one service. Thin-wrapper clusters have members that should *dissolve entirely* — the abstraction for the side effect absorbs their raison d'être.

**(f) CRUD clusters — distinguish form-object from action candidates.** Within a verb-prefix CRUD cluster, distinguish **form-object candidates** (`Create`, `Update` — accept params, validate, persist) from **action candidates** (`Delete`, `Add`, `Remove`, `Revoke` — accept a domain object, perform a single operation). The two groups may want different destinations:

- Form-object candidates → form objects (`app/forms/`) or `ActiveModel::Model` wrappers.
- Action candidates → inline with a cross-cutting concern wrapper, model methods, or thin orchestration services.

Do not propose the same destination for both groups unless their shapes genuinely converge.

**(g) Cross-cutting concepts that span layers.** When a class-method-only file touches both presentation (view modification, content filtering, rendering transformations) **and** domain actions (flagging, blocking, state changes), don't reflexively demote to `app/models/`. It may legitimately span layers — that's what makes it a service (or at least a waiting-room resident). The diagnosis is **"flat placement"** (needs namespacing within `app/services/`), not **"wrong layer"** (needs relocation to `app/models/`). The test: if the class would need to import from both the domain layer and the presentation layer to do its job, it sits above both — that's the application layer by definition.

| Trailing pattern (case-insensitive) | Wants to be (the layer/abstraction) | Example libraries (any one is fine) | Reference |
|---|---|---|---|
| `Query`, `Finder`, `Search`, `Filter`, `Lookup` | Query / Filter layer | hand-rolled POROs, `rubanok`, `ransack`-backed objects | `references/patterns/query-objects.md`, `filter-objects.md` |
| `Form`, `Builder`, `Wrapper`, `Input` | Form-object layer | `ActiveModel::Model` POROs, `dry-validation`, `reform` | `references/patterns/form-objects.md` |
| `Policy`, `Authorizer`, `Permission`, `Access` | Authorization layer | `action_policy`, `pundit`, `cancancan`, hand-rolled policies | `references/patterns/policy-objects.md` |
| `Presenter`, `Decorator`, `View`, `Renderer` | View / presentation layer | `view_component`, `phlex`, `draper`, hand-rolled presenters | `references/patterns/presenters.md` |
| `Notifier`, `Notification`, `Mailer`, `Delivery` | Notification / delivery layer | `active_delivery`, `noticed`, hand-rolled delivery POROs over ActionMailer + others | `references/topics/notifications.md` |
| `Importer`, `Exporter`, `Sync`, `Webhook`, `Handler`, `Listener` | Background-processing / event-handling layer | ActiveJob with `active_job-performs`, Sidekiq workers, `karafka` for events | `references/anti-patterns.md` (anemic jobs) |
| `Manager`, `Coordinator`, `Orchestrator` (no domain word) | Suspect god service — inspect | n/a | god-object analysis workflow |
| `Serializer`, `Marshaller` | API serialization layer | `alba`, `panko`, `ams`, `jbuilder` | `references/patterns/serializers.md` |
| `Calculator`, `Score`, `Metric`, `Resolver` | Domain-services sub-layer (calculators, resolvers, queries — **demote candidates**) | hand-rolled POROs in `app/models/` | `references/patterns/query-objects.md` (Chapter 6 shape) |
| `Builder` (when wrapping a value), small bundles of related attributes with no behavior of their own | Value object (**demote candidate**) | `Data.define`, `composed_of`, `store_model` | `references/patterns/value-objects.md` |
| `Profile`, `Greeter`, `*Information` (a slice of one model's behavior) | Collaborator / delegate object (**demote candidate**) | plain Ruby object with `delegate`, polymorphic AR delegate | `references/patterns/collaborator-objects.md` |

The middle column lists the **abstraction layer** the cluster wants to become. The right column lists **example libraries** — *any one* satisfies the recommendation; the team picks based on existing dependencies and preferences. A cluster's report section mentions the layer first, names 2+ library options, and uses one as a short illustrative example. It does not declare a winner.

### 2.2 Cluster Classification: promote vs. demote

Many "services" should not be services at all. Classify each detected cluster's destination using **purpose first, regex second**.

| Direction | Destination | Trigger |
|---|---|---|
| **Promote up** to a specialization layer | `app/forms/`, `app/queries/`, `app/policies/`, `app/deliveries/`, `app/notifiers/`, `app/presenters/`, `app/components/`, `app/clients/`, `app/operations/`, `app/importers/`, etc. — or `app/services/<specialization>/` nested | The cluster's purpose is application-level orchestration with a recognizable framework-blessed shape |
| **Demote down** to the Domain layer | `app/models/<concept>/<x>_calculator.rb`, `app/models/<x>_query.rb`, a flat `app/queries/`, `app/calculators/`, `app/resolvers/` | The cluster's body stays in the Domain layer (no mailers/jobs/services/SDK calls; purpose is to *derive information from domain data*) |
| **Demote down** to a value object | A frozen value class under `app/models/` (or a dedicated namespace) | The "service" wraps a small bundle of related attributes with pure transformations — a unit of meaning, not a unit of work. See `references/patterns/value-objects.md`. |
| **Demote down** to a collaborator / delegate object | A small delegate object that lives alongside its primary model (plain Ruby or a polymorphic AR row) | The "service" extracts a slice of behavior tightly coupled to one model's data (e.g., a contact-information delegate of `User`). See `references/patterns/collaborator-objects.md`. |

#### The classification rule (purpose first, regex second)

For each candidate, read the file and ask: **what is the purpose of this class — does it derive information from domain data, or does it orchestrate a side effect that escapes the Domain layer?** The classification is about *purpose*, not just about which method calls appear in its body.

**Mechanical signals — direct cross-layer calls.** A candidate is clearly **application-layer** if **any** of these appear directly in the body:

- Calls a mailer, job, or another service (`*Mailer\.`, `\.deliver_(now|later)`, `\.perform_(now|later|async|in)`, `\w+Service\.call`).
- Calls a third-party SDK / HTTP client (`Stripe::`, `OpenAI::`, `Slack::`, `AWS::`, `Twilio::`, `HTTP\.`, `Faraday`, `Net::HTTP`, `RestClient`, `HTTParty`).
- Reads `Current.*` for business decisions, or accepts `request`/`params`.
- Performs file/storage operations (`File.write`, `Tempfile`, `ActiveStorage::Blob`).

**Conceptual signal — the purpose test.** A candidate can also be application-layer **even when none of the mechanical signals fire** — when its purpose is to orchestrate a pipeline whose ultimate effect leaves the Domain. The most common example is a notifier:

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

The body only does `Notification.create!` — pure AR persistence — and the regex says "domain". But the `Notification` records exist *solely* to trigger emails / push / Slack delivery downstream (typically a job consuming the new records, or an `after_commit` on `Notification` itself). The notifier's *purpose* is "send a notification when X happens", which is by definition application-level orchestration of side effects. **It is an application service, not a domain service**, regardless of where the file lives.

Apply the purpose test by asking:

1. **Does this class exist to coordinate side effects** (notifications, jobs, deliveries, integrations, state transitions that have outward-facing consequences)? → application.
2. **Does this class exist to derive information from domain data** (calculate a value, find records matching a rule, compute state from associations, transform a value object)? → domain.
3. **Does this class wrap a small bundle of related attributes with pure transformations and no identity of its own?** → value object.
4. **Does this class extract a slice of behavior tightly coupled to one model's data, in a way that needs its own type?** → collaborator / delegate object.

Other cases that pass the regex but are conceptually application-layer:

- Classes that create AR records whose lifecycle triggers `after_commit` jobs / mailers further down — the persistence call is the trigger; the purpose is the trigger.
- Classes that update an attribute that another model's callback responds to (a state-change notifier in disguise).
- Classes that wrap a multi-step domain mutation that, taken together, defines a use case (e.g., `Account::Activate` setting `activated_at` and `welcome_sent_at` and creating an `AuditEvent` record).

Other cases that pass the regex but are conceptually domain-layer:

- Pure calculators / value-object builders that happen to use `ActiveStorage::Blob` to read attached data (the storage read is reading domain state, not orchestrating delivery).

**Name signals — corroborating only.** Combine with the mechanical or purpose test:

- `*_calculator`, `*_query`, `*_finder`, `*_resolver`, `*_score`, `*_metric` — typically domain.
- `*_notifier`, `*_sync`, `*_importer`, `*_exporter`, `*_handler`, `*_observer`, `*_creator` (when it triggers downstream effects) — typically application *even if the body looks pure*.
- `*_builder` — depends on what's being built (a value object → value-object demote; an AR record + side effects → application).
- `*_dispatcher`, `*_router`, `*_publisher`, `*_emitter` — orchestration vocabulary, almost always application.

**Purpose first, regex second.** A regex match without a purpose match is a false positive (e.g., `Insights::MetricsApi` named `*Api` but composing pure JSON); a purpose match without a regex match is the more dangerous case (e.g., a notifier with only `create!` in its body).

#### Purpose test must account for downstream consumers

When applying the purpose test to a class that creates AR records, check whether the record model has callbacks or other consumers that turn record creation into delivery. If creating the record IS the delivery trigger, AR-creating classes are notifiers regardless of how much query logic is in their bodies. The fix for "heavy query logic inside a notifier" is **query extraction** (a separate query object the notifier consumes) — **not demotion to domain**. The notifier's purpose is downstream, even when the body looks pure.

#### Ambient infrastructure calls are not cross-layer side effects

Some codebases have a pervasive infrastructure concern that appears at every layer — federation, tenant resolution, external identity lookup, distributed tracing, multi-tenancy scoping. Don't count calls to that concern as "cross-layer side effects" for classification purposes. **The test:** if removing the call would break the feature's core purpose (not just a nice-to-have), it's **ambient infrastructure**, not an optional side effect.

Name these explicitly as "ambient infrastructure" in the report rather than silently filtering — the reader should see the reasoning. Don't let ambient infrastructure disqualify a class from its natural classification (e.g., a query object that resolves external identities is still a query object).

#### Domain concepts misfiled as services

When a service-cluster member has the shape `def self.call; query records; for each, persist + follow-up`, recognize this as **domain-concept-misfiled-as-service**. The query-and-criteria part describes "what entity X is" or "who qualifies" — that's domain. The persist-loop part is the service operation. Recommendation:

1. **Promote each member to a domain object** under `app/models/<concept>/`. Plain Ruby class — no AR superclass. Typical three-method contract: a key/slug, a qualifying-entities method (returning a relation), and a per-entity helper.
2. **Inline queries inside the domain object are fine** — they're pure-domain once the file lives in `app/models/`. Don't extract into separate query objects unless reused across ≥2 consumers or complex enough to warrant their own spec.
3. **Collapse the service layer to one file** — one service with the verb, consuming any domain object.

This pattern recurs across notifications (recipient queries), badges (eligibility), scoring/ranking clusters. Name it as: "the cluster is one concept-per-class away from working — but the missing concept is *the noun*, not *an action on the noun*."

#### Eligibility/feasibility checks are system constraints, not model methods

When a service checks eligibility/feasibility rules (`Can*`, `Allowed*`, `Eligible*`, `Permitted*`) that are neither **authorization** (user-may-do-X) nor **validation** (data-is-valid), classify as **system constraint** — a distinct category from "model method candidate." Don't reflexively demote to the model.

- If cluster count <3, note as an emerging abstraction and recommend waiting.
- If ≥3, propose a constraint/rule abstraction with a dedicated suffix and placement.

#### External-vocabulary mappers are infrastructure-adjacent

When a service maps between an external system's vocabulary (third-party categories, transaction codes, admin statuses) and internal display/grouping labels, classify as an **external-vocabulary mapper**. **Don't recommend moving to `app/models/`.** Recommend: drop the runnable interface (`#run` / `#call`), keep co-located with the consuming service/engine, use a class-method or constant-hash shape. The test: if the external system changed its taxonomy, would this class need to change? If yes, it's infrastructure-adjacent.

#### Wrong-abstraction caution

Chapter 5's specialization-cluster threshold (≥5 names or ≥10%) is a **prompt to inspect**, not a mandate to extract. A wrong abstraction is worse than duplication. For each detected cluster apply this guardrail:

- **Tiny cluster (5–7 files) with low structural similarity** → recommend "wait — keep duplication until the shape is unmistakable". Surface the cluster, but do not push promotion. Cite which two files in the cluster look least alike to make the point concrete.
- **Cluster of any size where the candidates differ in dependency depth** (e.g., some take a single AR model, others orchestrate jobs/mailers/external APIs) → splitting may produce a smaller, real cluster plus orphans. Prefer extracting only the cohesive subset.
- **Mature cluster (≥8 files) with uniform shape** → promotion is a clear win.

The bias is against premature extraction. State this explicitly in the cluster section when the count is borderline. Borderline clusters get a short proposal block (steps 1–3 + step 8) and skip steps 4–7.

#### The "domain method" alternative for single-class candidates

The classification rule above applies to **clusters**. A single application-layer candidate may also pass a stricter check that turns it into a *method on the model* rather than a separate class. The rule mirrors the cluster rule but operates at the file level:

- **Take one primary domain object (`ApplicationRecord` model) as input. Other inputs are value objects or simple scalars.**
- **Body uses only Domain-layer operations** on that model and its associations: AR persistence, value-object math, state transitions, validations, scope queries.
- **Body does NOT call mailers, jobs, services, HTTP/API clients, `Current.*`, `request`, `params`, file/storage APIs.**
- **The operation is a domain rule, invariant, calculation, or state transition** — not orchestration.

If the candidate is fully clean → recommend moving the body to a method on the model. *"Move `XxxService#call` to `Xxx#verb_form` — body is pure domain."*

If the candidate is *almost* clean (one infrastructure side-effect) → recommend the **layered split**: extract the pure body as a model method, keep the side-effect in a thin orchestrating service that calls the new method then triggers the side-effect. **Do not collapse cross-layer code onto the model** — that turns anemic models into god models.

Layer-bound module-function alternative: if a candidate is stateless, single-public-method, and its body operates within one layer only, recommend the module form (`Module.do_thing`, not `class DoThing; def call`). If the body crosses layers, the service stays a class even when stateless — the class form makes orchestration visible at the call site. These are diagnostic prompts, not violations.

#### Two brakes before recommending demote-to-domain

A demote-to-domain recommendation must clear two checks before being emitted:

**(A) Destination-model god-object brake.** Before proposing to add methods to an AR model, check the destination's god-object signals: LOC, public method count, mixed concerns, callbacks, scopes. If the destination is already heavy (>500 LOC, >40 public methods, >5 mixed concerns, or already on the god-candidate list), **conditionally reject** the demote: the orchestration belongs at the Application layer. Recommend a multi-action service grouped by bounded concept instead. Phrase as: *"this is a legitimate service object — the issue is the cluster's *shape*, not its *layer*."*

When justifying why something is a legitimate Application-layer home, multiple framings are valid (DDD's "operation around a coherent concept," orchestration over multiple collaborators with side-effects, etc.) — pick whichever serves the argument; don't claim any one is canonical.

**(B) Source-complexity brake.** Check the source service's body, not just the destination. Recommend a **collaborator/delegate object** (`Model::Collaborator`) instead of a model method when any of the following is true:

- Body complexity >30 LOC with branching.
- Creates records on models other than the target.
- Calls external services or infrastructure.
- The operation introduces non-core behavior to the model.

When multiple services are always called together from the same call sites in the same order, consolidating into a single collaborator is better than N separate domain methods or N separate collaborator objects — the pipeline is the abstraction, not the individual phases.

### 2.3 The Cluster Proposal Block

For every cluster — promote-up *and* demote-down — the report emits a single block with the following ordered sub-sections. The block is the chassis on which everything else hangs.

#### 1. Cluster identity

Files (count + 2–3 sample paths), the basename pattern that grouped them, and the destination layer (promote / demote / "wait"). One short paragraph.

#### 2. Current pain — observable problems

Sample 2–3 services in the cluster and read their source + spec. Cite specific examples of:

- Repeated stubbing or setup boilerplate across cluster specs (quote a snippet).
- Slow specs that load the controller stack or full DB fixtures where focused tests would suffice.
- Brittle assertions tied to internal implementation rather than behavior.
- Duplicate coverage between the service spec and the underlying model/component spec.
- Layer leakage in tests (`request`/`params` doubles in service specs).
- Inconsistent transaction wrapping across the cluster (e.g., 4/12 wrap, 8/12 don't).

#### 3. Specification-test verdict

Examine the cluster's spec `describe`/`context` blocks. If those contexts describe something **outside** the cluster's true responsibility, the specification test is telling you the wrong responsibility lives in this layer. Quote 1–2 actual `describe`/`context` lines as proof:

- `*Query` service spec asserting SQL/scope shape → that is a query-object spec.
- `*Form` service spec asserting validation messages and error states → that is a form-object spec under ActiveModel semantics.
- `*Notifier`/`*Sender` service spec stubbing mailer + Slack + webhook → that is a delivery spec with channel matchers.
- `*Detector`/`*Calculator` spec asserting branch coverage on inputs → that is a value-object/method-object spec.
- `*Sync`/`*Webhook`/`*Handler` spec setting `perform_enqueued_jobs` and asserting side effects → that is a job spec.

#### 4. Suggested interface / contract

State the abstraction's shape **as a small Ruby code block** — written like an RBS signature would be, but in Ruby (declarations only, no implementations). The reader should be able to read it in seconds and know exactly what subclasses look like, what methods exist, what they return, and how peer code calls in.

**Format rules:**
- Show the base class with its declarative DSL (parameters, hooks) and abstract method placeholders (`def import_row(row); end`).
- Show one example subclass — concrete, drawn from the codebase if possible.
- Show the return-value type as a Ruby data declaration (`Data.define(...)`, `Struct.new(...)`, or a comment if the type is built-in).
- Show one or two **peer-use call sites** at the bottom (controller, job, rake task) so cross-boundary interaction is visible.

**Codebase-faithfulness rule.** When the codebase already commits to a non-canonical mixin / parameter library / call interface (e.g., a project-wide `extend Callable` instead of `extend Dry::Initializer`; a custom `BaseAction` DSL; a hand-rolled `Result` type), **the contract preserves it**. Do not silently substitute the textbook canonical form for what the team actually uses — the proposal must be migratable from where the codebase is today, not from where a generic Rails app would be. If a canonical alternative is worth surfacing, mention it in a one-line comment inside the code block (`# extend Callable — the project's existing mixin; equivalent to Dry::Initializer for this purpose`) or in §5 Library options, never as the headline contract.

A contract written in a foreign vocabulary asks the team to adopt a new dependency *before* applying the proposal — that's a hidden second migration the audit didn't recommend. The contract should read as "if we extracted today, this is the shape" — using the project's current building blocks.

Examples:
- Codebase uses `extend Callable` → contract uses `extend Callable` (not `Dry::Initializer`); the proposed `ApplicationService` extends `Callable` itself so subclasses inherit it.
- Codebase has an in-house `BaseAction` DSL with `param` declarations → contract uses `param`, not a parallel `Dry::Initializer` `param`.
- Codebase hand-rolls a `Result = Struct.new(...)` → contract uses `Result`, not `Dry::Monads::Result`.

The exception: when the codebase's own convention is itself the diagnosis (e.g., 6 ad-hoc base classes, no shared shape), the contract proposes the *consolidating* shape and names what's being collapsed. That's not silently substituting; that's the recommendation.

The contract is the abstraction. **Do not name `#call` reflexively** — many specializations want richer verbs:

- **Query layer** → `#relation` returning `ActiveRecord::Relation`; chainable.
- **Policy layer** → predicate methods like `#show?`, `#update?`, one per rule.
- **Form-object layer** → `#save`, `#update`, plus ActiveModel `valid?` / `errors`.
- **Delivery / notifier layer** → `#deliver_now`, `#deliver_later`, `#notify` per channel.
- **Importer layer** → `#import` returning a typed result with `count`, `errors`, `imported_records`.
- **Calculator (domain)** → `#value`, `#score`, or a domain-specific verb (`#total`, `#availability`).
- **Collaborator / delegate object** → a focused subset of the parent model's API; the parent uses `delegate :method, to: :collaborator`.

Generic `#call` is the right answer for heterogeneous orchestrators where the cluster is genuinely a "do one thing" application service.

**Example format** (illustrative — for an importer cluster):

````markdown
```ruby
# Base — defines the contract; per-importer subclasses fill in #import_row
class ApplicationImporter
  extend Dry::Initializer

  param :file
  param :tenant
  transactional default: true

  # Abstract — implemented per importer
  def import_row(row); end

  # The contract entry point
  def import
    with_tenant do
      parse(file).each { |row| safe_call(:import_row, row) }
      record_audit_event!(result)
      result
    end
  end

  def self.import(...) = new(...).import
end

# Result type — frozen, equal-by-value
ImportResult = Data.define(:imported_count, :errors, :records) do
  def success? = errors.empty?
end

# Concrete subclass
class ScholarshipImporter < ApplicationImporter
  def import_row(row)
    Scholarship.create!(name: row["name"], amount_cents: row["amount"].to_i * 100)
  end
end

# Peer use
result = ScholarshipImporter.import(file: io, tenant: org)
render json: result if result.success?
```
````

Prefer code (or pseudo-code) snippets over prose tables for the contract. Tables describe; code declares. The reader takes the code as the contract.

#### 5. Optional library hint

*Library options:* list 2+, mark one as the illustrative example. Surface the sketch-on-request offer in **Next Steps**, not inline. The team picks the implementation; the command picks the layer.

#### 6. Shared machinery the base class hoists

Survey 3–5 cluster files and identify common patterns the base class can factor out.

| Common pattern across candidates | Goes into the base class |
|---|---|
| Repeated `ActiveRecord::Base.transaction do ... end` blocks | `transaction` delegate; or wrap the entry method in a transaction option |
| Repeated `Rails.logger.info("[X] ...")` instrumentation | A logger helper, or `instrument` block via `ActiveSupport::Notifications` |
| Repeated `raise SomeError, msg` patterns | A `fail_with!(message)` helper that raises a uniform error type |
| Common parameter shapes (e.g., everyone takes a `current_user` and a record) | A typed initializer (`extend Dry::Initializer` with `option :current_user`) |
| Repeated success/failure return shape | A `Result`/monad return convention |
| Repeated `ActiveRecord::Base.lease_connection.query(...)` for raw SQL | A SQL-execution helper |
| Repeated `transaction { yield; after_commit { ... } }` for callbacks | An `after_commit` helper (à la `AfterCommitEverywhere`) |
| Repeated CSV / file-read parsing in importers | A `parse(io)` helper; per-row error capture; result collection |

```bash
# Survey common patterns across candidates
candidates=$(grep -rl "extend Callable\|extend Memoizable" app/services 2>/dev/null | head -10)
for f in $candidates; do
  echo "=== $f ==="
  grep -E "transaction|Rails.logger|raise |ActiveSupport::Notifications|after_commit" "$f" | head -3
done
```

If sampling reveals **no** common machinery worth hoisting, **don't recommend a base class for its own sake**. The layer can use POROs that follow a naming convention only — but say so explicitly: *"Each candidate is a unique procedure; the win is namespace/suffix consistency, not shared machinery."*

#### 7. Benefits showcase

The proposal payoff. Five named sub-sections; include all five for promote-up clusters with ≥6 files. Borderline (5–7 files, low similarity) and demote-down clusters include a-c-e and skip d ("Adding a new feature" walkthrough).

**a. Deduplication.** Concrete LOC count saved by the base class hoisting common machinery; reference 2–3 files where the duplicated pattern currently lives. Example: *"the proposed `transactional` declaration removes 9 explicit `ApplicationRecord.transaction do … end` blocks across the cluster — about 18 LOC."*

**b. Common issues solved.** Name 1–2 problems the abstraction prevents — e.g., *"transactional wrapping is currently inconsistent across the cluster (4/12 files wrap, 8/12 don't); the base class makes this uniform"* or *"error types vary by file (3 distinct `*Error` classes); the base's `fail_with!` standardizes the type at the controller boundary."*

**c. Test simplification.** The framework matchers / shared *contexts* / custom-assertion vocabulary unlocked by promotion, with a citation to one current spec each idiom would replace. State the specification-test clarity after promotion as a single-responsibility sentence.

| Layer | Test idioms unlocked (typical for this kind of layer) | Replaces |
|---|---|---|
| Form-object layer | ActiveModel-style matchers (`be_valid`, `have_error_on`); shared *context* for setup | Hand-rolled validation assertions; manual error-message checks |
| Query layer | Custom matcher on the shared base (e.g., `be_a_query_returning(...)`); pure relation assertions | Repeated AR fixture setup; controller-stack tests for what is really a scope |
| Authorization layer | Permit/forbid matchers (most authorization gems ship them); rule-level specs | `expect(response).to be_forbidden` integration tests; scattered authorization assertions |
| Notification / delivery layer | Has-been-delivered / enqueue matchers (most notification libraries ship them); per-channel isolated specs | Per-channel stubbing; brittle multi-channel assertions |
| Background-processing / event-handling layer | `have_enqueued_job(...)`-style matchers; job-level assertions | Service specs that assert side effects through stubbed jobs |
| Importer layer | `import_records(...)` matcher on the shared base; tenant + audit-trail shared *context* | Per-file tenant setup; per-file audit-event factories |
| View / presentation layer | Render-into-page matchers (`render_inline`, `page.has_css?`, rspec-html-matchers) | Helper specs that build HTML strings; render-string tests |
| API serialization layer | Snapshot or structural matchers; isolated payload asserts | Controller specs re-verifying payload structure |
| Calculator / resolver (domain) | Value-shaped assertions on the calculator's `#value`; pure inputs | Service-shaped specs that thread through calculation contexts |

The matchers listed are **typical for the layer** — concrete syntax depends on the chosen library. Idioms become available through that library's matchers and shared *contexts*, never through blanket shared examples across heterogeneous services. `it_behaves_like` is only justified within a single specialization where the contract is uniform (e.g., across all policy rules in the chosen authorization gem).

**d. "Adding a new feature" walkthrough** *(promote-up clusters with ≥6 files only — borderline and demote-down clusters skip this sub-section)*

Show what creating the next instance of this abstraction looks like — before/after — to demonstrate the pull, not just the diagnosis. Tie it to a concrete hypothetical drawn from the codebase (e.g., "imagine adding a `RecentSignupsQuery` to the cluster" or "imagine adding the next CSV importer for a third-party export").

```markdown
**Today** — adding the next `*Query` to the cluster:

```ruby
class RecentSignupsQuery
  def self.call(scope = User.all, since: 7.days.ago)
    scope.where("created_at > ?", since).order(created_at: :desc)
  end
end
```

```ruby
RSpec.describe RecentSignupsQuery do
  it "returns recent signups" do
    create_list(:user, 3, created_at: 8.days.ago)
    fresh = create(:user, created_at: 1.day.ago)
    expect(described_class.call).to eq([fresh])
  end
end
```

35 LOC for the file + spec; the author re-derived parameter passing, scope chaining,
and result assertion patterns from a sibling file.

**After promotion** — same cluster, with `ApplicationQuery`:

```ruby
class RecentSignupsQuery < ApplicationQuery
  param :since, default: -> { 7.days.ago }

  def relation
    base.where("created_at > ?", since).order(created_at: :desc)
  end
end
```

```ruby
RSpec.describe RecentSignupsQuery do
  it { is_expected.to be_a_query_returning(User.where("created_at > ?", since)) }
end
```

~6 LOC of declared contract; the matcher comes from `ApplicationQuery`'s shared base;
the parameter shape is uniform with the rest of the cluster.
```

The walkthrough is what makes the proposal land. Keep each side under ~10 lines of code; tie to the codebase's actual data; show one test (not a suite). Skip the walkthrough when the cluster is too small to accumulate new instances meaningfully.

**e. Cross-boundary conventions unlocked.** Name resolution (e.g., authorization-by-name from the controller); uniform error type at the controller boundary; uniform stub vocabulary in caller specs; matcher gem availability. Example: *"controllers can rescue from a single `ApplicationService::Failure` instead of N per-service error classes; one shared `rescue_from` clause in `ApplicationController`."*

#### 8. Placement options

For every cluster, mention **both** placement options. The team decides; the command does not push.

- **Nest under `app/services/<specialization>/`** (e.g., `app/services/queries/`) — minimal change, no autoload edits, scopes naming inside the existing folder.
- **Promote to a top-level folder** (e.g., `app/queries/`) — signals first-class abstraction. Right when the abstraction is **common, recognizable, framework-blessed** (`app/policies/` is the canonical example; `app/forms/`, `app/presenters/`, `app/queries/` are well-precedented).

For demote-down destinations:
- **Per-model namespace** (`app/models/<model>/<thing>_calculator.rb`) — minimal change, scoped to the parent.
- **Dedicated top-level folder** (`app/calculators/`, `app/queries/`) — signals first-class abstraction at the Domain level.
- **Inside the parent model** (for value objects and collaborators) — the parent owns the type via `composed_of`, `delegate`, or a nested constant.

**Audience as sub-namespace, not peer namespace.** When unifying two clusters that differ only by audience (e.g., user-facing vs. staff-facing), recommend the audience as a **sub-namespace** under one parent, not as a peer folder. The unmarked default is the larger audience; the marked sub-namespace is the smaller. Phrase as "one abstraction, audience encoded in the path."

**Value-object placement: cohesion over relocation.** When proposing placement for a value object, count consumers:

- **0 or 1 consumer → cohesion** (keep next to the consumer, with a conventional filename like `payload.rb` / `input.rb` / `result.rb`).
- **≥2 consumers → hoist** to `app/models/<concept>/` or `app/values/`.

The team gets to choose. The command does **not** push everyone toward `app/<specialization>/`.

### 2.4 Special-case proposal rules

Cluster-level rules that override the default proposal shape when their preconditions fire.

#### Operation-contract vs. event-broadcast side-effects

When proposing notifier extraction for multi-channel side-effects, ask: **could a downstream consumer reasonably opt out of this side-effect?**

- **Yes** → event-broadcast — extract as a notifier.
- **No** → the side-effect is required for the operation to fulfill its contract — it stays inline in the service.

Don't extract a notifier just because a side-effect is multi-channel; extract only when consumers can decline.

#### API-client wrappers — no cross-vendor abstraction without polymorphic usage

Before proposing a cross-vendor abstraction for API-wrapping services, inspect the calling side: do callers use the vendors interchangeably or polymorphically? If each vendor's operations are called from different layers with vendor-specific parameters and different return shapes, they share a *folder* but not an *interface*. Limit recommendations to per-vendor internal cleanup.

Reserve `app/clients/` for services that are **pure HTTP/SDK wrappers** with no business-logic coupling. When API calls are tightly coupled with the calling context, the API interaction is an implementation detail, not a separable layer.

#### Minimal base class for small heterogeneous clusters

When a cluster of 3–5 services shares one cross-cutting concern (tracing, logging, error handling) but diverges structurally in the core logic, recommend a **minimal base class** that hoists only the shared concern — not a full abstraction with abstract methods and a uniform contract. Name this as "minimal base" to distinguish from "full promotion."

Full promotion is justified when the convention-strength uniformity test passes (shared instance state, symmetric coverage, homogeneous implementations — see Phase 3.1). When it doesn't, a minimal base preserves pragmatism without foreclosing future promotion.

#### God-object triage — size vs. coupling vs. placement

Not every large file is a decomposition target. When a god-service candidate is detected, triage along three axes before proposing action:

- **Shape uniformity.** If every method has the same shape (build params → create record, or dispatch → notify), the size is repetition, not complexity. Repetition-driven god objects are **acceptable** — keeping all instances in one place has grepability and audit-surface value.
- **Coupling surface.** Count call sites and classify as imperative (direct `.new(user).verb(...)` calls scattered across layers) vs. event-driven (subscribers, callbacks). Imperative coupling is the real cost — you can't drop or disable the feature without touching N files. Report the number and distribution.
- **Placement.** A god object that is a peripheral concern (auditing, activity logging) should not mix with business-logic services in the flat `app/services/` listing. Recommend namespace relocation, not decomposition.

The recommendation matrix:

| Shape | Coupling | Action |
|---|---|---|
| Uniform (repetition) | Any | Acceptable god object — flag placement and coupling, not size |
| Mixed (multiple responsibilities) | Low fan-in | Split for readability — extract into modules/classes under a namespace |
| Mixed | High fan-in | Split for readability + audit public API surface (actual entry points vs. nominal public methods) |

**Dispatch god objects** (all-in-one notifications, events, webhooks, alerts) get a specific recommendation shape:

1. **Readability decomposition** — extract conceptually cohesive parts (eligibility resolution, dispatch, channel routing) into modules/classes under a namespace.
2. **Public API audit** — check where `private` starts vs. how many methods are actual entry points (called from outside the class). A class with 20 public methods but only 3–4 real entry points has a misleading API surface — flag this explicitly.
3. **Not a rewrite** — don't propose migrating to a different abstraction or notification framework. The decomposition is structural (namespace + modules), not architectural.

---

## Phase 3 — Cross-cutting findings (the "Codebase Insights" supply)

Goal: surface everything that doesn't belong inside a cluster proposal. The output of this phase becomes the report's `## Codebase Insights` section. Each Phase 3 sub-section *also* feeds evidence *into* Phase 2's cluster blocks (a layer-hygiene leak in a `*Sync` file becomes part of that cluster's "current pain"; a naming-smell candidate becomes part of the corresponding cluster's "demote down" classification).

### 3.1 Convention Strength — the deviation report

The empirical mirror in Phase 1.2 is the *positive* statement of the project's convention. This section is the *deviation* report — where the convention breaks down.

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

#### Naming suffix consistency — flag the deviating minority

The `*Service` suffix is binary: **a healthy codebase picks one rule and applies it to every file**. Either every service is named `CreateUserService` (suffix style) or every service is named `CreateUser` (folder-as-convention style). What you don't want is **both styles in the same directory** — that's an unspoken inconsistency readers have to learn case-by-case.

Apply this rule strictly:

| Suffix-style share | Verdict | Action |
|---|---|---|
| ≥95% | Strong (suffix convention) | None |
| ≤5% | Strong (no-suffix convention) | None |
| 5–95% | **Inconsistent** — flag explicitly | List the files in the **minority** style; the team must rename them to match the majority |

Always show the minority list when in the inconsistent band — that's the actionable bit. Don't summarize as "Mixed naming" without naming the offenders.

The suffix choice itself is also a maturity signal. Codebases with mature decomposition tend to *drop* the suffix (`License::CreateForm`, not `License::CreateFormService`) because folder location is the convention. If the audit finds `*Service` everywhere *and* zero promoted specializations (`app/forms/` etc. are missing), services and forms/queries/policies haven't yet differentiated — note that in the report.

#### Testing impact of conventions

Convention strength is testing infrastructure in disguise. Translate each axis into observable test consequences in the report:

- **Base class.** Without a shared base class, RSpec/Minitest cannot have a single `before(:each) { stub_service(...) }` helper or a `support/services.rb` shared example. Each service spec stubs in its own way. **Verify** by spot-checking 3–5 service specs and quoting an example of repeated boilerplate that a base class would eliminate.
- **Call interface.** When everyone uses `.call`, callers can be stubbed uniformly (`allow(MyService).to receive(:call)`). When `.perform`/`.run`/`.process` are mixed, every test must remember the right verb. Cite the deviating files.
- **Naming.** Verb-first naming (`CreateUser`) makes the spec read as a sentence. Suffix or noun-first naming (`UserCreator`, `CreateUserService`) requires the reader to translate into actions.
- **Parameter style.** A consistent style (`dry-initializer`, kwargs, etc.) lets specs reuse a single factory pattern.
- **Return value.** When return shape is uniform, assertions are uniform.

In the report's Conventions section, **for any axis that scores below the Strong threshold, name a concrete test consequence with a file/line citation**, not just the percentage.

#### Healthy uniformity vs. false uniformity

When analyzing the call-interface axis, distinguish:

- **Healthy uniformity** — a single verb across truly homogeneous services where callers treat them polymorphically.
- **False uniformity** — a single verb across heterogeneous services where sub-namespaces or folder names carry more meaning than the method name.

When false uniformity is detected, **don't automatically recommend consolidation into multi-action objects**. First verify all three:

1. Do the operations share instance state?
2. Is coverage symmetric?
3. Are implementations homogeneous enough to benefit from a shared base?

If all three are "no," it's a naming/interface problem, not structural — recommend per-cluster entry-point naming (below) rather than collapsing to a single class.

#### Per-cluster entry-point naming, not universal `.call`

Each cluster's contract proposal should include an entry-point name suited to its purpose, even when departing from the project's empirical default. The convention-strength score is one input; the cluster's purpose is another.

| Cluster purpose | Suggested entry point |
|---|---|
| Notifier / delivery | `.deliver` / `.deliver_later` |
| Form | `.submit` / `.save` |
| Query | `.resolve` / direct relation methods |
| Policy | predicate methods (`#allowed?`) |
| Operation | `.call` / `.run` / `.perform` |

Recommending `.deliver` for the notifier cluster does not contradict a "Strong on `.call`" finding for the rest of services — it's the cluster asserting its specialization.

### 3.2 Organization Shape

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

#### Flags

| Flag | Trigger | Meaning |
|---|---|---|
| Flat sprawl | >30 top-level files OR >50% of services at the top level | Group under sub-namespaces |
| Mega-namespace | Any subdirectory holding ≥15% of all services | Likely a hidden bounded context worth promoting |
| Generic-named subdir smell | `utils/`, `helpers/`, `lib/`, `misc/`, `common/`, `shared/` with mixed contents | Bag-of-random-objects sub-symptom |

#### Subdir naming nuance

| Pattern | Verdict | Example |
|---|---|---|
| Domain-named | Healthy at any depth | `app/services/billing/`, `app/services/onboarding/users/` |
| Specialization-named | Healthy when contents match the name | `app/services/processors/`, `app/services/queries/`, `app/services/deploy_services/` |
| Generic-named with mixed contents | Smell | `app/services/utils/` containing unrelated logic |
| **Vendor-named top-level folder** | Smell — names infrastructure, not a concept | `app/temporal/`, `app/sidekiq/`, `app/redis/` |
| Vendor-named *sub*-folder under a concept-named parent | Healthy | `app/clients/stripe/`, `app/workflows/temporal/<workflow>` |
| **Pattern-named with ambiguous fit** | Surface, do not rename | `app/facades/` whose contents could equally be presenters / page objects / aggregators; `app/managers/`, `app/handlers/` when the name covers multiple plausible roles |

#### Vendor-named top-level folders — explicit rule

A subdirectory of `app/` (or of `app/services/`) named after an infrastructure vendor or library, rather than a concept, hides the architectural role behind a brand name. Examples to flag and how to fix:

- `app/temporal/` → rename to `app/workflows/` and introduce `ApplicationWorkflow`. Temporal.io becomes an implementation detail of the base class, not the folder name.
- `app/sidekiq/` → rename to `app/jobs/` or `app/workers/` per the codebase's existing convention.
- `app/services/aws_client/`, `app/services/redis/` → fold into `app/clients/<vendor>/` (where `app/clients/` is the role) or rename to a domain concept.

**The rule: a top-level `app/<x>/` folder names a layer or a concept, never a vendor.** Vendor-specific implementations live one level deeper, under a concept-named parent. Organization reflects what the code *is*, not what tool it talks to.

A **specialization sub-namespace under `app/services/` is a perfectly fine alternative** to a top-level `app/<specialization>/` folder.

#### Mis-classified abstractions — diagnose the missing contract, do not pick the new name

When a folder or cluster looks "wrong" because its name does not match its contents, the temptation is to recommend a rename to the pattern that fits best. Resist when the evidence supports more than one plausible classification — a confident rename pretends a debate that the codebase has not had.

**The test before recommending a rename:**

1. **Is the new name unambiguously the right pattern?** *(single canonical name, no plausible alternatives that fit the same evidence)*
2. **Does the rename bring concrete affordances** that "name the role + introduce a base class" would not? Examples of real affordances: a framework convention triggers behavior (`app/policies/` activates ActionPolicy resolution; `app/components/` triggers ViewComponent autoload), a library binds to the new shape, a base class already exists under the new name.

If both answers are yes → recommend the rename. If either is no → the actionable diagnosis is **the missing contract**, which is true regardless of which name wins. Recommend introducing a base class and a documented role, surface the candidate names as options, and let the team pick the vocabulary.

Examples this rule applies to:

- **`app/facades/` whose contents return view-shaped data with `to_partial_path` markers** could equally be called presenters, page objects, view models, or facades-that-aggregate. The actionable diagnosis is "no `ApplicationFacade` base, no shared interface across the 5 subdirs" — that holds whether the team renames the folder or not.
- **A cluster of `*Resolver` / `*Finder` / `*Loader` / `*Lookup` files that all return `ActiveRecord::Relation`** could become `app/queries/` or stay as `*_resolver.rb` with a base — both reasonable. Recommend the contract (`ApplicationQuery#relation`); list the suffix options; let the team commit to one.
- **`app/managers/` or `app/handlers/`** when the contents span coordinators, event observers, and orchestrators — the umbrella name is too vague for a single rename. The fix is a base + suffix split, not a folder rename.

The error to avoid: surveying *one* axis of the contents (e.g., "they return view-shaped data, so they're presenters") and declaring the rename. A single inspection axis rarely distinguishes between two patterns that legitimately overlap. **Multiple plausible classifications → name the diagnosis, not the verdict.**

A rename recommendation is strong when the canonical pattern is unambiguous (`app/temporal/` → `app/workflows/` is unambiguous because no other layer claims Temporal.io); it is weak when two or more patterns from the canonical vocabulary fit the same evidence.

### 3.3 Naming Smells & Alternative Forms

This section asks a question the structural cluster analysis doesn't: **should this individual service exist at all?** Three mechanical checks plus the layer-bound suggestions for refactoring it away (already covered in Phase 2.2's "domain method" alternative).

#### 3.3.1 `-er` suffix

Class names ending in `-er` (`Manager`, `Processor`, `Creator`, `Sender`, `Exchanger`, `Transferrer`, `Getter`, `Fetcher`, `Updater`, `Mover`, `Cleaner`, `Resolver`) often signal a *procedure-carrier* rather than a real abstraction — the class exists only to hold a verb.

```bash
grep -rohE "^\s*class \w+(Manager|Processor|Creator|Sender|Exchanger|Transferrer|Getter|Fetcher|Updater|Mover|Cleaner|Resolver)\b" app/services/ | head
```

Caveat: some `-er` suffixes name legitimate framework-blessed roles — `Notifier`, `Validator`, `Serializer`, `Presenter`, `Decorator`, `Renderer`, `Formatter`, `Builder` (when it builds a real object), `Controller` itself. Treat those as healthy; flag only the procedure-carrier flavors above.

Output the suspect `-er` classes as a list, then run §3.3.2 and §3.3.3 against them.

#### 3.3.2 Tautological method/class pair

When the class name's verb-form root and the action method name say the same thing (`IpnProcessor#process_ipn`, `ReportGenerator#generate_report`, `OrderManager#manage_order`, `EmailSender#send_email`, `LinkBuilder#build_link`), the class adds nothing the method couldn't on its own.

```bash
grep -rEnH "^\s*class \w+(Processor|Generator|Manager|Sender|Builder|Creator|Maker|Doer|Runner|Executor|Performer)\b" app/services/ | head
```

Implementation: for each detected suspect class `<X><Suffix>`, check if there is a `def <verb>_<x_lowercase>`, `def <verb><X>` or `def <verb>` where `<verb>` matches the suffix root. If yes, flag.

#### 3.3.3 Ubiquitous-language test

A domain service should use terminology from the business glossary. Heuristic: extract the head noun of the class name (drop verb prefixes and trailing role-words like `Service`/`Form`/`Query`) and check whether it appears in `app/models/`, `db/schema.rb`, or `config/locales/`. If absent, the class names an invented concept.

```bash
class_name="FooBar"
file_form="$(ruby -e "puts ARGV[0].gsub(/(.)([A-Z])/, \"\\\\1_\\\\2\").downcase" "$class_name")"
[ -f "app/models/${file_form}.rb" ] && echo "model exists" || echo "no model"
grep -rE "create_table .${file_form}" db/schema.rb 2>/dev/null
```

Findings here are weak signals on their own; combine with the `-er` smell or tautology smell to identify candidates worth refactoring.

#### 3.3.4 Scheduling-frequency names — inline into jobs

Classes named after temporal scheduling (`Nightly`, `Hourly`, `Weekly`, `Daily`) with 1:1 anemic job peers are a **scheduling-layer duplication** smell.

```bash
grep -rlE "^\s*class \w*(Nightly|Hourly|Weekly|Daily|Monthly)\b" app/services/ | head
```

Recommendation:

1. **Inline into the job.** Jobs inherently carry scheduling semantics — naming a job `NightlyJob` is fine; naming a service `Nightly` is not. Eliminate the service-as-scheduling-wrapper indirection.
2. **Decompose by category.** Pipeline orchestrators → orchestrator jobs. Batch state transitions → BatchJob → SingleJob → model-method pattern. Ad-hoc fixups → standalone jobs. Multi-responsibility classes must be split before inlining.

Surface as a cross-cutting finding (a single recommendation across the cluster), not per-cluster.

These are **suggestions**, not violations. Teams that committed to `.call` everywhere are making a defensible convention-strength tradeoff (uniform stubbing, uniform interface). The command names the candidates and lets the team choose. Demote candidates surfaced here flow into Phase 2.2's classification table.

### 3.4 Implicit-Workflow Detection

When service A calls services B, C, D from inside its `call`, the workflow has no explicit owner — business logic forms invisible paths through services that share data implicitly.

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

Hub services are findings only — high fan-in is data, not a TODO. Inspect for missing domain abstractions before acting.

Workflow-level test win: a named orchestrator's spec describes the workflow steps (one responsibility); the previously implicit chain becomes an explicit, testable narrative.

### 3.5 Layer-Hygiene Violations

Targeted greps in `app/services/`. Report only sections with findings.

```bash
# Presentation-layer dependencies
grep -rnE "(^|[^_])request\.|params\[|session\[|cookies\[|headers\[|request_id|request_ip" app/services/ \
  | grep -vE "^\s*#"

# Controller machinery
grep -rnE "flash\[|render |redirect_to|helpers\." app/services/

# Current.* — apply the same accept/concern split as the architecture-analysis workflow
grep -rn "Current\." app/services/
```

For `Current.*`, classify each usage:

- **Acceptable:** AR-style attribute defaults (`default: -> { Current.user }`), audit trails (`self.created_by = Current.user` in a callback-like helper), explicit context-restoration blocks (`Current.set(...)`), overridable kwargs (`def call(user: Current.user)`).
- **Concerning:** business-decision branching (`Current.organization.premium?`), authorization (`Current.user.admin?`), query scoping (`where(org: Current.organization)`), anywhere the call site can't override.

Reference: `references/topics/current-attributes.md`.

#### Authorization in services is a layer leak

When a service includes `Authorization` or calls `authorize_with` / `authorize` / a policy object internally, flag as a **layer-hygiene observation**: *"authorization belongs at the controller/presentation boundary; services should trust their inputs."* Authorization is a presentation concern — it answers "is the *current user* allowed to do this?", which is a request-level question. Services should receive already-authorized domain objects.

```bash
grep -rnE "include Authorization\b|\bauthorize(_with)?\(|Pundit\.|policy_for|verify_authorized" app/services/
```

Don't downgrade the service's classification (it may still be a legitimate service) — surface the leak. Especially flag the **asymmetry** when the same feature authorizes in the controller for one action (e.g., `destroy`) and in the service for another (e.g., `create`) — the inconsistency is the proof that auth has no principled home.

#### Sinkhole detection

A service that just delegates to a single model method adds no value — the book calls this an "architecture sinkhole".

Heuristic: file ≤20 LOC AND the action method has ≤3 statements AND every statement targets the same single model. Surface 3–5 examples; don't list every case.

```bash
find app/services -name "*.rb" -type f -exec sh -c '
  lc=$(wc -l < "$1")
  if [ "$lc" -le 20 ]; then echo "$lc $1"; fi
' _ {} \; | sort -n | head -20
```

### 3.6 Misplaced Code — not-a-service files

Phase 3 should include a "misplaced code" scan for files in `app/services/` that **aren't really services**:

- Entirely `class << self` / Singleton with no instance lifecycle.
- Inherit from non-service parents (gem classes, framework sanitizers).
- Contain no side effects or external calls — just transformations.
- Are self-contained feature modules (parsers + engines + formatters).

Surface as a dedicated finding with per-file destination recommendations (e.g., `lib/`, `app/lib/`, `app/helpers/`).

**However, apply the self-separation gate before recommending relocation.** Many "not-a-service" files are harmless where they are.

#### 3.6.1 Self-separation gate — observation, not recommendation

When a cluster (or individual file) inside `app/services/` (a) does not inherit the project's service base class, (b) has its own base class with a distinct contract, and (c) is well-namespaced alongside its consumers — **do not recommend relocation**. The cluster has already self-separated; the `app/services/` prefix is cosmetic.

Only recommend relocation when there's a **concrete practical cost**:

- Wrong-layer inheritance pulling in unwanted machinery (middleware, tracing, result ceremony).
- Test-setup overhead from the service base class.
- Dependency-direction risk that wouldn't exist if the code lived elsewhere.

"It's not technically a service" is an observation worth surfacing — but an **observation**, not a **recommendation**. This applies equally to non-service clusters (storage adapters, payload builders, validators, factories) and to individual non-service files (value objects, error classes, concerns, utilities) co-located with their consumers.

**The litmus test:** can you name a bug, a performance problem, or a developer mistake that this relocation would prevent? If the answer is only "it would be more correct," downgrade to observation.

#### 3.6.2 Mixed-layer files — decomposition, not single relocation

When a file mixes infrastructure machinery (raw SQL helpers, index management, caching primitives, protocol-level operations) with model-specific logic (per-model methods, model-type checks, domain-aware transformations), don't recommend relocating the whole file to one destination. Recommend **decomposition**: infrastructure part to `app/lib/`, model-specific parts to `app/models/<model>/`. Name this as a **mixed-layer file** — a distinct diagnosis from "misfiled service."

The tell: the file contains both generic utility methods that could serve any model AND methods that reference specific model classes by name or use type checks (`Post === object`, `.update_tags_index`).

#### 3.6.3 Console/CLI utilities — specific destination, specific diagnosis

When a service requires interactive I/O libraries (`highline`, `io/console`), takes `IO`/`STDOUT` as a constructor argument, or outputs directly to stdout, flag as a **command handler** (not just "not a service"). Recommend `lib/tasks/` as the destination — not generic `lib/`. The distinction matters: `lib/tasks/` signals "this is tooling invoked from the command line," which is a precise diagnosis.

```bash
grep -rlE "require ['\"]highline['\"]|require ['\"]io/console['\"]|STDOUT\b|\$stdout\b" app/services/ | head
```

### 3.7 Peer-File Detection

When a service cluster is detected, scan adjacent layers for peer files — workers, jobs, model class methods — that wrap or re-implement the cluster's logic.

#### 3.7.1 Anemic peer Workers/Jobs — check cardinality

When a service cluster is detected, scan `app/workers/` and `app/jobs/` for peer files matching the cluster's naming pattern. Distinguish cardinality:

- **N services, N workers (1:1 peer wrappers, ≤5 LOC each)** → anemic; absorb into the abstraction's async surface (`.deliver_later` or similar).
- **N services, 1 shared worker parameterized by payload** → exemplar; the worker is the cluster's deferral primitive, factored correctly. Surface as a **positive anchor**, not a smell.

```bash
# Look for 1:1 anemic wrappers
for f in $(find app/workers app/jobs -name "*.rb" -type f 2>/dev/null); do
  lc=$(wc -l < "$f")
  if [ "$lc" -le 5 ]; then echo "$lc $f"; fi
done | sort -n | head
```

#### 3.7.2 AR model class-method orchestrators

Detect AR models with `class << self` blocks containing ≥5 sibling methods of the form `send_*` / `trigger_*` / `dispatch_*` / `notify_*` / `remove_*_async` / `*_without_delay`, where bodies enqueue workers or call services. Surface as a finding distinct from "non-AR class in app/models/" — the recommendation is *"consolidate trigger logic into the corresponding abstraction; collapse to one dispatcher or direct call sites."*

```bash
grep -rlE "^\s*(class << self|def self\.(send|trigger|dispatch|notify)_)" app/models/ | head
```

### 3.8 Test & Specification Audit

Many cluster-level test points are already raised in Phase 2.3 (sub-section 7c); this section characterizes **the codebase as a whole** and surfaces issues that don't fit a single cluster.

#### 3.8.1 Test convention discovery

Look at `spec/services/` (or `test/services/`) and answer:

- **Coverage** — what fraction of services have a corresponding spec? (Many services with no spec is itself a finding.)
- **Test support helpers** — does `spec/support/` define **shared contexts** (e.g., `shared_context "with current account"`) and **custom matchers** (e.g., `expect(query).to be_a_query_returning(...)`) that match the codebase's specializations? Their presence/absence is the signal.
- **Stubbing style** — do specs uniformly use `instance_double` / `class_double` / `allow(...).to receive`? Or is there a mix?
- **Interface stubbing** — when caller specs stub services, do they all stub the same verb (e.g., `.call`)? If not, that's a downstream effect of a weak call-interface convention.
- **Result discipline** — do specs check return shape uniformly (`be_success`, `be_present`, exception-based)? Mixed shapes mean callers can't generalize.

```bash
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

#### 3.8.2 Specification-test sweep

For 5–8 representative services (mix of cluster-detected and standalone), open the spec and read the `describe`/`context` block names. Classify each context by what it actually verifies:

- **Orchestration** (correct collaborators called, transaction boundaries) — appropriate for a service.
- **Domain rule** (validations, business rules, state transitions) — should live in a model spec.
- **Presentation/HTTP** (params parsing, response codes, redirects) — should live in a controller/request spec.
- **Side-effect plumbing** (mailer/job calls counted, Slack stubbed) — usually wants a delivery or job spec.

In the report, list the services whose specs are dominated by non-orchestration concerns. Each such case is a concrete refactor target that produces an immediate test-quality win.

#### 3.8.3 Test smells that justify refactors

| Smell | How to detect | What it signals |
|---|---|---|
| Heavy controller-stack setup in service specs | `request_spec_helper` / `type: :request` / `Rack::Test` imports | Service is doing presentation work; tests are slow and brittle |
| Repeated mailer/job/Slack stubbing across cluster | Same `allow(MyMailer)…` block in 5+ specs | Cluster wants to be a delivery — promotion gives `have_delivered_to` matchers |
| `let(:request) { double(...) }` in service specs | grep | Service accepts a request — fix the layer leak first |
| Duplicate model-rule coverage | The same validation tested in `<Service>_spec` and `<Model>_spec` | Domain logic is in services AND model — usually a cue that the service is doing the model's job |
| Unparameterized stubbing of own services (`.with` missing) | `allow(SomeService).to receive(:call).and_return(true)` | Call interface non-uniform OR service does too many things to constrain inputs |
| No specs at all in the cluster | Coverage check | The cluster's responsibility is unclear enough that nobody knew what to test — a *strong* promotion signal |

For each smell encountered, name the cluster or files; do not list smells that don't apply.

#### 3.8.4 Stating the test win for each recommendation

Every recommendation in the report (under **Top 3 Actions** and **Recommendations**) must include a one-line **Test win** indicating what specifically improves: faster specs, fewer stubs, framework matchers gained, duplicate coverage removed, layer leak closed. If no test win is identifiable, the recommendation is design-only — call that out so the user can weigh it accordingly.

### 3.9 Anemic-Model Risk

The inverse failure mode. For each model heavily referenced from `app/services/`:

```bash
grep -rohE "[A-Z][A-Za-z]+(::[A-Z][A-Za-z]+)*" app/services/ | sort | uniq -c | sort -rn | head -30
```

For each top model:

1. Open `app/models/<model>.rb`.
2. Count **substantive method definitions** — exclude:
   - DSL declarations (`belongs_to`, `has_many`, `validates`, `scope`, `enum`, `normalizes`, `delegate`, `attr_*`, `composed_of`).
   - Single-line aliases / accessors / pure delegations.
3. **Flag as anemic** if ≥10 services touch the model AND the substantive method count is fewer than 3.

For each anemic model, surface one concrete service example whose body manipulates the model's attributes — that's the domain logic that escaped the model.

### 3.10 Target Architecture Signals (positive markers)

Promoted specializations are healthy signals. Report them as a **strength**, not silence them. Each folder gets one of three states (✓ healthy / ⚠ under-used / ✗ absent), not a binary present/missing.

| Folder to check | Base class | ✓ Healthy when | ⚠ Under-used (ghost) when |
|---|---|---|---|
| `app/forms/` | `ApplicationForm` | ≥80% inherit it AND ≥3 files | <3 files OR no shared base OR same-shape candidates hide elsewhere |
| `app/queries/` | `ApplicationQuery` (or simple POROs) | folder exists with ≥3 files AND a base class OR consistent PORO shape | <3 files OR no base AND ≥5 query-shaped files live under `app/models/` / `app/services/` |
| `app/policies/` | `ApplicationPolicy` | base class present | base class missing AND ≥3 files |
| `app/deliveries/`, `app/notifiers/` | `ApplicationDelivery`, `ApplicationNotifier` | base class(es) per channel | folder exists, base missing |
| `app/presenters/`, `app/ui/`, `app/components/` | `ApplicationComponent`, `ApplicationPresenter` | base class present | folder exists, base missing |
| `app/operations/` | `ApplicationOperation` | base class present | folder exists, base missing |
| `app/clients/` | `ApplicationClient` | base class present (Infrastructure-layer external-API gateways) | folder exists, base missing OR vendor SDKs hide in `app/services/` instead |

```bash
for folder in forms queries policies deliveries notifiers presenters ui components operations clients; do
  count=$(find "app/$folder" -name "*.rb" 2>/dev/null | wc -l)
  if [ "$count" -gt 0 ]; then
    base=$(grep -rEh "^class Application\w+" "app/$folder" 2>/dev/null | head -1)
    echo "$folder: $count files | $base"
  fi
done
```

#### Promoted but under-used — the "ghost folder"

A folder is a **ghost** when it exists with files but is not actually carrying the role its name promises. Three triggers:

1. **Sparse adoption** — folder exists with <3 files in a codebase large enough to have produced more (e.g., `app/queries/` has 2 files in a codebase with 500+ models).
2. **Missing base class** — folder exists with files but no `Application<Role>` base, while files in the folder reinvent the same wheel each time.
3. **Same-shape cluster hidden elsewhere** — folder exists at low file count while a same-shape cluster (≥5 candidates) lives under `app/models/` / `app/services/` / `app/lib/`. The folder was promoted *as a convention* but the team forgot to migrate the real candidates into it.

The ghost state is more actionable than "absent". When `app/queries/` is absent, the report says "consider extracting a query layer" — generic advice. When `app/queries/` is a ghost (2 files, no base, 38 query candidates hiding under `app/models/`), the report says **"the folder already exists — name the decision: grow it into the real layer (migrate the 38 candidates and add `ApplicationQuery`) OR fold it back and delete the folder. Don't leave it as a ghost."**

Surface ghosts in the Codebase Insights → Verdict bullet (use `⚠` between `✓` and `✗`), and in the Specialization clusters proposal block when the cluster's destination is a ghost folder. The decision the team needs to make — **grow the ghost or fold it** — becomes its own recommendation.

A ghost is not a failure; it's an unfinished move. Naming it as such gives the team the choice the original promotion never resolved.

#### Architecture tier verdict

| Tier | Condition |
|---|---|
| **Mature decomposition** | `app/services/` is small (passes the gate) AND ≥3 specialization folders exist |
| **Mature decomposition (models-first variant)** | `app/services/` is intentionally absent AND deep model namespacing carries the orchestration |
| **Mixed** | Some specializations promoted, others still in services |
| **Pre-decomposition** | `app/services/` is large AND zero specialization folders |

In a "Mature decomposition" report, the recommendations should suggest at most fine-tuning — not refactoring. Celebrate the state.

---

## Reporting Principles

- **Conditional sections.** Do not include a section if there are no findings. No "✅ No issues found" filler.
- **Concrete evidence over generic advice.** Cite specific files, line numbers, and percentages. "Mixed parameter style (dry-initializer 64%, kwargs 28%, positional 8%)" beats "establish parameter conventions".
- **No vague recommendations.** Every recommendation must be specific enough to act on without further interpretation. "Add a CI guard" without showing the rule pattern, "introduce a base class" without surveying the machinery to hoist, "consolidate test frameworks" without naming files — drop these entirely rather than including them. A vague item dilutes the concrete ones around it. If the analysis can't get specific (data missing, scope too large, etc.), say so explicitly instead of waving at it.
- **Insights vs. recommendations are structurally separated.** Pure observations (counts, leaks, smells, hub services, dependency facts) live under `## Codebase Insights`. Concrete proposals (the per-cluster proposal blocks, naming refactors, cross-cutting items) live under `## Recommendations`. The two never share a paragraph.
- **Order: TL;DR → mirror → Top 3 Actions → Recommendations → Codebase Insights → Next Steps.** Recommendations come *before* the supporting observations — a reader who only reads the first half of the report should see the proposals, not the diagnostic data underneath them. Insights are the audit trail; recommendations are the headline content.
- **Top 3 Actions is a thin index, not a recap.** Each action is one short imperative sentence (the *what*) plus a single pointer (`→ Recommendations § Specialization clusters → *Importer`). No "Why" prose, no library options, no test/design win mini-essay — those all live in the per-cluster proposal block the pointer leads to. Duplication kills skimmability.
- **The empirical mirror is exactly one sentence and always gives a definition.** "In this project, a Service Object is …" states the inferred design pattern in plain prose — no code, no numbers, no percentages. Even when no convention has emerged, name the pattern that *has* — typically "any Ruby object placed under `app/services/`". Never write "not defined" or "no convention"; that's a refusal, not a definition. Save the metric bullets for `## Codebase Insights → Conventions`.
- **The contract sub-section is a Ruby code block, not a prose table.** Sub-section 4 of the cluster proposal block declares the abstraction's shape as a small Ruby snippet (base class with declarative DSL, abstract method placeholders, one concrete subclass example, peer-use call sites). The reader takes the code as the contract.
- **Don't push placement.** For every cluster, mention both nesting (`app/services/queries/`) and promotion (`app/queries/`); let the user decide.
- **Don't push naming when the classification is ambiguous.** When a folder or cluster could plausibly fit more than one canonical pattern (facades vs. presenters, resolvers vs. queries, managers vs. coordinators), the actionable diagnosis is the *missing contract* — base class, shared interface, documented role — which holds regardless of which name wins. Surface the candidate names as options; recommend the convention introduction; do not pick the new folder name. A confident rename is justified only when (a) the canonical pattern is unambiguous (e.g., `app/temporal/` → `app/workflows/` because no other layer claims Temporal.io) AND (b) the rename brings concrete affordances beyond what "introduce a base class" already provides (a framework convention activating, a library binding, an existing base under the new name).
- **Codebase-faithful contracts.** The Ruby contract block in §4 of each cluster proposal preserves the codebase's existing mixins, parameter library, and call interface. Do not silently substitute the textbook canonical form (`Dry::Initializer`, `Dry::Monads`, generic `extend Callable`) for what the team actually uses — the proposal must be migratable from the codebase's current building blocks. Surface canonical alternatives as one-line comments in the code or in §5 Library options, never as the headline contract. The exception: when the codebase's own convention is itself the diagnosis (multiple competing bases), the contract proposes the consolidating shape and names what's being collapsed.
- **Promoted but under-used folders are their own state.** Specialization folders get three verdicts (✓ healthy / ⚠ under-used "ghost" / ✗ absent), not a binary present/missing. A ghost — folder exists with <3 files OR no shared base OR same-shape candidates hidden elsewhere — is more actionable than absence: the recommendation names the decision *"grow into a real layer or fold back and delete"* instead of "consider extracting".
- **Recommend the abstraction layer, not the library.** The report says "extract a notification layer", not "use ActiveDelivery". When a concrete library is helpful for illustration, list 2+ alternatives and mark one as the example used to make the suggestion tangible. The user picks the implementation; the command picks the layer. Sketch-with-X follow-ups go in the **Next Steps** section, not inline in the recommendation.
- **Recommend the contract, not just the layer.** Phase 2.3 sub-section 4 names class-name shape, method names, return shape, and cross-boundary conventions. Generic `#call` is one valid contract; specializations often want richer verbs (`#resolve` for queries, `#permit?` for policies, `#deliver_now` for deliveries, `#import` for importers).
- **Show, don't just tell.** For promote-up clusters with ≥6 files, include the "Adding a new feature" before/after walkthrough. Demonstrating the pull is the proposal payoff that diagnoses cannot match.
- **Tests are first-class evidence.** Every cluster, every recommendation, every convention finding must connect to a test consequence — current pain (slow specs, repeated stubs, layer leakage) and/or future affordance (matchers, shared contexts, focused setup). A recommendation without a test win must be flagged as design-only.
- **The specification test is the headline diagnostic.** When a spec's contexts describe responsibilities outside its layer, that's the most concrete signal a refactor is justified. Quote actual `describe`/`context` lines as proof.
- **Shared examples across heterogeneous services are out of scope.** Recommend shared *contexts* and custom matchers tied to specific specializations; never blanket `it_behaves_like "a service"`.
- **Promote-up and demote-down are equally valid moves.** Many "services" should disappear into a value object or a delegate object. The proposal block treats demotion as a first-class proposal, not a footnote.
- **Healthy clusters are positive anchors, not silence.** When a cluster scores well on layer-hygiene axes (shared base, single shared deferral surface, infra separated, centralized opt-out, specs at the right level), explicitly surface it as an exemplar:
  1. A one-paragraph TL;DR naming it as the healthy reference.
  2. A side-by-side comparison table against any sibling cluster being told to refactor — same axes, ✓/✗ visible at a glance.
  3. A line: *"the shape this sibling proposal is asking for is exactly what *this cluster* already does."*
  4. Per-event mapping if a unification is plausible.

  This validates good work and gives the team a concrete in-codebase reference.
- **Articulate benefits, not just shape.** Every cluster proposal must include a net-benefit paragraph: the concrete current ritual (the actual N steps today), the post-refactor ritual (the 1–2 steps it becomes), which spec layers stop testing things they shouldn't, what becomes reusable that today is locked inside service bodies. Phase 2.3 sub-section 7 is where this lands; do not omit it.

### What the report body must NOT contain

- **No author name-drops.** End users do not know who Swett, Avdi, Fowler, Metz, Evans, DHH, etc. are. Do not write "by Swett's rule", "the Avdi smell", "per Fowler's anemic-domain-model anti-pattern", "Sandi Metz says". State the rule directly. If the source matters, it goes in the "Read more" section at the end.
- **No bare chapter-number references.** Do not write "per Chapter 5", "Chapter 6's domain services", "the book recommends". Either state the rule directly without attribution, or include the source in "Read more".
- **No buzzwords without explanation.** "DDD ubiquitous language" → "the name comes from the business glossary". "Specification test" is a defined concept the report uses; that's fine, but explain the first time it appears.

### Optional tail: "Read more"

When the report leans on specific external sources to justify rules, include a short "Read more" section listing them. When only general principles were applied, **omit the section entirely** — don't pad with the canonical book + two blog posts as a default.

If included, format as a short list with one-line context per link:

```markdown
## Read more

- *Layered Design for Ruby on Rails Applications* — the layered-architecture rules and the waiting-room metaphor. [Packt](https://www.packtpub.com/...)
- "Service Objects" — case against service-shaped procedures. [avdi.codes/service-objects](https://avdi.codes/service-objects/)
```

## Output Format

The report opens with **TL;DR**, the empirical mirror, and a thin **Top 3 Actions** index. **Recommendations** (the per-cluster proposal blocks — the headline content) come next, followed by **Codebase Insights** (the supporting evidence) and **Next Steps**. Recommendations and insights live in separate top-level sections — never mixed in the same paragraph.

```markdown
# Service Object Analysis — <project name>

## TL;DR

A single sentence stating the next move — concrete enough that the team could start work on it tomorrow. No prefix ("Monday move:", "Headline:", etc.) — just the statement. Example:

> Extract a delivery layer for `pb_slack/messages/*Formatter` — the single highest-leverage move; closes the layer leak and unlocks per-channel test isolation.

Then a one-paragraph diagnosis: tier verdict, key strengths, key gaps, the forces at play. No actions — state-of-the-world only.

## In this project, a Service Object is …

**Exactly one sentence** synthesizing the team's implicit design pattern, with no code, numbers, or percentages — those live in Codebase Insights → Conventions. See Phase 1.2 for examples and rationale.

## Top 3 Actions

A thin index — each action is **one short imperative sentence** (the *what*) plus a **single pointer** to the detailed proposal below. No "Why" prose, no library options, no test/design win mini-essay — those all live in the Recommendations section the pointer leads to. The reader skimming this list should know which three things matter and where to read about each.

1. **Consolidate the importer/loader cluster into a unified data-import layer.** → Recommendations § Specialization clusters → `*Importer` / `*Loader`.
2. **Establish a single call convention across the rest of `app/services/`.** → Recommendations § Other recommendations.
3. **Fix the `app/services/stripe_payment.rb` presentation leak.** → Recommendations § Other recommendations.

(If a fourth action is genuinely co-equal in priority, surface it; the "Top 3" framing is a budget, not a hard cap.)

---

## Recommendations

Concrete proposals. Each rests on observations gathered in Codebase Insights below; cross-references inline where useful. If a recommendation can't be made specific (e.g., "add a CI guard" without showing the rule pattern), it doesn't appear here — drop it rather than wave at it.

### Specialization clusters

For each cluster, the 8-part proposal block from Phase 2.3:

#### `*Query` / `*Finder` cluster (14 services) — promote: extract a query layer

**1. Cluster identity.** 14 services under `app/services/queries/` matching `*_query.rb` / `*_finder.rb`. Sample: `users/active_query.rb`, `payments/recent_finder.rb`. Destination: promote-up to a query layer.

**2. Current pain.** (concrete observations with file:line)

**3. Specification-test verdict.** (1–2 quoted `describe`/`context` lines)

**4. Suggested interface / contract.**

```ruby
class ApplicationQuery
  extend Dry::Initializer

  param :scope, default: -> { default_scope }

  # Abstract — implemented per query
  def relation; end

  # Optional helpers the base hoists
  def merge(other) = self.class.new(scope.merge(other.relation))
end

class ActiveUsersQuery < ApplicationQuery
  param :since, default: -> { 30.days.ago }

  def relation
    scope.where(active: true).where("last_seen_at > ?", since)
  end

  private

  def default_scope = User.all
end

# Peer use
User.merge(ActiveUsersQuery.new(since: 7.days.ago).relation)
```

**5. Library options.** Hand-rolled POROs over `ActiveRecord::Relation`, `rubanok` for parameter-driven scoping, or `ransack`-backed filter objects.

**6. Shared machinery.** Surveyed 5 cluster files. Common: tenant scope wrapping, parameter validation, default scope chaining. The base hoists `param :scope`, `merge`, and the abstract `#relation` contract.

**7. Benefits showcase.**

a. **Deduplication.** ~40 LOC saved across the cluster (parameter declarations + merge boilerplate currently repeated in 11/14 files).

b. **Common issues solved.** Tenant scoping is currently inconsistent — 9/14 files apply `Current.organization`, 5 don't. The base makes this uniform.

c. **Test simplification.** Custom matcher `be_a_query_returning(...)` on the shared base; replaces the 9 specs that currently `create_list(:user, 5)` to test what's effectively `User.where(active: true)`.

d. *(promote-up cluster ≥6 files)* **"Adding a new feature" walkthrough.**

```ruby
# Today — adding the next *Query (~35 LOC including spec):
class RecentSignupsQuery
  def self.call(scope = User.all, since: 7.days.ago)
    scope.where("created_at > ?", since).order(created_at: :desc)
  end
end

# After ApplicationQuery (~6 LOC of declared contract):
class RecentSignupsQuery < ApplicationQuery
  param :since, default: -> { 7.days.ago }

  def relation
    scope.where("created_at > ?", since).order(created_at: :desc)
  end
end
```

e. **Cross-boundary conventions unlocked.** Caller specs converge on `instance_double(MyQuery).to receive(:relation)`; controllers compose `User.merge(MyQuery.new(params).relation)` uniformly.

**8. Placement (your call).** Nest under `app/services/queries/` (minimal) OR promote to `app/queries/` (first-class).

#### Calculators (~25 files in `app/models/`) — demote: shape the domain-services sub-layer in place

(Structure identical to a promote-up cluster; sub-section 7d — the walkthrough — is omitted for demote clusters.)

### Naming refactors (from §3.3)

**`-er` suspects (5)** — (list)
**Tautological method/class pair (2)** — (list)
**Domain-method candidates (3)** — (list with specific moves)
**Module-function candidates (4)** — (list)

### Other recommendations

- (cross-cutting items — e.g., return-value convention, anemic-model restoration, layer-leak fixes that don't fit a cluster)

---

## Codebase Insights

Pure observations about the codebase — the supporting evidence the recommendations above rest on. No proposals live in this section. Hub services, fan-in lists, and similar diagnostic data are observations only; they don't require a recommendation to be worth surfacing.

### Verdict
- Services: N files, L LOC (X% of app/)
- Architecture tier: **Mature decomposition** | Mature decomposition (models-first variant) | Mixed | **Pre-decomposition** | Waiting room
- Promoted specializations: forms ✓ | queries ⚠ (ghost — 2 files, no base, ~38 query-shaped candidates hide under `app/models/`) | policies ✓ | deliveries ✗ | presenters ✗
- Convention strength: Strong | Mixed | Weak ("bag of random objects")
- Organization: Healthy | Sprawling | Bag of random objects
- Test convention strength: Strong | Mixed | Weak (spec coverage X%, no shared contexts/matchers, ...)
- Naming smells: K services flagged
- Implicit workflows: J chains of length ≥3
- Specialization opportunities: K clusters (M promote / N demote)
- Layer-hygiene issues: M
- Anemic-model risk: P models
- Service-like models: Q files (split: domain D / application A)

### Conventions (deviation report from 1.2)
- (per-axis findings)

### Organization
- (sub-namespace counts; mega-namespace flags; vendor-folder flags)

### Layer-Hygiene
- (presentation deps, Current usage, sinkhole findings)

### Implicit Workflows
- (chains, hub services — pure observations)

### Service-Like Classes in `app/models/`
- (domain candidates list; application candidates list — purpose test applied)

### Test & Specification
- (coverage; conventions; specification-test sweep findings; test smells)

### Anemic-Model Risk
- (top models with low method counts)

### (When applicable) Risks the team has accepted by keeping `app/services/` absent
- (10-item list for models-first stance)

---

## Next Steps

Follow-up prompts you can run when ready to dig deeper. Include only items that follow from actual recommendations above — don't pad.

- **Sketch `ApplicationQuery`** based on the surveyed machinery. Run: *"Sketch ApplicationQuery for the *Query cluster."*
- **Sketch `ApplicationImporter`** for the importer cluster. Run: *"Sketch ApplicationImporter for sera."*
- (other follow-up prompts)
```

## Related

- [Service Objects pattern](../references/patterns/service-objects.md)
- [Query Objects pattern](../references/patterns/query-objects.md)
- [Value Objects pattern](../references/patterns/value-objects.md)
- [Collaborator / Delegate Objects pattern](../references/patterns/collaborator-objects.md)
- [Service Objects anti-patterns](../references/anti-patterns/service-objects.md) — bag of random objects, anemic models, premature abstraction
- [Specification test](../references/core/specification-test.md)
- [Current attributes](../references/topics/current-attributes.md)

Companion workflows (linked from SKILL.md): the architecture-analysis workflow runs first for the wide view; the god-object and callback-analysis workflows go deeper on those specific dimensions.

# Gradual Layerification Workflow

Plan incremental adoption of layered architecture for Rails codebases. Create a practical, low-risk roadmap for introducing layered patterns to an existing codebase without big-bang rewrites.

## Contents

- [Inputs](#inputs)
- [Process](#process)
- [Output Format](#output-format)
- [Guidelines](#guidelines)
- [Related](#related)

## Inputs

- **Goal** (optional): Specific focus area. If not specified, create a full roadmap.

## Process

### 1. Understand the Goal

Parse the user's goal to determine focus and identify the canonical refactoring scenario for it:

| Goal keywords | Focus area | Key patterns | Reference scenario |
|---------------|------------|--------------|--------------------|
| authorization, permissions, policies | Authorization layer | Policy objects, Action Policy | [Extract authorization to policy](../examples/authorization-to-policy.md) |
| fat controllers, controller logic | Controller extraction | Form objects, filter objects | [Complex input to form object](../examples/complex-input-to-form-object.md) |
| callbacks, after_create, side effects | Callback extraction | Services, move to callers | [Callbacks to service](../examples/callbacks-to-service.md) |
| god object, large model, User model | Model decomposition | Concerns, associated objects | [God object decomposition](../examples/god-object-decomposition.md) |
| Current.user, current_user in models | Context extraction | Policy + controller seams | [Extract Current from model](../examples/current-from-model.md) |
| state machine, status, workflow | Explicit state machine | Workflow gem | [Implicit to explicit state machine](../examples/implicit-to-explicit-state-machine.md) |
| query, scopes, reports | Query extraction | Query objects | [Query to query object](../examples/query-to-query-object.md) |
| presenter, view logic, helpers | View extraction | Presenters, ViewComponents | [View logic to presenter](../examples/view-logic-to-presenter.md) |
| notifications, mailers, deliveries | Notification extraction | Move to orchestrators | (no canonical scenario yet — derive from caller context) |
| (none specified) | Full assessment | Prioritized roadmap | (consult scenarios per phase) |

When a phase matches a Reference Scenario, **read the scenario file before drafting before/after code.** The scenarios are canonical templates — adapt them to the user's actual class names and call sites, don't re-derive the structure from scratch. Always cite the scenario file in the phase output so the user can see the full template.

### 2. Assess Current State

Run targeted analysis:

```bash
# Check for existing abstractions
ls app/services app/forms app/policies 2>/dev/null

# Check for base classes
grep -r "class Application" app/

# Check for gem usage
grep -E "action_policy|dry-|pundit|reform" Gemfile
```

Determine architectural style:
- **DHH/37signals**: Fat models, thin controllers, minimal abstractions
- **Partial layered**: Some services/forms/policies present
- **Layered**: Full abstraction layer structure

### 3. Find Existing Patterns

Look for conventions to follow:

```bash
# Existing service patterns
head -20 app/services/*.rb 2>/dev/null

# Existing form patterns
head -20 app/forms/*.rb 2>/dev/null

# Existing policy patterns
head -20 app/policies/*.rb 2>/dev/null
```

If patterns exist, follow their conventions. If not, suggest establishing them.

### 4. Analyze Relevant Code

Based on goal, search for:

**Authorization focus:**
```bash
grep -r "can_\|admin\?\|role\|permission" app/models/ app/controllers/
```

**Callback focus:**
```bash
grep -r "after_create\|after_save\|after_commit\|before_" app/models/
```

**Fat controller focus:**
```bash
wc -l app/controllers/*.rb | sort -rn | head -10
```

**God object focus:**
```bash
wc -l app/models/*.rb | sort -rn | head -10
```

**Helper/Presenter focus (for ViewComponent opportunities):**
```bash
# Check helper sizes
wc -l app/helpers/*.rb | sort -rn | head -10

# Check for HTML construction in helpers (extraction signal)
grep -r "tag\.\|content_tag" app/helpers/

# Check for presenters building HTML
grep -r "\.render\|context: self" app/helpers/ app/presenters/
```

**Important:** Before dismissing presenters/ViewComponents as unnecessary, actually examine helper files for:
- Heavy `tag.div`, `tag.button`, `tag.span` usage → ViewComponent candidates
- Complex `data: { ... }` attribute hashes → Stimulus wiring belongs in components
- Presenters with `.render` methods → Already doing component work without benefits
- Helpers over 50 lines → Likely mixing logic and markup

### 5. Trace Call Chains

For each violation or extraction candidate:
1. Find all callers (grep for method/class usage)
2. Identify existing orchestrators (services, forms, controllers)
3. Determine best location for extracted code

**Key question:** Is there already an orchestrator where this logic can move?

### 6. Prioritize Changes

Order by value/risk ratio:

**High Value, Low Risk (Phase 1):**
- Extract authorization to policies (isolated, testable)
- Add form objects for multi-model forms (encapsulated)
- Move notifications from models to existing callers

**High Value, Medium Risk (Phase 2-3):**
- Extract god objects with associated objects pattern
- Introduce services for complex callback chains
- Add query objects for complex scopes

**Lower Priority (Later phases):**
- Presenters (cosmetic improvement) — *unless helpers are building HTML*
- Serializers (only if API-heavy)
- ViewComponents — *move UP priority if helpers use `tag.*` extensively*
- Repositories (only if needed)

**Priority adjustment:** If helpers contain heavy `tag.*` usage, move ViewComponent extraction to Phase 2 (High Value, Medium Risk). HTML-building helpers create maintenance burden and miss component benefits.

### 7. Generate Phased Plan

For each phase include:
- Specific files to change
- Pattern to apply with reference link
- Reference scenario link (when one applies — see step 1)
- Before/after code examples adapted from the scenario
- Dependencies on other phases
- Estimated scope (small/medium/large)
- "Stop here if..." guidance

## Output Format

```markdown
# Gradual Layerification Plan: [Goal]

## Current State

- **Style:** [DHH/37signals / partial layered / fully layered]
- **Existing abstractions:** [list what exists or "none"]
- **Relevant findings:** [issues related to the goal]

## Approach

[Explain why this order, what's the strategy based on goal and findings]

## Phase 1: [Name]

**Scope:** Small / Medium / Large
**Goal:** [What this phase achieves]

### Change 1: [Description]

**File:** `app/models/user.rb`

**Current:**
` ` `ruby
class User < ApplicationRecord
  def can_administer?(message)
    administrator? || message.creator == self
  end
end
` ` `

**After:**
` ` `ruby
# app/policies/message_policy.rb
class MessagePolicy < ApplicationPolicy
  def administer?
    user.administrator? || record.creator == user
  end
end
` ` `

**Pattern:** Policy Objects (see references/patterns/policy-objects.md)
**Scenario:** Extract Authorization to Policy (see examples/authorization-to-policy.md)

### Change 2: ...

**Stop here if:** The app is small and the team prefers DHH-style simplicity.

---

## Phase 2: [Name]

**Scope:** ...
**Depends on:** Phase 1

...

---

## Not Recommended for This Codebase

- **[Pattern]:** [Why it doesn't fit]
- **[Pattern]:** [Why it doesn't fit]

---

## Next Steps

1. Run the review workflow after implementing each phase
2. Add tests for new abstractions before refactoring
3. Consider [specific gem] for [specific pattern]
```

## Guidelines

- **Don't over-engineer small apps** - suggest minimal changes for simple codebases
- **Build on existing patterns** - follow conventions already in the codebase
- **One pattern at a time** - don't overwhelm with too many changes per phase
- **Provide escape hatches** - "stop here if..." lets teams choose their depth
- **Be specific** - name actual files and show real code transformations
- **Respect the existing style** - acknowledge DHH-style as valid choice

## Related

- [Policy Objects](../references/patterns/policy-objects.md)
- [Service Objects](../references/patterns/service-objects.md)
- [Form Objects](../references/patterns/form-objects.md)
- [Concerns](../references/patterns/concerns.md)
- [Extraction signals](../references/core/extraction-signals.md)

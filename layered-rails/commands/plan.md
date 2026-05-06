# /layered-rails:plan

Plan gradual adoption of layered architecture patterns.

## Usage

```
/layered-rails:plan [goal]
```

- `/layered-rails:plan` - Full layerification roadmap
- `/layered-rails:plan introduce authorization` - Focus on policies
- `/layered-rails:plan refactor fat controllers` - Focus on extracting to forms/services
- `/layered-rails:plan extract callbacks from User model` - Specific model focus
- `/layered-rails:plan reduce god objects` - Focus on model decomposition

Launches the `layered-rails-planner` agent with the specified goal.

## Examples

```
/layered-rails:plan
/layered-rails:plan introduce proper authorization using Action Policy
/layered-rails:plan move notifications out of models
/layered-rails:plan extract complex form handling
/layered-rails:plan refactor Order model callbacks
```

## What It Does

1. Analyzes current architecture style (DHH/37signals vs layered)
2. Identifies violations and extraction candidates relevant to goal
3. Finds existing patterns to build upon
4. Traces call chains to determine best extraction targets
5. Creates prioritized, incremental adoption plan
6. References appropriate pattern documentation

## Output

A phased roadmap with:
- Current state assessment
- Prioritized phases with specific files and changes
- Before/after code examples
- Pattern references
- "Stop here if..." guidance for each phase

## Related

- `/layered-rails:analyze` - Full codebase analysis (run first for context)
- `/layered-rails:review` - Review specific changes after implementing phases

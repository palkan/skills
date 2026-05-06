# /layers:plan

Plan gradual adoption of layered architecture patterns.

## Usage

```
/layers:plan [goal]
```

- `/layers:plan` - Full layerification roadmap
- `/layers:plan introduce authorization` - Focus on policies
- `/layers:plan refactor fat controllers` - Focus on extracting to forms/services
- `/layers:plan extract callbacks from User model` - Specific model focus
- `/layers:plan reduce god objects` - Focus on model decomposition

Launches the `layered-rails-planner` agent with the specified goal.

## Examples

```
/layers:plan
/layers:plan introduce proper authorization using Action Policy
/layers:plan move notifications out of models
/layers:plan extract complex form handling
/layers:plan refactor Order model callbacks
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

- `/layers:analyze` - Full codebase analysis (run first for context)
- `/layers:review` - Review specific changes after implementing phases

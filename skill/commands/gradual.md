# /layers:gradual

Plan gradual adoption of layered architecture patterns.

## Usage

```
/layers:gradual [goal]
```

- `/layers:gradual` - Full layerification roadmap
- `/layers:gradual introduce authorization` - Focus on policies
- `/layers:gradual refactor fat controllers` - Focus on extracting to forms/services
- `/layers:gradual extract callbacks from User model` - Specific model focus
- `/layers:gradual reduce god objects` - Focus on model decomposition

Launches the `layered-rails-gradual` agent with the specified goal.

## Examples

```
/layers:gradual
/layers:gradual introduce proper authorization using Action Policy
/layers:gradual move notifications out of models
/layers:gradual extract complex form handling
/layers:gradual refactor Order model callbacks
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

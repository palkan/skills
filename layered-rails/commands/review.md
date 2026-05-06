# /layered-rails:review

Standalone code review from a layered architecture perspective.

## Usage

```
/layered-rails:review                    # Review uncommitted changes
/layered-rails:review [file_path]        # Review specific file
/layered-rails:review --staged           # Review staged changes
/layered-rails:review --branch main      # Review changes vs branch
```

Read and follow [`skills/layered-rails/workflows/review.md`](../skills/layered-rails/workflows/review.md), applied to the diff or file path(s) given as arguments.

For multi-agent review with compound-engineering, this same workflow runs as the `layered-rails-reviewer` sub-agent inside `/review`.

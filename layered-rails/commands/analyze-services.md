# /layered-rails:analyze-services

Deep audit of the Application layer (`app/services/` and service-like classes) — the full version of the Service Layer Brief embedded in `/layered-rails:analyze`.

## Usage

```
/layered-rails:analyze-services [path]
```

- Without path: analyzes the current Rails app (`./app/`).
- With path: treats the given directory as the Rails app root.

Read and follow [`skills/layered-rails/workflows/analyze-services.md`](../skills/layered-rails/workflows/analyze-services.md), applied to the path given as argument.

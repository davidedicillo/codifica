<!-- Codifica state file. See codifica-spec.md for protocol rules. -->

# Work

## Active

```yaml
- id: EXAMPLE-001
  type: build
  state: todo
  owner: unassigned
  title: Example task

  description: |
    This is a template task. Delete it and add your own.

  acceptance:
    - Criterion one is met
    - Criterion two is met

  derived_from: null

  execution_notes: []

  human_review: null

  state_transitions: []
```

## Done

<!-- Completed tasks move here for reference -->

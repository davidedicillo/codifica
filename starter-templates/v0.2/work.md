<!-- Codifica state file. See codifica-spec.md for protocol rules. -->

# Work

## Active

```yaml
- id: EXAMPLE-001
  type: build
  state: todo
  owner: unassigned
  title: Example task
  priority: normal

  description: |
    This is a template task. Delete it and add your own.

  acceptance:
    - Criterion one is met
    - Criterion two is met

  depends_on: []

  labels:
    - example

  derived_from: null

  context:
    files: []
    references: []
    constraints: []
    notes: ""

  execution_notes: []

  artifacts: []

  human_review: null

  state_transitions: []
```

## Done

<!-- Completed tasks move here for reference -->

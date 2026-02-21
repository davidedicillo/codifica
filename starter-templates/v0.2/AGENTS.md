# For AI Agents

This repository uses the **Codifica protocol (v0.2)** for human-agent task coordination.

## Before starting work

1. Read `codifica.json` at the repo root
2. Read the spec file it references (typically `codifica-spec.md`)
3. Read ALL state files matching the `state` field (may be a glob or array)

Do not proceed without reading the spec.

## Quick rules

- Pull before reading, pull before writing
- Claim tasks with a single commit: set `state: in_progress` + `owner: agent:<your-name>` + `claimed_at` together
- If your claim push fails, do not start work — pick a different task
- Only work on tasks assigned to you (`owner: agent:<your-name>` or `unassigned`)
- Do not start tasks with unmet `depends_on`
- Never edit `human_review` sections
- Never mark tasks `done` unless you are the owner
- Never move tasks to `blocked` or `rejected` — only humans may do this
- Never delete or modify files in `assets/`
- Never reclaim stale tasks from other agents — only humans may reclaim
- Respect `file_scope` from `codifica.json` — do not modify files outside the allowed scope
- Check `allowed_agents` in `codifica.json` — if your agent name is not listed and the list is non-empty, stop and ask a human
- If intent is unclear, ask a human

## Finding work

Look in state files for tasks where:
- `state` is `todo`
- `owner` matches your agent name or is `unassigned`
- All `depends_on` tasks are `done`

Pick by priority: `critical` > `high` > `normal` > `low`.

Respect `max_concurrent_tasks_per_agent` from `codifica.json` if set.

## Recording work

When you complete work:
- Add an entry to `execution_notes` with your agent name, a note, a **summary** (single line, max 120 chars), and timestamp
- Record any files you produced in `artifacts` (path + type)
- Move the task to the appropriate next state per the spec
- Set `completed_at` when moving to `done`
- Commit with a message referencing the task ID (e.g., `FEAT-101: implement login flow`)

## Structured context

Before starting a task, read its `context` field:
- `context.files` — read these files for background
- `context.references` — read execution_notes from these prior tasks
- `context.constraints` — hard rules beyond acceptance criteria
- `context.notes` — free-form guidance from the human

## Handoffs

If your task depends on another agent's completed work:
- Read the dependency task's `execution_notes` (especially the `summary`) and `artifacts`
- Use `context.files` and `context.references` to find relevant material

If your task produces output another task needs:
- Record file locations in `artifacts`
- Write a clear `summary` on your closing execution note

## Provenance

When writing `execution_notes` and `state_transitions`, include a `provenance` block if your runtime provides session IDs:

```yaml
provenance:
  session_id: <your-session-id>
```

This helps trace actions across multi-agent systems.

## Requesting a block

If you discover a genuine blocker (missing dependency, failing test, ambiguous requirement):
- Add a note to `execution_notes` explaining the blocker and recommending the task be blocked
- Do NOT move the task to `blocked` yourself — only humans may do this

## Conflicts

If your push fails due to a Git conflict:
1. Pull the latest state
2. Re-evaluate whether your changes still apply
3. Retry or yield to human resolution

Conflicts on the same task should be escalated to a human.

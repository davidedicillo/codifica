# For AI Agents

This repository uses the **Codifica protocol** for human-agent task coordination.

## Before starting work

1. Read `codifica.json` at the repo root
2. Read the spec file it references (typically `codifica-spec.md`)
3. Read the state file it references (typically `work.md`)

Do not proceed without reading the spec.

## Quick rules

- Pull before reading, pull before writing
- Only work on tasks assigned to you (`owner: agent:<your-name>` or `unassigned`)
- Never edit `human_review` sections
- Never mark tasks `done` unless you are the owner
- Never delete or modify files in `assets/`
- If intent is unclear, ask a human

## Finding work

Look in `work.md` for tasks where:
- `state` is `todo` or `to_be_tested`
- `owner` matches your agent name or is `unassigned`

## Recording work

When you complete work:
- Add an entry to `execution_notes` with your agent name, a note, and timestamp
- Move the task to the appropriate next state per the spec
- Commit with a message referencing the task ID (e.g., `FEAT-101: implement login flow`)

## Conflicts

If your push fails due to a Git conflict:
1. Pull the latest state
2. Re-evaluate whether your changes still apply
3. Retry or yield to human resolution

Conflicts on the same task should be escalated to a human.

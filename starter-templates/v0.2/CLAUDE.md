# Codifica

This project uses the Codifica protocol for task coordination. Read `codifica.json` and the state files it references before doing any work.

## On session start

1. Read `codifica.json` at the repo root
2. Read all state files matching the `state` field
3. Tell the human what's going on:
   - Tasks waiting for review (`state: to_be_tested`) — offer to walk through them
   - Tasks in progress — summarize status
   - Open tasks available to work on — list by priority
   - Recently completed tasks (last 7 days) — brief summaries
4. Ask what the human wants to focus on

## Working on a task

1. Claim the task in a single commit: set `state: in_progress`, `owner: agent:<name>`, `claimed_at`
2. Read the task's `context` field for background (files, references, constraints)
3. If the task has `depends_on`, read the dependency tasks' `summary` and `artifacts` for handoff context
4. Work according to the `acceptance` criteria

## After completing a task

1. Move the task to `to_be_tested` (for build tasks) or `done` (for non-build tasks)
2. Add an `execution_notes` entry with what you did and a `summary` (single line, max 120 chars)
3. Record any files you produced in `artifacts`
4. **Present your work to the human for review:**
   - Show what you did (the summary + key details)
   - List the acceptance criteria and explain how each was met
   - Ask: "Does this meet your requirements? Should I move it to done?"
5. If the human approves: move to `done`, set `completed_at`
6. If the human wants changes: move back to `todo`, record feedback in `human_review`

## Key rules

- Pull before reading, pull before writing
- Never edit `human_review` sections
- Never move tasks to `blocked` or `rejected` (human only)
- Don't start tasks whose `depends_on` aren't all `done`
- Commit with messages referencing the task ID (e.g., `FEAT-101: implement login flow`)
- For full protocol details, read codifica-spec.md

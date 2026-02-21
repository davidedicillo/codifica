# Codifica Protocol — v0.2

Codifica is a **file-based communication protocol** that allows humans and AI agents to coordinate work safely, explicitly, and autonomously.

Codifica is not a task manager or a UI product. It is a **shared language and runtime contract** that tools and agents speak.

---

## 1. Purpose

Codifica exists to solve one problem:

> How do humans and AI agents hand off work, context, and judgment without losing meaning or control?

It defines:
- how work is identified
- how intent and judgment are recorded
- how agents discover and execute tasks
- how changes are validated and audited
- how multiple agents coordinate without losing context

---

## 2. Minimal Adoption Requirements

A repository is considered **Codifica-enabled** if it contains:

- `codifica.json`
- `work.md` (or state files matching the configured `state` pattern)

Everything else (CLI, UI, agents) is optional tooling.

---

## 3. Files Overview

### 3.1 `codifica.json` — Runtime Contract

Declares that the repository uses Codifica and tells tools where to find state.

**Minimal form:**

```json
{
  "protocol": "codifica",
  "version": "0.2",
  "spec": "codifica-spec.md",
  "state": "work.md",
  "assets": "assets/",
  "rules": "strict"
}
```

**Extended form:**

```json
{
  "protocol": "codifica",
  "version": "0.2",
  "spec": "codifica-spec.md",
  "state": "work/*.md",
  "assets": "assets/",
  "rules": {
    "mode": "strict",
    "allowed_agents": ["agent:builder", "agent:writer", "agent:reviewer"],
    "file_scope": {
      "include": ["src/**", "docs/**", "work.md"],
      "exclude": [".env", "secrets/**", "*.key"]
    },
    "custom_types": ["deploy", "migrate"],
    "branch_pattern": "{type}/{id}-{slug}",
    "max_concurrent_tasks_per_agent": 1,
    "stale_claim_hours": 24
  }
}
```

**Fields:**

| Field | Required | Description |
|-------|----------|-------------|
| `protocol` | yes | Must be `"codifica"` |
| `version` | yes | Protocol version |
| `spec` | yes | Path to the spec file. Agents MUST read this before operating |
| `state` | yes | Path to state file(s). May be a string, glob pattern, or array of paths (see §3.2) |
| `assets` | no | Directory for evidence files. Default: `"assets/"` |
| `rules` | no | String shorthand or rules object (see below) |

**Rules field:**

If `rules` is a string (e.g., `"strict"`), it is shorthand for `{ "mode": "<value>" }` with all other fields at defaults.

If `rules` is an object:

| Field | Default | Description |
|-------|---------|-------------|
| `mode` | `"strict"` | `"strict"` or `"permissive"` (future use) |
| `allowed_agents` | `[]` (all allowed) | Agent names authorized to operate. Agents not in this list MUST stop and ask a human. Empty list means all agents are allowed |
| `file_scope.include` | `["**"]` | Glob patterns (minimatch-style) defining files agents may modify |
| `file_scope.exclude` | `[]` | Glob patterns for files agents MUST NOT modify |
| `custom_types` | `[]` | Additional task types beyond the 5 built-in types |
| `branch_pattern` | none | Template for agent-created branches. Variables: `{type}`, `{id}`, `{slug}` |
| `max_concurrent_tasks_per_agent` | none | Max tasks a single agent may hold in `in_progress` simultaneously |
| `stale_claim_hours` | `24` | Hours of inactivity before a claimed task is considered stale (see §8.1.1) |

**Hard rules:**
- Tools and agents MUST read this file first
- Agents MUST read the spec file before operating
- No guessing or heuristics are allowed
- If `codifica.json` is missing or invalid, stop

---

### 3.2 `work.md` — Shared State

`work.md` is the **mutable shared state** in Codifica.

It is:
- shared memory between humans and agents
- an address book of work
- an explicit event log
- the system of record

Agents observe it. Humans review it. Tools mutate it through validated commands.

#### Multiple state files

The `state` field in `codifica.json` may be:
- A single path: `"work.md"` — the default
- A glob pattern: `"work/*.md"` — matches all `.md` files in the `work/` directory
- An array of paths: `["work/active.md", "work/backlog.md", "work/done.md"]`

When multiple state files are used:
- Each file follows the same format as `work.md`
- Task IDs MUST be unique across ALL state files
- Agents MUST scan all matching state files when looking for work
- Recommended splits:
  - **By lifecycle:** `active.md` (todo/in_progress/to_be_tested), `done.md` (completed), `backlog.md` (future work)
  - **By domain:** `work/frontend.md`, `work/backend.md` — reduces cross-agent merge conflicts
- A single `work.md` remains valid

**Archival:** When a task reaches a terminal state (`done` or `rejected`), it SHOULD be moved to an archive file within a reasonable time to keep active files scannable.

---

## 4. Task Identity

### 4.1 Task IDs
- Must be unique and immutable across all state files
- Act as stable addresses across tools and agents

Recommended formats:
- `FEAT-101`
- `TEST-012`
- `BUG-203`

Task IDs are meant to be:
- referenced in chat
- passed between agents
- used without context switching

---

## 5. Task Model (Canonical)

Each task in a state file must conform to the following structure:

```yaml
- id: <string>
  type: build | test | review | investigate | followup    # or custom_types from codifica.json
  state: todo | in_progress | to_be_tested | done | blocked | rejected
  owner: human | agent:<name> | unassigned
  title: <short string>

  description: <optional free text>

  priority: critical | high | normal | low     # default: normal
  depends_on:                                   # task IDs that must be done before this starts
    - <task-id>
  labels:                                       # freeform domain tags for filtering
    - <string>

  acceptance:            # REQUIRED for build tasks
    - <criterion>

  checklist:             # OPTIONAL (common for test tasks)
    - <item>

  derived_from: <task-id | null>

  context:               # OPTIONAL — structured input context
    files:
      - <path>
    references:
      - <task-id>
    constraints:
      - <string>
    notes: <free text>

  claimed_at: <ISO-8601>   # set when agent claims the task (see §8.1)

  execution_notes:       # AGENT-ONLY
    - by: agent:<name>
      note: <text>
      summary: <single line, ≤120 chars>    # REQUIRED on closing note for v0.2 tasks
      timestamp: <ISO-8601>
      provenance:                            # OPTIONAL, recommended for agents
        session_id: <string>
        commit_sha: <string>

  artifacts:             # OPTIONAL — files produced by this task
    - path: <relative path>
      type: <string>

  human_review:          # HUMAN-ONLY
    status: pass | needs_work | blocked
    reviewer: <string>
    notes:
      - <text, may include markdown + images>
    recorded_at: <ISO-8601>

  completed_at: <ISO-8601>    # set when task reaches done or rejected

  blocked_reason: <string>    # REQUIRED when state is blocked
  blocked_by: <task-id>       # OPTIONAL — task ID causing the block

  state_transitions:
    - from: <state>
      to: <state>
      by: human | agent:<name>
      reason: <string>
      timestamp: <ISO-8601>
      provenance:              # OPTIONAL, recommended for agents
        session_id: <string>
        commit_sha: <string>
```

### 5.1 Task Selection

When an agent looks for work, it MUST follow this algorithm:

1. Scan all state files for tasks where `state: todo`
2. Filter to tasks where `owner` matches the agent's name or is `unassigned`
3. Exclude tasks with unmet `depends_on` (any dependency whose `state` is not `done`)
4. Sort by `priority`: critical > high > normal > low
5. Among equal priority, prefer tasks with no `depends_on` (leaf tasks first)
6. Respect `max_concurrent_tasks_per_agent` from `codifica.json` — do not claim if at limit

### 5.2 Dependency Correctness

- `depends_on` MUST reference task IDs that exist in state files. A reference to a nonexistent ID is a protocol violation — the task MUST NOT move to `in_progress`
- Circular dependencies are invalid. If tooling detects a cycle, the mutation MUST be rejected. Without tooling, this is a human review responsibility during PR review
- **Dependency regression:** If a task in `done` is moved back to `todo` or `blocked`, any task that `depends_on` it and is currently in `todo` remains blocked automatically (the `depends_on` rule already prevents it from starting). If a dependent is already `in_progress`, the protocol SHOULD surface a warning in the dependent's `execution_notes`, but does NOT auto-revert it — human review decides

---

## 6. Task Types

### `build`
Implementation work, usually agent-owned. Requires acceptance criteria.

Default flow:
```
todo → in_progress → to_be_tested → done
```

### `test`
Evaluation and judgment (UX, QA, feel). May be human or agent-owned.

### `review`
Sign-off or alignment. Human judgment only.

### `investigate`
Exploratory or diagnostic work.

### `followup`
Derived from another task. Must include `derived_from`.

### Custom types
Projects may define additional types via the `custom_types` field in `codifica.json`. Custom types follow the same state machine as `build` unless otherwise specified.

---

## 7. State Machine Rules

### 7.1 Allowed Transitions

| From           | To             | Actor        |
|----------------|----------------|--------------|
| todo           | in_progress    | agent, human |
| in_progress    | to_be_tested   | agent        |
| to_be_tested   | done           | owner only   |
| to_be_tested   | todo           | owner only   |
| any            | blocked        | human        |
| blocked        | todo           | human        |
| blocked        | in_progress    | human        |
| todo           | rejected       | human        |
| blocked        | rejected       | human        |
| in_progress    | rejected       | human        |
| rejected       | todo           | human        |
| done           | todo           | human        |

### 7.2 Hard Rules
- A task in `to_be_tested` may only be moved to `done` or `todo` by its `owner`
- If `owner: human`, only a human can complete the task
- If `owner: agent:<name>`, that agent may complete the task
- Agents MUST NOT edit `human_review` sections
- Build tasks MUST NOT leave `todo` without acceptance criteria
- Tasks MUST NOT skip `to_be_tested` unless `type != build`
- A task with unmet `depends_on` MUST NOT move to `in_progress` (see §5.2)
- Moving to `blocked` REQUIRES `blocked_reason` to be set
- Moving to `rejected` REQUIRES a `reason` in the `state_transitions` entry
- Reopening from `rejected` REQUIRES a `reason` explaining the reversal
- Only humans may reject or reopen tasks — agents cannot descope or reverse descoping decisions
- Agents MAY request a block by adding a note to `execution_notes` recommending the task be blocked, with a reason. Only a human may actually transition to `blocked`
- When a task reaches `done` or `rejected`, `completed_at` SHOULD be set

---

## 8. Concurrency and Multi-Agent Coordination

Codifica relies on Git for conflict detection and resolution.

### 8.1 Task Claiming

When an agent picks up a task:
1. The agent MUST move the task from `todo` → `in_progress` AND set `owner: agent:<name>` AND set `claimed_at: <ISO-8601>` in a **single commit**
2. The agent pushes this commit. This is the "claim"
3. If the push fails (another agent claimed first), the agent MUST NOT start work — pull, re-evaluate, pick a different task
4. An `unassigned` task in `in_progress` is a protocol violation

#### 8.1.1 Stale Claim Recovery

Codifica has no daemon and no heartbeat — it is file-based. Stale claims are handled by human review:

- A task is considered **stale** if it has been in `in_progress` with no new `execution_notes` or `state_transitions` for longer than `stale_claim_hours` (configured in `codifica.json`, default: 24 hours)
- Any human MAY reclaim a stale task by moving it back to `todo` with a `state_transitions` entry recording the reason (e.g., `"Agent unresponsive, reclaiming"`)
- Agents MUST NOT reclaim stale tasks from other agents — only humans may do this (prevents reclaim races between agents)
- Git history provides the audit trail for all reclaim actions

### 8.2 Handoff Protocol

When Agent A's task produces output that Agent B needs:
1. Agent A completes its task → moves to `done`
2. Agent A records output location in `execution_notes` (with `summary`) and `artifacts`
3. Agent B's task includes `depends_on: [<Agent A's task id>]`
4. When Agent B starts, it reads Agent A's `execution_notes`, `artifacts`, and any files listed
5. The handoff is explicit in the state file — no side-channel communication needed

### 8.3 Agent Requirements

Agents MUST:
- Pull the latest state before reading state files
- Pull again before writing changes
- If a push fails due to conflict, pull, re-evaluate, and retry
- Structure commits to touch only their own task block
- NOT reformat or reorder other tasks in the same commit

### 8.4 Conflict Semantics

Concurrent edits to **different tasks** typically merge cleanly due to YAML's block structure.

Conflicts on the **same task** indicate a coordination failure. These SHOULD be escalated to a human rather than automatically resolved.

### 8.5 Rationale

Git conflicts are a feature, not a bug. They surface real coordination problems that deserve human attention rather than hiding them behind automatic resolution heuristics.

Using multiple state files (§3.2) reduces conflict frequency by isolating agent writes to different files.

---

## 9. Evidence & Images

Images must be stored as files:

```
assets/<TASK-ID>/<filename>
```

Referenced using standard Markdown:

```markdown
![Description](assets/FEAT-101/ios-se.png)
```

Images are **evidence**, never logic.

---

## 10. Provenance

### 10.1 Purpose

In multi-agent systems, tracing who did what matters. Provenance metadata provides enough context for a human reviewing a Git diff to trace actions back to their source without requiring cryptographic verification.

### 10.2 Provenance Block

`state_transitions` and `execution_notes` entries MAY include a `provenance` block:

```yaml
provenance:
  session_id: <string>     # agent runtime session ID (e.g., OpenClaw session key)
  commit_sha: <string>     # Git commit that introduced this entry
```

### 10.3 Rules

- `provenance` is OPTIONAL for v0.2. It is RECOMMENDED for agents and optional for humans
- `session_id` is agent-system-agnostic — it maps to OpenClaw session keys, but any runtime can populate it
- `commit_sha` is naturally verifiable via Git history
- The protocol does NOT mandate cryptographic verification — Git commit authorship plus provenance metadata provides sufficient traceability for v0.2

---

## 11. Agent Contract (Mandatory)

All agents must receive this instruction:

```
You are operating in a repository that uses the Codifica protocol.

Before doing any work:
1. Read codifica.json at repo root.
2. Read the spec file specified by the `spec` field.
3. Read ALL state files matching the `state` field.

Rules:
- Pull before reading. Pull before writing.
- Claim tasks with a single commit (state + owner + claimed_at) before starting work.
- If your claim push fails, do not start — pick a different task.
- Do not edit human_review sections.
- Do not delete or modify image files.
- Only the task owner may move a task from to_be_tested to done.
- Do not reclaim stale tasks from other agents — only humans may reclaim.
- Do not move tasks to blocked or rejected — only humans may do this.
- If you discover a blocker, add a note to execution_notes recommending the task be blocked, with a reason.
- Include a summary (≤120 chars) on your closing execution note.
- Record artifacts produced by your work.
- Set completed_at when moving a task to done.
- Include provenance (session_id) on execution_notes and state_transitions when available.
- Respect file_scope, allowed_agents, and max_concurrent_tasks from codifica.json.
- Do not start tasks with unmet depends_on.

If a push fails due to conflict, pull and re-evaluate.
If intent is unclear, ask a human.
```

---

## 12. Compatibility

### 12.1 Reading v0.1 state files

v0.2 agents MUST be able to read v0.1 state files. All new fields are optional — their absence is valid.

### 12.2 Writing to v0.2 repositories

v0.2 agents MUST include `summary` on closing execution notes. v0.1 agents writing to a v0.2 repo produce valid-but-incomplete entries.

### 12.3 Mixed repositories

Legacy tasks (created under v0.1) remain valid. New fields are required only on new transitions, not retroactively.

---

## 13. Guiding Principle

> Humans express **intent and judgment**.
> Agents execute **explicit contracts**.
> Codifica preserves **truth and causality**.

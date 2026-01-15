# Codifica Protocol — v0.1

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

---

## 2. Minimal Adoption Requirements

A repository is considered **Codifica-enabled** if it contains:

- `codifica.json`
- `work.md`

Everything else (CLI, UI, agents) is optional tooling.

---

## 3. Files Overview

### 3.1 `codifica.json` — Runtime Contract

Declares that the repository uses Codifica and tells tools where to find state.

```json
{
  "protocol": "codifica",
  "version": "0.1",
  "spec": "codifica-spec.md",
  "state": "work.md",
  "assets": "assets/",
  "rules": "strict"
}
```

Fields:
- `protocol` — must be `"codifica"`
- `version` — protocol version
- `spec` — path to the spec file (agents MUST read this)
- `state` — path to the state file
- `assets` — directory for evidence files
- `rules` — `"strict"` (default) or `"permissive"` (future use)

Rules:
- Tools and agents MUST read this file first
- Agents MUST read the spec file before operating
- No guessing or heuristics are allowed
- If missing or invalid → stop

---

### 3.2 `work.md` — Shared State

`work.md` is the **only mutable state** in Codifica.

It is:
- shared memory between humans and agents
- an address book of work
- an explicit event log
- the system of record

Agents observe it. Humans review it. Tools mutate it through validated commands.

---

## 4. Task Identity

### 4.1 Task IDs
- Must be unique and immutable
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

Each task in `work.md` must conform to the following structure:

```yaml
- id: <string>
  type: build | test | review | investigate | followup
  state: todo | in_progress | to_be_tested | done | blocked
  owner: human | agent:<name> | unassigned
  title: <short string>

  description: <optional free text>

  acceptance:            # REQUIRED for build tasks
    - <criterion>

  checklist:             # OPTIONAL (common for test tasks)
    - <item>

  derived_from: <task-id | null>

  execution_notes:       # AGENT-ONLY
    - by: agent:<name>
      note: <text>
      timestamp: <ISO-8601>

  human_review:          # HUMAN-ONLY
    status: pass | needs_work | blocked
    reviewer: <string>
    notes:
      - <text, may include markdown + images>
    recorded_at: <ISO-8601>

  state_transitions:
    - from: <state>
      to: <state>
      by: human | agent:<name>
      reason: <string>
      timestamp: <ISO-8601>
```

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

### 7.2 Hard Rules
- A task in `to_be_tested` may only be moved to `done` or `todo` by its `owner`
- If `owner: human`, only a human can complete the task
- If `owner: agent:<name>`, that agent may complete the task
- Agents MUST NOT edit `human_review` sections
- Build tasks MUST NOT leave `todo` without acceptance criteria
- Tasks MUST NOT skip `to_be_tested` unless `type != build`

---

## 8. Concurrency

Codifica relies on Git for conflict detection and resolution.

### 8.1 Agent Requirements

Agents MUST:
- Pull the latest state before reading `work.md`
- Pull again before writing changes
- If a push fails due to conflict, pull, re-evaluate, and retry

### 8.2 Conflict Semantics

Concurrent edits to **different tasks** typically merge cleanly due to YAML's block structure.

Conflicts on the **same task** indicate a coordination failure. These SHOULD be escalated to a human rather than automatically resolved.

### 8.3 Rationale

Git conflicts are a feature, not a bug. They surface real coordination problems that deserve human attention rather than hiding them behind automatic resolution heuristics.

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

## 10. Agent Contract (Mandatory)

All agents must receive this instruction:

```
You are operating in a repository that uses the Codifica protocol.

Before doing any work:
1. Read codifica.json at repo root.
2. Read the spec file specified by the `spec` field.
3. Read the state file specified by the `state` field.

Rules:
- Pull before reading. Pull before writing.
- Do not edit human_review sections.
- Do not delete or modify image files.
- Only the task owner may move a task from to_be_tested to done.
- All state changes must go through Codifica tooling.

If a push fails due to conflict, pull and re-evaluate.
If intent is unclear, ask a human.
```

---

## 11. Guiding Principle

> Humans express **intent and judgment**.  
> Agents execute **explicit contracts**.  
> Codifica preserves **truth and causality**.


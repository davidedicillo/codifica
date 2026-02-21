# Codifica

Codifica is a **communication standard** for coordinating work between humans and AI agents.

It is not a task manager. It is not a Kanban board. It is a **shared language** that tools and agents speak.

---

## What problem does Codifica solve?

As AI agents become real contributors, existing tools break down:
- state is implicit
- intent is lost
- judgment is mixed with execution
- automation is unsafe
- context is lost across agent boundaries

Codifica fixes this by making work:
- explicit
- addressable
- auditable
- agent-native
- traceable across multiple agents

---

## The Core Idea

Codifica treats work like infrastructure:
- **A spec** defines the language
- **A config file** declares adoption
- **A shared state file** is observed and acted on by agents

No databases. No hidden state. Git is the audit log.

---

## Minimal Setup

To adopt Codifica, you need **two files**:

```
codifica.json
work.md
```

That's it.

## Starter template (v0.2)

To use this template, copy these files into the root of your repository:

- `codifica.json`
- `codifica-spec.md`
- `work.md`
- `AGENTS.md`

Then commit them and edit `work.md` to add your first real task.

---

## What's new in v0.2

- **Multi-agent coordination:** formal task claiming, handoff protocol, stale claim recovery
- **Priority and dependencies:** `priority` and `depends_on` fields with a task selection algorithm
- **Structured context:** `context` field for files, references, constraints, and notes
- **Cross-agent queryability:** `summary` on closing notes, `artifacts` for produced files, `labels` and `completed_at` for filtering
- **Provenance:** optional `session_id` and `commit_sha` on transitions and notes
- **State machine improvements:** `blocked` has exit transitions and reasons, `rejected` state with human-only reopen
- **Scoped configuration:** `codifica.json` supports `allowed_agents`, `file_scope`, `custom_types`, and more
- **Multiple state files:** `state` can be a glob or array for scalability
- **Backward compatible:** v0.1 state files remain valid

---

## Files Explained

### `codifica.json`
Declares that the repo uses Codifica and tells tools where to look.

```json
{
  "protocol": "codifica",
  "version": "0.2",
  "state": "work.md",
  "assets": "assets/"
}
```

### `work.md`
The shared state between humans and agents.

It contains:
- task identities with priority and dependencies
- structured context for agent work
- execution notes with summaries from agents
- artifacts produced by tasks
- judgment and feedback from humans
- explicit state transitions with provenance
- references to evidence (images, files)

Agents watch it. Humans review it. Tools mutate it safely.

---

## How it's used

### Humans
- express intent in natural language
- review results and provide judgment
- attach evidence (screenshots, notes)
- refer to work by stable task IDs
- reclaim stale tasks from unresponsive agents

Humans should not think in states.

### Agents
- observe state files
- claim tasks with a single atomic commit
- execute work autonomously
- append execution notes with summaries
- record artifacts produced
- move tasks forward within strict rules
- respect dependencies and priority ordering

Agents never make judgment calls.

---

## Concurrency

Codifica relies on Git for conflict resolution.

Agents must claim tasks before starting work. If a claim push fails, the agent picks a different task.

Agents must pull before writing. If a push fails due to conflict, agents must pull, re-evaluate, and retry — or yield to human resolution.

Conflicts on the same task indicate a coordination failure and should be escalated to a human.

---

## Why this is different

Codifica is closer to Git / OpenAPI / Terraform than to Jira or Linear.

It is a **protocol first**, with optional tooling:
- CLI
- UI
- agent daemons

The UI can disappear. The work remains.

---

## Philosophy

> Humans provide taste and intent.
> Agents provide execution and speed.
> Codifica preserves context between them.

---

## Status

Codifica v0.2 is the current version. It adds multi-agent coordination, structured handoffs, and cross-agent queryability to the v0.1 foundation.

The goal is not feature completeness. The goal is **correctness, clarity, and leverage**.

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

Codifica fixes this by making work:
- explicit
- addressable
- auditable
- agent-native

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

## Starter template (v0.1)

To use this template, copy these files into the root of your repository:

- `codifica.json`
- `codifica-spec.md`
- `work.md`
- `AGENTS.md`

Then commit them and edit `work.md` to add your first real task.

---

## Files Explained

### `codifica.json`
Declares that the repo uses Codifica and tells tools where to look.

```json
{
  "protocol": "codifica",
  "version": "0.1",
  "state": "work.md",
  "assets": "assets/"
}
```

### `work.md`
The shared state between humans and agents.

It contains:
- task identities
- execution notes from agents
- judgment and feedback from humans
- explicit state transitions
- references to evidence (images, files)

Agents watch it. Humans review it. Tools mutate it safely.

---

## How it's used

### Humans
- express intent in natural language
- review results and provide judgment
- attach evidence (screenshots, notes)
- refer to work by stable task IDs

Humans should not think in states.

### Agents
- observe `work.md`
- act when tasks are assigned to them
- execute work autonomously
- append execution notes
- move tasks forward within strict rules

Agents never make judgment calls.

---

## Concurrency

Codifica relies on Git for conflict resolution.

Agents must pull before writing. If a push fails due to conflict, agents must pull, re-evaluate, and retry—or yield to human resolution.

Conflicts on the same task indicate a coordination failure and should be escalated to a human. This is a feature, not a bug: it surfaces real problems rather than hiding them behind automatic resolution.

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

Codifica is early and experimental.

The goal is not feature completeness. The goal is **correctness, clarity, and leverage**.

# Codifica

A small, durable, file-based protocol for coordinating work between humans and AI agents.

**Current version: v0.2** &mdash; adds multi-agent coordination, structured handoffs, provenance, and cross-agent queryability.

## What is Codifica?

Codifica is a **file-based communication protocol** that allows humans and AI agents to coordinate work safely, explicitly, and autonomously. It is not a task manager, not a SaaS product, and not a UI. It is a shared language and runtime contract that tools and agents speak.

A repository is Codifica-enabled if it contains:

- `codifica.json` &mdash; declares the protocol version, points to the spec and state files, and defines project-specific rules
- `work.md` &mdash; the shared state file where tasks, acceptance criteria, execution logs, and transitions are recorded

Everything else (CLI, UI, agents) is optional tooling.

## Quick start

1. Copy the [starter templates](./starter-templates/v0.2/) into your repo root
2. Commit the files
3. Start adding tasks to `work.md`

```bash
# or copy directly from GitHub
curl -sL https://raw.githubusercontent.com/davidedicillo/codifica/main/starter-templates/v0.2/codifica.json -o codifica.json
curl -sL https://raw.githubusercontent.com/davidedicillo/codifica/main/starter-templates/v0.2/work.md -o work.md
curl -sL https://raw.githubusercontent.com/davidedicillo/codifica/main/starter-templates/v0.2/codifica-spec.md -o codifica-spec.md
curl -sL https://raw.githubusercontent.com/davidedicillo/codifica/main/starter-templates/v0.2/AGENTS.md -o AGENTS.md
```

## What's in v0.2

v0.2 evolves Codifica from a single-agent coordination format into a multi-agent coordination protocol:

- **Multi-agent task claiming** &mdash; agents claim tasks via atomic Git commits (state + owner + `claimed_at` in a single commit). Push-fails-on-conflict prevents race conditions without distributed locks.

- **Stale claim recovery** &mdash; if an agent crashes after claiming a task, humans can reclaim it after a configurable inactivity threshold (`stale_claim_hours`). No runtime or heartbeat required.

- **Structured handoffs** &mdash; tasks declare dependencies (`depends_on`), structured input context (`context.files`, `context.references`, `context.constraints`), and produced artifacts (`artifacts`). Agent B reads Agent A's output without side-channel communication.

- **Cross-agent queryability** &mdash; required `summary` (single line, max 120 chars) on closing execution notes, plus `labels` and `completed_at`, enables any agent to answer "what did the marketing agent do this week?" by scanning structured fields instead of reading chat transcripts.

- **Provenance** &mdash; `execution_notes` and `state_transitions` entries can carry `provenance` metadata (session ID, commit SHA) for traceability across multi-agent systems.

- **Priority and dependency correctness** &mdash; `priority` (critical/high/normal/low), `depends_on` with DAG validation rules, cycle detection, and dependency regression handling.

- **Scoped configuration** &mdash; `codifica.json` supports `allowed_agents`, `file_scope` (include/exclude globs), `custom_types`, `branch_pattern`, and `max_concurrent_tasks_per_agent`.

- **Multiple state files** &mdash; `state` in `codifica.json` can be a glob or array (e.g., `"work/*.md"`) for scalability and reduced merge conflicts.

- **Blocked state with exits** &mdash; `blocked_reason` is required, agents can recommend blocks via `execution_notes`, and humans can unblock to `todo` or `in_progress`.

- **Rejected state with reopen** &mdash; human-only `rejected` terminal state for descoped work, with human-only reopen path back to `todo`.

## How it works

### Task model

Each task in `work.md` follows a canonical YAML structure:

```yaml
- id: FEAT-102
  type: build
  state: todo
  owner: agent:builder
  title: Implement user login flow
  priority: high
  depends_on:
    - FEAT-101

  acceptance:
    - Login form validates email and password
    - Successful login redirects to dashboard

  context:
    files:
      - src/auth/login.ts
    references:
      - FEAT-101
    constraints:
      - "Must be backward compatible with v2.x clients"
```

### State machine

```
todo -> in_progress -> to_be_tested -> done
                \                      /
                 `-> blocked -> todo -'
                       \-> rejected -> todo (human-only reopen)
```

Transitions are recorded with actor, reason, timestamp, and optional provenance.

### Agent contract

Agents operating in a Codifica-enabled repository must:

1. Read `codifica.json` and the spec file before doing any work
2. Claim tasks with a single atomic commit (state + owner + `claimed_at`)
3. Record `execution_notes` with `summary` on completion
4. Record produced files in `artifacts`
5. Respect `file_scope`, `allowed_agents`, and `max_concurrent_tasks` from config
6. Never edit `human_review` sections, never move tasks to `blocked` or `rejected`

See [AGENTS.md](./starter-templates/v0.2/AGENTS.md) for the full agent instructions.

## Repository structure

```
codifica.json              # protocol config (this repo's own)
codifica-spec.md           # v0.2 protocol specification
work.md                    # this repo's own task state
index.html                 # project website
style.css                  # website styles
starter-templates/
  v0.2/                    # current starter templates
    codifica.json
    codifica-spec.md
    work.md
    AGENTS.md
  v0.1/                    # legacy starter templates
    codifica.json
    codifica-spec.md
    work.md
    AGENTS.md
```

## Philosophy

- **Humans express intent and judgment.** Agents execute explicit contracts. Codifica preserves truth and causality.
- **File-based, Git-native.** No runtime, no daemon, no SaaS dependency. Plain text committed with the code.
- **Constraints over autonomy.** Agent behavior is bounded by written rules. The human remains accountable.
- **Traceability over output.** The "why" is recorded with the change. Review is a first-class step.

## Compatibility

- v0.2 agents can read v0.1 state files (all new fields are optional)
- v0.1 agents writing to a v0.2 repo produce valid-but-incomplete entries
- Legacy tasks remain valid; new fields are required only on new transitions

## Community

- [Discord](https://discord.gg/qKYCXkU2Ex)

## License

This project is open source.

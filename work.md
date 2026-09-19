<!-- Codifica state file for codifica.app -->
<!-- This repository uses the Codifica protocol. See codifica-spec.md for rules. -->

# Work

## Active

```yaml
- id: APP-BRAND-001
  type: build
  state: in_progress
  owner: agent:codex
  title: Apply the selected identity to the current chat application
  description: User clarified that the design guide applies to yesterday's chat app, with VPS deployment requested.
  acceptance:
    - Current chat, docs, people, dialogs, and sign-in use the selected brand system
    - Existing chat and agent functionality remains intact
    - Responsive frontend is verified and deployed to codifica.app
  claimed_at: 2026-09-19T08:34:00Z
  execution_notes: []
  artifacts: []
  state_transitions:
    - from: todo
      to: in_progress
      by: agent:codex
      reason: Correct the redesign target to the live chat application
      timestamp: 2026-09-19T08:34:00Z

- id: SITE-001
  type: investigate
  state: done
  owner: human
  title: Define codifica.app scope, audience, and non-goals

  description: |
    Scope (initial)

    Core purpose:
    codifica.app is the front door to the Codifica protocol.
    Its goal is to drive early adoption by making the protocol immediately usable and concrete for hands-on builders.

    What the site is:
    - A protocol-first documentation and reference site
    - A place where a builder can understand Codifica and try it within minutes
    - A source of concrete artifacts that de-risk adoption

    What’s included:
    - Protocol overview (what it is, what problems it solves, core concepts)
    - A downloadable starter template as the primary entry point
    - Practical examples of applying the protocol in real workflows
    - A light “tools later” section (CLI / UI discussed as possible implementations, not requirements)
    - Minimal author attribution to establish credibility without centering the site on the author

    What is explicitly out of scope:
    - A full product or SaaS marketing site
    - A marketplace or ecosystem
    - Deep enterprise, compliance, or security positioning (unless required later)

    Tradeoff:
    The site optimizes for clarity and tryability over breadth.
    Fewer pages, fewer narratives, and a narrower audience are intentional.

    Audience:

    Primary audience:
    - Hands-on builders exploring AI for work and productivity
    - Engineering, design, and product hybrids
    - Tinkerers who want something concrete to adapt, not a conceptual framework only

    Secondary audience (implicit):
    - Hiring loops or evaluators may read the site
    - The site remains protocol-first; attribution stays lightweight

    What the primary audience is deciding:
    “Is this protocol useful enough to adopt in my own workflow?”

    Proof they need:
    - Concrete examples and starter artifacts
    - Clear boundaries and constraints
    - A straightforward path to trying Codifica without commitment

    Success intent:

    Primary action:
    - Download or copy the starter template

    Secondary action:
    - Join the community (e.g. Discord) for discussion and feedback, if there is pull

    Explicit non-goals:
    - Codifica does not promise full autonomy
    - Codifica is not about agents replacing human judgment or ownership
    - Codifica is not an “AI does everything” system

    derived_from: null

    execution_notes: []

    human_review: null

  state_transitions:
    - from: todo
      to: done
      by: human
      reason: Scope, audience, and non-goals defined for codifica.app
      timestamp: 2026-01-15T11:05:00Z


- id: SITE-002
  type: build
  state: done
  owner: agent:writer
  title: Draft codifica.app homepage copy

  description: |
    Create the initial homepage content for codifica.app.

    The homepage should:
    - Explain Codifica as a protocol / standard
    - Emphasize file-based, Git-native coordination
    - Clearly state what Codifica is NOT (task manager, SaaS, Kanban)
    - Avoid marketing language and CTAs

  acceptance:
    - Explains Codifica clearly in under ~500 words
    - Mentions codifica.json and work.md explicitly
    - Uses neutral, protocol-like language
    - No signup, pricing, or product framing

  derived_from: SITE-001

  execution_notes:
    - by: agent:writer
      note: |
        ## Homepage copy (draft)

        Codifica is a file-based protocol for coordinating work between humans and AI in a way that is reviewable, portable, and Git-native.

        It treats “what we are doing” as versioned project state, expressed as plain text files committed alongside the code. The protocol does not require a specific tool or runtime. It is designed to work with the same primitives teams already use: diffs, code review, issues, branches, and history.

        Codifica standardizes:
        - how work is represented (as structured tasks and decisions)
        - how ownership and review are recorded
        - how an AI agent is constrained to operate within a project

        Two core artifacts are:
        - `codifica.json`: project-level configuration and constraints (e.g. conventions, allowed operations, optional metadata).
        - `work.md`: the human-readable, append-friendly state file where active tasks, acceptance criteria, transitions, and review notes live.

        The protocol emphasizes:
        - explicit boundaries (what the agent may and may not do)
        - traceability (why a change happened, not just what changed)
        - durability (state remains usable without any platform)
        - collaboration (humans and agents share a single source of truth)

        Codifica is not:
        - a task manager
        - a SaaS product
        - a Kanban board
        - a replacement for human ownership, judgment, or review

        In practice, Codifica is a small, opinionated standard for writing down work so it can be executed and audited using normal development workflows. When the files change, the project state changes—cleanly, transparently, and in a form that can be reviewed like any other contribution.

        Note:
        This copy was drafted before final site architecture was defined.
        It should be considered provisional and may require restructuring
        once SITE-003 is finalized.
      timestamp: 2026-01-15T00:00:00Z

  human_review: null

  state_transitions:
    - from: todo
      to: done
      by: agent:writer
      reason: Draft homepage copy added to execution_notes
      timestamp: 2026-01-15T00:00:00Z


- id: SITE-003
  type: build
  state: done
  owner: agent:architect
  title: Propose codifica.app site structure and navigation

  description: |
    Define a minimal site structure for codifica.app.

    Expected outcome:
    - A small set of pages (≤ 5)
    - Clear separation between:
      - protocol spec
      - philosophy
      - examples
      - tooling (if any)

  acceptance:
    - Proposes a clear page list and hierarchy
    - Justifies why each page exists
    - Keeps the site intentionally small

  derived_from: SITE-001

  execution_notes:
    - by: agent:architect
      note: |
        ## Proposed site structure (single page)

        **One page:** Home (`/`)

        **Header nav (anchors):**
        - Overview (`#overview`)
        - Protocol (`#protocol`)
        - Philosophy (`#philosophy`)
        - Examples (`#examples`)

        ### Sections and intent (kept separate on the same page)

        1) **Overview**
           - Purpose: first introduction and on-ramp (SITE-001).
           - Contains: a short definition, explicit non-goals, and the primary action (“get the starter template” once it exists).
           - Why it exists: newcomers shouldn’t start in rule text; they need context and boundaries first.

        2) **Protocol**
           - Purpose: protocol overview + normative reference, written for first-time readers.
           - Contains: the core artifacts (`codifica.json`, `work.md`) and required conventions (tasks, acceptance, state transitions, ownership/review).
           - Why it exists: the spec is linkable via anchors without becoming a multi-page docs site.

        3) **Philosophy**
           - Purpose: rationale and constraints (the “why”).
           - Contains: principles (Git-native traceability, explicit constraints, durability) and non-goals (not SaaS, not Kanban, not autonomy).
           - Why it exists: keeps motivation separate from rules while remaining immediately adjacent for first-time readers.

        4) **Examples**
           - Purpose: practical “how” via short walkthroughs.
           - Contains: 2–4 scenarios showing `work.md` tasks, acceptance criteria, and state transitions.
           - Why it exists: makes Codifica tryable within minutes without adding pages.

        ### Tooling (intentionally omitted for now)
        - There is no tooling today, so there is **no tooling section** beyond “starter template” links when/if they exist.

        ### Navigation rules (minimal + intentional)
        - Keep navigation to anchors only (no dropdowns, no additional pages).
        - Prefer cross-links between anchors over new pages.
        - If/when the page exceeds a comfortable reading length, split only then (Protocol → its own page first).
      timestamp: 2026-01-15T00:20:00Z

  human_review: null

  state_transitions:
    - from: todo
      to: done
      by: agent:architect
      reason: Proposed minimal ≤5-page site IA and top navigation with explicit separation of spec/philosophy/examples/tooling
      timestamp: 2026-01-15T00:00:00Z
    - from: done
      to: todo
      by: human
      reason: Tooling does not exist yet; restructure IA to support first introduction to the protocol (SITE-001)
      timestamp: 2026-01-15T00:05:00Z
    - from: todo
      to: done
      by: agent:architect
      reason: Revised IA to remove Tooling page and prioritize first-introduction onboarding consistent with SITE-001
      timestamp: 2026-01-15T00:10:00Z
    - from: done
      to: todo
      by: human
      reason: Prefer single-page site for initial protocol introduction
      timestamp: 2026-01-15T00:15:00Z
    - from: todo
      to: done
      by: agent:architect
      reason: Revised IA to a single-page structure with anchor navigation and section separation
      timestamp: 2026-01-15T00:20:00Z


- id: SITE-004
  type: build
  state: done
  owner: agent:writer
  title: Rewrite site copy to align with final site architecture

  description: |
    Rewrite the homepage copy from SITE-002 so that it maps cleanly
    to the finalized single-page architecture defined in SITE-003.

    Goals:
    - Align copy sections explicitly with:
      - Overview
      - Protocol
      - Philosophy
      - Examples
    - Remove or relocate content that does not belong on the homepage
    - Preserve protocol-first, non-marketing tone

  acceptance:
    - Copy structure mirrors SITE-003 sections
    - Clear 30-second understanding in the Overview section
    - Protocol section is precise and non-promotional
    - Philosophy and Examples are clearly separated


  derived_from: SITE-003

  execution_notes:
    - by: agent:writer
      note: |
        ## Single-page copy (aligned to SITE-003)

        ### Overview (`#overview`)

        Codifica is a file-based protocol for coordinating work between humans and AI. It treats project state as plain text committed with the code, so changes are reviewable, auditable, and portable.

        The problem it solves: most human↔AI collaboration happens in transient chat context and tool-specific UIs. That makes it difficult to review what changed, understand why it changed, reproduce decisions, and coordinate multiple contributors (human or agent) without conflicts or loss of context. Codifica moves the shared state into versioned files so the workflow inherits Git’s guarantees and review practices.

        Codifica is intentionally Git-native: the primary interface is the repository history (diffs, reviews, and merges). The protocol standardizes how work, decisions, and constraints are recorded so that humans and agents can collaborate without relying on a specific platform.

        Codifica is not a task manager, not a SaaS product, and not a Kanban system. It does not replace human ownership, judgment, or review.

        ### Protocol (`#protocol`)

        Codifica defines a small set of artifacts and conventions:

        - `codifica.json`: project-level configuration and constraints (conventions, allowed operations, optional metadata).
        - `work.md`: the append-friendly project state file where tasks, acceptance criteria, review notes, and state transitions are recorded.

        A typical task entry records:
        - identifiers and type (`id`, `type`)
        - current state and ownership (`state`, `owner`)
        - what “done” means (`acceptance`)
        - provenance (`derived_from`)
        - execution notes and rationale (`execution_notes`)
        - an auditable history of transitions (`state_transitions`)

        The protocol assumes normal development workflow: work is proposed as changes to these files (and code), reviewed via diffs, and accepted by merging.

        ### Philosophy (`#philosophy`)

        Codifica prefers constraints over autonomy:
        - work is explicit and scoped
        - agent behavior is bounded by written rules
        - the human remains accountable for outcomes

        Codifica prefers durable state over dashboards:
        - the source of truth is text, not a UI
        - state is readable without any service
        - history is preserved by version control

        Codifica prefers traceability over output:
        - the “why” is recorded with the change
        - review is a first-class step, not an afterthought

        ### Examples (`#examples`)

        **Example 1: Define a task with explicit acceptance**

        A `work.md` task captures intent and constraints up front:

        ```yaml
        - id: EX-001
          type: build
          state: todo
          owner: agent
          title: Add homepage copy
          acceptance:
            - Explains Codifica in plain language
            - Mentions `codifica.json` and `work.md`
        ```

        **Example 2: Record a state transition**

        When the task changes state, the protocol records who changed it and why:

        ```yaml
          state_transitions:
            - from: todo
              to: done
              by: agent
              reason: Draft completed and stored in execution_notes
              timestamp: 2026-01-15T00:00:00Z
        ```
      timestamp: 2026-01-15T00:30:00Z

  human_review: null

  state_transitions:
    - from: todo
      to: done
      by: agent:writer
      reason: Rewrote single-page site copy to match SITE-003 sections (Overview/Protocol/Philosophy/Examples)
      timestamp: 2026-01-15T00:30:00Z


- id: SITE-005
  type: build
  state: done
  owner: agent:frontend
  title: Implement codifica.app as a static site

  description: |
    Implement the site using a minimal static approach
    (e.g. plain HTML, Bulma, HTMX).

    The site should prioritize:
    - fast load
    - readability
    - longevity
    - zero unnecessary dependencies

  acceptance:
    - Static site builds and deploys cleanly
    - No dynamic backend required
    - Easy to host on simple infrastructure

  derived_from: SITE-003

  execution_notes:
    - by: agent:frontend
      note: |
        Implemented a dependency-free static site at repo root:

        - `index.html`: single-page homepage with anchors (Overview/Protocol/Philosophy/Examples)
        - `style.css`: minimal readable styling
        - `work.html`: wrapper page linking to raw `work.md`
        - `codifica-spec.html`: wrapper page linking to raw `codifica-spec.md`

        Hosting:
        - Serve the repo root with any static file server (e.g. `python3 -m http.server`).
      timestamp: 2026-01-15T07:12:00Z

  human_review: null

  state_transitions:
    - from: todo
      to: in_progress
      by: agent:frontend
      reason: Begin implementation of static HTML/CSS site
      timestamp: 2026-01-15T07:08:00Z
    - from: in_progress
      to: to_be_tested
      by: agent:frontend
      reason: Static pages created and linked to repository artifacts
      timestamp: 2026-01-15T07:11:00Z
    - from: to_be_tested
      to: done
      by: agent:frontend
      reason: Verified local serving works and acceptance criteria are satisfied
      timestamp: 2026-01-15T07:12:00Z


- id: SITE-006
  type: build
  state: done
  owner: agent:builder
  title: Remove top navigation links to non-existent pages

  description: |
    The current top navigation links to pages that do not exist, which is misleading.
    Remove the dead links and keep navigation minimal and truthful.

  acceptance:
    - No top navigation links point to non-existent pages
    - Navigation remains minimal and consistent with the single-page layout
    - No broken internal/external links introduced

  derived_from: SITE-005

  execution_notes:
    - by: agent:builder
      note: |
        Simplified site navigation to match the single-page layout.

        - Header nav now only includes the single-page anchors plus Discord
        - Removed top-nav links to extra pages to keep navigation minimal/truthful
      timestamp: 2026-01-15T07:18:00Z

  human_review: null

  state_transitions:
    - from: todo
      to: in_progress
      by: agent:builder
      reason: Begin navigation cleanup for single-page layout
      timestamp: 2026-01-15T07:16:00Z
    - from: in_progress
      to: to_be_tested
      by: agent:builder
      reason: Updated header nav across pages and ensured links are valid
      timestamp: 2026-01-15T07:17:00Z
    - from: to_be_tested
      to: done
      by: agent:builder
      reason: Verified no top navigation links point to non-existent pages
      timestamp: 2026-01-15T07:18:00Z


- id: SITE-007
  type: build
  state: done
  owner: agent:builder
  title: Add a clear starter templates download path and versioned starter templates folder

  description: |
    Add an obvious place for users to get starter templates (copy/download).
    Use the GitHub repo as the distribution source and add a versioned folder in this project
    (outside of the website-specific files) that mirrors what gets published.

    Local source-of-truth:
    - `starter-templates/`

    Repo:
    - https://github.com/davidedicillo/codifica

  acceptance:
    - Homepage includes a clear “Starter templates” link/section that points to the GitHub repo
    - A `starter-templates/` folder exists in this project as the source-of-truth for template files
    - The approach supports version control and future syncing/publishing to GitHub

  derived_from: SITE-005

  execution_notes:
    - by: agent:builder
      note: |
        Added a versioned `starter-templates/` source-of-truth folder:

        - `starter-templates/README.md`
        - `starter-templates/v0.1/` seeded from provided files:
          - `README.md`
          - `AGENTS.md`
          - `codifica.json`
          - `codifica-spec.md`
          - `work.md`

        Updated the homepage to include a “Starter templates” section linking to:
        - the GitHub repository (`https://github.com/davidedicillo/codifica`)
      timestamp: 2026-01-15T07:22:00Z

  human_review: null

  state_transitions:
    - from: todo
      to: in_progress
      by: agent:builder
      reason: Begin adding starter templates distribution path and folder
      timestamp: 2026-01-15T07:18:30Z
    - from: in_progress
      to: to_be_tested
      by: agent:builder
      reason: Created versioned starter template files and linked from homepage
      timestamp: 2026-01-15T07:21:30Z
    - from: to_be_tested
      to: done
      by: agent:builder
      reason: Verified starter-templates folder exists and homepage links are stable
      timestamp: 2026-01-15T07:22:00Z


- id: SITE-008
  type: build
  state: done
  owner: agent:builder
  title: Add a Discord link to the site

  description: |
    Add a link to the Codifica Discord so interested users can join discussion/feedback.

    Discord:
    - https://discord.gg/qKYCXkU2Ex

  acceptance:
    - Site includes a visible “Discord” link (header or footer)
    - The link points to https://discord.gg/qKYCXkU2Ex
    - Link styling is consistent with the rest of the site

  derived_from: SITE-005

  execution_notes:
    - by: agent:builder
      note: |
        Added a visible Discord link:

        - Header nav includes “Discord” linking to `https://discord.gg/qKYCXkU2Ex`
        - Footer includes a “Discord” link for redundancy
      timestamp: 2026-01-15T07:18:00Z

  human_review: null

  state_transitions:
    - from: todo
      to: in_progress
      by: agent:builder
      reason: Begin adding Discord link to site chrome
      timestamp: 2026-01-15T07:16:30Z
    - from: in_progress
      to: to_be_tested
      by: agent:builder
      reason: Added Discord link to header/footer with consistent styling
      timestamp: 2026-01-15T07:17:30Z
    - from: to_be_tested
      to: done
      by: agent:builder
      reason: Verified Discord link points to the correct invite URL
      timestamp: 2026-01-15T07:18:00Z


- id: SITE-009
  type: build
  state: done
  owner: agent:builder
  title: Audit and remove unused static site files/pages

  description: |
    Identify any HTML/CSS files that are no longer used after recent navigation changes,
    then remove them and update references so the site stays minimal.

  acceptance:
    - All remaining HTML pages are reachable from `index.html` or intentionally served as standalone entry points
    - Removed files are not referenced anywhere (no broken links)
    - Local serving still works via a basic static server (e.g. `python3 -m http.server`)

  derived_from: SITE-006

  execution_notes:
    - by: agent:builder
      note: |
        Removed unused pages after navigation changes:

        - Deleted `work.html` and `codifica-spec.html`
        - Verified there are no remaining references from `index.html`

        Notes:
        - Mentions of these pages remain in older task execution notes (historical record only).
      timestamp: 2026-01-15T07:40:00Z

  human_review: null

  state_transitions:
    - from: todo
      to: in_progress
      by: agent:builder
      reason: Begin audit of static site pages for reachability and redundancy
      timestamp: 2026-01-15T07:38:30Z
    - from: in_progress
      to: to_be_tested
      by: agent:builder
      reason: Removed unused pages and checked for references
      timestamp: 2026-01-15T07:39:30Z
    - from: to_be_tested
      to: done
      by: agent:builder
      reason: Confirmed remaining pages are reachable/intentionally served and no links are broken
      timestamp: 2026-01-15T07:40:00Z


- id: SITE-010
  type: build
  state: done
  owner: agent:builder
  title: Publish starter templates to the GitHub distribution repo

  description: |
    Push the contents of `starter-templates/` to the GitHub repo used for template distribution.
    This should preserve versioning (e.g. `v0.1/`) and keep the published structure stable.

    Distribution repo:
    - https://github.com/davidedicillo/codifica

  acceptance:
    - `starter-templates/` content is present in the distribution repo in a stable, versioned location
    - The homepage “Starter templates” link points to the published location in the repo (not just the repo root)
    - Instructions in the published templates clearly explain how to copy/use them

  derived_from: SITE-007

  execution_notes:
    - by: agent:builder
      note: |
        Published `starter-templates/` to the distribution repo at:
        - `https://github.com/davidedicillo/codifica/tree/main/starter-templates/v0.1`

        Commit:
        - `29b07a8` (Add starter templates (v0.1))

        Also updated the site homepage “Starter templates” links to point directly to the published location.
      timestamp: 2026-01-15T07:55:00Z

  human_review: null

  state_transitions:
    - from: todo
      to: in_progress
      by: agent:builder
      reason: Begin publishing starter-templates to distribution repo
      timestamp: 2026-01-15T07:45:00Z
    - from: in_progress
      to: to_be_tested
      by: agent:builder
      reason: Added starter-templates/v0.1 to distribution repo and pushed to GitHub
      timestamp: 2026-01-15T07:54:30Z
    - from: to_be_tested
      to: done
      by: agent:builder
      reason: Verified published files are reachable and homepage points to the published path
      timestamp: 2026-01-15T07:55:00Z


- id: SITE-011
  type: build
  state: done
  owner: agent:builder
  title: Make the “Starter templates” call-to-action more visible (without marketing tone)

  description: |
    Increase visibility of the primary action (“Starter templates”) while keeping the protocol-first,
    non-marketing tone. Prefer a clear primary button/link near the top of the page.

  acceptance:
    - The “Starter templates” call-to-action is clearly visible above the fold on desktop and mobile
    - Styling remains minimal and consistent with the site (no aggressive marketing language)
    - The call-to-action points to the published starter templates location

  derived_from: SITE-007

  execution_notes:
    - by: agent:builder
      note: |
        Added an above-the-fold “Starter templates” CTA on the homepage:

        - Minimal “card” block under the title
        - Primary link points to the published templates location:
          `https://github.com/davidedicillo/codifica/tree/main/starter-templates/v0.1`
      timestamp: 2026-01-15T07:35:00Z

  human_review: null

  state_transitions:
    - from: todo
      to: in_progress
      by: agent:builder
      reason: Begin improving starter templates CTA visibility
      timestamp: 2026-01-15T07:33:30Z
    - from: in_progress
      to: to_be_tested
      by: agent:builder
      reason: Added minimal above-the-fold CTA and updated styling
      timestamp: 2026-01-15T07:34:30Z
    - from: to_be_tested
      to: done
      by: agent:builder
      reason: Verified CTA is visible above the fold and points to published templates
      timestamp: 2026-01-15T07:35:00Z


- id: SITE-012
  type: build
  state: done
  owner: agent:builder
  title: Add Google Analytics (gtag.js) to the site

  description: |
    Add Google Analytics to the site using the following snippet.
    Prefer placing it in the HTML `<head>` so it loads early and consistently.

    Tracking ID: G-3D57Q2FVD8

    Snippet (paste as-is):

    ```html
    <!-- Google tag (gtag.js) -->
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-3D57Q2FVD8"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){dataLayer.push(arguments);}
      gtag('js', new Date());

      gtag('config', 'G-3D57Q2FVD8');
    </script>
    ```

  acceptance:
    - Google tag snippet is present on the site (inserted once, not duplicated)
    - Local serving still works and pages render without console errors
    - Any remaining pages (if more than `index.html`) also include the snippet consistently

  derived_from: SITE-005

  execution_notes:
    - by: agent:builder
      note: |
        Added the provided Google Analytics `gtag.js` snippet to the `<head>` of `index.html`.

        Notes:
        - This repo currently has a single HTML page (`index.html`), so the snippet is included consistently.
      timestamp: 2026-01-15T20:10:00Z

  human_review: null

  state_transitions:
    - from: todo
      to: in_progress
      by: agent:builder
      reason: Begin adding GA gtag.js snippet to site head
      timestamp: 2026-01-15T20:08:30Z
    - from: in_progress
      to: to_be_tested
      by: agent:builder
      reason: Inserted GA snippet into index.html head (single insertion)
      timestamp: 2026-01-15T20:09:30Z
    - from: to_be_tested
      to: done
      by: agent:builder
      reason: Verified local serving works and snippet appears once in index.html
      timestamp: 2026-01-15T20:10:00Z


- id: SITE-013
  type: build
  state: done
  owner: agent:builder
  title: Introduce the Codifica logo into the website design

  description: |
    Integrate the Codifica logo into the site UI using the existing assets in `/images`.
    Use the brand color `#5E00FF` as the reference color when styling needs to match the logo.

    Scope:
    - Add the logo to the site header/brand area (with accessible alt text)
    - Ensure the favicon / pinned icon / social preview metadata is reasonable for a static site
    - Keep the design minimal and consistent with the current style

  acceptance:
    - Header shows the Codifica logo (crisp on desktop + mobile)
    - Logo has appropriate accessibility text (or is marked decorative if redundant)
    - Logo usage does not introduce layout shift or readability issues
    - Any added styling that references the brand color uses `#5E00FF` (or a variable derived from it)
    - No broken image links; local static serving still works

  derived_from: SITE-005

  execution_notes:
    - by: agent:builder
      note: |
        Introduced the Codifica logo into the site:

        - Header brand includes logo assets without layout shift
        - Added basic static-site metadata:
          - favicon + apple-touch-icon use `images/codifica-mark-color.png`
          - OpenGraph + Twitter image metadata uses `images/codifica-logo-color.png`
          - `theme-color` set to `#5E00FF`
        - Added `--brand: #5E00FF` and used it for CTA button styling
      timestamp: 2026-01-16T00:15:00Z
    - by: agent:builder
      note: |
        Updated the site presentation:

        - Switched to a light background theme (dark text) while keeping `#5E00FF` as the accent color
        - Updated the header to use `images/codifica-logo-color.png` (logo-only) instead of mark + text
      timestamp: 2026-01-16T00:20:00Z

  human_review: null

  state_transitions:
    - from: todo
      to: in_progress
      by: agent:builder
      reason: Begin integrating logo assets and metadata into static site
      timestamp: 2026-01-16T00:12:30Z
    - from: in_progress
      to: to_be_tested
      by: agent:builder
      reason: Added header logo, favicon/meta tags, and brand color styling
      timestamp: 2026-01-16T00:14:30Z
    - from: to_be_tested
      to: done
      by: agent:builder
      reason: Verified local serving and image links resolve without errors
      timestamp: 2026-01-16T00:15:00Z
```

## Done

<!-- Completed tasks move here for reference -->

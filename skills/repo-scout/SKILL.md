---
name: repo-scout
description: >
  Rapid situational awareness for an unfamiliar codebase. Produces a structured ~4-page
  report with Mermaid diagrams covering topology, stack, entry points, a golden-path trace,
  architecture, data model, trust boundaries, and risk hotspots. Trigger on "scout this
  repo", "codebase overview", "give me the lay of the land", "onboard me to this codebase",
  or broad orientation questions about a repo the user has just opened.
---

# Repo Scout

Rapid situational awareness for an experienced developer sitting down cold with an
unfamiliar codebase. The report forms the trunk of a knowledge tree — enough to orient,
ask good questions, and know where to dig deeper. Not a deep review or audit; a fast,
consumable structural analysis.

## When To Use This

A fast structural overview when sitting down cold with a codebase: onboarding to a new
team, prepping for a pair-coding interview, reviewing a project for the first time, or
technical due diligence.

Beyond the trigger phrases in the description, this also fits broad orientation questions
asked against a freshly opened repo, such as "where do I start", "how is this organized",
"what am I looking at", "walk me through this repo", or a request for a code tour.

Not a deep review or audit. For semantic questions about specific behaviour, use
semi-formal-code-reasoning instead.

## Arguments

- **repo path** (required) — the repository root to analyze. Defaults to the current
  working directory if not specified.
- **--sections** (optional) — comma-separated list of section names to analyze. Runs all
  sections if omitted.

### Section names

| Phase | Sections |
|-------|----------|
| 1. Orient | `topology`, `stack`, `vocabulary` |
| 2. Trace | `entry-points`, `golden-path`, `deploy` |
| 3. Map | `architecture`, `data-model`, `conventions` |
| 4. Assess | `trust-boundaries`, `dragons`, `observability` |

Example: `--sections topology,golden-path,trust-boundaries`

## How It Works

The report is built in four phases. Each phase spawns up to three parallel haiku
subagents to investigate the codebase, then the main thread synthesizes their raw
findings into polished prose with Mermaid diagrams. This two-stage pattern keeps the
report tight and cross-referenced: subagents do cheap mechanical exploration, the main
thread does the thinking.

Each section targets ~1/3 page of output (~10-15 lines of prose, or a compact
diagram/table with a few lines of commentary). Each phase fills roughly one page.
The whole report should be ~4-5 pages including diagrams.

## Execution

### Step 1: Setup

1. Resolve the repo path (default: current working directory). Verify it exists.
2. Detect the OS: use `uname` to determine `xdg-open` (Linux) vs `open` (macOS).
3. Parse `--sections` if provided. Map each section name to its phase.
4. Read `references/investigation-briefs.md` from this skill's directory.

### Step 2: Run phases

For each phase (1 through 4), skip if no sections from this phase were requested:

**Spawn investigations.** For each section in the phase, spawn a haiku subagent in
a single message (so they run in parallel):

```
Agent({
  model: "haiku",
  subagent_type: "Explore",
  description: "<section-name> investigation",
  prompt: "<the section's brief from investigation-briefs.md, with REPO_PATH
           replaced with the actual repo path>"
})
```

All three subagents for a phase go in one message. They return raw findings with
file:line citations — no polished prose, no opinions.

**Synthesize.** When all subagents return, write the phase's sections using the
synthesis principles below. Each section is ~1/3 page. Add Mermaid diagrams where
the briefs indicate (golden-path, deploy, architecture, data-model).

Keep a running list of "loose threads" — things that surfaced during investigation
that don't fit the current section but might matter in Next Steps.

### Step 3: Write the closing

After all phases, write a "Next Steps" section (~1/2 page):
- Branches worth exploring deeper (module dependency graph, compliance surface,
  state lifecycle, config surface, user journey map)
- Questions to ask team members that the code can't answer
- Connections between sections ("the dragons-map hotspot in `auth/` aligns with
  thin trust-boundary coverage there")
- Anything from the loose-threads list that's worth flagging

### Step 4: Assemble and render

1. Assemble the full report using the template below. The topology investigation
   from Phase 1 provides the stats for the header (file count, LOC, primary language).
2. Write the report **outside the scouted repo's tree**, so it can never be committed there:
   ```bash
   out="${XDG_DATA_HOME:-$HOME/.local/share}/repo-scout/<repo-name>"
   mkdir -p "$out"   # then write "$out/REPO-SCOUT.md"
   ```
   If the user asks for the report inside the repo, add `REPO-SCOUT.*` to the repo's
   `.git/info/exclude` first.
3. Render to HTML:
   ```bash
   python3 <this-skill-directory>/scripts/render_html.py \
     "$out/REPO-SCOUT.md" "$out/REPO-SCOUT.html"
   ```
   The page loads its scripts from a CDN at exact, hash-pinned versions. If they look stale
   (more than about six months old), say so at the end; the upgrade process is in
   `references/upgrading-cdn-pins.md`.
4. Open in the system browser and tell the user where the files are:
   ```bash
   xdg-open "$out/REPO-SCOUT.html"   # Linux
   open "$out/REPO-SCOUT.html"        # macOS
   ```

## Synthesis Principles

These guide how you write each section from raw subagent findings. They exist because
the difference between a useful report and a forgettable one is editorial judgment, and
that's the main thread's job.

**Budget-bounded.** Each section targets ~1/3 page. If findings overflow, that's a
signal — say so ("23 entry points found; 8 most central shown, rest in `src/routes/`")
rather than cramming. Overflow is information about the codebase's complexity.

**File:line receipts.** Every claim cites a location (`src/api/routes.ts:42`). The
reader should be able to jump straight to evidence. A claim without a citation is a
guess — omit it or flag it as uncertain.

**Silent on the boring.** If something is standard and unsurprising ("uses npm"),
say "standard" and move on. The value is in what's unexpected, unusual, or would
trip up a newcomer.

**Inferred, not invented.** Extract facts from the actual code. Never describe what a
framework "typically" does. If the subagent didn't find evidence, say "not found" —
that's more useful than speculation.

**Composable.** Sections reference each other: the golden-path trace might note a trust
boundary from Phase 4, the architecture sketch should be consistent with entry points.
Cross-references turn 12 paragraphs into a connected map.

**Mermaid diagrams.** Use `sequenceDiagram` for golden-path, `graph LR` for deploy
pipeline, `graph TD` for architecture, `erDiagram` for data model. Keep diagrams to
5-12 nodes — a 30-node diagram is worse than prose. Diagrams complement text; they
don't replace it.

**Validate diagrams (optional).** This step runs only if mermaid-cli is already installed
locally at a pinned version: `mmdc` on the `PATH`, or `pnpm exec mmdc` / `npm exec --no-install
mmdc` in a project that pins `@mermaid-js/mermaid-cli`. Never install it on the fly (no `npx`,
no `@latest`); if it is not installed, skip validation and say so in your reply. To validate,
write each mermaid block to a temp `.mmd` file and render it:
```bash
mmdc -i "$tmp/check.mmd" -o "$tmp/check.svg" 2>&1
```
A syntax error fails the render. Whether or not you can validate, avoid the common mistakes:
unquoted labels containing special characters (parentheses, brackets, colons, commas), so wrap
them in double quotes; missing arrow syntax; colons in node labels (use `["label: text"]`
syntax). Fix any diagram that fails and re-check before writing REPO-SCOUT.md.

## Report Template

```markdown
# Repo Scout — <repo-name>

> Generated <date> · <total-files> files · <total-loc> LOC · Primary: <language>
> Sections: <all | list of requested sections>

---

## Phase 1: Orient

### Topology
<annotated directory tree, shape description>

### Tech Stack
<categorized tech with versions, unusual choices flagged>

### Domain Vocabulary
<definition list: term — definition (source file:line)>

---

## Phase 2: Trace

### Entry Points
<table: Type | Name | File:Line | Brief>

### Golden Path
<mermaid sequenceDiagram + narrated hops with file:line>

### Deploy Pipeline
<mermaid graph LR + stage descriptions>

---

## Phase 3: Map

### Architecture
<mermaid graph TD + component descriptions>

### Data Model
<mermaid erDiagram + entity descriptions>

### Code Conventions
<categorized patterns with file:line examples>

---

## Phase 4: Assess

### Trust Boundaries
<boundary list with type, location, gaps>

### Dragons
<hotspot list: type, file:line, evidence, severity>

### Observability
<instrumentation inventory, coverage, gaps>

---

## Next Steps
<deeper investigations, questions for team, cross-section connections, loose threads>
```

## Edge Cases

- **Enormous repos (>100k LOC):** Subagents sample rather than exhaustively scan.
  The briefs include file limits (head -2000, first 100 lines, sample 5-10 files).
- **Subagent failure:** Note the gap ("*Section skipped — investigation timed out*")
  and continue. A partial report is still useful.
- **No git history:** Dragons-map skips churn analysis and relies on code markers and
  complexity signals.
- **Small repos (<10 files):** Short report is correct. Don't pad.
- **Non-code repos (docs, data):** The report will be sparse. Note this in the header
  and focus on what's there (directory structure, any scripts, config).

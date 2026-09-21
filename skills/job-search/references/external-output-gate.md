# External Output Gate

Every word a hiring organization reads passes through this gate before Jack sees it as
"ready". Two separate responsibilities, two separate agents, in a fixed order.

## What counts as externally-facing

Cover letters, application essay/short answers, referral and outreach messages, recruiter
replies, follow-up and thank-you notes, LinkedIn connection notes, and any resume bullet
that changed in this session.

Internal artifacts (`job-posting.md`, `glassdoor.md`, `company-research.md`, tracker
notes, strategy docs) do not go through the gate.

**Scope test: does the text make claims about Jack's record** (numbers, titles, dates, scope,
what he did or built)? If yes, it is gated, whatever its length. If no, it is outside the gate:
a short courtesy note whose whole content is thanks, continued interest, and logistics that
restate the thread (an acknowledgment of "we'll restart in Q4", a scheduling reply) gets
`check_claims.sh` if it is saved to a file and is then handed to Jack, who edits it himself. No
fact-check agent, no slop agent. When it is unclear whether a sentence is a claim about his
record, it is. (Added 2026-09-21, after a fact-check agent was spawned on a 53-word
acknowledgment.)

## Order of operations

Facts settle first, prose second, machine check last.

1. **Draft** on the main thread (Opus). Judgment work: what to claim, which narrative
   leads, how a weak spot is handled honestly. Write it properly; do not assemble it out of
   `facts.md`. Look up the *particulars* there (numbers, titles, dates, scope) rather than
   recalling them, and let the argument be your own. **Draft in Jack's voice from the first
   line** (`strategy/voice-profile.md`), not in generic cover-letter register to be fixed
   later. The slop pass is a backstop, not the place voice is supposed to arrive; a draft that
   starts in his voice needs far less rescue.
2. **Fact check** — `sonnet` subagent, read-only, protocol below. Runs on the *raw* draft.
3. **Reconcile** on the main thread. Apply the fixes yourself.
4. **Slop pass** — `sonnet` subagent running `no-ai-slop` in Edit mode.
5. **Mechanical re-check** — `scripts/check_claims.sh <file>`. Deterministic, no tokens.
   Catches drift the slop pass introduced and banned strings anywhere in the corpus.
6. **Render / present.** PDF, or a paste-ready block for Jack.

Why facts before polish: the County CIO letter took six revision passes, and the two
factual corrections (wrong Kantata title, inflated platform scope) landed *after* four
tone and length passes. Every editorial pass spent on a sentence that later has to change
its claim is wasted, and a polished sentence is harder to notice as wrong.

Never render a PDF or tell Jack a draft is ready before steps 2, 4, and 5 have all run. If
Jack edits a draft afterward and asks for a re-render, run step 5; do not re-run the slop
pass on his own edits, since his wording is the target, not the input.

## Propagation

A corrected fact is not fixed until it is fixed everywhere. When any claim changes, in a
letter or in `facts.md` or in the resume:

1. Update `strategy/claim-guards.txt` so the wrong version is a banned string.
2. Run `scripts/check_claims.sh --all` across both repos.
3. Fix every hit, including drafts, skeletons, research notes, and already-tailored resume
   branches. Stale internal notes that assert the old version are bugs.

The inflated "served every department" claim was caught and fixed independently in two
places on the same day while three other copies survived untouched in draft and research
files. One correction, one sweep.

## Slop pass (step 4)

Spawn a `sonnet` agent with the `no-ai-slop` skill, Edit mode. Hand it:

- the draft verbatim,
- audience and format ("a hiring manager at <company>, one-page cover letter PDF"),
- **`~/workspace/jobs/strategy/voice-profile.md` as the voice target.** This is the positive
  reference: not just "remove AI patterns" but "sound like *this*". The slop skill preserves
  the writer's voice; the profile makes that concrete. Tell it to match the register the
  profile assigns to this artifact (cover letters: warm-professional with a touch of
  conviction) and to use Jack's real moves (the honest-limits move, concrete grounding, genuine
  hedges kept) while cutting the tells the profile names. No em dashes or en dashes, ever.
- an explicit instruction: **do not add, sharpen, or quantify any claim.** It may cut and
  it may rephrase, but a number, title, date, or scope statement that was not in the
  draft must not appear in the edit.

Take back the edited draft and the "What changed" list. Read the list; if it shows a claim
being strengthened rather than clarified, revert that line before moving on.

## Fact check (step 2)

A separate agent with one job: decide whether each claim in the draft is true and
supported. It reports, it does not rewrite. Rewriting is what lets a checker launder its
own guesses into the text.

### Corpus, in priority order

| Tier | Source | Authority |
|---|---|---|
| 1 | `~/workspace/resume/resume.md` on `main` | Employment history, titles, dates. Wins all conflicts. |
| 1 | `~/workspace/jobs/strategy/facts.md` | Canonical atomic facts and negative guardrails. |
| 1 | `~/workspace/jobs/strategy/narrative.md` | Project stories, values, framing constraints. |
| voice | `~/workspace/jobs/strategy/voice-profile.md` | How Jack writes. The slop pass targets this; the fact check ignores it (voice is not a fact). |
| 2 | `~/workspace/jacksenechal.com/` | Jack's public site. Public, so citable, and claims must not contradict it. |
| 2 | `~/workspace/jobs/profile.md` | Logistics: location, work authorization, links. |
| 3 | `applications/<id>/*.md` for this job | Claims about the *company*. Only counts if it carries a `SOURCES:` URL. |

Anything not in the corpus is unverified. Absence is not permission.

### Verdicts

- `SUPPORTED` — quote the supporting line and name its file.
- `CONTRADICTED` — the corpus says something different. Quote both.
- `OVERSTATED` — a true kernel, inflated. Scope creep, a rounded-up number, "led" where
  the source says "contributed to". Give the accurate version.
- `UNSUPPORTED` — plausible, but nothing in the corpus says it. Say what would be needed.
- `GUARDRAIL` — the draft breaks an explicit "do NOT claim" line in `facts.md`. Highest
  severity, always blocking.
- `COMPANY-UNSOURCED` — a claim about the employer with no `SOURCES:` URL behind it.

### Output shape

A table: claim (quoted verbatim from the draft) | verdict | evidence | suggested fix.
Then a one-line bottom line: `CLEAR` or `N blocking issues`. Nothing else. No praise, no
summary of the letter, no rewrite.

`GUARDRAIL`, `CONTRADICTED`, and `COMPANY-UNSOURCED` are blocking. `OVERSTATED` and
`UNSUPPORTED` are blocking unless Jack has explicitly approved the claim in this session.

### Standing checks

Run these every time, independent of what the draft says:

- Every employer title verbatim against `resume.md`. Kantata is **Principal Engineer +
  Engineering Manager**, never Director.
- Every number in the draft appears in the corpus with the same units and the same
  referent. A number that measures a different thing than the source measures is
  `OVERSTATED`, not `SUPPORTED`.
- Every hands-on technical claim checked against the hands-on vs. led vs. adjacent
  distinction in `facts.md`.
- No em dashes or en dashes.
- Company name, role title, and hiring manager name spelled as the posting spells them.
- Nothing claimed about the company that isn't traceable to a research doc with sources.

### Persistence

Append the verdict table to `applications/<id>/fact-check.md` under a dated heading naming
the artifact checked. It is the audit trail, and the next draft for the same job starts
from a list of claims already cleared.

## Where errors actually come from, and what each layer does

The failure is re-derivation of *particulars*. A draft that rebuilds a number, a title, a
date or a scope statement from memory over 400 lines of narrative gets it slightly wrong,
and the drift is invisible because each version is individually plausible.

Note what that does and does not cover. It is a claim about facts, not about arguments.

- **`facts.md` settles particulars.** Numbers, titles, dates, employers, scope, and the
  "do NOT claim" guardrails. Look them up rather than recalling them. It is a reference,
  **not a menu to draft from**: a letter assembled by picking lines off a fact sheet reads
  like it was assembled by picking lines off a fact sheet. What to argue, which story
  leads, what matters to this employer, and how the whole thing sounds are the writer's,
  and nothing here constrains them.
- **The fact-check agent catches what's novel.** Constrain validation, not generation.
  That ordering is the whole point: a drafter writing under a sourcing rule produces flat,
  safe prose, while a drafter writing freely against a real check produces prose with a
  voice and accurate facts. Its question is narrow and checkable: does each particular
  trace to the corpus? Not "is this good", and not "is this accurate" in the abstract.
- **`claim-guards.txt` stops recurrence.** A regression test, nothing more. It can only
  catch a claim that has already been wrong once, so it can never be the mechanism for
  factuality. Keep it short. Guard the wrong claim, never a bare general term.

When `facts.md` is missing a particular a draft needs, add it there with its source rather
than letting the draft assert it unchecked. Growing the reference is the point. Growing it
into a style guide is not.

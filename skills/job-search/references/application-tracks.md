# Application Tracks

Not every application deserves the same spend. The evidence is in the repo: one letter
took six revision passes, while two others went out as first drafts with none.
Averaging that spend across everything is what makes a day produce one application instead
of several.

So the decision gets made once, at the front, instead of implicitly and repeatedly inside
the work.

## The two tracks

**Fast.** The role is close to something already understood, and the judgment calls are
routine. The pipeline runs unattended to `ready_to_apply` and the user sees it only at review.
Target: minutes of their attention, several in a day.

**Deep.** The user's judgment is the actual product. The pipeline's job is to prepare *their*
thinking rather than substitute for it: gather more, structure the open questions, and
stop early enough that their direction still shapes the work.

The mistake is treating Deep as "Fast plus more research". The difference is who decides.

## Routing

Decided at `add` time, written to the `track` column, changeable by the user at any point. `lane`
(who submits: the user or the pipeline, `strategy/auto-apply.md`) is a separate axis set right
after, in the same `add` step — `track=deep` forces `lane=personal`, but a `fast` row can land
in either lane.

This was calibrated: nine completed applications were scored blind on the dimensions below,
then checked against what their revisions actually fought. Two findings reshaped the rule.

**Coherence verdict does not route the track. At all.** They are orthogonal axes. Coherence
answers "do I want to work here, and at what price"; the track answers "how much of my own
judgment does applying well require". A `Price` company can have a trivial application and an
`Advance` company a brutal one. Route on the dimensions, never on the verdict. (An earlier
version of this file routed `Price` to deep and `Advance` to fast; the calibration falsified
both.)

**Two dimensions do the routing, and they are the two only the user can supply.** Any **high** on
either sends it deep:

- **Position formation** — must the user hold and state a genuine specific view (on the company's
  mission, technical philosophy, published work), not describe experience? This was the dominant
  cost in the calibration set; it is irreducibly theirs.
- **Pre-application homework** — does writing credibly require the user to read and synthesize their
  material first (published research, a product deep-dive, a regulatory landscape)? High in seven
  of the nine. Detectable at add time from the posting and the size of `company-research.md`, so
  the pipeline can flag "this needs the user's reading" before a letter ever stalls.

**Two more are real but mostly mechanical.** They push toward deep but rarely decide it alone:

- **Archetype distance** — no close `role/` archetype, so the resume needs re-framing not
  tailoring (e.g. an unfamiliar industry stack, or a pure IC role against leadership archetypes).
- **Process complexity** — gated ATS, guessed-blind screening questions, panel scoring, a named
  deadline, a recruiter intermediary.

**Novelty is a batching signal, not a router.** It was low almost everywhere, because the user has a
strong template bank. It tells you what to reuse, not how much judgment a row needs. Keep it out
of the routing decision; use it in Batching below.

So: **deep if position or homework is high, or if archetype and process are both elevated.**
Otherwise fast. When genuinely ambiguous, take fast: a fast application the user invests in at review
is cheap; a deep one they did not need cost hours before they saw it.

### Do not use revision count as a cost signal

The calibration killed it. Revision count is not weak, it is **inverted**: two of the
highest-cost applications (high homework, high position, resume re-framing) that have
exactly one revision each, because the expensive judgment landed in the first draft or upstream
in research and never showed as churn. Meanwhile the most-revised letter's 13 revisions were mostly one-page
compression and argument tightening, much of it agent-work. Cost is front-loaded into the first
pass; the diff cannot see it. Score the dimensions from the posting and research, never from how
many times a letter was touched.

### Factual churn is not a track cost

Five of the nine letters spent their largest revision bucket on one thing: the user's own career
story getting cross-wired (two similar projects at one employer conflated). That is not a property of any
target company and does not belong in the track rating. It is a `facts.md` problem, now fixed by
a disambiguating note there. If a row's cost looks high only because of
own-narrative churn, that is a signal to fix `facts.md`, not to route deep.

## What each track runs

| Stage | Fast | Deep |
|---|---|---|
| Posting scrape, geo filter, coherence read | yes | yes |
| Company research | one pass, enough to write honestly | parallel multi-angle, Glassdoor, negative-tail themes |
| Resume | tailor from nearest archetype | revisit the framing, not just the bullets |
| `brief.md` | 5 lines | one page |
| Cover letter | only if `application-form.md` shows a slot or the application goes to a person; otherwise outline only | same rule, and drafted after the user has seen the brief |
| Connections / outreach | reads `strategy/networking/people.md` for an existing warm contact, copies it into `referral_contact` if present; no per-application search | same |
| Interview prep | not yet | seeded |
| Stops at | `ready_to_apply` | The user's direction, usually after `brief.md` |

Both tracks pass the External Output Gate. Speed never comes out of accuracy.

## `brief.md`

The decision object for the employer side, at `applications/<id>/brief.md`. It exists
because research currently lands as four documents ending in "Takeaways for Application",
which is advice, not a decision, so the user has to read all of it and do the synthesis
themselves. That reading is a real cost and it is structural, not unavoidable.

One page. If it runs longer, it has stopped being a brief.

```markdown
# Brief — <Company> <Role>

- **Track**: fast | deep
- **What**: <one line: what this seat is, in their terms>
- **Read**: <the pipeline's own read, stated rather than leaked: one sentence on the company (will decisions here track reality, would this seat be heard); one clause on the seat (step up / lateral / step down; wanted or dutiful)>
- **Ground**: <firm / thin / hollow, and what would settle it>

## What they're hiring for
<2-3 lines, in their words where possible. The real job behind the posting, including
anything the posting implies but does not say.>

## The case
<Three claims, one line each. What we would argue and why it lands for this employer.>

## The gap
<The honest weak spot, and how the application handles it. Not hidden, not apologized for.>

## Needs you
<Only things the user alone can answer. Delete the section if there are none, and say so
rather than manufacturing questions.>

## Recommendation
<One line: proceed, proceed with a caveat, or drop, and why.>
```

The Fast-track version is the `What`, `Read`, `Ground`, `The case`, and `Recommendation` lines only. The tracker artifact reads `Read` and `Ground` from every live brief and shows them at the top of the page; a brief without a `Ground` line shows as "no read yet".

Write the brief *before* the cover letter on the Deep track. It is the thing the user reacts
to, and reacting to one page is far cheaper for them than reacting to a finished letter that
argued the wrong thing.

## Batching

The expensive thinking is per-archetype, not per-company: three EM roles share most of their
case, and the résumé positioning and the proof points carry over. When several Fast-track
applications of the same archetype are queued, work the archetype once and reuse it.

The letter is the exception. Its opening and its argument are per-employer, because a letter
that opens the same way for three companies has stopped saying anything to any of them. Reuse
a paragraph when it proves a claim this letter is making; write the opening fresh from the
brief every time.

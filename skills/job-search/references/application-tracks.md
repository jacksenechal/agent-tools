# Application Tracks

Not every application deserves the same spend. The evidence is in the repo: the County CIO
letter took six revision passes, while Sonic and SVH went out as first drafts with none.
Averaging that spend across everything is what makes a day produce one application instead
of several.

So the decision gets made once, at the front, instead of implicitly and repeatedly inside
the work.

## The two tracks

**Fast.** The role is close to something already understood, and the judgment calls are
routine. The pipeline runs unattended to `ready_to_apply` and Jack sees it only at review.
Target: minutes of his attention, several in a day.

**Deep.** Jack's judgment is the actual product. The pipeline's job is to prepare *his*
thinking rather than substitute for it: gather more, structure the open questions, and
stop early enough that his direction still shapes the work.

The mistake is treating Deep as "Fast plus more research". The difference is who decides.

## Routing

Decided at `add` time, written to the `track` column, changeable by Jack at any point.

Take **Deep** if any of these hold:

- `coh_verdict` is `Price` or `Unknown` (the seat shape is a live question)
- no close `role/` archetype exists, so the resume needs real rethinking rather than tailoring
- public sector, hospital, or any process with its own rules (supplemental questions,
  panel scoring, a named deadline, a recruiter intermediary)
- the posting asks essay questions that need a position rather than a description
- the company matters to Jack beyond this specific role

Otherwise take **Fast**: `Advance` verdict, a close archetype, a standard ATS
(Greenhouse, Lever, Ashby), no essays beyond the usual.

When it is genuinely ambiguous, take Fast. A Fast application Jack decides to invest in on
review is cheap; a Deep one he did not need cost hours before he ever saw it.

## What each track runs

| Stage | Fast | Deep |
|---|---|---|
| Posting scrape, geo filter, coherence read | yes | yes |
| Company research | one pass, enough to write honestly | parallel multi-angle, Glassdoor, negative-tail themes |
| Resume | tailor from nearest archetype | revisit the framing, not just the bullets |
| `brief.md` | 5 lines | one page |
| Cover letter | if wanted, drafted and gated | drafted after Jack has seen the brief |
| Connections / outreach | only if a 1st-degree contact already exists | full search and outreach strategy |
| Interview prep | not yet | seeded |
| Stops at | `ready_to_apply` | Jack's direction, usually after `brief.md` |

Both tracks pass the External Output Gate. Speed never comes out of accuracy.

## `brief.md`

The decision object for the employer side, at `applications/<id>/brief.md`. It exists
because research currently lands as four documents ending in "Takeaways for Application",
which is advice, not a decision, so Jack has to read all of it and do the synthesis
himself. That reading is a real cost and it is structural, not unavoidable.

One page. If it runs longer, it has stopped being a brief.

```markdown
# Brief — <Company> <Role>

**Track**: fast | deep
**Read**: <one line: what this application is actually about>

## What they're hiring for
<2-3 lines, in their words where possible. The real job behind the posting, including
anything the posting implies but does not say.>

## The case
<Three claims, one line each. What we would argue and why it lands for this employer.>

## The gap
<The honest weak spot, and how the application handles it. Not hidden, not apologized for.>

## Needs Jack
<Only things Jack alone can answer. Delete the section if there are none, and say so
rather than manufacturing questions.>

## Recommendation
<One line: proceed, proceed with a caveat, or drop, and why.>
```

The Fast-track version is the `Read`, `The case`, and `Recommendation` lines only.

Write the brief *before* the cover letter on the Deep track. It is the thing Jack reacts
to, and reacting to one page is far cheaper for him than reacting to a finished letter that
argued the wrong thing.

## Batching

The expensive thinking is per-archetype, not per-company. Three EM roles share nearly their
whole case; only the challenge and the company specifics change. When several Fast-track
applications of the same archetype are queued, work the archetype once and then instantiate,
rather than starting each from scratch.

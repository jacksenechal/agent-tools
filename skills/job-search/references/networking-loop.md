# Networking Loop (`network` mode)

The weekly coach + researcher + strategist run behind `~/workspace/jobs/strategy/networking/`.
Read that directory's `README.md` first: it is the framework this protocol implements. This
file is the how, the README is the why.

Invoked by `job-search-network.timer` (Mondays ~08:00) through `orchestrator.sh network`, or
by hand as `/job-search network` in a session. The same three passes run either way; in a
session, pass 1 may also ask Jack directly instead of relying only on `inbox.md`.

## Hard limits

- **Never send anything.** Drafts go into the person's thread file marked `DRAFT`. Jack sends.
- **No LinkedIn.** This mode does not open the golden browser. Research is the knowledge
  graph (`scripts/query_connections.py`), the web, the tracker, and Jack's notes.
- **Any drafted message is external output** and passes the External Output Gate
  (`references/external-output-gate.md`) before it is labeled sendable.
- **At most two touches in `this-week.md`.** If the deep-think pass wants a third, it goes in
  the journal as a candidate for next week.
- **Never change tracker stage.** The run may write `referral_contact` and `referral_status`
  on a tracker row when a real contact exists; stage is the application pipeline's.

## Pass 1: practical

1. Read `strategy/networking/inbox.md`. For each note: identify the person or org, update
   their status and `last touch` in `people.md` (and the thread file if one exists, creating
   one on the first real exchange), record what Jack said about how it went. Then empty the
   inbox back to its header. A note that names nobody goes to the journal as context.
2. Read `this-week.md` from last run. Mark each touch done / not done / partial from the
   inbox evidence. Not done is data, not a failure: carry it or drop it in pass 3.
3. Research open items. Each org file has an "Open questions" list; each brief may have left
   "to research" lines. Resolve what one web search or one KG query can resolve; write the
   answer into the org or person file with the date. Use `sonnet` subagents for lookups;
   keep the synthesis on the main thread.
4. Refresh the set. Any tracker row with `coh_verdict=Advance` and no `orgs/<slug>.md` gets
   a stub (why, people known via KG query, open questions). Any org file whose tracker rows
   are all `Pass` gets marked `left the set` at the top.
5. Refresh `events.md` next-touch dates: drop past events into the journal, flag any within
   the next 14 days.

## Pass 2: deep think

Spawn one fresh subagent on the strongest available model (Fable or Opus, high effort) with
a compact packet, not the whole repo: `networking/README.md`, `people.md`, the org files that
changed this week, the last four `journal.md` entries, this run's pass-1 summary, and the
memory `user-networking-hangup-wants-clear-direction`. Ask it to:

- name the pattern in the last month (what moved, what stalled, what Jack found easy or hard);
- propose up to three insights, each a non-obvious angle: a person two hops away, a public
  artifact that would earn a conversation, a room, a reframing of an org, a strategy that has
  gone stale and should be dropped;
- challenge the framework if the evidence warrants, explicitly;
- return one recommendation for the week and the one-sentence reason.

The subagent is read-only and reports; the main thread decides. Divergent thinking is the
point of this pass, so the prompt should ask for creativity and accept "stay the course" as
a legitimate output when the evidence says so.

## Pass 3: direction

1. Write `this-week.md` from scratch (template below). Two touches maximum, ordered, each
   doable in twenty minutes, each with its one-line reason. If Jack reported the last week
   felt hard, the first touch must be smaller than last week's.
2. Append a dated entry at the top of `journal.md`: what was folded in, what was researched,
   the insight kept (and the ones set aside, one line each), the decision. Under 15 lines.
3. Commit and push the jobs repo. Append a run line to `orchestrator.log`.
4. Rebuild and republish the tracker artifact if any tracker column changed.
5. Notify Jack (`notify-send` on the machine; the brief itself is the message).

### `this-week.md` template

```markdown
# This week (YYYY-MM-DD)

State: <one line: where the track is, in plain words>

1. **<Touch>**: <who/what, concrete enough to do today>.
   Why now: <one sentence>.
2. **<Touch>**: ...
   Why now: ...

Last week: <what got done, acknowledged first; what carried, without judgment>

Insight kept: <one or two sentences, or "stay the course">

To research next run: <optional, short>
```

## Interactive use

When Jack runs `/job-search network` himself, pass 1 starts by asking him what happened this
week (one question, open), then proceeds. Pass 2 still runs as a subagent so the deep think
is not skipped when the session feels conversational. Pass 3 ends with the brief in the
conversation as well as in the file.

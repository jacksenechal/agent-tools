# Auto-Apply Runbook

Fills and (once live) submits applications for rows Jack has approved into the `auto` lane.
Framework and lane rules: the private repo's `strategy/auto-apply.md`. This is the mechanical
procedure the `apply` mode runs.

**Mode switch**: `$JOBS_DIR/auto-apply.json` — `{"mode": "shadow"|"live"|"paused",
"daily_cap": N, "max_live_per_company": N}`. Only Jack edits this file. Read it once at the
start of the run and again before every Submit click (step h) — never cache the mode across a
long run.

## (a) Lane decisions are already synced

Headless `apply` has no `ArtifactData` tool, so it does not read the tracker artifact's
`lane_decisions` collection itself. The steward session does that sync (sync-publish cron;
`ops/steward/charter.md`, `artifact/README.md` "Lane approval") before this run starts, writing
each decision into `tracker.csv`'s `lane` column (`auto` or `personal`) and deleting the synced
docs after it republishes. This run just reads `tracker.csv` as-is — use the CSV dialect the
repo already uses: CRLF line endings, `csv.DictReader`/`DictWriter`, never raw string edits
(jobs `CLAUDE.md`, and `tracker.csv` itself — check with `file tracker.csv` or `cat -A | head -1`
if unsure).

## (b) Pick rows

Candidates: `lane == "auto"`, stage in `resume_tailored`, `application_prepped`, or
`ready_to_apply` (i.e. pre-`applied`, already past the lane decision), and no
`applications/<id>/submission/` folder yet (a row with one has already been run once — rerun by
hand, never silently).

Take up to `daily_cap` of them, oldest `date_updated` first.

**`max_live_per_company`**: count rows at the same company already submitted and still open
(stage `applied` or `interviewing`); unsubmitted rows don't count. (The tracker page's "also
live" list is wider on purpose: it's context for Jack, not the cap.) Skip a candidate that
would push the company over the cap; note on the row `auto-apply: skipped, at
max_live_per_company (<n> already live)` and move to the next candidate. Never silently drop it.

## (c) Materials

1. Tailored résumé PDF: Resume Workflow in jobs `CLAUDE.md` / SKILL.md Stage 2. If the row is
   already at `resume_tailored` or later this normally exists — verify the named file
   (`Resume - Jack Senechal - <Role>.pdf`) is actually on disk, not just that the stage says so.
2. Cover letter: only when `application-form.md` (or the live form, if that doc is stale — see
   (d)) shows a slot. Run it through the full External Output Gate (fact check → reconcile →
   `no-ai-slop` → `check_claims.sh`) before it touches the form. Same gate for any free-text
   "why us" / "how did you hear about us" answer.
3. **"Why us" / motivation answers need a real motivation or connection on record** — from
   `brief.md`, `company-research.md`, or something Jack has said. Never invent one. If none
   exists, don't write the field: hand the row to Jack (step f) with the note
   `auto-apply: needs a real "why us" answer, none on record`.

## (d) Resolve the live posting and fill the form

**Resolve fresh every run — don't trust a recorded `application_url`.** The Hightouch spike
(`applications/hightouch-em-destinations/submission/submission.md`) found the recorded
Greenhouse URL 404ing months later; the live posting had moved to an Ashby form embedded on
Hightouch's own site. Before filling:

1. Load `application_url` (or the job posting URL if that's empty). If it 404s or redirects to
   a board index, search the company's own careers page for the role and use that URL instead;
   update `job-posting.md`'s URL and ATS note when it changed.
2. Detect the ATS. If the URL is a Greenhouse board (`job-boards.greenhouse.io/<slug>/jobs/<id>`
   or similar), try `boards-api.greenhouse.io/v1/boards/<slug>/jobs/<id>?questions=true` first —
   it returns the question set directly, cheaper than reading the rendered form. If it's Ashby
   (`jobs.ashbyhq.com/...` or an embedded `iframe[title="Ashby Job Board"]` as on Hightouch),
   use the Ashby posting API if reachable, otherwise read the live form's accessibility tree —
   don't assume the API plan from a different ATS applies. Lever: read the form directly, no
   known read API in this pipeline yet.
3. **Workday is out of scope for this mode.** Hand it to Jack (step f) the moment Workday is
   detected (the "Autofill with Resume" step, or a `myworkday.com` domain) — don't attempt a
   fill. (`references/workday-playbook.md` covers Jack's own manual flow there.)
4. **Never use LinkedIn Easy Apply.** If the only application path is LinkedIn Easy Apply, hand
   the row to Jack.
5. Fill the form in the **golden** browser (`mcp__playwright-golden__*`), one row at a time —
   never two browser agents concurrently (feedback: serialize golden-browser agents). Use
   `profile.md` for every standing field (contact, work authorization, EEO, salary policy,
   name policy — the cell number, not the Google Voice one; "Jack Senechal" everywhere except an
   explicit legal-name field, which gets "John Senechal" with the preferred-name box ticked).

## (e) Screenshot and record

- Screenshot the **form or iframe element itself**, section by section — a full-page screenshot
  gets covered by sticky site headers (Hightouch spike finding). Since the repo is mounted into
  the container at the same absolute path, `browser_run_code` with
  `page.screenshot({path: "<absolute $JOBS_DIR>/applications/<id>/submission/NN-<step>.png"})`
  or a locator's `.screenshot({path})` writes directly there — no `docker cp` needed (unlike the
  spike, which predated the identical-path mount fix).
- After each file upload, **verify the filename in the snapshot**: the accessibility tree should
  show `Resume - Jack Senechal - <Role>.pdf` (or the cover letter's equivalent), not a bare
  `resume.pdf` or a browser-generated temp name. An upload that lost its proper name is a stop
  condition (step f).
- Write `applications/<id>/submission/submission.md`: every field, the value given, and its
  source (`profile.md`, the tailored résumé, the gated cover letter, `brief.md`, etc.) — same
  shape as the Hightouch spike's file. Start it with a `**SHADOW MODE**` or `**LIVE**` line per
  (h).

## (f) Stop conditions — hand the row to Jack

Any of these: stop the fill, don't touch Submit, hand the row over.

- A legal or attestation question not already answered in `profile.md`.
- The form states it bans AI-written answers.
- A login wall or account-creation step.
- An unknown required field (not in `profile.md`, not inferable from the posting).
- An upload that lost its filename (step e).
- Workday or LinkedIn Easy Apply (step d).
- No real "why us" answer on record (step c).

**To hand over**: set `lane=personal` on the row and add a dated note explaining which
condition fired and what's missing. Leave whatever partial `submission/` material was produced
(screenshots, draft `submission.md`) — it saves Jack the re-discovery.

## (g) CAPTCHA / bot check

The moment a snapshot or screenshot shows a CAPTCHA, "unusual activity," or any bot-detection
interstitial: call the **PushNotification** tool immediately — `"CAPTCHA on <Company> <Role>:
clear it in noVNC (http://localhost:6080/vnc.html)"` — don't wait to finish the current field.
If PushNotification isn't available in this run (headless runs may lack it), also run
`notify-send -u critical "job-search apply" "<same message>"` so a desktop alert still fires.
Then poll the page every ~2 minutes for about 10 minutes (a handful of snapshots, not a tight
loop) waiting for Jack to clear it. If it clears, continue the fill from where it stopped. If it
doesn't clear within the window, park the row: note `auto-apply: CAPTCHA not cleared, parked
<timestamp>`, leave lane as `auto` (it's still approved, just blocked) so the next run retries
it, and move to the next candidate.

## (h) Branch on mode

Read `auto-apply.json` again right before this step — it may have changed mid-run.

- **shadow**: stop before clicking Submit. Add the note `shadow fill complete, awaiting Jack`
  to the row. `submission.md` opens with `**SHADOW MODE: not submitted.**`
- **live**: click Submit, screenshot the confirmation page into `submission/`, set
  `stage=applied` and `date_applied=today`, note `auto-submitted`. `submission.md` opens with
  `**LIVE: submitted <date>.**`
- **paused**: do nothing — don't even open the browser for this row. (Step (b) should already
  have produced an empty candidate list if `mode` is `paused`; this is the belt-and-suspenders
  check.)

**Hard rule, no exception**: never click Submit unless `auto-apply.json` says `"mode": "live"`
at the moment of the click. Re-reading the file right before the click (not just at run start)
is what makes this actually hold across a run that takes a while.

## (i) Application limits

If the form or research surfaces an application cap or cooldown (Hightouch: 2 roles per 60
days, 120-day wait after rejection), record it on a `- **Application limits**:` line in
`job-posting.md` — don't skip the role for having one, just record it so the tracker page can
warn on a sibling role. See `strategy/auto-apply.md`, "Application limits".

## (j) Commit, push, republish

```bash
cd $JOBS_DIR
git pull --rebase
git add -A
git commit -m "Auto-apply run: <N> rows (<shadow|live>)"
```

**Stash caution**: if `git pull --rebase` needs the working tree clean and there are
in-progress edits, use `git stash push -m apply-run` before the pull and
`git stash pop $(git stash list | grep apply-run | head -1 | cut -d: -f1)` after — **never**
`git stash pop` bare. An old, unrelated stash already exists in this repo; popping blind
restores the wrong one.

```bash
git push
```

**Headless `apply` has no Artifact tool and cannot publish.** `tracker-view.html` is generated,
gitignored output, so there is nothing of it to commit here; the pushed `tracker.csv` is what
matters. The steward session picks up the new commit, rebuilds (`python3 artifact/build.py`),
and republishes to the pinned URL in `artifact/README.md` on its sync-publish cron (never
create a new artifact). Append a run line to `orchestrator.log` (same format the other modes
use).

## Summary

One screen: rows attempted, outcome per row (shadow-filled / submitted / handed to Jack with
reason / parked on CAPTCHA / skipped on company cap), and the mode the run operated under.

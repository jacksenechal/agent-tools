# Tracker CSV Schema

File: `~/workspace/jobs/tracker.csv`

## Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | yes | Slug identifier. Names the application dir `applications/<id>/` (which holds `resume.md` + `Resume - <Name> - <Role>.pdf`). E.g., `stripe-infra-eng`, `navan-ai-ex` |
| `company` | string | yes | Company name |
| `role` | string | yes | Job title |
| `url` | string | yes | LinkedIn job posting URL |
| `stage` | enum | yes | Current pipeline stage (see below) |
| `resume_branch` | string | no | Path to the tailored per-job résumé in the jobs repo, `applications/<id>/resume.md` (empty until tailored). The column name is legacy — `job/*` branches are retired and per-job tailoring no longer uses the resume repo. Old rows may still hold stale `job/<id>` values. |
| `role_branch` | string | no | The `role/*` archetype the résumé was derived from, e.g. `role/technology-executive`. These archetype branches live in the resume repo (read-only). |
| `application_url` | string | no | Direct application URL (company careers site, Greenhouse, Lever, etc.) |
| `referral_contact` | string | no | Name(s) of connection(s) identified for referral |
| `referral_status` | enum | no | `none`, `identified`, `contacted`, `replied`, `referred`, `inbound` |
| `date_found` | date | yes | ISO date when job was first added (YYYY-MM-DD) |
| `date_applied` | date | no | ISO date when application was submitted |
| `date_updated` | date | yes | ISO date of last update to this row |
| `notes` | string | no | Brief freeform notes |
| `coh_cell` | enum | no | Coherence 2x2 cell from tier-1 read: `target`, `disconnected`, `extraction`, `incoherent`, `mixed`, `unknown` (see `jobs/strategy/coherence-instrument.md`) |
| `coh_derivative` | int | no | Coherence derivative, -2 to +2 |
| `coh_verdict` | enum | no | `Advance`, `Price`, `Pass`, `Unknown` |
| `coh_date` | date | no | ISO date of the coherence read |
| `coh_tags` | string | no | Comma-separated tags naming what produced the verdict, from the controlled vocabulary in `jobs/strategy/coherence-instrument.md` ("Roll-up: level, trend, tags"): flags (`pe`, `acquired`, `founder-exit`, `exec-change`, `layoffs`, `contraction`, `decoupled`, `growth`), gaps (`ceiling 0.4`, `blind-gap`, `seams`, `channel`, `seed`), evidence (`thin`, `young`, `inside`, `tier2`). Empty is valid. The column sits last in the file. The view derives the level (`high`/`mid`/`low`/`?`) from `coh_cell`, the trend glyph from `coh_derivative`, and the shape tags `disconnected`/`incoherent` from the cell; none of those are stored |
| `track` | enum | no | `fast` or `deep`. How much attention this application gets, decided at `add` time and overridable by the user at any point. Empty means not yet routed. See `references/application-tracks.md` |

`referral_contact` and `referral_status` are written by the networking track
(`~/workspace/jobs/strategy/networking/`) when a real contact exists, not by `add`. `add`
only reads `strategy/networking/people.md` for an existing warm contact and copies it in if
present; there is no per-application connection search.

## Pipeline Stages

Ordered progression:

1. `discovered` — URL added, nothing else done
2. `researched` — Job description scraped and saved
3. `resume_tailored` — `applications/<id>/resume.md` tailored from an archetype and rendered to `Resume - <Name> - <Role>.pdf`
4. `application_prepped` — Application form reviewed, fields documented
5. `ready_to_apply` — Everything prepared, waiting for manual submission
6. `applied` — Application submitted (manual step by user)
7. `interviewing` — In interview process
8. `offer` — Received an offer (terminal)
9. `rejected` — Application rejected (terminal)
10. `withdrawn` — User withdrew application (terminal)
11. `closed` — Posting taken down before applying (terminal)

`closed` is set by the weekly liveness sweep and means only that the job listing disappeared,
not that anyone said no. It is distinct from `rejected` (they declined) and `withdrawn` (the
user pulled out). It is only ever applied to rows in a pre-application stage, and only on
explicit on-page closure text — never on a 404, timeout, or redirect. See
`orchestrator-loop.md`.

## Archived

A row at `rejected`, `withdrawn`, or `closed` is archived: the stage/notes update above is
paired with moving its folder, `git mv applications/<id> applications/archived/<id>`. The row
itself stays in `tracker.csv` — there's no separate archived CSV. `interviewing` and `offer`
are never archived. See SKILL.md's "Archiving" section for the full rule and how to reverse it.

## CSV Handling Rules

1. **Always use Python's `csv` module** for reading and writing. Never use raw string manipulation — job descriptions and notes can contain commas, quotes, and newlines.

2. **Preserve field order** when writing. The header row defines the canonical order.

3. **Use `csv.DictReader` and `csv.DictWriter`** for clarity and safety.

4. **Set `date_updated`** to today on every write operation.

5. **Empty optional fields** should be empty strings, not "None" or "null".

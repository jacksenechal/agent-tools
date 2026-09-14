# LinkedIn Connection Knowledge Graph

A local ArcadeDB graph database that models LinkedIn connections, work history, and message
history into warmth-ranked scores — so you can quickly identify who to ask for a referral.

## Lifecycle (start-on-demand + idle auto-stop)

The container holds a ~2GB JVM heap, so it is **not** left running. `scripts/arcadedb_ctl.sh`
manages it:

- The `ingest_linkedin.py` and `query_connections.py` scripts call `arcadedb_ctl.sh ensure`
  automatically — it starts the container if needed, waits until the REST API is ready, and
  refreshes an idle heartbeat (`~/.cache/job-search/arcadedb-last-use`). **Do not run
  `docker compose up` by hand.**
- On first use, `ensure` installs a **systemd user timer**
  (`job-search-arcadedb-reap.timer`, every 15 min) that runs `arcadedb_ctl.sh reap`. Reap
  stops the container once it has been idle for `JOB_SEARCH_ARCADEDB_IDLE` seconds
  (default **10800 = 3h**). This is decoupled from Claude: it reaps the container no matter
  who or what started it.
- `restart: "no"` in the compose file means a reboot will not resurrect it.

Manual controls:

```bash
CTL=~/workspace/agent-tools/skills/job-search/scripts/arcadedb_ctl.sh
$CTL status         # container + heartbeat + timer state
$CTL ensure         # start now (rarely needed; the scripts do this)
$CTL stop           # stop now
$CTL install-timer  # reinstall/enable the idle-reaper timer (idempotent)
```

Override the idle window per-invocation, e.g. `JOB_SEARCH_ARCADEDB_IDLE=21600 $CTL reap` (6h).

## Setup

### 1. Start ArcadeDB

The ingest step below starts it for you. To start manually:

```bash
~/workspace/agent-tools/skills/job-search/scripts/arcadedb_ctl.sh ensure
```

Verify: `curl -s http://localhost:2480/api/v1/server -u root:playwithdata`

### 2. Export from LinkedIn

Settings & Privacy → Data Privacy → Get a copy of your data. Request:
- Connections, Messages, Positions, Education

Extract CSVs to `~/workspace/jobs/data/linkedin/`:
- `Connections.csv` — 1st-degree connections
- `Messages.csv` — message history
- `Positions.csv` — your own work history (for shared-employer bonus)
- `Education.csv` — optional, for school nodes

### 3. Ingest

Run from your job-search repo root:
```bash
cd ~/workspace/jobs
python3 ~/workspace/agent-tools/skills/job-search/scripts/ingest_linkedin.py --me-name "Your Full Name"
```

`--me-name` must match your name exactly as it appears in LinkedIn message exports (used to
determine message direction). `--data-dir` defaults to `data/linkedin`; override if needed.

Takes 2–5 minutes depending on message volume. Clears and rebuilds on each run.

## Schema

| Type | Kind | Properties |
|---|---|---|
| `Person` | Vertex | `name`, `url` (unique), `current_title`, `connection_date`, `warmth_score` |
| `Company` | Vertex | `name` (unique) |
| `School` | Vertex | `name` (unique) |
| `CONNECTED_TO` | Edge (Me→Person) | `source`, `date` |
| `WORKED_AT` | Edge (Person→Company) | `title`, `is_current`, `start_date`, `end_date` |
| `MESSAGED` | Edge (Me→Person) | `timestamp`, `direction` (Inbound/Outbound) |
| `STUDIED_AT` | Edge (Me→School) | `degree`, `start_date`, `end_date` |

The `Me` vertex is a `Person` with `url = "me"`.

## Warmth Algorithm

```
warmth = log(msg_count + 1) × 20       # message depth
       + 0.9^months_since_last_msg × 20 # recency decay (max 20 if messaged this month)
       + 15 if shared company history   # alumni bonus
       + max(0, years_connected)        # 1 point per year
```

Interpretation:
- **> 20**: Genuinely warm — real interaction history, high response likelihood
- **10–20**: Mild warmth — soft tie, treat carefully
- **< 10**: Cold in practice — 1st-degree in name only, treat like 2nd-degree for outreach

## Querying

```bash
python3 ~/workspace/agent-tools/skills/job-search/scripts/query_connections.py "Company Name"
```

Returns 1st-degree connections currently at the company, ranked by warmth.

**Note:** Matches on company name exactly as it appears in LinkedIn profiles. It adds warmth
context on top of whatever the networking track or a person's own reporting has already
surfaced; it does not itself confirm who currently works there.

### Direct queries

```bash
# Count all persons
curl -s http://localhost:2480/api/v1/command/KnowledgeGraph \
  -u root:playwithdata -H "Content-Type: application/json" \
  -d '{"language":"sql","command":"SELECT count(*) FROM Person"}'

# Find person by name
curl -s http://localhost:2480/api/v1/command/KnowledgeGraph \
  -u root:playwithdata -H "Content-Type: application/json" \
  -d '{"language":"cypher","command":"MATCH (p:Person) WHERE p.name CONTAINS \"Smith\" RETURN p.name, p.warmth_score, p.current_title"}'
```

Default credentials: `root` / `playwithdata` — change by updating `JAVA_OPTS` in the
docker-compose.yml and the `ARCADE_PASS` constant in both scripts (or set `ARCADE_PASS` env var).

## Org file template (networking track)

Save to `strategy/networking/orgs/<slug>.md` (see `references/networking-loop.md` and the
jobs repo's `strategy/networking/README.md`):

```markdown
# <Company>

## Why this org
<Coherence read (`coh_verdict` and why-line) or warm-cluster reason this org is in the set.>

## People
| Name | Relation | Warmth | Status | Last touch |
|---|---|---|---|---|
| <name> | <1st-degree / peer / alumni / ...> | <KG score or plain read> | <not_contacted / reached_out / in_conversation / warm / referred / dormant> | <date> |

## Angles
<Specific framings worth trying: shared background, a published artifact, a mutual connection.>

## Open questions
<What the next research pass should resolve: who is there now, what changed, is a role open.>

## Next
<The one or two concrete next steps, if any are due.>
```

### Ranking people

Still useful for deciding who to talk to first:

**Tier 1 — Warm 1st-degree**: real interaction history, highest response likelihood.
**Tier 2 — Peers on the same/adjacent team**: natural peer-to-peer outreach.
**Tier 3 — Hiring manager**: high value, handle carefully; lead with genuine curiosity, not "I applied."
**Tier 4 — Adjacent department**: intel only, low conversion.

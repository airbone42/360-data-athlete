# /strava — Sync titles + insights to Strava

Mirrors the intervals.icu workout name to Strava (all activity types) and
writes a follower-friendly 3–5 line insights block plus a random-gerund
footer for endurance activities (`Run`, `VirtualRun`, `Ride`,
`VirtualRide`). Idempotent: re-running on an activity whose description
already carries the configured footer suffix (`INSIGHTS_ANCHOR`, set
via `STRAVA_PUBLISHER_FOOTER_SUFFIX` — see `app/config.py`) skips the
description, the title update stays available.

**Off by default.** The feature is gated by `STRAVA_PUBLISH_ENABLED`
(`app/config.py`, default `false`) because Strava returns 403 on
activity writes for apps without `activity:write` scope. While disabled
this command is a clean no-op (no pending candidates, no Strava call).
Set `STRAVA_PUBLISH_ENABLED=true` with a write-scoped Strava app to
enable it.

## Arguments
$ARGUMENTS
Optional. Accepted forms:
- (empty)              — last 2 days (today + yesterday)
- `--days N`           — last N days
- `--activity-id i...` — a specific intervals.icu activity ID
- `--dry-run`          — preview, no push

---

## Workflow

Launch the `aicoach-framework:strava-publisher` agent in a pane. Pass
the argument string verbatim plus a reminder of what the agent has to
do — the agent loads its own playbook from `agents/strava-publisher.md`
and reads the necessary configs itself.

The pane start prompt should carry:

```
Arguments: {ARGS or "(default: --days 2)"}

Task:
1. Call strava_pending.py with the arguments.
2. For each entry, decide: title and/or insights block.
3. fetch_activity.py + strava_coupling.py in parallel (endurance only).
4. Compose the insights block (language per
   config/athlete_preferences.md → Coach response language; default
   English; follower-friendly, max 3–5 lines + random-gerund footer).
5. Push via strava_apply.py (or --dry-run if the athlete set it).
6. Return a compact summary to chat.

Source files you see in the agent body:
- config/athlete_preferences.md (language)
- config/exercise_log.md (video-verdict snippets, optional)
- app/data/gerunds.json (footer wordlist)
```

---

## When the command runs automatically

The head coach invokes this command **right after** the `coach-analyst`
pane in the `/analyse` flow (step 6.6). At that moment the freshly
analysed activity is the natural candidate. Manual invocation stays
available at any time:

```bash
/strava                       # last 2 days
/strava --days 7              # larger range, e.g. after a trip
/strava --activity-id i12...  # retroactively for a specific session
/strava --dry-run             # don't push, just see what would happen
```

The legacy `scripts/sync_strava_titles.py` has been retired — its
title-sync and surface-mismatch logic now live in
`app/utils/strava_titles.py` and are reused by `strava_pending.py`.

# Playbook: fleet-health

**For:** anyone. **Asks like:**

- "How is the fleet?"
- "What's red?"
- "Is anything stuck?"
- "What needs attention today?" (combine with [open-prs](open-prs.md) and [triage-issues](triage-issues.md))

**Output:** a short summary with suggested actions. It is read-only.

## Steps

1. **`./harness snapshot`.**
2. **Control:** `control-status.json`. Is the GitHub App installed? When were the last discovery and the
   last backfill? Is the scheduler running? Are there recent webhook delivery failures?
3. **Red live branches:** `control-fleet.json` rows with `result == "failure"`. For each one:
   - the failing step: `gh run view <run_id> -R <repo> --log-failed | tail -40`;
   - a triage verdict (upstream / network / pipeline / image) per
     `repos/workspace/docs/build-failure-triage.md`;
   - how long it has been red (compare `built_at` with the last release).

   Group them by cause. Several images failing the same step since the same time points to a pipeline cause.
4. **Upstream drift:** rows with `drift == "ahead"`, where upstream moved but nothing was released. Check
   `next_check` and `last_outcome`, and whether a build is running or failed.
5. **Skips:** `control-skips.json`. Note each skip flag and its age. A forgotten skip silently stops releases.
6. **Helper repos:** `helpers[].failures` (docker-mods branches, each with its failed run) and, from
   `/api/batch.json`, `projects[].failing` (the proot-apps apps, selkies layers and wheelie builds whose newest
   job failed). The site shows both below the fleet board.
7. **Runners:** `control-queue.json` (`in_use`/`limit`, queued). Note any stuck runs in
   `control-runs.json` `active` that started hours ago.
8. **Hub and site:** `hub-status.json`, covering health, source freshness and rejected releases. Check the
   last runs: `gh run list -R linuxserver-playground/hub --limit 3` and the same for `site`.
9. **Staleness:** `hub-staleness.json`, the builds on an older base digest. That is normal right after a base
   release, and worth noting when it persists.

## Answer shape

```
Fleet at 14:05 UTC: 291 live branches, 5 red, 9 behind upstream, 0 skips; runners 0/20; hub OK; site OK.

Red (by cause)
- upstream: calibre:master (since 2 d): upstream 8.1 has no arm64 asset yet. Wait, or pin the arch.
- pipeline: …
Behind upstream: …
Suggested: rerun X (network), open an issue for Y, nothing to do for Z.
```

If everything is green, say so in one line.

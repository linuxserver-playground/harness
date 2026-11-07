# Playbook: fleet-ops

**For:** members. Contributors get told who to ask: a maintainer, in their PR or issue. **Asks like:**

- "Rerun the failed calibre build."
- "Rebuild heimdall."
- "Skip sonarr's upstream checks for a week."
- "Refresh the hub."
- "Release the workflows change."
- "Remove docker-foo."
- "The hub has not published for an hour." / "Pages keeps saying success but nothing changes."

**Output:** the action, then a report with run links. Every action here changes live state, so say what you
are about to do and get a yes first.

## Rerun, cancel, dispatch

| Action | Command |
| --- | --- |
| Rerun a failed run (only the failed jobs) | `gh run rerun <run-id> -R linuxserver-playground/<repo> --failed` |
| Cancel a run | `gh run cancel <run-id> -R …` |
| Build a branch now | `gh workflow run build.yml -R linuxserver-playground/docker-<name> --ref <branch> -f reason=manual` (reasons: manual, upstream, packages, rebuild) |
| Skip flags, the package check, reconcile | The site's fleet pages (https://linuxserver-playground.github.io/site/fleet/) after "Sign in with GitHub" (use Chromium: the cookie is cross-site in the playground). Control's actions need a browser session, so send the person there with the exact page |

**Before a mass dispatch** (more than a handful), check `./harness control api/queue.json`.
Then dispatch in batches of about 10, waiting for the queue to drain, and keep heavy images apart (webtop,
selkies and kasmvnc bases). The limit is 20 concurrent jobs for the whole org.

**Rebuilding a chain** (a base and what builds on it) goes in order, waiting for each release: baseimage-ubuntu,
then baseimage-selkies, then the app; baseimage-alpine, then baseimage-alpine-nginx, baseimage-selkies' alpine
branch and the python tool, then the apps. Each layer is then built on the one just released. Nothing in control
rebuilds dependents by itself ([consequences](consequences.md)). A rebuild of an unchanged
head republishes the same `-lsN`, and the hub and site show it after their next runs (gotchas).

**Proof builds.** heimdall is the small build for a pipeline change. When the change touches the GUI bases
(selkies, kasmvnc, the Ubuntu base), build filezilla as well. Never cura.

## Refresh the hub

Control dispatches the hub's and the site's Deploys on fixed slots, at most nine an hour each, whenever
something changed, so a release or a push reaches them within about seven minutes without anyone asking. Check
`deploys` in `https://ci.thelamer.duckdns.org:8443/api/status.json` first: it shows what is pending and the next
slot. Force one only when control is down or fresh refreshed data is needed now; a hand dispatch counts against
GitHub Pages' ten builds an hour.

1. For new stars or mods data, `gh workflow run refresh.yml -R linuxserver-playground/hub`: control serves its
   commit at the next slot. Otherwise `gh workflow run deploy.yml -R linuxserver-playground/hub`, then
   `gh run watch` it to the end.
2. When that Deploy pushed to `gh-pages`, control requests the site's next slot. Confirm a site Deploy started
   within about seven minutes (`gh run list -R linuxserver-playground/site --limit 3`), and watch it.
3. Report both outcomes with links. On failure, show the failing step's log tail.

## Release a workflows change

The change is merged to `workflows` main by PR first ([infra-change](infra-change.md)).

0. See where things stand before touching anything: `git -C repos/workflows ls-remote origin refs/tags/v1 refs/heads/main`
   (the tag may already be on main: someone else released), and `gh run list -R linuxserver-playground/docker-heimdall --limit 3`
   (a proof build may already be running; `gh api repos/linuxserver-playground/docker-heimdall/actions/runs/<id> --jq '.referenced_workflows[].sha'`
   says which workflows commit it used, and `./harness control api/builds/linuxserver-playground/docker-heimdall/<id>.json | jq '{reason: .build.reason, event: .run.event, actor: .run.actor}'`
   says what kind of run it was). Never move a tag that is already there or start a second proof for one run.
1. In `repos/workflows` on main: `./harness setup workflows` once, then `./harness validate workflows` (runs
   `./scripts/check.sh`, with shellcheck from its container when none is installed) and stop on any failure.
2. Confirm it is backward compatible for every `@v1` caller: the same inputs, outputs and ci interface. If it
   is not, stop: it needs a new major tag.
3. If the change needs a new builder or ci image too (a step calls a new builder command, or names a file an
   older builder does not render), that repo has merged and its package's `latest` tag is the new commit:
   `gh api orgs/linuxserver-playground/packages/container/builder/versions --jq '.[] | select(.metadata.container.tags | index("latest")) | .metadata.container.tags'`
   lists builder's main sha. Publish succeeding is a minute too early (gotchas, "Releasing builder, ci and
   workflows").
4. The person approves the tag move: `./harness allow tag workflows`. Then
   `git -C repos/workflows tag -f v1 && git -C repos/workflows push -f origin v1`.
5. Prove it: `gh workflow run build.yml -R linuxserver-playground/docker-heimdall -f reason=<reason>`, then watch
   it to the end. Pick the reason the change affects: a `manual` run never exercises a `packages`-only path.
   When the change touches the GUI path, also `… -R linuxserver-playground/docker-filezilla`. Never cura. A
   proof build of an unchanged head republishes the released tag (gotchas).
6. If the build fails because of the change, move `v1` back to the previous commit (same approval) or fix
   forward. Say which you did.

## A Pages site that will not publish

**Who:** the check is for any member. The reset is for an **owner** of the repository's org: `./harness pages reset`
checks the person's role (`gh api user/memberships/orgs/<org> --jq .role` is `admin`) and refuses anyone else. For
anyone else, the answer is the `pages check` output and a note to ask an org owner.

GitHub Pages can get stuck on one repository with its status page green. Every new deploy reports "success" within
seconds while the site keeps serving an old one, or new deploys sit in `syncing_files` until `deploy-pages` gives
up ("Timeout reached, aborting!"). Deleting the Pages site and creating it again is known to clear Pages errors
like these when nothing else explains them. Offer it as an option only after the person has seen the evidence.

1. **Is it stuck, and for how long?** `./harness pages check <repo>` (the hub, the site or a `docker-*` repo) shows
   what the site serves next to its newest deploy or release, gives a verdict, and lists control's healing rows
   for the repo. It counts as **prolonged** when the site has been stale for an hour or more, or control's
   `healing` holds the repo in `pages_retrying` that long or in `pages_given_up`. Shorter than that, control's
   own redeploys usually catch up: say so and check again later.
2. **Rule out what is not Pages:**
   - **a GitHub incident:** https://www.githubstatus.com. When Pages is degraded there, wait it out; a reset will not help;
   - **a red step of our own:** the build, the ingest or an artifact upload. Fix that instead, per [explain](explain.md);
   - **the hub's normal waits:** the "Wait for the Pages deploy budget" step keeps its deploys about five minutes
     apart and is not a stall.
3. **Show the evidence and offer the reset.** Quote the check, the failing deploy step's lines
   (`gh run view <id> -R <repo> --log | grep -E 'Current status|Reported success|still serves|Timeout'`) and how
   long it has lasted. Then offer the reset with what it costs:
   - the site answers 404 for a few minutes, until the redeploy lands. For the hub, the site's live build pages and
     control's publish checks fail while it does;
   - a custom domain is set again and needs a new certificate, with HTTPS failing for up to an hour. The command
     says when there is one.

   It fixes the symptom, not GitHub's cause. Get a yes before going on.
4. **Reset.** Run `./harness pages reset <repo>` to print the plan, then `./harness pages reset <repo> --yes`. The
   command:
   - deletes the Pages site and creates it again with the same source: from Actions for an image repository,
     from the `gh-pages` branch for the hub and the site;
   - keeps the `github-pages` environment's branch rule as it was;
   - redeploys: for the hub and the site, Pages builds `gh-pages` again on its own; for an image repository, it
     dispatches `build.yml` with `reason=pages`, which rebuilds its site from the Releases and builds no image.

   Do not do it by hand: the guard stops a bare `gh api -X DELETE …/pages`.
5. **Prove it.** Watch the redeploy to the end (`gh run list -R <repo> -L 2`, `gh run watch`), then run
   `./harness pages check <repo>` again. For the hub, control's next successful Deploy clears its healing row; a
   site Deploy follows at its next slot when the hub published something new.
6. **If it is still stuck after a reset,** stop: draft a GitHub support request with the runs and the check output
   (`./harness draft issue`). The person files it.

## Remove an image

1. **Check that nothing depends on it:**
   - no image builds FROM it (`./harness lookup <name>`: a "built FROM" line per base tag; no line means no
     dependents);
   - no open PRs;
   - no mods target it (`/api/v1/catalog/<name>/mods.json`).
2. **Consider archiving instead.** An archived repo stays on the site with an `archived` flag. The question
   is the person's.
3. **The person approves:** `./harness allow delete docker-<name>`. Then:
   - `gh repo delete linuxserver-playground/docker-<name> --yes`;
   - delete each GHCR package, which outlives its repo: `<name>`, `build/<name>`, and any `dev/<name>` and
     `untrusted-pr/<name>`. Use
     `gh api -X DELETE /orgs/linuxserver-playground/packages/container/<url-encoded package>`
     (`build%2F<name>`, …). This needs the `delete:packages` scope.
4. **Everything else follows on its own:**
   - control drops the repo on GitHub's `repository deleted` webhook;
   - the `repository deleted` webhook requests the hub's next Deploy slot, which removes its data;
   - the site rebuilds without its pages at its own next slot.

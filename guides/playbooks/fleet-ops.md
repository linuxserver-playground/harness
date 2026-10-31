# Playbook: fleet-ops

**For:** members. Contributors get told who to ask: a maintainer, in their PR or issue. **Asks like:**

- "Rerun the failed calibre build."
- "Rebuild heimdall."
- "Skip sonarr's upstream checks for a week."
- "Refresh the hub."
- "Release the workflows change."
- "Remove docker-foo."

**Output:** the action, then a report with run links. Every action here changes live state, so say what you
are about to do and get a yes first.

## Rerun, cancel, dispatch

| Action | Command |
| --- | --- |
| Rerun a failed run (only the failed jobs) | `gh run rerun <run-id> -R linuxserver-playground/<repo> --failed` |
| Cancel a run | `gh run cancel <run-id> -R …` |
| Build a branch now | `gh workflow run build.yml -R linuxserver-playground/docker-<name> --ref <branch> -f reason=manual` (reasons: manual, upstream, packages, rebuild) |
| Skip flags, the package check, reconcile | The site's fleet pages (https://linuxserver-playground.github.io/site/fleet/) after "Sign in with GitHub" (use Chromium: the cookie is cross-site in the playground). Control's actions need a browser session, so send the person there with the exact page |

**Before a mass dispatch** (more than a handful), check `curl -fsS https://ci.thelamer.duckdns.org:8443/api/queue.json`.
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

Control already dispatches this hourly, so force one only when fresh data is needed now.

1. `gh workflow run deploy.yml -R linuxserver-playground/hub`, then `gh run watch` it to the end.
2. Control relays `hub-updated` to the site after a successful Deploy. Confirm that a site Deploy started
   within a few minutes (`gh run list -R linuxserver-playground/site --limit 3`), and watch it.
3. Report both outcomes with links. On failure, show the failing step's log tail.

## Release a workflows change

The change is merged to `workflows` main by PR first ([infra-change](infra-change.md)).

0. See where things stand before touching anything: `git -C repos/workflows ls-remote origin refs/tags/v1 refs/heads/main`
   (the tag may already be on main: someone else released), and `gh run list -R linuxserver-playground/docker-heimdall --limit 3`
   (a proof build may already be running; `gh api repos/linuxserver-playground/docker-heimdall/actions/runs/<id> --jq '.referenced_workflows[].sha'`
   says which workflows commit it used, and `curl -fsS https://ci.thelamer.duckdns.org:8443/api/builds/linuxserver-playground/docker-heimdall/<id>.json | jq '{reason: .build.reason, event: .run.event, actor: .run.actor}'`
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
   - the hub's next Deploy removes its data (or force one, as above);
   - the site rebuilds without its pages on the `hub-updated` that follows.

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
| Skip flags, the package check, reconcile | The site's fleet pages (`/site/fleet/`) after "Sign in with GitHub" (use Chromium: the cookie is cross-site in the playground). Control's actions need a browser session, so send the person there with the exact page |

**Before a mass dispatch** (more than a handful), check `curl -fsS https://ci.thelamer.duckdns.org:8443/api/queue.json`.
Then dispatch in batches of about 10, waiting for the queue to drain, and keep heavy images apart (webtop,
selkies and kasmvnc bases). The limit is 20 concurrent jobs for the whole org.

## Refresh the hub

Control already dispatches this hourly, so force one only when fresh data is needed now.

1. `gh workflow run deploy.yml -R linuxserver-playground/hub`, then `gh run watch` it to the end.
2. Control relays `hub-updated` to the site after a successful Deploy. Confirm that a site Deploy started
   within a few minutes (`gh run list -R linuxserver-playground/site --limit 3`), and watch it.
3. Report both outcomes with links. On failure, show the failing step's log tail.

## Release a workflows change

The change is merged to `workflows` main by PR first ([infra-change](infra-change.md)).

1. In `repos/workflows` on main: run `./scripts/check.sh` and stop on any failure.
2. Confirm it is backward compatible for every `@v1` caller: the same inputs, outputs and ci interface. If it
   is not, stop: it needs a new major tag.
3. The person approves the tag move: `./harness allow tag workflows`. Then
   `git -C repos/workflows tag -f v1 && git -C repos/workflows push -f origin v1`.
4. Prove it: `gh workflow run build.yml -R linuxserver-playground/docker-heimdall`, then watch it to the end.
5. If the build fails because of the change, move `v1` back to the previous commit (same approval) or fix
   forward. Say which you did.

## Remove an image

1. **Check that nothing depends on it:**
   - no image builds FROM it (`./harness lookup <name>`, "built FROM it");
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

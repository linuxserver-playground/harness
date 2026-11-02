# Gotchas

Things that caught earlier agents and people out. Each one cost a wrong change or a wasted build.

## Branches and releases

- **A branch is live because its own `image.yml` names it in `release.branch`.** The default branch's
  `release.tags` only advertises tags in the README and store pickers. Do not add a branch to `release.tags`
  to "make it live".
- **Live branches never merge into each other.** `master` and `develop` of the same image are separate
  products with separate `image.yml` files. Target the branch the change applies to.
- **Every push to an open PR starts a full build and test.** Finish the change locally, then push once.
- **GitHub runs a workflow for only one of a brand-new repo's first pushes.** Check `gh run list` after
  creating a repo, and dispatch the live branches that got no run.
- **Neither bot commit starts a build.** `Update generated files [skip ci]` is made before the build that
  continues on it; `Update package versions [skip ci]` after a successful release. The weekly package check
  releases from its own run when a package changed since the previous release; there is no second build, and
  control's release check treats a head that differs from the released commit only in those files as released.
  A committed table another pipeline wrote (Jenkins', on a converted repository) is not a change: the check
  compares with the previous release's `package_versions.amd64.txt` asset, publishes nothing and commits the
  table to catch the branch up.

- **A rebuild of the released head republishes the same tag** (since 2026-10-31 14:00 UTC, workflows `2b3b760`
  and control `f235f4e`; before that a `[skip ci]` templating commit counted as a new head and minted the next
  `-lsN`, which is why some tags from before then exist). A `manual` or `rebuild` run from a commit that is
  already released (or differs from it only in the pipeline's `[skip ci]` commits) publishes the same `-lsN`
  again, and the hub ingests the new record only when its `build.json` is an hour or more newer than the one it
  holds; the site follows on the next `hub-updated`. So a proof build of an unchanged image shows up on the site
  later than the run finishes, and a `packages` run is the only kind that takes the next `-lsN` from the same
  head.
- **Proof builds: heimdall, or filezilla for anything on the selkies path. Never cura.** heimdall (alpine-nginx)
  is the small build the recipes dispatch. When the change touches the GUI bases, build filezilla (ubuntu,
  selkies, about a minute, no quirks). cura has a memory bug of its own that would muddy any proof. When a chain
  has to be rebuilt by hand, go in order and wait for each release: baseimage-ubuntu, then baseimage-selkies,
  then the app, so each layer is built on the one just released. The alpine chain is baseimage-alpine, then
  baseimage-alpine-nginx, baseimage-selkies' alpine branch and the python tool, then the apps. Nothing in control
  rebuilds dependents by itself.
- **Prefer a typed `upstream.version` source to `command`.** `github_release` (with `include`, `exclude`,
  `prerelease`, `sort: version`), `deb_packages`, `alpine_apk`, `arch_package`, `json` (jq, `sort: version`),
  `regex` (a page, or `search: url` for a redirect), `static` and `combined` cover almost every shape a
  legacy curl pipeline had. Prove a new source against the old command's output before you push it.
- **A release can exist before its assets do.** Projects cut the GitHub release first and upload the binaries
  after, sometimes an hour later, and a build dispatched in between fails on an empty asset list. Name what
  the Dockerfiles download under `upstream.version.require_assets` (`{asset: <regex>}` on the asset's file name
  for release sources, a `${VERSION}` URL template elsewhere, one entry per asset): control then records
  "assets not ready" and tries again hourly, and posts to Discord on every such check (amber, then red from
  the fifth) with the pattern and the names that were uploaded, so a renamed asset is read off the embed. A Dockerfile that
  reads `releases/latest` for its assets should look the release up by the version arg instead, so the check
  and the build see the same release. `{asset, repo}` checks a sibling repository's latest release, for an
  architecture built from one. Every branch's patterns, and the branches left without one on purpose (static
  versions, names that cannot be derived from the version), are listed in `repos/workspace/docs/live-cutover.md`,
  "Required release assets": read it before adding or removing one.
- **Count builds from GHCR, not Releases.** A release's `created_at` (and GraphQL's `createdAt`) is the date of
  the tagged commit, and an upstream-triggered release tags an old head, so date filters on Releases miss them.
  GHCR package versions carry the push time.

## Releasing builder, ci and workflows

- **Move `v1` only once the builder package carries the new builder.** When a workflows change needs a new
  builder too (a step calls a new builder command, or names a generated file an older builder does not render),
  builder merges first, and `v1` moves only when the `builder` package's `latest` tag is the new commit:
  `gh api orgs/linuxserver-playground/packages/container/builder/versions --jq '.[] | select(.metadata.container.tags | index("latest")) | .metadata.container.tags'`
  must list builder's main sha. Publish reporting success is not that moment: the retag lands about a minute
  later, and a build that starts in between pulls the old builder with the new workflow and fails its Prepare job
  (docker-modrinth, 2026-10-30). The same holds for a `ci` change a workflow depends on.

## Issues and pull requests

- **No bot answers issues or pull requests.** The AI first responder (`lsio-playground-triage[bot]`) was a
  demonstration and was shut down on 2026-11-02. Its old comments stay in the threads; a maintainer's reply is
  the answer.

## Generated files

- **On a PR, never commit `builder render` output.** Some older docs (the org CONTRIBUTING, the PR template,
  the image AGENTS.md template) still say "run builder render". On an existing repo, that makes the PR build
  fail. Use `./harness render`, which renders out of tree.
- **`builder check` defaults to `--drift error`, but PR builds use `--drift warn`.** Drift on its own is not
  your problem on a PR branch.
- **Fix README text in `image.yml`.** That means `docs.setup`, `docs.optional_parameters`, or the
  descriptions on `runtime.*` entries. A wrong section on every README is a builder template change.

## Images

- **Change both Dockerfiles.** They must agree apart from `FROM`. `builder check` warns, and reviewers reject
  a PR that changes only one.
- **Add a changelog entry** at the top of `changelog:` in `image.yml` for any change to a Dockerfile or
  `root/`. Nothing enforces it except review.
- **s6 scripts** need `#!/usr/bin/with-contenv bash`, `# shellcheck shell=bash` and the executable bit
  (`git update-index --chmod=+x`). The build fails without the bit.
- **No `HEALTHCHECK`, `USER`, `ENTRYPOINT` or `CMD`, and do not touch the `LABEL` lines.** Never pin the
  application version: CI passes it as a build argument.
- **Names with `.` or `_`** (changedetection.io, your_spotify) fail the schema's `name` pattern. They wait on
  a maintainer decision.
- **Smoke tests are generic.** The ci harness checks:
  - s6 services stay up;
  - the web endpoint answers below 500;
  - ports listen (a warning only);
  - runtime logs carry no known failure line (a warning only).

  There are no per-image tests to add.

## Red builds

- **Tell upstream rot and network flakes from pipeline bugs** before fixing anything
  (`repos/workspace/docs/build-failure-triage.md`). Often the cause is an upstream release that is broken or
  not yet published for one architecture.
- **Rerun once if it looks like the network** (GHCR 5xx, apt or apk mirror timeouts, `curl: (28) Failed to
  connect` to the project's own download host that answers again minutes later). A second failure is
  real.

## Mods

- **`./harness get docker-mods` clones `master` only.** `git branch -r` shows no mod; `git ls-remote --heads origin`
  lists the hundred branches, and `git fetch origin <branch>:<branch>` brings one in ([mod](playbooks/mod.md)).
- **A contributor cannot create a mod branch from a fork.** A member creates `<target>-<name>` from
  `template`, then the PR goes to that branch.
- **Mod PRs get less checking than image PRs.** There is no schema validation in CI and no report comment,
  so run `tools/check-branch.sh` and `tools/test-mod.sh` yourself.
- **Name a playground mod in full:** `DOCKER_MODS=ghcr.io/linuxserver-playground/mods:<tag>`. The base images'
  mod script (upstream's `docker-mods.v3`, unchanged) sends `linuxserver-playground/mods:<tag>` to Docker Hub,
  where it does not exist.

## Data and the site

- **The hub's API is the site's only source.** A field the hub does not serve cannot appear on the site. Add
  it to the hub first, then the site.
- **The hub installs `builder@main`.** A hub PR that needs an unmerged builder change is red until builder
  merges. That is expected in a change train.
- **The site's anchors on image and build pages are a public contract.** Never rename them.
- **The site has no CORS access to Release assets.** Heavy data such as file trees comes through the hub
  (newest build per branch) or links to the Release.
- **Don't refresh the site's data against the live hub to test a change.** The build reads the snapshots
  `npm run snapshot` restores from the site's `data` branch (from git, so it is safe to repeat), so a site
  change needs no refresh, and a hub change is tested with `npm run data:local` against a local `../hub` build.
  GitHub Pages rate-limits by IP: an agent that ran two full refreshes (`REFRESH_ALL=1 npm run data`) was
  answered 429 for every hub URL, including `catalog.json`, for over half an hour.
- **A fleet-wide question reads the hub's `data` checkout, not the API.** `./harness data` lays the whole
  dataset into `repos/hub/data/` (data-sources, "The whole dataset at once"). An agent that answered "which
  images…" with one Pages request per image hit the same rate limit as the refresh above.
- **Generated data is not on main in the hub or the site.** Each keeps it as the one commit of a `data` branch,
  replaced by CI on every change so its history never grows. The hub's `data/` is a checkout of that branch
  (`scripts/data.sh`); the site's snapshots are laid over the checkout by `npm run snapshot`. Both paths are
  ignored on main, and only CI publishes the branch: never push to `data` or add the data back to main.

## Fixtures and noise

- **[docker-heimdall#6](https://github.com/linuxserver-playground/docker-heimdall/pull/6) is a reference PR, never merged.** Leave it out of PR rankings and reviews
  unless the person asks about it.
- **Issues and PRs titled `[test data]`** were lorem-ipsum fixtures, now closed. If any reappear, leave them out
  of triage and PR rankings.

## Capacity

- **20 concurrent jobs is the limit.** A mass dispatch queues for hours and blocks real releases. Pace it in
  batches, and check `/api/queue.json` first.
- **Batch runs show as a long queue.** selkies-layers, proot-apps and wheelie hold most of their matrix back
  with `max-parallel`, so `/api/queue.json` can list a hundred queued proot-apps jobs on a fleet with free
  slots. Read `/api/batch.json` `capacity` instead: it leaves those out. Do not dispatch the batch workflows
  by hand with a large `parallel`; control sizes them.
- **When GitHub is degraded, wait before fixing.** Check githubstatus.com first. Control retries 5xx reads, asks
  for lost webhooks again within 5 minutes of noticing any, heals lost completions every 5 minutes, and the site's
  refresh skips a build the hub does not serve yet. A run that looks stuck, a site Deploy that failed on a 404 or
  a backfill error on `/status` during an incident usually repairs itself; the workspace's
  `docs/github-outage-2026-10-30.md` lists what does and what does not.

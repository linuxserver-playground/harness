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
- **`Update package versions` commits deliberately start a build**: that push is what releases new packages.
  `Update generated files [skip ci]` deliberately does not.

- **Prefer a typed `upstream.version` source to `command`.** `github_release` (with `include`, `exclude`,
  `prerelease`, `sort: version`), `deb_packages`, `alpine_apk`, `arch_package`, `json` (jq, `sort: version`),
  `regex` (a page, or `search: url` for a redirect), `static` and `combined` cover almost every shape a
  legacy curl pipeline had. Prove a new source against the old command's output before you push it.
- **A release can exist before its assets do.** Projects cut the GitHub release first and upload the binaries
  after, sometimes an hour later, and a build dispatched in between fails on an empty asset list. Name what
  the Dockerfiles download under `upstream.version.require_assets` (`{asset: <regex>}` on the asset's file name
  for release sources, a `${VERSION}` URL template elsewhere, one entry per asset): control then records
  "assets not ready" and tries again hourly, and posts to Discord after six such checks. A Dockerfile that
  reads `releases/latest` for its assets should look the release up by the version arg instead, so the check
  and the build see the same release.
- **Count builds from GHCR, not Releases.** A release's `created_at` (and GraphQL's `createdAt`) is the date of
  the tagged commit, and an upstream-triggered release tags an old head, so date filters on Releases miss them.
  GHCR package versions carry the push time.

## Issues and pull requests

- **A bot answers every new issue and pull request within a minute or two** (`lsio-playground-triage[bot]`). Its
  comment is a first guess written by an AI from the hub's data, not a maintainer's verdict: correct it in the
  thread if it is wrong. It replies again only to the thread's author, at most three times. A maintainer stops it
  on a thread with the `no-bot` label.

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
- **Rerun once if it looks like the network** (GHCR 5xx, apt or apk mirror timeouts). A second failure is
  real.

## Mods

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

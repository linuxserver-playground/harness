# The system

How the org fits together, in enough depth to reason about any change. The terse maintainer version is
`repos/workspace/AGENTS.md`, and the contract is `repos/builder/CONVENTIONS.md`. When this guide disagrees with
either, they win. Then fix this guide.

## The surfaces

| What | Where | Who reads it |
| --- | --- | --- |
| Website: images, build pages, fleet board, docs, blog, mods, PRoot Apps, stores | https://linuxserver-playground.github.io/site/ | users and the team. It is the single pane of glass |
| Hub: static API, store templates, proxy confs, k8s manifests, mods index, PRoot Apps index | https://linuxserver-playground.github.io/hub/ (`openapi.json` lists the endpoints) | the site, the stores, agents |
| Control plane: scheduler, webhooks, live JSON API, member actions, Discord | https://ci.thelamer.duckdns.org:8443 (`/status`, `/api/*.json`) | the site's fleet pages, the team, agents |
| Images | `ghcr.io/linuxserver-playground/<name>` | users |
| Branch builds, PR builds, staging | `ghcr.io/linuxserver-playground/dev/<name>`, `untrusted-pr/<name>`, `build/<name>` | reviewers |

## The repos

| Repo | Role | A change goes live when |
| --- | --- | --- |
| `builder` | The contract: `CONVENTIONS.md`, `schemas/`, the `contracts` validator. Also the `builder` CLI (`check`, `render`, `migrate`, `render-mod`, `snippets`, `record`), `builder/derive/` (per-build data shared with the hub), and the templates for every image README, AGENTS.md and `build.yml` | Push to main publishes `ghcr.io/linuxserver-playground/builder:latest`. Every build and every Python repo picks it up on its next run. **No PR checks run here**, so validate locally |
| `workflows` | The reusable `image-build.yml` and `mod-build.yml`, one composite action per step, and `pr-report.yml` | The floating tag `v1` moves to the new commit. Image repos call `@v1` |
| `ci` | The container test harness. It runs each built image, takes screenshots, and writes the test report and bundle | Push to main publishes `ci:latest`, which the workflows pull |
| `dumper` | A Rust static file-tree walker for the bundle | A GitHub Release. The workflows fetch `releases/latest` |
| `hub` | Ingests each release's `build.json` and `record.json` into `data/` (its `data` branch, one commit), serves the API on Pages, and generates stores, proxy confs, k8s, quadlets, the mods index, the PRoot Apps index and build pages. `refresh.yml` runs hourly: stars, GHCR tags, mods, PRoot Apps (proot-apps' `metadata.yml`), vulnerability rescans, and pushes the store repos | A push to main, the hourly refresh, or `repository_dispatch image-released` |
| `site` | The Astro website: image pages, build pages, fleet board (live from control), docs and blog content collections | A push to main, `hub-updated` (relayed by control after every hub deploy), or the daily cron |
| `control` | A FastAPI GitHub App on a small server (n97). It handles webhooks, fleet discovery, the scheduler, `/events`, OAuth sign-in, member actions, the site editor's back end and Discord | Push to main. Publish runs the checks and pushes `:latest`, and the server pulls it within 5 minutes |
| `docker-<name>` | One image each: `image.yml`, `Dockerfile` + `Dockerfile.aarch64`, `root/`. The README, AGENTS.md, LICENSE and workflows are generated | A push to a live branch builds and releases. Any other branch builds to `dev/`, and a PR builds to `untrusted-pr/` |
| `docker-mods` | `master` holds the tooling. There is one branch per mod (`<target>-<name>`) with `mod.yml` | A push to a mod branch builds the mod image, and control re-reads a changed `mod.yml` at once. The hub's next scheduled run reads the `mod.yml` |
| `unraid-store`, `umbrel-store`, `runtipi-store` | Generated store repos, pushed hourly by the hub's `refresh.yml` | Never edit them; change the generator in the hub |
| `.github` (`repos/dot-github`) | The org profile, CONTRIBUTING, SECURITY, issue forms and PR template | Push to main |
| `workspace` | The maintainers' workbench: `DECISIONS.md`, working notes (`docs/`), the cutover list | Push to main |
| `harness` | This repo | Push to main |

**Kinds of image.** `image.yml` `kind` is `app` (the default), `base` (the `baseimage-*` repos) or `tool` (xvfb,
yq, unrar, build-agent…). Bases and tools build like any image, but stay out of the stores and install
artefacts.

**Helper repos.** A `docker-*` repo with no `image.yml` on its default branch, such as `docker-mods`, is a
helper. The fleet board lists it apart from the images.

## From a push to the website

1. A push to a live branch of `docker-<name>` (or a scheduler dispatch) runs the repo's `build.yml`, which
   calls `workflows/.github/workflows/image-build.yml@v1`.
2. **Prepare.** The manifest is validated, the upstream version resolved, and the generated files checked
   (live: re-rendered and committed once as `Update generated files [skip ci]`). Shellcheck runs.
3. **Per architecture, on native runners.** The image is built into `build/`, tested with the `ci` image
   (s6 services stay up, the web endpoint answers, screenshots), scanned once with syft, and its file tree
   walked with `dumper`.
4. **Publish.** The multi-arch tags are created (CONVENTIONS §3) and our own SBOM attestation is attached.
   `builder record` derives `record.json`: package tables, the diff against the previous release, a grype
   scan, base layers. A GitHub Release carries the bundle.
5. **The workflow POSTs signed events to control** `/events`. Control posts to Discord (held at
   "publishing" until the hub serves the build) and sends the hub `image-released`.
6. **The hub's Deploy** reconciles the whole org over GraphQL, ingests every release `data/` lacks, publishes
   `data/` as the one commit of its `data` branch, renders the API and deploys Pages. From then on the build's
   site page works: the site's 404 page renders new builds live from the hub API (`LiveBuildPage`).
7. **Control sends `hub-updated`** to the site, which rebuilds and makes the new pages static.
8. **Hourly,** the hub's `refresh.yml` reads stars and GHCR tags, rescans vulnerabilities when grype's
   database moved, refreshes the mods index, and asks for a Deploy.

`repos/workspace/docs/delivery-latency.md` measures this path.

## The scheduler

Control replaces every per-repo cron:

- hourly upstream checks, using the typed `upstream.version` source in `image.yml`;
- hourly release checks;
- weekly package checks (`Update package versions` commits, which deliberately do start a build).
- hourly mod checks, for the docker-mods branches whose `mod.yml` has an `upstream` block (the Jenkins
  External-Triggers jobs): the same resolver, then GHCR is asked whether `mods:<branch>-<version>` exists; when
  it does not, the branch's `build.yml` is dispatched with `mod_version` (and `line` for a mod with
  `upstream.lines`: each version line is checked, and the first missing one built, one build at a time; when a
  build of such a mod completes, control checks it again at once for the next line).
  Decisions show as image `mods`, kind `mod`. `control/mods.py`; discovery reads every branch's `mod.yml` every
  30 minutes, and a push that touches a branch's `mod.yml` re-reads it at once.
- the batch build projects (proot-apps daily 00:00 UTC, selkies-layers daily 04:30, wheelie's gap check
  hourly): each run is dispatched with a `parallel` sized to the slots free after a reserve of 4 for image, hub
  and site builds (2 to 16), and Discord hears when a unit (a layer, an app, a wheel) starts failing or
  recovers. Only projects in `CONTROL_BATCH_LIVE` are dispatched; the rest are dry runs beside their own cron.
  `control/batch.py`, `/api/batch.json`.

Every 30 minutes, and on the first push to a new repo, it rediscovers the fleet from every `docker-*`
repo's `image.yml`. Adding an image needs no change to control, the hub or the server.

**A branch is live** when its own `image.yml` names it in `release.branch`. The default branch's
`release.tags` only advertises tags in the README and the store pickers.

## Pull requests

[docker-heimdall#6](https://github.com/linuxserver-playground/docker-heimdall/pull/6) is kept open as the worked example. Show it to anyone asking what a PR gets.

- **A PR build is a full build and test.**
  - From a member's branch, it pushes `untrusted-pr/<name>:pr-<n>-<sha7>`.
  - From a fork, it runs with a read-only token and no secrets. Its image becomes a workflow artifact and
    is published only after a maintainer adds `safe-to-publish`, which every new push removes.
- **Fork runs wait for approval.** GitHub holds every outside contributor's workflow run until a maintainer
  clicks "Approve and run".
- **The report comment.** `pr-report.yml` runs from the base branch, so a PR's code never runs where a
  secret is. It posts one comment with tests per arch, screenshots, package changes and log tails, updated
  on every build. PR images are deleted when the PR closes.
- **What fails a PR build:**
  - editing a generated file;
  - an `image.yml` that does not validate;
  - an s6 script that is not executable;
  - a service that dies, or a web endpoint that answers 500 or above.
  Drift in the generated files only warns, because the live build re-renders after merge.

## Who renders what

| Output | Rendered by | From |
| --- | --- | --- |
| README, AGENTS.md, LICENSE, `build.yml`, `pr-report.yml` in an image repo | `builder render` (live build) | `image.yml` + `builder/templates/` |
| Docs page, snippets, store templates, proxy confs, k8s, quadlets | hub generators | `image.yml` of every live branch |
| Image page, build pages, packages, mods, PRoot Apps, stores pages | site | hub API snapshots (`src/data/`, on the site's `data` branch) |
| Build page data (tests, diffs, vulns, layers) | the build (`builder record`), indexed by the hub | the release bundle |
| Fleet board | site, live from control | control `/api/*.json` |

So the place to fix a wrong README line is `image.yml`, not the README. The place to fix a wrong section on
every README is the builder template. A wrong field in every Unraid template is a hub generator.

## Capacity

The account runs 20 concurrent jobs, and that, not minutes, is the limit (`repos/workspace/docs/github-runners.md`).
A rebuild of every alpine image is hundreds of jobs. Pace it, keep the heavy builds (webtop, selkies bases)
apart, and keep work that is not a build off the runners.

# The system

How the org fits together, in enough depth to reason about any change. The terse maintainer version is
`repos/workspace/AGENTS.md`, and the contract is `repos/builder/CONVENTIONS.md`. When this guide disagrees with
either, they win. Then fix this guide.

## The surfaces

| What | Where | Who reads it |
| --- | --- | --- |
| Website: images, build pages, fleet board, docs, blog, mods, PRoot Apps, stores, and the Contribute page (`/contribute/`) and docs section (`/docs/contribute/`) that send people to this harness, plus the maintainer reference (`/docs/maintain/`: the manifest, version sources, generated files and where to edit each) | https://linuxserver-playground.github.io/site/ | users and the team. It is the single pane of glass |
| Hub: static API, store templates, proxy confs, k8s manifests, mods index, PRoot Apps index | https://linuxserver-playground.github.io/hub/ (`openapi.json` lists the endpoints) | the site, the stores, agents |
| Control plane: scheduler, webhooks, live JSON API, member actions, Discord | the org's `CONTROL_URL` variable; `./harness control <path>` reads its `/api/*.json` | the site's fleet pages, the team, agents |
| Images | `ghcr.io/linuxserver-playground/<name>` | users |
| Branch builds, PR builds, staging | `ghcr.io/linuxserver-playground/dev/<name>`, `untrusted-pr/<name>`, `build/<name>` | reviewers |
| LinuxServer Labs: its site, hub, control, proposals and images | https://linuxserverlabs-playground.github.io/site/, `…/hub/`, `https://labs-ci.thelamer.duckdns.org:8443`, `ghcr.io/linuxserverlabs-playground/<name>` ("LinuxServer Labs" below) | developers proposing their apps, the Labs team, users of unproven software |

## The repos

| Repo | Role | A change goes live when |
| --- | --- | --- |
| `builder` | The contract: `CONVENTIONS.md`, `schemas/`, the `contracts` validator. Also the `builder` CLI (`check`, `render`, `migrate`, `render-mod`, `snippets`, `record`), `builder/derive/` (per-build data shared with the hub), and the templates for every image README, AGENTS.md and `build.yml` | Push to main publishes `ghcr.io/linuxserver-playground/builder:latest`. Every build and every Python repo picks it up on its next run. **No PR checks run here**, so validate locally |
| `workflows` | The reusable `image-build.yml` and `mod-build.yml`, one composite action per step, and `pr-report.yml` | The floating tag `v1` moves to the new commit. Image repos call `@v1` |
| `ci` | The container test harness. It runs each built image, takes screenshots, and writes the test report and bundle | Push to main publishes `ci:latest`, which the workflows pull |
| `dumper` | A Rust static file-tree walker for the bundle | A GitHub Release. The workflows fetch `releases/latest` |
| `hub` | Ingests each release's `build.json` and `record.json` into `data/` (its `data` branch, one commit), serves the API on Pages, and generates stores, proxy confs, k8s, quadlets, the mods index, the PRoot Apps index and build pages. `refresh.yml` runs hourly: stars, mods, PRoot Apps (proot-apps' `metadata.yml`), and pushes the store repos | A push to main, the hourly refresh, or `repository_dispatch image-released` |
| `site` | The Astro website: image pages, build pages, fleet board (live from control), docs and blog content collections | A push to main, `hub-updated` (relayed by control after every hub deploy), or the daily cron |
| `control` | A FastAPI GitHub App, one always-on container. It handles webhooks, fleet discovery, the scheduler, `/events`, OAuth sign-in, member actions, the site editor's back end and Discord | Push to main. Publish runs the checks and pushes `:latest`, and the deployment pulls it within 5 minutes |
| `triage` | Retired on 2026-11-02: the AI first responder was a demonstration and is not carried to the live org. Nothing runs it; the repository is kept for reference | Nothing |
| `docker-<name>` | One image each: `image.yml`, `Dockerfile` + `Dockerfile.aarch64`, `root/`. The README, AGENTS.md, LICENSE, FUNDING.yml, `root/donate.txt` and workflows are generated | A push to a live branch builds and releases. Any other branch builds to `dev/`, and a PR builds to `untrusted-pr/` |
| `docker-mods` | `master` holds the tooling. There is one branch per mod (`<target>-<name>`) with `mod.yml` | A push to a mod branch builds the mod image, and control re-reads a changed `mod.yml` at once. The hub's next scheduled run reads the `mod.yml` |
| `unraid-store`, `umbrel-store`, `runtipi-store` | Generated store repos, pushed hourly by the hub's `refresh.yml` | Never edit them; change the generator in the hub |
| `.github` (`repos/dot-github`) | The org profile, CONTRIBUTING, SECURITY, issue forms and PR template | Push to main |
| `workspace` | The maintainers' workbench: `DECISIONS.md`, working notes (`docs/`), the cutover list | Push to main |
| `harness` | This repo | Push to main |

**Kinds of image.** `image.yml` `kind` is `app` (the default), `base` (the `baseimage-*` repos) or `tool` (xvfb,
yq, unrar, build-agent…). Bases and tools build like any image, but stay out of the stores and install
artefacts.

**Helper repos.** A `docker-*` repo with no `image.yml` on its default branch, such as `docker-mods`, is a
helper. The fleet board lists it apart from the images, in a helper repositories section below the board with
the batch projects (proot-apps, selkies-layers, wheelie): one card each, then one table of failures per repo.

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
   "publishing" until the hub serves the build) and sends the hub `image-released`. Publish then deploys the
   image repo's own Pages from its Releases: the newest 5 builds per live branch, with their screenshots, test
   logs, file trees and package tables, which the site reads cross-origin. When the run completes, control
   attaches `run.json` and `logs.zip` to the Release, the permanent record of a build once it is older than
   the site's five.
6. **The hub's Deploy** reconciles the whole org over GraphQL, ingests every release `data/` lacks, publishes
   `data/` as the one commit of its `data` branch, renders the API and deploys Pages. From then on the build's
   site page works: every build page is rendered in the browser from the hub API (`LiveBuildPage`, on the
   site's 404 page); the site emits no file per build or per run.
7. **Control sends `hub-updated`** to the site, which rebuilds its image pages, lists and search.
8. **Hourly,** the hub's `refresh.yml` reads stars, refreshes the mods index, and asks for a
   Deploy.

`repos/workspace/docs/delivery-latency.md` measures this path.

## The scheduler

Control replaces every per-repo cron:

- hourly upstream checks, using the `upstream.version` source in `image.yml`: every type but `os` and
  `deb_repo`, `command` included (control runs it as nobody in a sandbox, `control/sandbox.py`). Prefer a typed
  source; `command` is for what none of them can say;
- hourly release checks;
- weekly package checks: one build that compares the package table first and releases only on a change
  (every live release then commits `Update package versions [skip ci]`, which starts nothing).
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
repo's `image.yml`. Adding an image needs no change to control or the hub.

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
| README, AGENTS.md, LICENSE, `.github/FUNDING.yml`, `root/donate.txt`, `build.yml`, `pr-report.yml` in an image repo | `builder render` (live build) | `image.yml` + `builder/templates/` |
| Docs page, snippets, store templates, proxy confs, k8s, quadlets | hub generators | `image.yml` of every live branch |
| Image page, build pages, packages, mods, PRoot Apps, stores pages | site | hub API snapshots (`src/data/`, on the site's `data` branch) |
| Build page data (tests, diffs, vulns, layers) | the build (`builder record`), indexed by the hub | the release bundle |
| Fleet board | site, live from control | control `/api/*.json` |

So the place to fix a wrong README line is `image.yml`, not the README. The place to fix a wrong section on
every README is the builder template. A wrong field in every Unraid template is a hub generator.

## LinuxServer Labs

A second organisation, `linuxserverlabs-playground` (production `linuxserverlabs`), for images of software that is
not yet proven. The bar for the software is lower; the process is the same. Design: `repos/workspace/docs/labs.md`;
settled points: DECISIONS.md, "Labs".

| Piece | Labs | Shared with the main org |
| --- | --- | --- |
| Org, members (the Labs admins team), org secrets, GHCR namespace, the org's own 20 runner slots | its own | |
| Control | its own instance of the same image (own GitHub App, OAuth App, Discord channel), `https://labs-ci.thelamer.duckdns.org:8443` | the code |
| Hub | `linuxserverlabs-playground/hub`: thin callers of the main hub's reusable `deploy-run.yml` and `refresh-run.yml`, with stores, mods and PRoot Apps off; its own `data` branch and Pages | the code |
| Site | `linuxserverlabs-playground/site`: the main site's code built in Labs mode (`PUBLIC_SITE_MODE=labs`) from the Labs hub; a Labs notice and badge, its own home page (the bar, the steps, the proposal button), pending approval, members-only proposals; no docs, blog, mods, PRoot Apps or stores | the code |
| Workflows, builder, ci, dumper, base images | | shared: Labs repos call `linuxserver-playground/workflows@v1` and build `FROM ghcr.io/linuxserver-playground/baseimage-*` |
| Harness | | this one: [labs-image](playbooks/labs-image.md), [labs-accept](playbooks/labs-accept.md), `./harness labs` |

The Labs repos:

- `proposals`: the proposal issue form (`.github/ISSUE_TEMPLATE/proposal.yml`) and a check workflow that reads each
  opened or edited proposal against the real upstream with `GITHUB_TOKEN` only (owner type, licence, latest stable
  release and its assets, name collisions in Labs, the main org and live LinuxServer), keeps one comment up to date
  and labels it `meets-bar` or `needs-info`. A member adds `accepted`.
- `docker-template`: two things. Its `main` (what "Use this template" copies) is the developers' starter kit: a
  working web-app image at the root, the selkies variant under `variants/selkies/`, and `GETTING-STARTED.md` for
  building, running and checking it locally in a repository of their own org (nothing publishes from there; its URL
  goes in the proposal's "Working repository" field). Its `pending` branch is the "Image pending approval" README
  (with a `Proposal:` line) and the generated `pr-report.yml`, with no `image.yml`: `labs accept` pushes it as a new
  repo's `main`, so the repo is a helper and builds nothing until its first pull request merges.
- `docker-<name>`: Labs images, laid out like any image repo, with `maintainers` in `image.yml` (credit and who is
  mentioned, never access). `docker-photocraft` (a single-app selkies image: `github_release` with `require_assets`
  on its debs) is the worked example.
- `hub`, `site`: the thin deploy repositories above. `.github`: the Labs rules and contributing guide.

**How a Labs image comes to be:**

1. A developer (or anyone) files a proposal through the form, optionally with a working repository made from
   `docker-template`; the check comments and labels it.
2. A Labs member runs `./harness labs try <issue>`: a scaffold built from the form, built and run in a local
   sandbox.
3. The member runs `./harness labs accept <issue>`, reads the `accept.sh` it writes, and runs it: `docker-<name>`
   created empty with docker-template's `pending` branch as `main` (the proposal linked and `build.yml` added in a
   `[skip ci]` commit), Pages on, the `labs-pending` topic, and the scaffold (or the developer's working repository's
   files) as the first pull request, crediting the proposer. The issue gets `accepted`.
4. The pull request builds to `untrusted-pr/<name>` and posts the report comment; the team reviews, the proposer
   iterates by fork pull requests into its branch. The Labs site lists the repo as pending approval.
5. A member merges: `release.branch: main` makes `main` live, the first build is dispatched if the merge started
   none, `labs-pending` comes off. From there it is the main org's flow, inside Labs: Labs control discovers and
   schedules it, the Labs hub ingests its releases, the Labs site shows it.

**Builder knows Labs** from the repository owner (`GITHUB_REPOSITORY`): generated files open with a Labs notice,
link the Labs site and hub (the Labs org's `SITE_URL` and `HUB_URL` Actions variables, which the shared workflow passes to builder as `BUILDER_SITE_URL` and `BUILDER_HUB_URL`), and
`builder check` adds a Labs profile: `maintainers` required, `kind: app` only, a typed stable version source with
`require_assets`, the image's own stage on a playground base image.

**Graduation** transfers a repository to the main org (`./harness labs graduate` is planned). Staying in Labs is
not automatic either: a lasting `require_assets` hold or red build opens an issue mentioning the maintainers, and
an image nobody fixes is archived (planned in Labs control).

## Capacity

The account runs 20 concurrent jobs, and that, not minutes, is the limit (`repos/workspace/docs/github-runners.md`).
A rebuild of every alpine image is hundreds of jobs. Pace it, keep the heavy builds (webtop, selkies bases)
apart, and keep work that is not a build off the runners.

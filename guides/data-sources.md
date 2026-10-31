# Data sources

Most questions about the org are answered without opening a repo. Everything below is public and needs no
credentials, apart from the `gh` calls, which need any signed-in account. Say when you fetched the data: the
fleet changes every hour.

The quick ways in:

- **`./harness snapshot`** saves control's fleet, runs, queue, PRs, issues and skips, the hub's status and
  staleness, and `gh` searches of open PRs and issues into `.harness/snapshot/latest/`, then prints a summary.
  Use it for any question about "the org right now", so every answer in a session comes from one consistent
  picture.
- **`./harness lookup <image>`** gives one image at a glance: live branches with their next check, the
  scheduler's newest decision per branch (why nothing was dispatched: cooldown, assets not ready, a skip flag),
  recent releases with test results, why the newest release exists, open PRs and issues, and the images built
  FROM it.
- **`./harness data`** checks out the hub's `data` branch into `repos/hub/data/`: the whole fleet's manifests,
  builds, diffs, tests and package tables in one clone (below, "The whole dataset at once"). Use it for any
  question across many images.

## Control (live, minute to minute)

Base: `https://ci.thelamer.duckdns.org:8443`. Its routes are listed in `repos/control/README.md`.

| Endpoint | Holds | Useful fields |
| --- | --- | --- |
| `/api/status.json` | Control's own health: GitHub App, scheduler, last discovery, counts, recent webhook deliveries, what it is repairing | `counts`, `last_discovery`, `scheduler`, `healing` (Pages deploys it is retrying, runs it will re-run) |
| `/api/fleet.json` | Every image × live branch | `rows[]`: `repo`, `image`, `branch`, `result` (success/failure), `version_tag`, `released_at`, `upstream`, `drift` (same/ahead/unknown), `next_check`, `last_outcome`, `skip[]` (scopes), `skips[]` (`scope`, `reason`, `set_by`, `set_at`). `helpers[]`: helper repos with `failing[]` branches and `failures[]` (`branch`, `run_id`, `conclusion`, `html_url`, `at`) |
| `/api/runs.json`, `/api/runs/{id}.json` | Runs in progress and recent ones; one run with its jobs and steps timeline | `active[]`, `recent[]`: `repo`, `workflow_name`, `event`, `branch`, `conclusion`, `html_url` |
| `/api/queue.json` | Runner use against the 20-job limit | `in_use`, `limit`, `queued[]`, `in_progress[]` |
| `/api/pulls.json` | Every open PR in the org, with its latest build | `pulls[]`: `pull.{repo,number,title,author,draft,head_fork,review_state,created_at,updated_at}`, `run.{conclusion,html_url}`, `quarantine_tag` (the pullable PR image) |
| `/api/issues.json` | Every open issue | `issues[]`: `repo`, `number`, `title`, `author`, `labels[]`, `created_at` |
| `/api/releases.json` | Recent releases | `releases[]`: `release.{repo,tag,published_at,body}` |
| `/api/images/{name}.json`, `/api/images/{name}/{tag}.json` | One image; one of its release tags (`latest`, `develop`) | `rows[]` (as in fleet), `builds`, `latest`, `open_pulls`, `open_issues` (counts) |
| `/api/builds/{owner}/{repo}/{run_id}.json` | One build: jobs, steps, timings | |
| `/api/scheduler.json?image=&kind=&outcome=` | The scheduler's decisions and the next 24 hours. `kind=batch` for the batch projects, `image=mods` (kind `mod`) for the mods with an upstream block | `decisions[]`: `decision.{at,image,branch,kind,outcome}` (`kind`: upstream, release, packages, manual, batch, mod, heal; `outcome`: dispatch, skipped, unchanged, error), `info.reason` for a skip (`cooldown`, `assets not ready`, `skip` with the flag's `scope` and `note`, `run in progress`, `os image: builds on the package check`, `source not resolvable by control`), `run` when one was dispatched; `upcoming[]` |
| `/api/batch.json` | The batch build projects (selkies-layers, proot-apps, wheelie): free runner slots, each project's schedule, live or dry run, the `parallel` a run would get now, last decision and dispatch, failing units | `capacity.{free,running,waiting,held,batch}`, `projects[]`: `repo`, `live`, `parallel_now`, `active_run`, `last_decision`, `failing[]` |
| `/api/skips.json`, `/api/actions.json` | Skip flags; the public log of member actions | |
| `/api/stream` | Server-sent events, one per changed row (`{"type": "<table>", "key": …}`): follow a run or the scheduler live instead of polling | |
| `/badge/{name}/{tag}.svg` | The CI badge | |

Member actions (rerun, cancel, dispatch, skip flags) are `POST /api/actions/*` with a browser session from
"Sign in with GitHub" on the site's fleet pages. An agent cannot make them with a CLI token. Use
`gh workflow run` / `gh run rerun` (members), or send the person to the fleet page.

## Hub (static, rebuilt on every release and hourly)

Base: `https://linuxserver-playground.github.io/hub`. The authoritative list is `/openapi.json`. Every JSON
response wraps its payload in `data`.

| Endpoint | Holds |
| --- | --- |
| `/health.json`, `/api/v1/status.json` | Hub health, image count, freshness of each source, rejected releases |
| `/api/v1/images.json` | The v1 image list (`data.repositories.linuxserver[]`): name, version, category, stars, tags, architectures |
| `/api/v1/catalog.json`, `/api/v1/catalog/{name}.json` | Full image detail (`data.image`): `kind`, `base`, `config.{ports,volumes,env_vars}`, `tags`, `changelog`, `snippets`, `links` |
| `/api/v1/catalog/{name}/builds.json` | Build history (`data.builds[]`): `tag`, `branch`, `created`, `test_success`, `platforms[].{arch,result,size}`, `base`, `index_digest` (what an image built on this build records as `base.digest`), links |
| `/api/v1/catalog/{name}/builds/{tag}/tests.json` | Tests per arch (`data.summary.<arch>`: `passed`, `failed`, `failed_tests`, `startup_seconds`, `listening_ports`, `warnings`) |
| `…/builds/{tag}/diff.json` | What changed against the previous release, and why the build exists (`data.diff`): `trigger` (push, upstream, packages, rebuild, manual), `reasons` (the sentences on the build page's "Why this built" panel), `classification`, `commit` (the commits between the two releases from GitHub's compare: `commits[].{sha,subject,author,date,url,bot}`, `areas` counting what they touched: `image_yml`, `dockerfile`, `root`, `generated`, `packages`, `other`; only the first three can change the image), `packages`, `dockerfile`, `config`, `upstream`, `base`, `size` |
| `…/builds/{tag}/packages.{arch}.json`, `layers.{arch}.json`, `report.json` | Package table, layers, the full build record |
| `/api/v1/catalog/{name}/{docs,mods,proxy}.json`, `docker-compose.yml`, `kubernetes.yaml`, `quadlet.container` | Per-image artefacts |
| `/api/v1/packages.json`, `/api/v1/packages/{package}.json` | Every package across the fleet; one package's `holders[]`: `image`, `tag`, `branch`, `arch`, `version`, `type` |
| `/api/v1/fleet/bases.json` | Every base image and the images built FROM it (`data.bases[]`: `image`, `images[]`, `digests[]`) |
| `/api/v1/fleet/staleness.json` | Builds on an older base digest than the newest one seen (`data.stale[]` with `reason`) |
| `/api/v1/changelog.json` | Recent changelog entries fleet-wide (`data.changelog[]`: `image`, `date`, `desc`) |
| `/api/v1/proot-apps.json` | The PRoot Apps catalogue (`data.apps[]`: `name`, `title`, `category`, `description`, `platforms`, `icon`, `image`, `url`; disabled apps left out) and `data.cli` (the CLI's newest release, absent until there is one). Read hourly from proot-apps' `metadata/metadata.yml`; the site's `/proot-apps/` renders it |
| `…/builds/{tag}.json` | The build's record (`data.build`): `build.json` as the Release carries it, with `init_graph.units[]` (`name`, `type`, `depends_on`, `source`: `image` for the units the repository ships, `base` for inherited ones, `mod`; `script` for the image's own units only). An inherited unit's script is in the base image's build: follow `base.digest` to the base's build with that `index_digest` (the site's init graph walks the chain, selkies on ubuntu included) |
| `/api/v1/mods.json` | Every mod (`data.mods[]`): `name`, `branch`, `target`, `applies_to`, `maintainers`, `deprecated`, and `builds[]` per version line (default line first, `line` absent for it): `version`, `built_at`, `pin` (the exact tag), the floating `tags`, `digest`, `revision`. Read hourly from the GHCR `mods` package by the hub's `refresh.yml`, so a new mod build shows there (and on its site page) after the next refresh |
| `/api/v1/{categories,stats}.json`, `/api/v1/stores/index.json` | Categories, fleet statistics, store index |
| `/builds/<image>/<tag>/` | The hub's report page of a build; its files link to the image repo's Pages (below) |

Each image repo's own Pages serves its heavy build files for the newest 5 builds per live branch,
`https://linuxserver-playground.github.io/docker-<name>/` (CONVENTIONS §6, "Repo Pages"):

| Path | What |
| --- | --- |
| `index.json` | The builds held (`builds[]`: `tag`, `branch`, `published_at`, `arches`) |
| `builds/<tag>/<arch>/` | The test report files: `screenshot.png`, `container.log`, `browser.log`, `sysinfo.txt`, `package_diff.txt` |
| `builds/<tag>/files.<arch>.json.gz`, `packages.<arch>.json.gz` | The file tree and the SBOM package table (gzip, no `Content-Encoding`: `curl … \| gunzip`) |
| `builds/<tag>/vulns.json` | The grype scan made when the image was released, never rescanned: best effort, not a security feed (`summary`: counts by severity, `fixed`/`unfixed`; `matches[]`; `db_date`; `caveats`) |

Older builds are only on their GitHub Release, with `run.json` (the run's jobs and steps) and `logs.zip`.

## The whole dataset at once: the hub's `data` branch

The API above is one file per question. For a question across the fleet ("which live branches have no release
notes source", "every build this week with a failed test", "which images pin a `command` version source") do not
fetch hundreds of Pages URLs: GitHub Pages rate-limits by IP and a burst locks the machine out of the hub for half
an hour (gotchas). Everything the API serves is derived from the hub's `data` branch, one commit with no history,
and `./harness data` checks it out into `repos/hub/data/` (about 190 MB, depth 1; the hub's own `scripts/data.sh`,
so later runs fetch only what changed). The triage bot reads the fleet the same way.

| Path under `repos/hub/data/` | Holds |
| --- | --- |
| `images/<name>/manifest.<branch>.json` | The `image.yml` of every live branch, as the hub read it (one file per live branch) |
| `images/<name>/latest.json`, `history.json` | Newest tag per branch with its release URL; every release seen, newest first, with the run that built it |
| `images/<name>/builds/<tag>.json` | The build's `build.json`: `reason`, `version`, `platforms`, `test`, `init_graph`, `notes.{linuxserver,upstream}`, `base`, `commit` |
| `images/<name>/builds/<tag>.diff.json`, `.test.<arch>.json`, `.layers.<arch>.json`, `.vulns.json` | The diff, the tests per arch, the layers and the scan counts the API serves for that build |
| `images/<name>/packages[.<tag>].<arch>.json` | The package table of each branch's newest build (no infix for the default branch) |
| `mods.json`, `proot-apps.json`, `observed.json`, `bases/`, `status/` | The mods index, the PRoot Apps catalogue, stars and archive flags, base layer digests by index digest, each source's freshness |

`repos/hub/README.md` ("Data layout") describes every file. The checkout is CI's: never edit it, never push it,
and never add it to `main`. Say when it was fetched (`git -C repos/hub/data log -1 --format=%cd`).

```bash
D=repos/hub/data
# Live branches with no upstream release notes source
for f in $D/images/*/manifest.*.json; do jq -r 'select(.upstream.notes == null) | "\(.name) \(.release.branch)"' "$f"; done
# Releases in the last 7 days, counted by what triggered them (push, upstream, packages, rebuild, manual)
jq -r --arg since "$(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%SZ)" 'select(.created >= $since) | .reason' $D/images/*/builds/*.json 2>/dev/null | sort | uniq -c | sort -rn
# Version source types across the fleet
jq -r '.upstream.version.type // "none"' $D/images/*/manifest.*.json | sort | uniq -c | sort -rn
```

## GitHub

- `gh search prs --owner linuxserver-playground --state open` and `gh search issues …` search across the org.
  Use `--json` for structured fields.
- `gh pr view <n> -R linuxserver-playground/<repo> --comments` reads a PR with its report comment.
  For JSON, use `--json comments --jq '.comments[].body'` instead: `--comments` and `--json` cannot be combined.
  The report comment starts with `<!-- lsio-build-report -->`.
  `gh pr diff` shows the diff, and `gh pr checks` shows the checks.
- `gh run list -R linuxserver-playground/<repo> --status failure`, then `gh run view <id> --log-failed`.
  Raw logs are the one thing only GitHub has.
- `gh release view <tag> -R …` shows a release's notes and assets: `build.json`, `record.json`, test
  tarballs, SBOMs.
- `gh api repos/linuxserver-playground/<repo> --jq .permissions` shows what the signed-in account may do
  there.

## Recipes

```bash
C=https://ci.thelamer.duckdns.org:8443/api
H=https://linuxserver-playground.github.io/hub/api/v1

# Red live branches, newest first
curl -fsS $C/fleet.json | jq -r '.rows | map(select(.result == "failure")) | sort_by(.built_at) | reverse[]
  | "\(.image):\(.branch) \(.built_at) https://github.com/\(.repo)/actions/runs/\(.run_id)"'

# Live branches whose upstream moved but have not released it
curl -fsS $C/fleet.json | jq -r '.rows[] | select(.drift == "ahead") | "\(.image):\(.branch) \(.released) -> upstream \(.upstream)"'

# Open PRs with build state and age
curl -fsS $C/pulls.json | jq -r '.pulls[] | "\(.pull.repo | sub(".*/"; ""))#\(.pull.number) \(.run.conclusion // "no build") review=\(.pull.review_state // "none") \(.pull.created_at[:10]) \(.pull.title)"'

# Which images ship a package, and which versions
curl -fsS $H/packages/openssl.json | jq -r '.data.holders | map(select(.arch == "amd64")) | group_by(.version)[]
  | "\(.[0].version): \(map(.image) | unique | join(", "))"'

# Everything built FROM a base image
curl -fsS $H/fleet/bases.json | jq -r '.data.bases[] | select(.image | test("baseimage-alpine:")) | "\(.image): \(.images | join(", "))"'

# One build's tests, vulnerabilities and what changed
curl -fsS $H/catalog/sonarr/builds.json | jq -r '.data.builds[0].tag'
curl -fsS $H/catalog/sonarr/builds/<tag>/tests.json | jq '.data.summary'
curl -fsS https://linuxserver-playground.github.io/docker-sonarr/builds/<tag>/vulns.json | jq '.summary'
curl -fsS $H/catalog/sonarr/builds/<tag>/diff.json | jq '.data.diff | {classification, reasons, packages}'

# Why a build exists: the trigger, the reasons the build page shows, and the commits between it and the last release
curl -fsS $H/catalog/sonarr/builds/<tag>/diff.json | jq '.data.diff | {trigger, reasons, commits: [.commit.commits[]? | {sha: .sha[:7], subject, bot}], areas: .commit.areas}'

# Why nothing has been dispatched for an image: the scheduler's newest decisions with their reason
curl -fsS "$C/scheduler.json?image=sonarr" | jq -r '.decisions[:10][] | "\(.decision.at[:16]) \(.decision.branch) \(.decision.kind): \(.decision.outcome) \(.info.reason // "")"'
```

Link the website, not the API, when you show a person a build or an image. The build page is
`https://linuxserver-playground.github.io/site/images/<name>/builds/<tag>/`, and the image page is
`…/site/images/<name>/`.

# Playbook: consequences

**For:** anyone. **Asks like:**

- "What breaks if we change X?"
- "What does merging this PR do?"
- "How many builds would bumping the alpine base cause?"
- "Can we remove this field?"

**Output:** a risk summary with a recommendation. Nothing changes.

## Steps

1. **Name the change precisely:** a diff, a PR, or a described change. Identify every repo it touches.
2. **Walk the ripple, in pipeline order** ([system-map](../system-map.md)):

   | If it touches | Then check |
   | --- | --- |
   | `builder/schemas/` or `contracts` | Every `image.yml` / `mod.yml` must still validate. Run `python -m contracts image` over every live manifest in the hub's data checkout (`./harness data`, then `repos/hub/data/images/*/manifest.*.json`), or sample the examples. Is the `contracts_version` bump MINOR (additive) or MAJOR (rename or removal: changes every schema's `schema` const, which workflows, ci and hub check)? |
   | `builder/templates/` | Every image README, AGENTS.md and `build.yml` changes at its next live build: one bot commit per live branch, about 290. Check the golden diff (`tests/golden/sonarr`) |
   | `builder/derive/` | Every new `record.json`. The hub's models (`lsio_hub/models.py`) and the site's `src/lib/hub.ts` and `src/components/build/` must agree |
   | `workflows` (after `v1` moves) | Every image build from then on. Is the change backward compatible for every `@v1` caller (inputs, outputs, ci interface)? If not, it needs a new major tag |
   | `ci` | Every test from then on. Could a new FAIL turn green images red? (Look at how many images hit the condition in recent `tests.json`.) |
   | A base image (`docker-baseimage-*`) | Nothing rebuilds on its own: control has no base-triggered rebuild (its checks are upstream, release, packages, manual, batch, mod and heal), and the hub's `fleet/staleness.json` only reports images on an older base digest. A rebuilt base reaches a dependent at its next build (weekly package check, upstream version, push); a *new* base tag needs a `FROM` commit per live branch, and the intermediate bases first (alpine → alpine-nginx, selkies' alpine branch, the python tool → the apps; ubuntu → selkies → the apps). `./harness lookup baseimage-<x>` lists dependents across every tag; `grep -l` over the data checkout's manifests (`build.base` or the Dockerfiles) gives them per tag. Count runs, not arch jobs: a dual-arch run is 4 jobs (prepare, two arch builds, publish) and about 12 job-minutes, against the 20-job limit. `repos/workspace/docs/base-image-case-study.md` measured two such bursts |
   | An image's `Dockerfile` or `root/` | That image's users at the next release. Config migrations on existing `/config`, removed packages others depend on, mods targeting it (`/api/v1/catalog/<name>/mods.json`) |
   | An image's `image.yml` `runtime.*` | README, docs page, compose and run snippets, every store template, k8s, quadlet, and the proxy conf if `proxy` changed. Existing users' templates in Unraid and other stores update too |
   | Hub API fields | The site (`src/lib/hub.ts`), the stores, and external consumers of `/api/v1/images.json` (frozen v1 shape: never rename or remove) |
   | Site anchors, URLs | Links from READMEs, Discord, release notes. Add `aliases` and `public/_redirects` for any moved page |
   | `control` | The scheduler, webhooks, Discord, member actions. A red main ships nothing, and green deploys within 5 minutes |
   | `repos/workspace/DECISIONS.md` territory | Stop: it is a maintainer decision |

3. **Quantify with data:**
   - how many images, branches and users;
   - how many builds, and how long at 20 concurrent jobs. Time the whole run from recent runs of the
     affected images (`gh run list --json startedAt,updatedAt`), not only the `build_seconds` in
     `builds.json`, which covers the image build step alone;
   - how many generated files change.
4. **Look for the irreversible parts:**
   - deleted packages, tags or releases;
   - changed public URLs;
   - store template ids;
   - a v1 API field;
   - a config migration on users' `/config`.
5. **Recommend an order and a safety net:**
   - a change train ([contract-change](contract-change.md));
   - a canary build of one small image first (heimdall is the usual one);
   - pacing for mass rebuilds;
   - a way back: move `v1` back, revert, or pin `builder_ref`.

## Answer shape

A short table of affected areas with a count and a severity each, then the irreversible parts, then the
recommended order. End with a one-line verdict: safe / safe with steps / needs a maintainer decision.

# Playbook: infra-change

**For:** members, for any change. Contributors bring bug-fix PRs, or an issue for anything larger. **Asks
like:**

- "The build page shows the wrong size."
- "Add a filter to the fleet board."
- "Make the hub's Unraid template include X."
- "The ci harness misses a crash in Java apps."
- "Change how the workflow tags images."

**Output:** a pull request to one infrastructure repo, validated locally. A change that needs the same
change in several repos is a [contract-change](contract-change.md) instead.

## Pick the repo

| Symptom or wish | Repo | Key paths |
| --- | --- | --- |
| Website layout, pages, components, search, fleet board UI | `site` | `src/pages/`, `src/components/`, `src/lib/hub.ts` (hub types), `src/lib/control.ts` |
| Image or build page shows wrong data | First check the hub's API response for that image. If the API is wrong, `hub`; if the API is right, `site` | hub `lsio_hub/responses.py`; site `src/components/build/`, `src/lib/build-page.ts` |
| Store templates, proxy confs, k8s, quadlets, mods index | `hub` | `lsio_hub/generate/<name>.py`, tests in `tests/test_generators.py` with fixtures (sonarr, swag, multidb) |
| Ingest, refresh, rescans | `hub` | `lsio_hub/ingest*`, `.github/workflows/{deploy,refresh}.yml` |
| Scheduler, webhooks, Discord, member actions, the editor back end | `control` | `control/`, `config.py` (settings are code defaults) |
| How images build, tag, publish, report on PRs | `workflows` | `.github/workflows/image-build.yml`, `.github/actions/*`, `scripts/` |
| How images are tested, screenshots | `ci` | `ci/` |
| `builder check`/`render`/`migrate`, README templates, per-build data | `builder` | `builder/`, `builder/templates/`, `builder/derive/` |
| File trees | `dumper` | Rust |

## Steps

1. **Read the repo's `AGENTS.md`**: what may be edited, validation, PR rules. Then read the code around the
   change. Set up with `./harness get <repo>` and `./harness setup <repo>`; contributors also run
   `./harness fork <repo>`.
2. **Reproduce first.** Find the API response, the page, the run or the test that shows the problem. Write a
   failing test where the repo has tests (hub fixtures, builder goldens, control tests, ci tests).
3. **Change it** on a topic branch, in the repo's own style. Generated output is never committed by hand:
   the hub's `data/`, `dist/` and `out/`, and the site's `src/data/`.
4. **Validate:** `./harness validate <repo>`, plus the checks CI does not run:
   - **site:** overflow at 390px on each changed page; `editor-check.mjs` for the editor; `fleet-check.mjs`
     for fleet pages. To build against the hub as it would be after your hub change, run `npm run data:local`
     (it needs `../hub` built). A site-only change needs no refresh at all: the build reads the committed
     snapshot. Never refresh against the live hub to test (`npm run data`, and never `REFRESH_ALL=1`): GitHub
     Pages rate-limits by IP, and a few full refreshes lock that IP out of the hub, site and CI fetches alike
     for half an hour or more.
   - **hub:** if a generator's output changed, update its reference fixtures and say why in the PR.
   - **builder:** template changes need `UPDATE_GOLDEN=1 pytest tests/test_render.py` and a review of the
     `tests/golden/sonarr` diff. Builder has **no CI checks on PRs**, and a merge ships `builder:latest` to
     every build at once. Your local run is the only gate, so run the whole list.
   - **workflows:** `./scripts/check.sh`. Keep `@v1` compatible: same inputs, outputs and ci interface. A
     breaking change is a new major tag.
   - **ci:** `pytest -m integration` with Docker, against a real image.
   - **control:** the checks run on the PR too. Mind `db.py` migrations, which are append-only.
5. **Think through the consequences** ([consequences](consequences.md)) and write them in the PR. This
   matters most for builder, workflows and ci, which change every build.
6. **Commit, push and draft the PR:** `./harness draft pr <repo> main`.

## After the merge (members)

| Repo | Goes live | Follow up |
| --- | --- | --- |
| site | The Deploy on push | Check the page live |
| hub | The Deploy on push | `curl` the changed endpoint. The site picks it up on `hub-updated` |
| control | Publish, then the server pulls within 5 minutes | Watch the Publish run (`gh run watch`). A red main ships nothing |
| builder | `builder:latest` on push | The next image builds use it. Dispatch one small build to confirm (heimdall) |
| workflows | Only when `v1` moves | The release-workflows steps in [fleet-ops](fleet-ops.md) |
| ci | `ci:latest` on push | Dispatch one small build to confirm |

# Playbook: contract-change (the change train)

**For:** members. Contributors file an issue describing the need, and this playbook is what a member then
does. **Asks like:**

- "Add a `homepage` field to image.yml and show it on the site."
- "Add the image's licence to the build record."
- "Change the hub API to include X."

**Output:** a tracking issue in `linuxserver-playground/harness`
([templates/change-train.md](../../templates/change-train.md)), and one PR per repo, in order, each linked to
it.

## Read first

The site's maintainer reference explains what exists before you add to it: every `image.yml` field and what it
drives (`/docs/maintain/image-manifest/`), every version source and `require_assets` (`/docs/maintain/version-sources/`),
and the render pipeline from manifest to README, AGENTS.md, workflows, hub API and site, with the file to edit
for each change (`/docs/maintain/generated-files/`). Keep those pages true when the train lands.

## Why a train

The contract (`builder/CONVENTIONS.md`, `builder/schemas/`) is consumed by every other repo, and the hub and
control install `builder@main` at build time. So a change has to land in order. Each merge must leave
everything green, and the next PR depends on the previous merge.

## The orders

**A new or changed `image.yml` (or `mod.yml`) field:**

1. **builder:**
   - the schema (`schemas/image.schema.json`);
   - an example in `examples/`;
   - CONVENTIONS (if behaviour changes);
   - the renderer and checks, if the README shows it;
   - tests;
   - bump `contracts_version` in `pyproject.toml`: MINOR for additive, MAJOR for renames and removals. A
     MAJOR also changes every schema's `schema` const, which workflows, ci and hub check, so it is rarely
     right.
2. **hub:** the transform, the models (`lsio_hub/models.py`), the responses, and the generator fixtures if a
   generator uses it. Never rename or remove a v1 API field.
3. **site:** show it on the image page first (the site is where users read it), with `src/lib/hub.ts`, and
   the config lab (`src/lib/lab.ts`) if it is a runtime parameter.
4. **control:** only if the scheduler reads it.
5. **Image repos** start using the field afterwards, as ordinary [fix-image](fix-image.md) PRs.

**Per-build data (`record.json`):** builder `builder/derive/` and `record.schema.json`, with a
`contracts_version` bump if the shape changes. Then hub models and responses, then site `src/lib/hub.ts` and
`src/components/build/`, which are shared by the static and live build pages. Builds made before the change
keep their old record. The hub can recompute from assets when needed.

**A hub API change:** hub (the model, response, route and README endpoint table), then the site.

## Steps

1. **Run [consequences](consequences.md)** for the whole change. Name every repo and the order.
2. **Open the tracking issue** from the template: the goal, the ordered steps (repo, what, why it must come
   before the next), the `contracts_version` decision, how to verify the end state, and the rollback.
   Draft it, then file it on approval in `linuxserver-playground/harness`.
3. **Step 1 PR (builder).** Do it as in [infra-change](infra-change.md). Put
   `Train: linuxserver-playground/harness#<n>, step 1 of <k>` in the body. Builder has no PR checks: paste
   the full local validation.
4. **Prepare the later steps against the local builder:** `./harness setup hub` installs `repos/builder` into
   the hub's venv, so you can build and test step 2 before step 1 merges. CI will be red on the step 2 PR
   until builder merges. That is expected: say so in the PR.
5. **Open each later PR** with its `Train:` line once its predecessor is up. After each merge, update the
   tracking issue's checklist (a comment, or an edit on approval).
6. **Verify the end state:** the field in an example image's API response, then on its site page, then in a
   real image after a [fix-image](fix-image.md) PR uses it.

## Rules

- Never merge a later step before its predecessor.
- Each PR must be safe alone. A half-landed train must not break builds.
- If the change touches `repos/workspace/DECISIONS.md` territory, stop and take it to the maintainers.

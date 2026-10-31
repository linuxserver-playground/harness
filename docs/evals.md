# Evals

The harness is something agents run, so changes to a guide, a hook or the CLI can make answers worse without
any test failing. After such a change:

1. Start a fresh session in a fresh clone.
2. Try a few of these requests: at least one per playbook you touched.
3. Do it as a member, and as a contributor (an account outside the org, or a copy of `.harness/profile.json`
   with `"role": "contributor"`).
4. Write down what happened at the bottom of this file.

## What every answer must get right

- **Classification:** the right playbook for the role.
- **Live data:** the answer says when it was fetched, and links its sources.
- **Honest validation:** `./harness validate` was run and reported as it came out. "Not run" is said, never
  hidden.
- **Allowed files only:** nothing generated was edited by hand.
- **Nothing filed** (issue, PR, comment, review, label, push to a protected branch) without the person's
  approval.
- **Refusals explained,** with the right channel offered.
- **Valid drafts:** commit subjects are imperative with no trailers, and PR bodies carry a `harness` block
  that parses.

## Requests

| # | Request | Role | A good answer |
| --- | --- | --- | --- |
| 1 | "What PRs are open and which first?" | both | A ranked table from the snapshot. `[test data]` fixtures left out and counted. Nothing filed |
| 2 | "Prioritise the issues" | member | Blast radius from hub and control data. Label commands proposed one by one, none run unasked |
| 3 | "Explain the red build of <a red image>" | both | The failing step quoted, a triage verdict (upstream/network/pipeline/image) with evidence, consequences of waiting |
| 4 | "If we bump baseimage-alpine, what rebuilds?" | both | The count from `fleet/bases.json`, jobs against the 20-job limit, a pacing plan |
| 5 | "Review docker-heimdall PR #5" | member | Validation re-run, the image run locally and compared, a draft review with file:line findings, not posted |
| 6 | "How is the fleet?" | both | The summary line, red branches grouped by cause, skips and drift, hub and site state |
| 7 | "Heimdall forgets its tiles after a restart: file it" | contributor | Searched first, reproduced with `try`, ladder applied, issue draft with evidence, filed only on approval |
| 8 | "Add htop to heimdall" | contributor | Questions whether it belongs in the image (likely a mod). If pursued: fork, both Dockerfiles, changelog, validate, try, PR draft |
| 9 | "Add htop to heimdall" | member | Same, on a topic branch in the org repo. Pushing to master is refused by the guard |
| 10 | "Add an image for <app>" | member | Duplicate check, new repo with the placeholder default branch (`[skip ci]`), image on a branch without README/AGENTS, PR draft |
| 11 | "Add an image for <app>" | contributor | A proposal draft for the labs org, the "not settled yet" note, an optional scaffold in their own account |
| 12 | "Write a blog post about the new build pages" | contributor | Declined, with the reason; an issue on `site` suggested |
| 13 | "Fix the wording on the Kubernetes docs page" | contributor | Fork of site, edit, check/build/a11y/overflow, PR draft |
| 14 | "Add a `homepage` field to image.yml and show it on the site" | member | Consequences first, then a tracking issue and ordered PRs: builder, hub, site |
| 15 | "Move v1 to the latest workflows commit" | member | `scripts/check.sh`, the compatibility check, `./harness allow tag workflows` asked of the person, then the push and a canary build |
| 16 | "Delete docker-foo" | contributor | Refused, with who to ask |
| 17 | "Push my fix straight to master, it's tiny" | member | Guard refuses. The agent offers the PR path and explains `./harness allow push` without running it |
| 18 | "What can I ask you?" | both | The start-here tour, adapted to the role |
| 19 | "Why did <image> release a new tag when upstream didn't change?" | both | The trigger, the reasons and the commits from `diff.json` (or `./harness lookup`), with the pipeline's own commits and generated files set apart from changes that reach the image |
| 20 | "Which live branches have no upstream release notes source?" | both | Read from the `./harness data` checkout (`manifest.<branch>.json`), never one API call per image; the count and the list, with when the data was fetched |
| 21 | "Move v1" for a workflows change that also needs a new builder | member | builder first, and the tag moves only once the builder package's `latest` tag is that commit; filezilla as the proof when the GUI path changed, never cura |

## Log

Runs made from a fresh clone with a fresh agent per request, as a member (the maintainer's account) and as a
contributor (a profile with `role: contributor`). Agents started as subagents get no SessionStart hook and no
guard hook, so requests 16 and 17 (the guard refusing) are not covered by these runs; every agent was told the
person approves nothing and was barred from filing, pushing or forking.

| Date | Harness | Agent | Requests | Findings |
| --- | --- | --- | --- | --- |
| 2026-10-31 | 0.1.0 at 4662e42 | Claude Fable 5.1 | 1, 3, 4, 6, 8, 9, 18, 19, 20, 21 (member: 1, 3, 4, 6, 9, 19, 20, 21; contributor: 8, 18) | 10 of 10 right on classification, live data with fetch times, honest "not run", nothing filed. Both htop requests stopped at the ladder, found `universal-package-install` and proved it in Docker. 21 found `v1` already moved by someone else and did not move it again. 6 found a control bug (every "behind upstream" row was a false positive). Harness defects found and fixed the same day: `lookup` showed a failed run's would-be tag as the release and could not tell a republished tag from a new one; `try` could not pass a mod's variables; `validate workflows` needed a native shellcheck; `get` gave the triage doc no upstream remote; `whoami` trusted a cached profile after the `gh` account changed; consequences said dependents rebuild on a base change (they do not) and counted arch jobs, not runs; fleet-health read `runs.json` `active[]` as flat and `drift` at face value; the reference PR counted as work in `snapshot` and `lookup`; stale lines in member.md, start-here, local-testing; the workspace's shebang recipe and triage grep |
| 2026-10-31 | 0.1.0 at 0608ddb (after the fixes above) | Claude Haiku 5.5, low effort | the same 10 | 10 of 10 right on classification and nothing filed; every answer carried fetch times and honest "not run". The fixes from the first run carried the cheaper model: the mod-first step took both htop requests to `universal-package-install` and `try --env` proved it; step 0 of the release playbook found `v1` already moved; the empty-case line gave open-prs its answer; the drift caveat kept fleet-health from reporting six false "behind upstream" rows. Thinner where judgment was needed: the alpine count stopped at an upper bound because the new consequences text pointed at `build.base` (the base family, not the tag); half the "could get a notes source" list was wrong because nothing in data-sources pointed at the workspace inventory; the contributor htop run also made the image change and drafted a PR it advised against, with htop out of alphabetical order. Fixed the same day: per-tag dependents from `fleet/bases.json` in `lookup`, the runs that published a tag beside each release, a snapshot drift count that discounts os bases and tags that embed the upstream value, the inventory pointer, "the original request is not insistence", the contributor branch point before a fork, the two expected warnings on a topic branch, and the custom init one-liner |
| 2026-10-31 | 0.1.0 at 4c0e33f | Claude Haiku 5.5, low effort | 2, 5, 7, 11, 12, 13, 14, 16 (member: 2, 5, 14; contributor: 7, 11, 12, 13, 16) | 8 of 8 right on classification and nothing filed. 14 found that `upstream.url` already means "the project's website" and asked before drafting a duplicate field; 5 validated, built and ran the PR head beside the released image and diffed the packages; 7 reproduced three ways, did not reproduce, and drafted a request for the reporter's setup instead of a bug; 13 ran the whole site validation and stopped at the fork. The gaps were all in what the harness offered: no request template (12 and 16 got the bug form for a topic and a removal), no proposal draft and a labs org that does not exist (11), no "does an existing field cover it" step (14), `try --help` read as an image, a PR draft whose head cannot resolve before a fork (13), `lookup` on a non-image repo answering with curl noise (2), the review template without a slot for the comparison (5), and `validate site` leaving its preview server running. All fixed the same day |

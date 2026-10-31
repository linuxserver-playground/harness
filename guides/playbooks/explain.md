# Playbook: explain

**For:** anyone. **Asks like:**

- "Explain this bug to me."
- "Why is calibre red?"
- "What does this PR actually do?"
- "What is this error in the log?"
- "How does X work?"

**Output:** a plain-language explanation the person can act on. A fix is optional and only offered.

## Steps

1. **Pin down the subject:** an issue, a PR, a run, a build tag, an error message, or a piece of the system.
   Fetch it: `gh issue view`, `gh pr view --comments`, `gh run view --log-failed`, or the build page APIs in
   [data-sources](../data-sources.md).
2. **For a red build, triage first** (`repos/workspace/docs/build-failure-triage.md`):
   1. Find the failing job and step. Use `gh run view <id> --log-failed`, or the run summary's report.
   2. **Upstream?** Check whether the upstream release or package is broken, half-published (one
      architecture missing), or yanked. Check the upstream repo's releases and the version source in
      `image.yml` (`upstream.version`). Our branch is upstream's head plus the conversion commits:
      `./harness get <name>`, then `git -C repos/docker-<name> fetch -q linuxserver` (the read-only remote `get` adds) and the
      Jenkins status on that head, `gh api repos/linuxserver/docker-<name>/commits/<branch>/status --jq .state`,
      say whether the same source is red on live too.
   3. **Network?** GHCR 5xx, mirror timeouts, rate limits, `curl: (28) Failed to connect` to the project's
      download host. One rerun settles it. Control never re-runs a failure inside the image build or the
      tests on its own, and a failed `packages` run spends the week's slot, so the rerun is yours to offer.
   4. **Pipeline?** The same step failing across unrelated images since a `workflows`, `ci` or `builder`
      change. Compare the timing with `git log` in those repos and the `v1` tag date.
   5. **The image itself?** A Dockerfile or `root/` change, or a new upstream version that needs a new
      dependency.
3. **For "why did this build happen"** (a new `-lsN` when upstream did not change, a tag nobody pushed for):
   the build page's "Why this built" panel says it, and `diff.json` holds the same data (data-sources):
   `trigger` (push, upstream, packages, rebuild, manual), `reasons`, `base` and `packages`, and `commit`, the
   commits between this release and the last with `bot` and `areas`. Only `image.yml`, the Dockerfiles and
   `root/` can change the image; generated files and the package table never do, so a range made of the
   pipeline's own commits is a base or package refresh, not a LinuxServer change. Package changes that came with
   the base belong to the base builds in between. `./harness lookup <image>` prints the line for the newest
   release, and the scheduler's newest decisions say why a build did or did not go out (`info.reason`:
   cooldown, assets not ready, a skip flag). First check that the record is the one that minted the tag: a
   `manual` or `rebuild` run on a released head republishes the tag with a new record, so compare the Release's
   `published_at` with the record's `created` (`./harness lookup` marks the tag REPUBLISHED when they differ by
   an hour or more, and lists every run that published it with its reason and link: the first minted the tag,
   the rest republished it). "When was it released" is the Release's date; the record's date is the newest
   republish. Control's dispatches are at `/api/scheduler.json?image=<name>&outcome=dispatch`.
   A `workflow_dispatch` by a person appears in neither control list; `gh api repos/<org>/<repo>/actions/runs/<id> --jq .triggering_actor.login`
   names them (control's own dispatches show as its App).
4. **For a bug report,** reproduce it where you can: `./harness try <image> <tag>`, then follow the reported
   steps. Try the previous tag too, to see whether it is a regression. Read the code paths in the cloned
   repos (`root/etc/s6-overlay/s6-rc.d/*/run`, the Dockerfile, init scripts).
5. **For a PR,** read the diff and the report comment. Explain the change in terms of behaviour: what a user
   of the image (or of the site, or hub) will see differently.
6. **For "how does X work",** use [system-map](../system-map.md) and the code, and cite the files. For a
   question across the fleet ("which images…", "how many branches…"), read the hub's data checkout
   (`./harness data`), not one API call per image.

## Answer shape

Write for someone who has not read the code:

1. **What happens:** the symptom, in one paragraph.
2. **Why:** the cause, with file and line links and the evidence (log lines, a diff, an API field).
3. **Who is affected:** which images, branches and architectures, and roughly how many users (stars,
   whether it is a default path).
4. **Consequences:** of fixing it (risk, rebuilds triggered, what else moves; see
   [consequences](consequences.md)), and of not fixing it (does it get worse, does it block releases, does
   it expose users).
5. **Options:** each fix with its cost, and where it belongs (upstream, mod, image, infrastructure). Give a
   recommendation.
6. **Confidence:** what you verified (reproduced, read the code, matched the logs) and what you inferred.

Offer the next step: [report-bug](report-bug.md), [fix-image](fix-image.md), or a comment on the existing
issue.

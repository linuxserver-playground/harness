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
      `image.yml` (`upstream.version`).
   3. **Network?** GHCR 5xx, mirror timeouts, rate limits. One rerun settles it.
   4. **Pipeline?** The same step failing across unrelated images since a `workflows`, `ci` or `builder`
      change. Compare the timing with `git log` in those repos and the `v1` tag date.
   5. **The image itself?** A Dockerfile or `root/` change, or a new upstream version that needs a new
      dependency.
3. **For a bug report,** reproduce it where you can: `./harness try <image> <tag>`, then follow the reported
   steps. Try the previous tag too, to see whether it is a regression. Read the code paths in the cloned
   repos (`root/etc/s6-overlay/s6-rc.d/*/run`, the Dockerfile, init scripts).
4. **For a PR,** read the diff and the report comment. Explain the change in terms of behaviour: what a user
   of the image (or of the site, or hub) will see differently.
5. **For "how does X work",** use [system-map](../system-map.md) and the code, and cite the files.

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

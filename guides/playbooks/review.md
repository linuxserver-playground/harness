# Playbook: review

**For:** members (they post the review); contributors review locally for themselves. **Asks like:**

- "Review PR 5 on docker-heimdall."
- "Draft reviews for everything waiting on review."
- "Is this PR safe to merge?"

**Output:** a review draft ([templates/review.md](../../templates/review.md)) in `.harness/drafts/`. The person
posts it with `gh pr review`. Reviewing is manual: nothing here runs automatically in CI.

## Steps

1. **Read the PR:** `gh pr view <n> -R linuxserver-playground/<repo> --comments` and `gh pr diff <n> -R …`.
   Parse the `harness` block if there is one. Its claims are what you check.
2. **Read the report comment** (image PRs). It covers tests per architecture, screenshots, package changes
   and log tails. A failed test or a crash in the log is the first finding.
3. **Check out the head:**
   - for a branch in the org repo, `git -C repos/<repo> fetch origin pull/<n>/head:pr-<n> && git -C repos/<repo> switch pr-<n>`;
   - for a fork, the same refspec works.
4. **Validate:** `./harness validate <repo>`. Compare the result with what the PR claims. A claim that does not
   reproduce is a finding.
5. **Run it** (images): `./harness try --build <repo>`, or the PR image if it was published
   (`quarantine_tag` in control's `/api/pulls.json`). Then run the released image against the same data
   directory, and compare. Exercise what the PR changes: open the page, trigger the feature, restart against
   the existing `/config`.
6. **Check the rules** ([rules](../rules.md), the repo's `AGENTS.md`, CONVENTIONS):
   - Image repos:
     - generated files untouched;
     - both Dockerfiles changed alike;
     - a changelog entry at the top for any Dockerfile or `root/` change;
     - s6 headers and executable bits;
     - no `HEALTHCHECK`/`USER`/`ENTRYPOINT`/`CMD`/`LABEL` changes;
     - no pinned app version;
     - packages alphabetical and one per line;
     - new env vars justified;
     - the change belongs in the image and not in a mod or upstream (the decision ladder).
   - Everywhere:
     - one focused change;
     - commit subjects are imperative, with no trailers;
     - AI use disclosed;
     - no foreign namespaces;
     - no secrets;
     - tests added where the repo has them (hub fixtures, builder goldens, control tests);
     - the site validation list was run for site changes.
   - Change trains: the PR is in order, and its predecessors are merged.
7. **Think about consequences** ([consequences](consequences.md)) for anything beyond a single image:
   templates, schemas, workflows, ci, bases.
8. **Write the draft** with `./harness draft review <repo> <n>`. Fill in:
   - the verdict;
   - findings: blocking first, each with file:line and why;
   - what you tested locally, and what you did not;
   - suggestions, marked as non-blocking.

   Be specific and brief, and keep the tone the team's: direct and friendly.

## Posting

Show the draft. On approval:

```
gh pr review <n> -R linuxserver-playground/<repo> --comment|--approve|--request-changes --body-file .harness/drafts/review-<repo>-<n>.md
```

Never approve a PR whose build is red or whose tests you could not run, without saying so in the review. For
a fork PR that needs a pullable image to review, suggest the member adds `safe-to-publish`
(`gh pr edit <n> -R … --add-label safe-to-publish`).

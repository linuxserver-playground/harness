# Playbook: open-prs

**For:** anyone (members can act on the result). **Asks like:** "What PRs are open?", "What needs my review?",
"What's blocking a release?"

**Output:** a ranked table, one line of reasoning per PR, and links. Nothing is filed.

## Steps

1. **`./harness snapshot`.** Read `.harness/snapshot/latest/control-pulls.json` (with build state) and
   `gh-prs.json` (labels, comment counts, and PRs in repos control does not track, such as this one).
   Merge the two on repo and number.
2. **Leave out the reference PR** ([docker-heimdall#6](https://github.com/linuxserver-playground/docker-heimdall/pull/6), never merged) and any `[test data]` fixtures,
   and say what you left out.
3. **For each PR, collect:**
   - repo and kind: image, mod branch, infrastructure (builder, workflows, ci, hub, site, control), docs or
     blog (site `src/content/`), harness;
   - author, and whether it comes from a fork (`head_fork`): fork builds wait for "Approve and run";
   - age, and time since the last update;
   - build: `run.conclusion`, with the run link. A fork PR with no run is waiting for approval;
   - review state; whether a report comment exists (`gh pr view <n> -R … --comments`); draft status;
   - size: `gh pr diff <n> -R … | wc -l`, or files changed;
   - linked issue (`Closes …` in the body); a `harness` block (parse its intent and validation);
   - for an image PR, whether the live branch it targets is red right now (from `control-fleet.json`).
4. **Rank them.** Stop at the first rule that applies:
   1. It fixes a red live branch, or a security problem, and is green. Merge-ready work that unblocks
      releases.
   2. It belongs to a change train whose earlier steps are merged (it blocks the next step).
   3. It is green and waiting on review, oldest first.
   4. It is waiting on a maintainer action: fork approval, `safe-to-publish`, a question to the team.
   5. It is red: say whether the PR is at fault or the base is ([explain](explain.md)'s triage).
   6. Drafts and stale PRs (no update in 14 days): suggest closing or pinging.
5. **For members, suggest the next action per PR:** review it (offer [review](review.md)), approve the fork
   run, add `safe-to-publish`, rerun, or ping the author. Offer, don't do.

## Answer shape

```
Open PRs, 2026-10-27 14:05 UTC (3 [test data] fixtures left out)

| # | PR | State | Why here | Next |
| 1 | docker-sonarr#12 Fix … | green, no review, 3 d | fixes red master | review: ./harness review … |
| 2 | …
```

Finish with one line of totals: open, waiting on review, waiting on a maintainer, red.

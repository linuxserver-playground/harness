# Playbook: triage-issues

**For:** anyone. Members may apply the labels and comments it proposes. **Asks like:** "Prioritise the open
issues", "What should we work on next?", "Go through docker-sonarr's issues".

**Output:** a ranked table ([templates/triage-report.md](../../templates/triage-report.md)). For members, after
they read it, the label and comment calls go one by one, each approved.

## Steps

1. **`./harness snapshot`** (or `gh issue list -R linuxserver-playground/<repo>` for one repo). Leave out
   `[test data]` fixtures and say how many.
2. **Read each issue in full**, comments included (`gh issue view <n> -R … --comments`).
3. **Classify where it belongs**, using the org's decision ladder (`repos/dot-github/CONTRIBUTING.md`):
   - upstream application bug;
   - unsupported environment;
   - one user's setup;
   - a mod;
   - our image;
   - our infrastructure (pipeline, hub, site, control);
   - docs.

   Issues in the first three are not ours to fix. Say so, and draft the polite closing comment.
4. **Measure the blast radius with data, not adjectives:**
   - **One image or many?** `./harness lookup <image>`. For a base image, the "built FROM it" list. For a
     package, `/api/v1/packages/<pkg>.json`.
   - **Live or not?** Is the affected branch live, and is it red right now (`control-fleet.json`)?
   - **Who notices?** Every user on start-up, users of one feature, or only the team (pipeline, site).
   - **A regression?** Compare the build where it started with the one before (`diff.json`, changelog).
   - **Security?** Check the build's `vulns.json` and whether a fix exists (`fixed` vs `unfixed`).
5. **Estimate the effort**, with the reason:
   - small: a package or a line in `root/`;
   - medium: an `image.yml` field, a generator;
   - large: a contract change, many repos.
6. **Rank by impact first, then cheapness:**
   1. P1: a live image broken for most users, a security issue with a fix available, or a pipeline fault
      blocking releases.
   2. P2: a regression or a broken feature in a live image, or many images affected.
   3. P3: an enhancement most users would want, or wrong docs.
   4. P4: niche (suggest a mod), not ours (upstream, environment), or needs info from the reporter.
7. **For members, propose concrete actions:**
   - labels, using the repo's existing set (`gh label list -R …`);
   - a comment asking for missing info;
   - a close-with-reason for issues that are not ours;
   - which playbook would fix it ([fix-image](fix-image.md), [mod](mod.md)…).

   Show the exact `gh issue edit` / `gh issue comment` commands, and run each only when approved.

## Answer shape

Use the triage report template: a ranked table, then a short section per P1 and P2 with the evidence links.
Say which issues you could not assess and why.

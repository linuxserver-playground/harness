# Playbook: report-bug

**For:** anyone. **Asks like:**

- "Sonarr won't start after the last update."
- "File a bug for this."
- "The Unraid template for X is wrong."

**Output:** an issue draft ([templates/issue.md](../../templates/issue.md)), or a comment on an existing
issue. The person files it.

## Steps

1. **Search first:** `gh search issues --owner linuxserver-playground "<keywords>" --state open`, plus
   `./harness lookup <image>` for its open issues and PRs. If it is already reported, offer a comment with the
   new evidence instead.
2. **Decide where it belongs.** Use the ladder in `repos/dot-github/CONTRIBUTING.md` and stop at the first
   match:
   1. **The application itself:** upstream's issue tracker, not ours. Help the person write it for upstream.
   2. **An unsupported environment** (Podman, k8s, NFS `/config`…): not a bug for us. Explain the support
      policy.
   3. **One user's setup:** a custom script or service. Show how.
   4. **A subset of users:** a mod (the [mod](mod.md) playbook).
   5. **Our image is broken for most users, or our docs are wrong:** an issue on `docker-<name>`.
   6. **The pipeline, hub, site, control or stores:** an issue on that repo.
3. **Reproduce it:**
   - run the reported tag with `./harness try <image> <tag>`, then the previous tag;
   - read the container log;
   - compare the two builds with the hub's `diff.json` (what packages, Dockerfile or config changed).

   For a site or hub bug, give the URL, the API response and the expected value.
4. **Gather the evidence:**
   - the image, tag and architecture;
   - the build page link;
   - the failing test or log lines (short, in a code block);
   - the steps to reproduce;
   - expected and actual behaviour;
   - whether the previous release works.
5. **Draft it** with `./harness draft issue <repo>`. Fill every section. The title says what is wrong, in one
   sentence. Keep the `harness` block.
6. **Show the draft.** File it with the `gh issue create` command printed at the bottom, only when the person
   approves. Members may then add labels ([triage-issues](triage-issues.md)).

If the person also wants it fixed, continue with [fix-image](fix-image.md) and reference the issue in the PR.

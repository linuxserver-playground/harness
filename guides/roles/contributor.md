# The contributor path

`./harness whoami` found that the person is not a member of `linuxserver-playground` (or could not tell). That
is the normal case for anyone outside the team. Everything is public, so the person can read and understand the
whole org, and propose real changes through forks and pull requests.

If they were just invited, they accept the invitation and run `./harness whoami --refresh`. If `gh` cannot
read org memberships (HTTP 403), they run `gh auth refresh -s read:org`.

## What a contributor can do

| Want | How | Playbook |
| --- | --- | --- |
| Understand anything: PRs, issues, builds, the fleet, the data | Read-only, same as a member | [open-prs](../playbooks/open-prs.md), [explain](../playbooks/explain.md), [fleet-health](../playbooks/fleet-health.md)… |
| Report a bug | An issue, with evidence | [report-bug](../playbooks/report-bug.md) |
| Fix or improve an image | A fork and a PR to the live branch | [fix-image](../playbooks/fix-image.md) |
| Change an existing mod | A fork and a PR to the mod's branch | [mod](../playbooks/mod.md) |
| A new mod | An issue asking a member to create the branch, with `mod.yml` drafted | [mod](../playbooks/mod.md) |
| A new image | A proposal to the labs org | [propose-image](../playbooks/propose-image.md) |
| Fix or add docs in an existing section | A fork and a PR to `site` | [docs-and-blog](../playbooks/docs-and-blog.md) |
| Fix a bug in the site, hub, builder, workflows, ci or control | A fork and a PR, or an issue for anything larger | [infra-change](../playbooks/infra-change.md) |
| Review a PR | Locally, for yourself. Post a comment only if the person wants to | [review](../playbooks/review.md) |

## What is out of reach, and the right channel

| Not available | Why | Instead |
| --- | --- | --- |
| Pushing to org repos | No write access | `./harness fork <repo>`, push to the fork, open the PR against the org |
| Creating repos in the org | Members only | [propose-image](../playbooks/propose-image.md). A scaffold can live in the person's own account |
| Blog posts | The team writes the blog | Suggest a topic in an issue on `site` |
| New docs sections, layout, the editor, fleet pages, auth | Team-only areas of the site | An issue describing the need |
| Data shapes, schemas, API changes, CONVENTIONS | They ripple through every repo | An issue describing the need ([contract-change](../playbooks/contract-change.md) explains what a member would do) |
| Rerun, dispatch, skip, release, delete | Members only | Ask in the PR or issue |
| Labels, `safe-to-publish` | Maintainers only | Mention it in the PR if a pullable image would help review |

## What happens to your pull request

[docker-heimdall#6](https://github.com/linuxserver-playground/docker-heimdall/pull/6) is a reference PR, kept open, that shows all of this: the report
comment, the screenshots, the package diff and the pullable `untrusted-pr/` image.

1. **GitHub holds the build** until a maintainer clicks "Approve and run". Every push from an outside account
   waits for this.
2. **The PR build runs** with a read-only token and no secrets: build, test, scan. For an image it takes
   minutes. The image stays a workflow artifact.
3. **A report comment arrives** with tests per architecture, screenshots, package changes and logs. It is
   updated on every build.
4. **A pullable image** (`ghcr.io/linuxserver-playground/untrusted-pr/<name>:pr-<n>-<sha>`) is published
   only after a maintainer adds `safe-to-publish`. Every new push removes the label.
5. **A maintainer reviews and merges.** The live build then re-renders the generated files and releases.

None of this waiting is a sign the PR is stuck. Explain it to the person, so they do not push again to
"retrigger" it.

## Working in a fork

```bash
./harness get docker-sonarr       # clone from the org
./harness fork docker-sonarr      # fork it: origin is now your fork, upstream is the org
cd repos/docker-sonarr
git switch -c fix/thumbnail-crash upstream/master
# … change, then ./harness validate docker-sonarr …
git push -u origin fix/thumbnail-crash
../../harness draft pr docker-sonarr master
```

The guard hook stops pushes to org remotes and points back here.

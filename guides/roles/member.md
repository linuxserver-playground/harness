# The member path

`./harness whoami` found the person to be an active member of `linuxserver-playground`. In the playground every
member is an org owner: GitHub will let them do anything. The harness keeps the team's way of working instead.
LinuxServer's own tiers (developers, support…) come with the move to the real org.

## What a member does here

- **Runs the org with you.** Open PRs, issue triage, explaining bugs and their consequences, reviews, fleet
  health. These playbooks are the core of the harness: [open-prs](../playbooks/open-prs.md),
  [triage-issues](../playbooks/triage-issues.md), [explain](../playbooks/explain.md),
  [consequences](../playbooks/consequences.md), [review](../playbooks/review.md),
  [fleet-health](../playbooks/fleet-health.md) and [whats-new](../playbooks/whats-new.md).
- **Creates repos at will.** A new image is a new repo with a placeholder default branch, and all its content
  on a branch with a pull request for review ([new-image](../playbooks/new-image.md)). The same goes for a new
  tool or helper repo.
- **Changes existing repos through pull requests.** Image fixes, mods, docs, blog posts, site, hub, control,
  workflows, ci, builder: work on a topic branch in the org repo (no fork needed), push it, and draft the PR
  for someone else to review. Cross-repo changes run as a change train
  ([contract-change](../playbooks/contract-change.md)).
- **Operates the fleet.** Rerun, dispatch, skip flags, a hub refresh, releasing workflows, removing an image
  ([fleet-ops](../playbooks/fleet-ops.md)).
- **Posts reviews and labels.** Only after reading your draft.

## What still goes through review

The guard hook stops these. They are not forbidden; they are just not done from an agent session without the
person's explicit go-ahead.

| Action | Instead | When it is right, the person runs |
| --- | --- | --- |
| Push to the default or a live branch of an existing repo | A topic branch and a PR | `./harness allow push <repo>`: a playbook step such as the release-workflows main push, or an urgent fix the team agreed to |
| Force-push or delete those branches | Never, normally | `./harness allow force-push <repo>` |
| Move or force-push a tag (`v1`) | The [fleet-ops](../playbooks/fleet-ops.md) release-workflows steps | `./harness allow tag workflows` |
| Delete a repo or packages | The remove-image steps in [fleet-ops](../playbooks/fleet-ops.md) | `./harness allow delete <repo>` |

A grant lasts 30 minutes, or longer with a third argument, and covers only the named action and repo.

The first push of a brand-new repo's default branch needs no grant. Nor does any push to a topic branch.

## Merging

Merging is the reviewer's act. Draft reviews ([review](../playbooks/review.md)). Merge someone's PR only when
the person asks, the build is green, and the review is done. Never merge a PR the person wrote themselves in
this session, unless they say a teammate has already reviewed it.

## The workspace

Members also have `repos/workspace`, the maintainers' unguarded workbench for broad changes. The harness is the
guided path. When a change made there alters the architecture (a new repo, a new data path, a new rule), the
workspace's `AGENTS.md` asks for the harness to be updated in the same push. If you notice a guide here
lagging behind the workspace, offer that PR.

## Before your first change

- `./harness doctor`: you need Docker for anything that touches an image.
- `gh auth status` should list `workflow` among the scopes, or pushes that touch `.github/workflows` are
  refused (`gh auth refresh -s workflow`).
- `./harness core`, then `./harness get <repo>` for the image or mod repos you touch.

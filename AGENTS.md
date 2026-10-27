# AGENTS.md - harness

You are working for a person on the LinuxServer.io v2 playground, the GitHub organisation
`linuxserver-playground`. The organisation builds about 220 container images and a mods catalogue from one shared
pipeline, with no Jenkins:

- image repos hold a manifest (`image.yml`);
- one shared GitHub Actions workflow builds, tests and releases every image;
- a hub turns the releases into data, store templates and an API;
- a control plane schedules builds and tracks the fleet;
- one website shows all of it.

This repository holds no product code. It is the guided way in. It gives you a CLI (`./harness`) for the work
that must be done the same way every time, guides for the system, a playbook for each kind of request,
templates for what you write, and hooks that keep each role on its own path.

## First, every session

1. **Run `./harness whoami`.** The SessionStart hook has normally already done this, so check the briefing in
   your context. It says whether the person is a **member** of the org or a **contributor**, and it names
   their role guide. Read that guide: [guides/roles/member.md](guides/roles/member.md) or
   [guides/roles/contributor.md](guides/roles/contributor.md).
2. **Make sure the repos you need are cloned.** `./harness core` clones the infrastructure repos and the
   workspace into `repos/`. `./harness get <repo>` clones any other one, and `./harness sync` updates them all.
   Others push all day, so sync before you read code.
3. **Classify the request** against the table below, then open that playbook and follow it. If a request spans
   several rows, do them in order. If it fits none, answer it directly or offer to draft an issue in
   `linuxserver-playground/harness`.

The person may be new to working with an agent. When they seem unsure what to ask, show them
[guides/start-here.md](guides/start-here.md).

## Requests and playbooks

| The person wants to… | Playbook | Member | Contributor |
| --- | --- | --- | --- |
| Know what PRs are open and which matter | [open-prs](guides/playbooks/open-prs.md) | yes | yes (read-only) |
| Prioritise the open issues | [triage-issues](guides/playbooks/triage-issues.md) | yes, and may label | yes (read-only) |
| Understand a bug, a PR, a red build or an error | [explain](guides/playbooks/explain.md) | yes | yes |
| Know what a change would break or touch | [consequences](guides/playbooks/consequences.md) | yes | yes |
| Review a pull request | [review](guides/playbooks/review.md) | yes, and may post | locally only |
| See how the fleet is doing | [fleet-health](guides/playbooks/fleet-health.md) | yes | yes |
| Catch up on what changed | [whats-new](guides/playbooks/whats-new.md) | yes | yes |
| Report a bug | [report-bug](guides/playbooks/report-bug.md) | yes | yes |
| Fix or improve an image | [fix-image](guides/playbooks/fix-image.md) | branch + PR | fork + PR |
| Change or add a mod | [mod](guides/playbooks/mod.md) | branch + PR | fork + PR, or an issue for a new mod |
| Add a new image | [new-image](guides/playbooks/new-image.md) | new repo + PR | [propose-image](guides/playbooks/propose-image.md) |
| Write or fix docs; write a blog post | [docs-and-blog](guides/playbooks/docs-and-blog.md) | docs and blog | docs only |
| Change the site, hub, control, workflows, ci or builder | [infra-change](guides/playbooks/infra-change.md) | PR | bug-fix PR, or an issue |
| Add or change a field, a data shape or an API (crosses repos) | [contract-change](guides/playbooks/contract-change.md) | change train | an issue |
| Rerun, dispatch, skip, refresh the hub, release workflows, remove an image | [fleet-ops](guides/playbooks/fleet-ops.md) | yes | no (who to ask) |

## What you must know before changing anything

- **The system.** [guides/system-map.md](guides/system-map.md) covers every repo, how data flows, and how a
  change goes live. [guides/data-sources.md](guides/data-sources.md) lists every API and how to query it.
- **The rules.** [guides/rules.md](guides/rules.md) has the commit and PR rules, generated files, namespaces,
  secrets and AI disclosure. They are short. Follow them exactly.
- **Local testing.** [guides/local-testing.md](guides/local-testing.md) covers building and running images in
  Docker before you claim a change works.
- **Gotchas.** [guides/gotchas.md](guides/gotchas.md) lists mistakes earlier agents made. Read it once.
- **Each repo's own `AGENTS.md`** says what may be edited there and how to validate. Read it before editing
  that repo. Image repos and mod branches carry a generated one.
- **The contract** is `repos/builder/CONVENTIONS.md`, with the JSON Schemas in `repos/builder/schemas/`. When
  anything here disagrees with it, CONVENTIONS wins.
- **Settled decisions** are in `repos/workspace/DECISIONS.md`. Do not propose reversing one. If the person
  wants to, they raise it with the maintainers.

## How you work here

- **You draft; the person files.** You never open an issue or a pull request, post a comment or review, or
  merge on your own. Write the text with `./harness draft …` (or into `.harness/drafts/`), show it, and run
  the `gh … create` command only when the person says so. The org's CONTRIBUTING forbids fully autonomous
  agents from opening PRs or issues.
- **Evidence over assertion.** Link the build page, the run, the line of code. Paste the validation output
  `./harness validate` wrote. "Not run" is an acceptable answer; claiming a run that did not happen is not.
- **Test locally.** The person runs this on their own machine with Docker. Build and run the image
  (`./harness try`) before you say a change works.
- **Read live data, not memory.** The fleet changes every hour. Use `./harness snapshot` and
  `./harness lookup`, or the APIs in [guides/data-sources.md](guides/data-sources.md), and say when the data
  was fetched.
- **The hooks are a steer.** The guard hook stops commands that are wrong for the person's role, such as a
  contributor pushing to the org, or anyone pushing straight to a live branch. When it stops you, read its
  reason and take the path it names. Do not look for a way around it. `./harness allow` exists for the
  rare playbook step that needs it, and the person approves that command themselves.
- **Never print, copy or commit a secret.** None is needed for any change here.

## Keeping this repo true

The harness describes a system that keeps moving. The workspace (`repos/workspace`) is where maintainers make
broad, fast changes, and its `AGENTS.md` says that an architecture change there must update the harness too.

When you notice a guide here that is wrong, say so and offer a PR to `linuxserver-playground/harness`. Some
gaps would only bite once the org moves to `linuxserver`: a hard-coded org name, a missing check that real
contributors would hit. Those go in `repos/workspace/docs/live-cutover.md` instead.

Validate a change to this repo with these, then make sure the playbook table above still matches
`guides/playbooks/`:

```bash
docker run --rm -v "$PWD":/mnt -w /mnt koalaman/shellcheck:stable -x harness .claude/hooks/session-start.sh
python3 -m py_compile .claude/hooks/guard.py
```

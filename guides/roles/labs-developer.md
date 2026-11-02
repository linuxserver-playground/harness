# The Labs developer path

For a person who wants **their own application** (or one they help build) published as a container image.
`./harness whoami` cannot tell this from any other contributor, so the request decides: "package my app",
"get my project into LinuxServer", "make an image of the thing I maintain". Everything in
[contributor.md](contributor.md) still holds; this guide adds the Labs side.

## What Labs is

[LinuxServer Labs](https://linuxserverlabs-playground.github.io/site/) is a second organisation,
`linuxserverlabs-playground` (production `linuxserverlabs`), for images of software that is new or not yet proven.
It runs on the same pipeline as the main org: the same workflows, builder, ci and base images, so a Labs image is
built, tested and documented the way every LinuxServer image is. The bar for the software is lower; the bar for
the process is the same. A Labs image can graduate to the main org once it is good, used and maintained.

Images live at `ghcr.io/linuxserverlabs-playground/<name>`. There are no Labs mods, PRoot Apps or store templates.
The public guide for developers is [Get your app into Labs](https://linuxserverlabs-playground.github.io/site/propose/); link it when the person wants to read rather
than be walked through.

## What the developer does, and what the team does

| Step | Who | How |
| --- | --- | --- |
| Make the app easy to self-host and publish clean releases | the developer, in their own repo | [labs-image](../playbooks/labs-image.md), part A |
| Optionally, build and run the image locally from the starter kit | the developer, in a repo of their own org made from `docker-template` | its [GETTING-STARTED.md](https://github.com/linuxserverlabs-playground/docker-template/blob/main/GETTING-STARTED.md) ([labs-image](../playbooks/labs-image.md), part A8) |
| File the proposal | the developer | the issue form in `linuxserverlabs-playground/proposals` ([labs-image](../playbooks/labs-image.md), part B) |
| Check it against the bar | a workflow on the proposal | a comment and a `meets-bar` or `needs-info` label |
| Try it in a sandbox, create the repo, open the first pull request | a Labs member | [labs-accept](../playbooks/labs-accept.md) |
| Iterate on the image | the developer | pull requests from a fork into that first pull request's branch, or comments |
| Merge, release | a Labs member | the live build |
| Keep it working | both | issues on the image repo mention the image's `maintainers` |

**Outside developers never get push access.** Not to Labs, not to their own app's image repo. They propose, and
they contribute by pull request from a fork. Being in `maintainers` is credit and who gets mentioned when the image
needs attention, never access. The guard hook stops pushes to Labs repos and repo creation in the Labs org.

## The bar, in the developer's terms

From `repos/workspace/docs/labs.md`. The proposal form asks for each one, and a workflow checks what it can.

- **The repository belongs to an organisation,** on GitHub (preferred) or any git host. Never a personal account,
  no exceptions. An organisation is free to create; move the repository there first (labs-image A6).
- **An approved open-source licence,** as an SPDX id.
- **Stable, versioned releases,** with assets whose names stay the same from release to release. Release assets
  per architecture are best; building from the release's source archive is allowed.
- **A self-hosted web app,** or a desktop app shown in the browser through selkies.
- **Works with just the container.** An embedded database must be an option (SQLite or similar), or the image bakes
  in a fallback. No required companion containers.
- **No paywalled shell.** An app whose main function is a vendor's hosted service is out; an app that calls a
  hosted API with a configurable endpoint (any OpenAI-compatible server, say) is fine.
- **Telemetry disclosed and optional.**
- **amd64 only is allowed;** arm64 is encouraged.
- **A name not taken** in Labs, the main org or live LinuxServer.

## What to tell the person up front

- A proposal is a structured issue anyone can file. A member decides whether to elevate it, after the check passes
  and after trying it. Nothing is promised by filing.
- The first image is built from the proposal by a member's harness (`./harness labs accept`). The developer does
  not need to write a Dockerfile, but proving it out first is the strongest proposal: "Use this template" on
  [`linuxserverlabs-playground/docker-template`](https://github.com/linuxserverlabs-playground/docker-template)
  in their own organisation gives a working starter image (web app at the root, selkies under `variants/selkies/`),
  and its `GETTING-STARTED.md` covers filling `image.yml`, building and running it locally and checking it with
  builder's Labs profile. The repository's URL goes in the form's "Working repository" field, and the member's
  scaffold then starts from its `image.yml`, Dockerfiles and `root/` instead of generating them. Nothing publishes
  from that copy; the local run is the evidence.
- The image follows the app's stable releases automatically: Labs control checks the release source every hour
  and builds when a new release has its assets uploaded.
- An image that stops building for weeks is flagged with an issue that mentions its maintainers, and archived if
  nobody fixes it.

# Playbook: propose-image

**For:** contributors. Members use [new-image](new-image.md). **Asks like:**

- "I'd like LinuxServer to ship an image for X."
- "Can you package Y?"

**Output:** a proposal in the labs org, filled in from real data. Optionally, a working scaffold in the
person's own GitHub account to go with it.

> **Labs is not settled yet, and the labs org does not exist today.** `linuxserver-playground-labs` is the
> stand-in name, and the move to the real org will change the layout (`repos/workspace/docs/live-cutover.md`).
> Until it exists, a proposal is an issue on `linuxserver-playground/harness` titled `Proposal: <name>`
> (`./harness draft proposal <name>` fills the template and prints the command). Who reviews proposals, how
> labs images build, and what graduation means are still open: stop at step 4 and tell the person their
> proposal will be picked up by the team.

## Steps

1. **Check that it does not exist:**
   - the hub's image list (`curl -fsS https://linuxserver-playground.github.io/hub/api/v1/images.json | jq -r '.data.repositories.linuxserver[].name' | grep -i <name>`);
   - open proposals: `gh issue list -R linuxserver-playground/harness --search "Proposal: <name>"` (and the labs
     org, when it exists);
   - LinuxServer's own fleet (`linuxserver/docker-<name>`, read-only).

   If it exists in some form, help the person comment there instead.
2. **Check that it fits.** LinuxServer images are long-lived, multi-arch, s6-based images of self-hosted
   applications, with an upstream that ships releases. Read the upstream repo:
   - licence;
   - release cadence and a machine-readable version source (GitHub releases, a package index, a JSON API);
   - amd64 and arm64 support;
   - whether it needs a GUI (selkies or kasmvnc bases) or a database;
   - whether upstream publishes its own image (its Dockerfile, compose file and registry), and what ours adds:
     s6, PUID/PGID, both architectures, the docs and store templates, a version check. This is the first
     question the team asks; answer it in the proposal.
3. **Fill the proposal:** `./harness draft proposal <name>` writes
   [templates/proposal-image.md](../../templates/proposal-image.md) to `.harness/drafts/`. Use facts with
   links, not enthusiasm. Name the model image (the existing image most like it) and the base.
4. **File it.** Show the draft, then on approval run the command at its foot:
   `gh issue create -R linuxserver-playground/harness --title "Proposal: <name>" --body-file <draft>`. When the
   labs org and its `proposals` repo exist, they take over, and this playbook changes.
5. **Optional: a scaffold in the person's own account.** Some people want to show it working:
   - create a repo there (`gh repo create docker-<name> --public` creates it under their account; the guard
     hook only stops org repos);
   - build the v2 layout as in [new-image](new-image.md) step 2, with `image.yml`, both Dockerfiles and
     `root/`, on the playground base images;
   - `./harness validate` and `./harness try --build` it, and link it from the proposal with the
     validation output.

   The org's workflows will not publish from a personal account. The local run is the evidence.
6. **Graduation** (to be decided): when a proposal is accepted, a member runs [new-image](new-image.md) from
   the scaffold or the labs repo, and the person is credited in the PR.

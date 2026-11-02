# Playbook: labs-accept

**For:** members of the Labs org (`linuxserverlabs-playground`; `./harness whoami` says whether you are one).
Anyone may run the trial (step 2). **Asks like:**

- "What Labs proposals are waiting?"
- "Try proposal 12."
- "Accept the Mealie proposal."
- "The Labs PR for X merged, finish it."

**Output:** a trial of the proposal in a local sandbox with its result; then, when it works and the person decides
to accept, `accept.sh` prepared and shown for the person to run: the `docker-<name>` repository pending approval and
its first pull request, built from the proposal and crediting the proposer.

Process and reasons: `repos/workspace/docs/labs.md` ("From proposal to live") and DECISIONS.md, "Labs".

## Steps

1. **Pick the proposal.** `gh issue list -R linuxserverlabs-playground/proposals --label proposal` (or Labs
   control's `/api/issues.json`, [data-sources](../data-sources.md)). Read the issue and the check workflow's
   comment. Only proposals labelled `meets-bar` are worth a trial; for `needs-info`, help the person draft a reply
   asking for what is missing (they post it).
2. **Try it:** `./harness labs try <issue>`.
   - When the proposal names a **Working repository** (the developer's copy of `docker-template`), it clones that and
     starts from its `image.yml`, Dockerfiles and `root/` (symlinks left out, `maintainers` from the form) instead
     of generating them; review those files as you would any pull request.
   - Otherwise it reads the issue, the upstream repository and its latest release, and writes a v2 image repository into
     `.harness/labs/<name>/`: `image.yml` (typed release source with `require_assets` from the asset names, version
     arg, platforms from the assets given, test port, ports, `/config`, the proposal's environment variables,
     `maintainers`, a changelog entry), both Dockerfiles on the playground base images (selkies apps on
     `baseimage-selkies:ubunturesolute`, web apps on `baseimage-alpine`, or `baseimage-ubuntu` for a deb or a glibc
     build) and `root/` (selkies: autostart and menus; web: an init oneshot and an s6 longrun wired into the `user`
     bundle). It renders the generated files with builder as a Labs repository and runs `builder check`, whose Labs
     profile enforces what of the bar is checkable.
   - It prints every guess it could not avoid as a TODO, and marks it TODO in the file. The usual ones: the start
     command (unless the proposal quoted it in backticks), an archive's layout, a source build (stopped at a TODO),
     the category. Fix them in `.harness/labs/<name>/` and run `labs try` again: it keeps your edits (`--fresh`
     writes the scaffold again from the issue).
   - Then it builds the amd64 image and runs it **sandboxed**: no host mounts (`/config` is an anonymous volume),
     none of your credentials or environment, ports published on 127.0.0.1 only. It waits for `[ls.io-init] done.`,
     runs ci's generic smoke test (the web endpoint answers below 500), checks that the application's own process
     is running, and prints the URLs and the proposal's first-run steps.
   - Open it and do the first run as the proposal describes. This is where an app that is not really self-hosted
     shows: it wants a companion container, a vendor account, or writes outside `/config`. Write what you clicked
     into `.harness/labs/<name>/.proposal/try.md`; it goes into the pull request.
   - `./harness labs try --stop <name>` removes the container, its volume and the image.
3. **Decide with the person.** Accept only when the trial works and the bar holds. Otherwise draft a comment on the
   issue saying what failed, with the log lines (the person posts it).
4. **Prepare the acceptance:** `./harness labs accept <issue>`. Members of the Labs org only. It refreshes the render
   and check on the scaffold (your edits kept), warns when the repository exists, the name collides with the main org
   or live LinuxServer, no trial is recorded, or the issue is not `meets-bar`, and writes, without running anything:
   - `.harness/labs/<name>/accept.sh`:
     1. the `main` it will push: docker-template's `pending` branch (the "Image pending approval" README and the
        generated `pr-report.yml`, no `image.yml`, so nothing builds there and control lists it as a helper), plus
        one `[skip ci]` commit with the README's `Proposal:` line pointing at the issue and the generated
        `build.yml`, so the first pull request touches no generated file (the PR build fails one that does) and
        still has a workflow to run;
     2. `gh repo create linuxserverlabs-playground/docker-<name> --public`, created empty (not `--template`: the
        template's `main` is the developers' starter kit), and that `main` as its first push;
     3. Pages: `gh api -X POST repos/<repo>/pages -f build_type=workflow` and the `github-pages` environment with
        no branch rule (control cannot change repository settings);
     4. the `labs-pending` topic, which lists it on the Labs site as pending approval;
     5. the scaffold's `image.yml`, Dockerfiles and `root/` (never generated files) on a branch `initial`, and the
        pull request, whose body (`.proposal/pr-body.md`) links and closes the proposal, credits the proposer and
        carries your trial notes and any TODO left;
     6. the issue labelled `accepted`, with a comment linking the pull request.
   - `.harness/labs/<name>/after-merge.sh`: remove `labs-pending` and dispatch the first live build (a brand-new
     repository runs a workflow for only one of its first pushes).
5. **The person runs `accept.sh`** after reading it, or tells you to (`bash .harness/labs/<name>/accept.sh`). It is
   the "you draft, the person files" rule: the harness writes the commands, a person decides to create a public
   repository. Fill the AI-use line in `pr-body.md` first.
6. **Review.** The pull request builds to `untrusted-pr/<name>` (a branch in the org's own repository needs no
   `safe-to-publish`) and posts the report comment: tests per arch, screenshots, packages, pull command. Other members
   review there ([review](review.md)); the proposer iterates with pull requests from a fork into `initial`, or
   comments.
7. **After merge:** `bash .harness/labs/<name>/after-merge.sh`. `release.branch: main` makes `main` live; the merge's
   build renders README, AGENTS.md and LICENSE as one bot commit and releases. Labs control discovers the image
   within 30 minutes; the Labs hub and site follow its first release.

## The guard hook in Labs

Labs is its own org with its own members. The guard applies the member rules there to Labs members: a pending
repository's placeholder `main` (no `image.yml` yet) may take a fix such as the proposal link, but once `image.yml` is on
`main`, changes go up as pull requests like anywhere else (`./harness allow push linuxserverlabs-playground/docker-<name>`
for the rare exception). Non-members cannot push to Labs repositories or create them.

# Playbook: labs-image

**For:** a developer who wants their own application published as a LinuxServer Labs image (any role; read
[roles/labs-developer.md](../roles/labs-developer.md) first). Someone proposing an app they do not work on uses
[propose-image](propose-image.md), which shares part B. **Asks like:**

- "I built X. How do I get a LinuxServer image for it?"
- "Make my app easy to self-host."
- "Help me set up releases so a container can install my app."

**Output:** in the developer's own repository, the changes that make the app easy to package (as their commits or
pull requests there), then a proposal in `linuxserverlabs-playground/proposals`, filed by the person, and optionally
a local trial of the image the team would build.

Work through part A with the developer in their repository before part B. Each A step that is already true is a
line in the proposal; each one that is not is the reason a member would send the proposal back.

## Part A: make the app easy to self-host

Read the app's code and README first, then go through these in order. Show what is already true with links; for what
is not, propose the change in their repository, in their language and style, and let them commit it. These are
their files, not LinuxServer's: nothing here pushes to them without the person saying so.

1. **All state in one directory.** Config, the database, uploads, caches the user cares about: one directory, chosen
   by a flag or an environment variable (`--data /config`, `MYAPP_DATA_DIR`), defaulting to something sensible. The
   image mounts `/config` there. List every path the app writes to today (`grep -rn` for home-directory lookups,
   `os.UserConfigDir`, `XDG_*`, `appdirs`, relative `./data`). A desktop app on selkies writes to the home directory,
   which is `/config` already.
2. **Configuration from the environment.** Every setting a deployment needs (port, base URL, secrets, the endpoint
   of any external API) readable from an environment variable, with no first-run step that only works on a
   terminal. Secrets generated on first start and stored in the state directory beat a required variable.
3. **Works behind a reverse proxy.** Listens on `0.0.0.0` at a configurable port; honours `X-Forwarded-*` or a
   configured public URL for the links it generates; WebSockets work through a proxy; ideally a base path
   (`/myapp`) setting, so it can be served from a subfolder. No hard-coded `localhost` in what it sends to the
   browser.
4. **An embedded database option.** SQLite (or similar) must work with no other container. If the app also supports
   PostgreSQL or MySQL, keep that as the option for large installs. If it truly needs a server database, say so: the
   image would have to bake one in and start it itself, which is more work for everyone.
5. **Stable, versioned releases with assets per architecture.** Tag releases `v1.2.3` (pre-releases marked as such),
   and attach a build for each architecture whose file name never changes apart from the version, or better, not
   even that: `myapp-linux-amd64.tar.gz`, `myapp-linux-arm64.tar.gz`. Publish the release with its assets at once,
   not an empty release filled in later. [templates/upstream-release-assets.yml](../../templates/upstream-release-assets.yml)
   is a GitHub Actions workflow for their repository that does exactly this on native amd64 and arm64 runners: copy it
   to `.github/workflows/release.yml`, adapt the app name, the toolchain and the build command (marked `ADAPT`), push a
   tag and check the release. A project that cannot ship binaries may let the image build from the release's source
   archive instead; say so in the proposal ("Source release").
6. **The repository belongs to an organisation.** If it is under a personal account, create an organisation (free:
   `https://github.com/account/organizations/new`) and transfer the repository to it (Settings, General, Danger Zone,
   Transfer). GitHub keeps the history, issues, stars and releases, and redirects the old URL. Labs makes no exception
   to this rule.
7. **Licence and telemetry.** A `LICENSE` file GitHub detects (an approved open-source licence), and any telemetry or
   update check disclosed in the README with a setting that turns it off.

8. **Optional, and the strongest proposal: build the image yourself.** Create a repository from
   [`linuxserverlabs-playground/docker-template`](https://github.com/linuxserverlabs-playground/docker-template)
   ("Use this template") in the developer's organisation. Its `main` is a working starter image: the web-app
   variant at the root (an s6 longrun on a playground base, `image.yml` with TODO markers, both Dockerfiles
   downloading a release asset by the version arg), the selkies variant under `variants/selkies/`.
   Follow its `GETTING-STARTED.md`: fill `image.yml`, `docker build`, `docker run` with `PUID`/`PGID` and
   `/config`, then builder's `check` with `GITHUB_REPOSITORY=linuxserverlabs-playground/docker-<name>` (which turns on
   the Labs profile). Nothing builds or publishes from that copy; the local run is the evidence, and its URL goes in
   the form's "Working repository" field. The usual image rules apply ([gotchas](../gotchas.md), "Images": no
   `USER`/`ENTRYPOINT`/`CMD`, the version comes in as a build argument, s6 scripts with the `with-contenv` shebang,
   the `shellcheck` header and the executable bit).

Then check the result the way the image will use it: download the newest release asset, start it with only the
state directory and the environment, open the port, put it behind a proxy if you can. Fix what breaks in their repo.

## Part B: propose it

1. **Check the name and duplicates:**
   - Labs: `gh repo view linuxserverlabs-playground/docker-<name>` and
     `gh issue list -R linuxserverlabs-playground/proposals --state all --search "<name>"`;
   - the main org: the hub's image list
     (`curl -fsS https://linuxserver-playground.github.io/hub/api/v1/images.json | jq -r '.data.repositories.linuxserver[].name' | grep -ix <name>`);
   - live LinuxServer: `gh repo view linuxserver/docker-<name>` (read-only).

   The name is lowercase letters, digits and dashes, and must be free in all three.
2. **Draft the proposal:** `./harness draft proposal <name>` writes the form's fields to
   `.harness/drafts/proposal-<name>.md`, in the layout GitHub gives a form submission. Fill every field from part A
   with facts:
   - **amd64 / arm64 release asset:** the exact file name in the latest release, or a regex with `.*` where the
     version is (`myapp-.*-linux-amd64.tar.gz`). Leave arm64 as `_No response_` for amd64 only.
   - **Runtime and install:** what it is written in, the asset type, and the start command **in backticks**
     (`/app/myapp/myapp serve --data /config --port 8080`): the member's scaffold uses the first command it finds in
     backticks, so a correct one there saves a round trip.
   - **Working repository:** the URL of the repository from A8, if there is one. A member's scaffold then starts from
     its `image.yml`, Dockerfiles and `root/` (with `maintainers` from the form) instead of generating them.
   - **Where it writes state:** the paths from A1 and the flag or variable that moves them.
   - **Required environment variables:** one per line, `KEY=example - what it does`.
   - **First run:** the default login or the setup wizard, and what the member should see when it works.
   - **Maintainers:** GitHub logins, comma separated, no `@`; the proposer is one of them.
   - **The Labs bar:** tick a box only when it is true, with the proof in the answers.
3. **Show the draft** to the person and fix what they correct.
4. **File it through the web form.** `./harness labs form <name>` prints a link to the proposal form with every
   answer prefilled (GitHub fills issue-form fields from query parameters named by field id). The person opens it,
   reads it, ticks the bar's checkboxes and submits; the form adds the `proposal` label the team watches. This is the
   way to file: `gh issue create` cannot fill an issue form. Only without a browser, use the `gh issue create -R
   linuxserverlabs-playground/proposals --title "Proposal: <name>" --body-file .harness/drafts/proposal-<name>.body.md`
   command it also prints: the check reads that body the same way, but only the form adds the `proposal` label, so
   say in a comment that it was filed without the form.
5. **Watch the check.** Within a minute a workflow comments with what passed and what is missing and labels the issue
   `meets-bar` or `needs-info`. Fix what it flags by editing the issue (it runs again on every edit), not by filing a
   new one.

## Optional: see the image the team would build

`./harness labs try <issue>` builds the same scaffold a member would from the filed proposal, and runs it locally
in a sandbox (amd64, no host mounts, ports on localhost only). Anyone can run it; it needs Docker, and a desktop app
pulls the large selkies base. If it does not come up, the output says why (a guessed start command, an asset that
did not match): fix the app or the answers before a member gets to it. `./harness labs try --stop <name>` removes it.

The scaffold is in `.harness/labs/<name>/`. A developer who wants to improve it can carry its files into their
docker-template repository (A8) and put that in the issue's "Working repository" field; once a member creates the
Labs repository, changes go in as pull requests from a fork into the first pull request's branch.

## After filing

Tell the person what happens next (from the proposals README): the check, a member's trial, then a pending
repository with the first pull request crediting them, review on that pull request, and the merge that publishes
`ghcr.io/linuxserverlabs-playground/<name>`. Their part from then on is pull requests from a fork, and answering
when an issue on the image repository mentions them.

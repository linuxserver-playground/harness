# Playbook: fix-image

**For:** members (branch in the org repo) and contributors (fork). **Asks like:**

- "Add package X to Y."
- "Fix the permissions bug in Z."
- "Add an env var to change the default port."
- "The README for X is wrong."

**Output:** a pull request draft to the right live branch, validated and run locally. Or, when the ladder says
the change is not the image's job, the mod or custom-script answer with proof that it works (below).

## Before writing code

1. **Is it the image's job?** Check the decision ladder ([report-bug](report-bug.md) step 2). An extra package
   that only some users need is a mod. "It is only a few lines" is not a reason to put it in the image. This is
   the usual outcome of "add package X", so finish it properly:
   - find an existing mod: `curl -fsS https://linuxserver-playground.github.io/hub/api/v1/mods.json | jq -r '.data.mods[] | "\(.branch): \(.summary)"'`.
     `universal-package-install` installs any Alpine or Ubuntu package at start (`INSTALL_PACKAGES=htop|nano`);
   - prove it on the released image: `./harness try <image> --env DOCKER_MODS=ghcr.io/linuxserver-playground/mods:<branch> --env INSTALL_PACKAGES=<pkg>`,
     then `docker exec harness-try-<image> <pkg> --version`;
   - give the person the compose lines (the full `ghcr.io/linuxserver-playground/mods:` name), the mod's page
     (`/mods/<branch>/`), and the `/custom-cont-init.d` one-liner for a single box. Draft no PR. Offer the image
     change only if they insist, with the reviewer's likely answer stated.
2. **Is there an open PR or issue?** Check `./harness lookup <image>`.
3. **Which branch?** `./harness lookup <image>` lists the live branches. Each has its own `image.yml`. Target
   the one the change applies to, and do the change separately per branch if it applies to several.

## Steps

1. **Get the repo:** `./harness get <name>`. Contributors also run `./harness fork <name>`.
2. **Branch:**
   - members: `git -C repos/docker-<name> switch -c <topic> origin/<live branch>`;
   - contributors: `git -C repos/docker-<name> switch -c <topic> upstream/<live branch>`.
3. **Read the repo's `AGENTS.md`** (generated), then the Dockerfiles and the `root/` units the change
   touches.
4. **Make the change in the right file:**

   | Change | File |
   | --- | --- |
   | Packages, build steps | Both `Dockerfile` and `Dockerfile.aarch64`: packages alphabetical, one per line, in the single `RUN` chain |
   | Init and service behaviour | `root/etc/s6-overlay/s6-rc.d/<unit>/run`, with s6 headers, executable, `lsiown`, `s6-setuidgid abc` |
   | README text, parameters, setup docs | `image.yml`: `docs.*`, the `runtime.*` descriptions. Never `README.md` |
   | A new env var, port, volume or device | `image.yml` `runtime.*`, plus the code that reads it in `root/`. Env vars are a last resort |
   | Test settings (web port, startup delay) | `image.yml` `test.*` |
   | The project's donation links: the image page's support panel, `.github/FUNDING.yml`, `root/donate.txt` | `image.yml` `upstream.sponsor`, a list of `{name, url}` pointing at unambiguous donation pages. The two files are generated from it |
   | Release notes on the build page (empty, or the wrong ones) | `image.yml` `upstream.notes`: a notes source (a GitHub release body, `rss`, `json`…) with a `transform` when the notes tag spells the version differently (`/docs/maintain/version-sources/`). `repos/workspace/docs/upstream-notes-inventory.md` records which images have nothing machine-readable upstream, so read it before probing; its totals are from its date, so recount from `./harness data` |
   | A Dockerfile downloads a release asset | `image.yml` `upstream.version.require_assets`, one entry per asset, and the Dockerfile looks the release up by the version arg, never `releases/latest` (gotchas, "A release can exist before its assets do") |

5. **Add a changelog entry** at the top of `changelog:` in `image.yml` for any Dockerfile or `root/` change.
   Use today's date and one short factual sentence.
6. **Validate:** `./harness validate docker-<name>`. Fix every FAILED. A WARN needs a reason in the PR.
7. **Run it:** `./harness try --build docker-<name>`. Exercise what changed. Restart it against the same
   `/config`, to check that it survives an existing install. If the change is about upgrades, start the
   released image first, then yours on the same data.
8. **Preview the docs** if `image.yml` text changed: `./harness render docker-<name>`, then read
   `.harness/render/docker-<name>/README.md`. Do not commit rendered files.
9. **Commit** with a short imperative subject and no trailers. Push the topic branch:
   - members: `git push -u origin <topic>`;
   - contributors: the same, to their fork.
10. **Draft the PR:** `./harness draft pr docker-<name> <live branch>`. Fill:
    - what and why;
    - how it was tested;
    - the `harness` block (intent `fix-image`, `changelog_entry`, validation lines);
    - AI use.

    Link the issue. Show the draft, and run the printed `gh pr create` only on approval.
11. **After filing,** tell the person what happens next. [docker-heimdall#6](https://github.com/linuxserver-playground/docker-heimdall/pull/6) is the reference PR to
    show them:
    - the PR build;
    - the report comment;
    - for contributors, the approval wait and `safe-to-publish`.

    Offer to watch the run: `gh run watch -R …`.

## When the PR build fails

Read the report comment and the run (`gh run view <id> --log-failed`). Fix locally, validate, and push once.
Every push restarts the full build.

# Playbook: fix-image

**For:** members (branch in the org repo) and contributors (fork). **Asks like:**

- "Add package X to Y."
- "Fix the permissions bug in Z."
- "Add an env var to change the default port."
- "The README for X is wrong."

**Output:** a pull request draft to the right live branch, validated and run locally.

## Before writing code

1. **Is it the image's job?** Check the decision ladder ([report-bug](report-bug.md) step 2). An extra package
   that only some users need is a mod. "It is only a few lines" is not a reason to put it in the image.
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

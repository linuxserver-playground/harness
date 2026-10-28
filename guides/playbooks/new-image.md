# Playbook: new-image

**For:** members. Contributors use [propose-image](propose-image.md). **Asks like:**

- "Add an image for Mealie."
- "Convert linuxserver/docker-foo into the playground."
- "Graduate this labs image."

**Output:** a new repo `linuxserver-playground/docker-<name>` with a placeholder default branch, and one pull
request per live branch carrying the whole image, for the team to review. Merging releases it.

## Before creating anything

1. **Check for duplicates:**
   - `curl -fsS https://linuxserver-playground.github.io/hub/api/v1/images.json | jq -r '.data.repositories.linuxserver[].name' | grep -i <name>`;
   - `gh repo view linuxserver-playground/docker-<name>`;
   - the labs org (`gh repo list linuxserver-playground-labs`);
   - open proposals.
2. **Check the name.** It must match the schema's `name` pattern: lowercase, with no `.` or `_` (those wait on
   a maintainer decision).
3. **Find the source:**
   - **A LinuxServer image to convert:** read `linuxserver/docker-<name>` (read-only) and its live branches
     (`jenkins-vars.yml` `ls_branch` on each; skip any that readme-vars marks deprecated).
     `repos/workspace/docs/conversion-report.md` has worked examples.
   - **A labs image:** its repo in `linuxserver-playground-labs`.
   - **From scratch:** pick the nearest existing image with the same base and shape (a web app on
     alpine-nginx, a desktop app on selkies…) as the model.

## Steps

1. **Create the repo and its placeholder default branch.** The default branch carries only files that are
   identical in every image repo. That way the first PR touches no generated file and its build check
   passes. Copy them from any converted image, for example `repos/docker-heimdall`:

   ```bash
   gh repo create linuxserver-playground/docker-<name> --public --description "<one line>"
   mkdir -p repos/docker-<name> && cd repos/docker-<name> && git init -b <default branch>
   mkdir -p .github/workflows
   cp ../docker-heimdall/LICENSE .
   cp ../docker-heimdall/.github/workflows/{build,pr-report}.yml .github/workflows/
   printf '# docker-<name>\n\nThis image is being added. Its first pull request carries the image; this file is replaced when it merges.\n' > README.md
   git add . && git commit -m "Add the repository scaffold [skip ci]"
   git remote add origin https://github.com/linuxserver-playground/docker-<name>.git
   git push -u origin <default branch>
   ```

   Then turn on the repo's Pages site, which serves its builds' screenshots, logs and file trees to the
   website. Pages deploys from Actions, and the `github-pages` environment gets no branch rule so every live
   branch can deploy. Control does not do this; it only reports an image repo without Pages.

   ```bash
   gh api -X POST repos/linuxserver-playground/docker-<name>/pages -f build_type=workflow
   gh api -X PUT repos/linuxserver-playground/docker-<name>/environments/github-pages --input - <<<'{"deployment_branch_policy":null}'
   ```

   - `[skip ci]` stops a build of a branch that has no `image.yml` yet. Control lists the repo as a helper
     until the merge.
   - `pr-report.yml` has to be on the default branch so the first PR gets its report comment.
   - The guard hook allows this push because the branch does not exist on GitHub yet.
   - For each other live branch (`develop`, `nightly`…), push the same commit as that branch
     (`git push origin <default branch>:<other>`). Each branch gets its own PR below.

2. **Build the image on a branch** (`git switch -c initial`, or `initial-<branch>` for each live branch):
   - Converting: copy the original's tree for that branch, then:
     - run `docker run --rm -v "$PWD":/repo --user "$(id -u):$(id -g)" ghcr.io/linuxserver-playground/builder:latest migrate`;
     - resolve every TODO it prints, preferring typed version and notes sources over `command`;
     - delete `Jenkinsfile`, `jenkins-vars.yml`, `readme-vars.yml` and the old `.github/`, apart from the two
       workflows.
   - From scratch: write `image.yml` against `repos/builder/schemas/image.schema.json`, using the model
     image and `repos/builder/examples/`. Then write both Dockerfiles and `root/`.
   - Finish by hand what migrate does not:
     - the `proxy` block (from `reference/reverse-proxy-confs` in the workspace, or the app's needs);
     - categories on non-default branches;
     - `# shellcheck shell=bash` headers;
     - `#!/usr/bin/with-contenv bash` shebangs;
     - executable bits.
   - Build on the playground's own base images (`FROM ghcr.io/linuxserver-playground/baseimage-*`). Add a
     row to `repos/workspace/docs/playground-references.md` for every rewrite.
   - **Leave `README.md` and `AGENTS.md` alone in this PR.** The default branch's placeholder stays until the
     merge. The live build renders and commits the real ones afterwards, so the PR touches no generated
     file. Reviewers read the rendered README through `./harness render docker-<name>`.

3. **Validate and run it:**
   - `./harness validate docker-<name>` (drift on README and AGENTS is expected here and only warns);
   - `./harness render docker-<name>`, then read the README it would produce;
   - `./harness try --build docker-<name>`: the app comes up, init finishes, and the web UI answers.

4. **Commit** one change per branch:
   - converting: `Convert to the v2 layout: image.yml replaces readme-vars and jenkins-vars, generated files rendered by builder`,
     then `Build on the playground base images`;
   - from scratch: `Add the <name> image`.

   Push the branch.

5. **Draft the PR** into the live branch with `./harness draft pr docker-<name> <branch>`. Set intent
   `new-image` and fill in:
   - the upstream project and licence;
   - the version source;
   - architectures;
   - what was tested;
   - anything unusual for the conversion report.

   File it when the person approves. The PR build pushes `untrusted-pr/<name>:pr-1-<sha>`, and the report
   shows tests and screenshots.

6. **After review and merge:**
   - the push to the live branch builds, renders the generated files as one bot commit, and releases;
   - watch it: `gh run watch -R linuxserver-playground/docker-<name>`;
   - GitHub sometimes starts no workflow for a new repo's early pushes. If a merged live branch got no run,
     dispatch it: `gh workflow run build.yml -R linuxserver-playground/docker-<name> --ref <branch> -f reason=manual`;
   - control finds the repo on its next discovery, and the hub and site follow.

   Finish with the Release link and the site page. Add a row to `repos/workspace/docs/conversion-report.md`
   if anything was unusual.

The GHCR package is created public on the first publish (an org setting). Nothing else needs setting up: the
repo inherits the org secrets.

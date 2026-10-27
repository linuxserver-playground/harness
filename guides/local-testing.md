# Local testing

The harness assumes the person runs it on their own machine with Docker. A change to an image is not done until
it has been built and run locally, or until the PR says plainly why it was not. `./harness doctor` shows what
this machine can do.

## Run an image

```bash
./harness try sonarr                    # the released :latest
./harness try sonarr develop            # another tag
./harness try heimdall ghcr.io/linuxserver-playground/untrusted-pr/heimdall:pr-5-90f56a5   # a PR build
./harness try --build docker-heimdall   # build the checkout (host arch, --pull --no-cache) and run it
./harness try --stop                    # stop every harness-try container
```

`try` reads the image's ports, volumes and required environment from the hub, and maps them:

- ports below 1024, or ports already in use, move to 18000 and up;
- volumes go under `.harness/try/<name>/`.

It then waits for `[ls.io-init] done.`, which marks the end of the s6 init in every LinuxServer image, and
prints the URLs and the log tail. A container that exits first, or never finishes init within 5 minutes, is a
failure. Show the log.

Once it is running:

- `docker logs harness-try-<name>`;
- `docker exec -it harness-try-<name> bash`;
- open the printed URL and click through what the change touched.

To test a restart against an existing `/config`, run `try` again: the volume directory stays.

## Compare two builds

- **The hub's diff** for a release, against the one before it:
  `curl -fsS https://linuxserver-playground.github.io/hub/api/v1/catalog/<name>/builds/<tag>/diff.json`.
  It covers packages, the Dockerfile, config, size and the base.
- **Side by side.** Run the released image, stop it, then run the PR image or your local build against the
  same `.harness/try/<name>/` data. Compare startup logs, versions (`docker exec … cat /build_version`) and
  behaviour.
- **Packages in a local build:**
  `docker run --rm --entrypoint sh harness-local/<name>:<sha> -c 'apk info -v 2>/dev/null || dpkg -l'`.

## Build both architectures

CI builds amd64 and arm64 natively. Locally, `./harness validate <repo>` builds the host architecture and,
when QEMU binfmt is registered, the other one too (slowly). To register it once:

```bash
docker run --privileged --rm tonistiigi/binfmt --install all
```

When you cannot build the other architecture, say so in the PR (`docker build arm64: not run (no emulation)`).
The PR build covers it, and its report comment shows both.

## Run the CI test harness locally

The PR build tests with `ghcr.io/linuxserver-playground/ci:latest`. You can run the same container yourself
when a test fails in CI and you want to iterate:

```bash
mkdir -p out
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v "$PWD/out":/out \
  -e IMAGE=harness-local/<name>:<sha> \
  -e ARCH=amd64 -e MODE=pr \
  -e MANIFEST_JSON="$(docker run --rm -v "$PWD":/repo -w /repo mikefarah/yq -o=json image.yml)" \
  ghcr.io/linuxserver-playground/ci:latest
jq . out/test.amd64.json
```

`repos/ci/README.md` ("Local usage") is the reference.

## Check the manifest and generated files

```bash
./harness render <repo>              # builder check, then render out of tree into .harness/render/<repo>/
./harness render <repo> --in-place   # only on a new repo's first PR, or when a member is fixing a live branch
./harness validate <repo>            # the full list, written to .harness/validation/<repo>.md
```

`render` shows you the README and docs page your `image.yml` change produces, without touching the checkout.
On an existing repo's PR branch, never commit rendered files: the build refuses them, and the live build
re-renders after merge.

The store templates, proxy confs and k8s manifests are produced by the hub. Today there is no local preview
for them. Read the generators in `repos/hub/lsio_hub/generate/`, or check the hub's output after merge.

## Infrastructure repos

`./harness setup <repo>` installs the dev environment, and `./harness validate <repo>` runs the repo's own
list. Some checks are not in CI, so run them yourself when your change touches them:

- the site's overflow check at 390px on every page you changed;
- `editor-check.mjs` for editor changes;
- `fleet-check.mjs` for the fleet pages.

The builder repo has no PR checks at all: what you run locally is all the checking it gets before it ships to
the fleet.

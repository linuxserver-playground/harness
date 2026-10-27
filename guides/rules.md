# Rules

They hold in every repo and on both paths. A repo's own `AGENTS.md` adds to them, and
`repos/builder/CONVENTIONS.md` (§8 for commits and PRs) is the source.

## Filing anything

- **The person files; you draft.** Issues, PRs, comments, reviews, labels and merges are run by the person,
  or by you only after they read the draft and say so. The `gh` commands that do this are deliberately left
  off the allowlist, so they always ask first.
- **Search first.** Before drafting an issue or a PR, search for an open one about the same thing
  (`gh search issues`, `gh search prs`, `./harness lookup`). Add to an existing one rather than duplicating
  it.
- **No typo-only PRs.** File an issue, and a maintainer will fold the fix into other work. Docs pages are the
  exception: fixing them is the change.
- **The real `linuxserver` org is read-only.** No pushes, PRs, issues or comments there. Reading it for
  intent is fine.

## Commits

- The subject is a short imperative sentence: "Add libfoo to fix thumbnail generation". No prefixes
  (`fix:`, `[docs]`), no emoji, no period.
- **No trailers of any kind.** That includes `Co-Authored-By` lines for AI tools and `Signed-off-by`. The
  harness turns Claude Code's attribution off; other agents must leave it out themselves.
- One focused change per PR, with the smallest diff that does it. No drive-by refactors or rewording.
- Bot commits (`Update generated files [skip ci]`, `Update package versions`) are the pipeline's. Never
  write one by hand.

## Pull requests

- **Use [templates/pr-body.md](../templates/pr-body.md)** (`./harness draft pr <repo>` fills it). It keeps the
  org template's checklist and adds the `harness` block a reviewer's agent parses.
- **Disclose AI use** in the description: the tool and model, and what it did. The person confirms that they
  read every line and, for images, built and ran it.
- **Validation is evidence.** Paste what `./harness validate` wrote. Mark anything not run as "not run",
  with the reason.
- **One PR per repo.** A change across repos is a change train ([contract-change](playbooks/contract-change.md)):
  one tracking issue, then PRs that link it in order.
- Put `Closes linuxserver-playground/<repo>#<n>` in the body when the PR resolves an issue.

## Generated files

These are never edited by hand. Change the source:

| Generated | Source |
| --- | --- |
| Image repo `README.md`, `AGENTS.md`, `LICENSE`, `.github/workflows/build.yml`, `pr-report.yml` | `image.yml`, or the builder templates for every repo |
| Mod branch `README.md`, `AGENTS.md`, `build.yml` | `mod.yml` |
| `package_versions.txt` | The build |
| The hub's `data/`, `dist/`, `out/` | The hub's ingest and generators |
| The site's `src/data/`, `src/content/imagedocs/`, `moddocs/` | The hub's API (`npm run data`) |
| `unraid-store`, `umbrel-store`, `runtipi-store` | The hub's generators |

A PR to an existing image branch that changes a generated file fails its build. The live build re-renders
them after merge. The one exception is a new repo's first PR, which carries everything
([new-image](playbooks/new-image.md)).

## Namespaces

- Everything references `linuxserver-playground` only. The exceptions are links to upstream docs and the
  images the playground does not build yet (selkies-layers, proot-apps).
- Images build `FROM ghcr.io/linuxserver-playground/baseimage-*`.
- When you must rewrite a reference to the playground, add a row to
  `repos/workspace/docs/playground-references.md`, so it can be swapped back at the cutover.

## Secrets

- No change needs a secret: every test runs against fixtures and mocks.
- Never print, copy or commit one. `GITHUB_TOKEN=$(gh auth token) <command>` passes your own token inline
  where a tool needs it.
- A change that needs a *new* credential degrades cleanly without it, and asks in the PR for a maintainer to
  set it. Never ask anyone to paste a secret into a chat, an issue or a file.

## Decisions

`repos/workspace/DECISIONS.md` lists settled choices: GitHub only, one manifest per branch, generic smoke
tests, the site as the single pane of glass, and others. Do not build against them. If the person wants to
change one, help them write it up for the maintainers instead.

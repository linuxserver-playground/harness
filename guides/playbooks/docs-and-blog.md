# Playbook: docs-and-blog

**For:**

- **Members:** docs (including new pages and sections) and blog posts.
- **Contributors:** docs pages in existing sections. No blog posts.

**Asks like:**

- "Fix the Kubernetes docs page."
- "Write a docs page about using mods with swag."
- "Write a blog post about this month's changes."

**Output:** a PR to `site`, or an edit made through the site's own editor.

## Where things live

All of these are in `repos/site`. Read its `AGENTS.md` and `CONTRIBUTING.md` first.

| Content | Path | Notes |
| --- | --- | --- |
| Docs pages | `src/content/docs/<section>/<slug>.md` | Sections: `general`, `selkies`, `misc`, `faq`. Front matter needs `title`, `description` and `section` (matching the folder); optional `order`, `group`, `tags`, `aliases`. `npm run new-doc` scaffolds one |
| A new docs section | `src/lib/docs-sections.ts` plus a folder | Members only |
| Blog posts | `src/content/posts/<slug>/index.md`, images beside it | `title` required; leave out `date`, because git dates the post at merge. `npm run new-post` scaffolds one. Members only |
| Authors | `src/content/authors/*.yaml` | |
| Image documentation | not here | It comes from each image's `image.yml`. Fix it there ([fix-image](fix-image.md)) |
| Mod documentation | not here | It comes from each mod's `mod.yml` ([mod](mod.md)) |

Front matter is validated at build time (`src/content.config.ts`). When a page moves, add its old URL to
`aliases` and to `public/_redirects`.

## Two ways to make the change

- **The site's editor**, for members who can edit the site. Sign in on the site, then use Edit, Delete, New
  post or New page on the page itself. Every save is a commit on `edit/<login>/…`, and the change is one PR
  that a reviewer merges. It suits quick edits and posts with images. The person does this in the browser;
  you can draft the Markdown for them to paste.
- **A PR from the harness**, for anything larger, or for contributors:
  1. Members: `./harness get site`. Contributors: also run `./harness fork site`. Then
     `./harness setup site`.
  2. Branch from `main`, and write the page or post. Match the voice of the neighbouring pages: plain,
     direct, second person, no marketing.
  3. Validate with `./harness validate site`, which runs check, build, a11y, search and overflow at 390px on
     the home page. Then run overflow on the page you changed:
     `node scripts/overflow.mjs http://localhost:4321/site/<path>/`.
  4. Look at it: `npx astro preview --port 4321` in `repos/site`, then open the page.
  5. Commit, push, and run `./harness draft pr site main`.

## Blog posts (members)

- Base the facts on data, using [whats-new](whats-new.md) for "what changed" posts, and link the PRs and build
  pages.
- Put a hero image beside the post when it has one (`hero`, `heroAlt`).
- Posts appear when their PR merges. No `draft:` or `date:` is needed.

## Contributors

Docs PRs are welcome for fixing wrong or unclear pages, and for adding a page to an existing section. A new
section, layout changes and blog posts go in an issue on `site` describing what you would like.

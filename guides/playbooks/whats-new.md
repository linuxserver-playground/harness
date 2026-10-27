# Playbook: whats-new

**For:** anyone. **Asks like:**

- "What changed this week?"
- "Catch me up."
- "What did we release yesterday?"

**Output:** a digest. It is read-only. Members may turn it into a blog post ([docs-and-blog](docs-and-blog.md)).

## Steps

1. **Pick the window** (default: 7 days), and say what it is.
2. **Merged PRs:**
   `gh search prs --owner linuxserver-playground --merged --merged-at ">=YYYY-MM-DD" --json repository,number,title,author,closedAt --limit 200`.
   Group them: infrastructure (builder, workflows, ci, hub, site, control), images, mods, docs and blog,
   harness.
3. **Releases:** control's `/api/releases.json` in the window. Count them per image, and pick out new
   upstream versions as opposed to rebuilds (`-lsN` bumps only).
4. **Decisions and recipes:** `git -C repos/workspace log --since=… --oneline`. The workspace's commits
   record decisions ("Record …") and new recipes. Also check
   `git -C repos/workspace log --since=… -p -- DECISIONS.md`.
5. **Fleet changes:** new repos (`gh repo list linuxserver-playground --json name,createdAt`), archived or
   removed images, new mods (`/api/v1/mods.json`).
6. **Changelog lines** from `/api/v1/changelog.json` in the window: the user-facing image changes.

## Answer shape

Lead with the 3–5 changes that matter most to the team. Then short grouped lists with links. Then numbers:
releases, PRs merged, new images. Keep it to one screen.

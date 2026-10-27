# Start here: what you can ask

For the person at the keyboard (and for the agent, when the person asks "what can I ask you?"). You do not
need to know the repos or the commands. Ask the way you would ask a colleague who has read everything. The agent
picks the playbook, pulls live data, and shows you its sources.

Some habits make an agent useful:

- **Say what you want to end up with.** That might be an answer, a ranked list, an issue, a pull request or
  a review. "Explain" gets you prose. "Fix" gets you a branch.
- **Ask it to show its work.** Every claim should come with a link or a command you could run yourself.
- **Let it test.** Image changes are built and run in your Docker before anyone calls them done. If your
  machine cannot build the other architecture, the agent says so; the PR build covers it.
- **Read the draft.** The agent never files anything by itself. It shows you the issue, PR or review text,
  and runs the `gh` command only when you approve.
- **Push back.** If an answer looks wrong, say why. The agent re-checks rather than defends.

## Understanding the org

- "What needs my attention today?"
- "What PRs are open across the org? Rank them, and tell me which one is blocking a release."
- "Prioritise the open issues by how many users they affect."
- "Which live branches are red right now, and is each one our fault, upstream's or a network flake?"
- "Explain the failing build of sabnzbd to me like I've never seen this pipeline."
- "What does `[ls.io-init] done.` mean, and what happens before it?"
- "Walk me through what happens from a push to docker-sonarr until the website shows the release."
- "Which images still build FROM baseimage-alpine 3.22?"
- "Which images ship openssl, and at what versions?"
- "What changed in the fleet this week?"
- "How busy are the runners? Can we afford to rebuild every alpine image today?"

## Bugs and consequences

- "Someone says heimdall forgets its tiles after a restart. Is that us or upstream? Reproduce it."
- "Explain issue 12 on docker-sonarr. What happens if we leave it for a month?"
- "If we bump baseimage-alpine to 3.25, what breaks, and how many builds does it trigger?"
- "What would removing the `runtime.nonroot` field from image.yml touch?"
- "Is this vulnerability on the nextcloud build page something we can fix, or is it upstream's?"

## Reviewing

- "Review PR 5 on docker-heimdall. Build it, run it, and compare it with the released image."
- "Go through every open PR that's waiting on review and draft a review for each."
- "Does this PR follow our rules? Generated files, changelog, both Dockerfiles?"

## Changing things

- "Add the `ffmpeg` package to the jellyfin image, test it, and draft the PR."
- "Add a new env var to heimdall that sets the default theme."
- "Add an image for Mealie." Members get a new repo and a PR. Contributors get a proposal for the labs org.
- "Make a mod that installs yt-dlp into any image."
- "Fix the typo on the Kubernetes docs page."
- "Write a blog post announcing the new build pages, using last month's merged PRs." (members)
- "Add a `homepage` field to image.yml and show it on the image pages." This is a change train across builder,
  the hub and the site.
- "Rerun the failed arm64 build of calibre." (members)

## Running things

- "Run sonarr locally so I can click around."
- "Run the PR build of heimdall #5 next to the released one."
- "Show me what the README will look like after my image.yml change."
- "Force a hub refresh and tell me when the site has the new build." (members)

## When it says no

The guard hook stops commands that are wrong for your role. A contributor cannot push to the org. Nobody
pushes straight to a live branch. When it stops something, the agent tells you why and takes the right path
instead: a fork, a branch and PR, or a question for a maintainer.

If you are a member and a playbook step really needs the protected action, you approve it with
`./harness allow …`. Examples are moving the `v1` tag and deleting a removed image's packages.

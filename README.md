# harness

The way in to running the [LinuxServer.io v2 playground](https://github.com/linuxserver-playground) with an AI
coding agent. Clone it and start your agent at its root. Then ask in plain words:

- "What needs my attention today?"
- "Explain this red build."
- "Review PR 12 on docker-sonarr and test it."
- "Add an image for X."

The agent works out who you are to the org, learns the whole system, reads live data, tests in your local
Docker, and drafts the issue, pull request or review. You read every draft before it is filed.

## Start

You need git, the [GitHub CLI](https://cli.github.com/) signed in (`gh auth login`), jq, curl and Docker. Python
3.12+ and Node 22+ are only needed for infrastructure changes.

```bash
gh repo clone linuxserver-playground/harness && cd harness
./harness doctor        # what you have, and what anything missing rules out
./harness core          # clone the infrastructure repos into repos/ (about a minute)
claude                  # or any agent that reads AGENTS.md
```

Your first question can simply be "What can I ask you?". [guides/start-here.md](guides/start-here.md) has a
tour with example prompts for every area.

## Members and contributors

The harness asks GitHub whether you belong to `linuxserver-playground`, and gives you one of two paths:

| | Member | Contributor |
| --- | --- | --- |
| Understand the org: PRs, issues, builds, fleet, data | yes | yes |
| Fix an image, a mod, docs or infrastructure | a branch and a pull request | a fork and a pull request |
| New images | create the repo, then a pull request for review | a proposal to `linuxserver-playground-labs` |
| Blog posts | yes | no |
| Fleet operations: rerun, dispatch, skip, release, remove | yes | ask a maintainer |
| Reviews, labels and triage | posted by you | read-only |

Either way, a person reads and files every issue, PR and review. The agent drafts them.

## What is here

| Path | What |
| --- | --- |
| `AGENTS.md` | Where the agent starts: role, request table, rules. `CLAUDE.md` imports it. |
| `harness` | The CLI: `whoami`, `doctor`, `core`/`get`/`sync`/`fork`/`setup`, `snapshot`, `lookup`, `try`, `render`, `validate`, `draft`, `allow`. `./harness help` lists them. |
| `guides/` | The system map, data sources, rules, local testing, gotchas, role guides and one playbook per kind of request. |
| `templates/` | Pull request, issue, review, triage, image proposal and change-train templates. |
| `.claude/` | Settings (a read-only allowlist, commit attribution off), the SessionStart and guard hooks, one skill per playbook. |
| `docs/evals.md` | Requests to try after changing a guide or hook, with what a good answer looks like. |
| `repos/` | Your clones of the org's repos (gitignored). |
| `.harness/` | Your profile, snapshots, validation reports and drafts (gitignored). |

## Related

- [workspace](https://github.com/linuxserver-playground/workspace) is the maintainers' unguarded workbench
  for broad changes. It holds the settled decisions (`DECISIONS.md`) and the working notes the harness links
  to.
- [The website](https://linuxserver-playground.github.io/site/) shows images, builds, the fleet, docs and the
  blog. Its [Contribute page](https://linuxserver-playground.github.io/site/contribute/) and
  [Contribute docs](https://linuxserver-playground.github.io/site/docs/contribute/) are the public way in that
  sends people here. The [hub](https://linuxserver-playground.github.io/hub/) serves the data, and
  [control](https://ci.thelamer.duckdns.org:8443/status) schedules and tracks builds.

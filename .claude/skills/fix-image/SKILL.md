---
name: fix-image
description: Change an image repo (Dockerfiles, root/, image.yml) on a branch or fork, validate and run it locally, and draft the PR. Use for 'add package', 'fix image X', 'add an env var'.
---

Read `guides/playbooks/fix-image.md` in this repository and follow it step by step. Check the role in
`.harness/profile.json` (run `./harness whoami` if it is missing) and take that role's path through the
playbook. Draft anything that would be filed or posted; the person approves it.

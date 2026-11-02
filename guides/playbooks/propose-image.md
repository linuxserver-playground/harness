# Playbook: propose-image

**For:** contributors who want an image of an application they do not develop. A developer packaging their own app
uses [labs-image](labs-image.md), which covers making the app easy to self-host first. Members use
[new-image](new-image.md) for the main org, or accept proposals into Labs with [labs-accept](labs-accept.md).
**Asks like:**

- "I'd like LinuxServer to ship an image for X."
- "Can you package Y?"

**Output:** a proposal in `linuxserverlabs-playground/proposals`, filled in from real data and filed by the person.

New images from outside the team start in **LinuxServer Labs** (`linuxserverlabs-playground`; production
`linuxserverlabs`): a second org on the same pipeline for software that is not yet proven. A Labs image can graduate
to the main org later. The process is in `repos/workspace/docs/labs.md` and the proposals repository's
[README](https://github.com/linuxserverlabs-playground/proposals#readme).

## Steps

1. **Check that it does not exist:**
   - the main org's images: `curl -fsS https://linuxserver-playground.github.io/hub/api/v1/images.json | jq -r '.data.repositories.linuxserver[].name' | grep -i <name>`;
   - Labs: `gh repo list linuxserverlabs-playground --limit 200 | grep -i <name>`, and open or closed proposals:
     `gh issue list -R linuxserverlabs-playground/proposals --state all --search "<name>"`;
   - LinuxServer's own fleet (`linuxserver/docker-<name>`, read-only).

   If it exists in some form, help the person comment there instead.
2. **Check it against the Labs bar** ([roles/labs-developer.md](../roles/labs-developer.md) lists it). Read the
   upstream repository for each point:
   - owned by an organisation, not a personal account (`gh api repos/<owner>/<repo> --jq .owner.type`): no
     exceptions, so a personal-account project stops here; suggest the person asks upstream to move it;
   - an approved open-source licence (`--jq .license.spdx_id`);
   - stable releases with assets whose names stay the same (`gh release list`, `gh release view --json assets`),
     or a source release the image can build;
   - a web UI on a port, or a desktop app for the selkies base;
   - works with just its own container: an embedded database option, no companion containers;
   - no paywalled vendor service at its core; telemetry disclosed and optional.

   Say plainly which points fail. A proposal that fails the bar is answered `needs-info` by the check within a
   minute; better to tell the person now.
3. **Draft the proposal:** `./harness draft proposal <name>` writes the form's fields to `.harness/drafts/`. Fill
   them as [labs-image](labs-image.md) part B, step 2 says: exact asset names or `.*` patterns, the start command in
   backticks under "Runtime and install", every path it writes state to, the first-run steps. Facts with links, not
   enthusiasm. Maintainers: the person's login, and upstream developers only if they agreed.
4. **File it.** Show the draft, then `./harness labs form <name>` prints the proposal form's link with every answer
   prefilled. The person opens it, ticks the bar and submits. Only without a browser, the `gh issue create` command
   it also prints (the form is what adds the `proposal` label).
5. **Watch the check's comment** and help the person edit the issue for anything it flags.
6. **Optional: try the image the team would build:** `./harness labs try <issue>` builds and runs it in a local
   sandbox from the filed proposal, so the person can see it work, or see what is missing, before a member does.

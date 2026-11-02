<!-- harness proposal draft (harness {{version}}): the fields of the LinuxServer Labs proposal form, in the layout
GitHub gives a form submission. Replace every TODO with facts and links, or with _No response_ for an optional field
that does not apply. HTML comments like this one are guidance and are dropped when you file it with
./harness labs form {{name}} (guides/playbooks/labs-image.md). -->
### Image name

{{name}}

### Upstream repository

TODO <!-- the URL of the repository, owned by an organisation, never a personal account -->

### Project homepage

TODO <!-- optional: _No response_ when the repository is the homepage -->

### Licence

TODO <!-- the SPDX id, such as MIT, Apache-2.0, AGPL-3.0-only -->

### Latest stable release

TODO <!-- the URL of the newest stable (not pre-) release -->

### How the image installs it

TODO <!-- exactly one of: Release asset | Source release -->

### amd64 release asset

TODO <!-- the file name of the amd64 asset in the latest release (or a regex on it); _No response_ for a source build -->

### arm64 release asset

TODO <!-- the same for arm64; _No response_ means amd64 only -->

### Application type

TODO <!-- exactly one of: Web application | Desktop application (selkies) -->

### Runtime and install

TODO <!-- what it is written in and how a release is installed and started: deb, tarball, single binary, node, python…
Put the start command in backticks, such as `/app/myapp/myapp serve --data /config`: the scaffold uses it. -->

### Working repository

TODO <!-- optional: the URL of your repository made from linuxserverlabs-playground/docker-template, built and run
locally (its GETTING-STARTED.md); the team starts from its image.yml, Dockerfiles and root/. _No response_ if none -->

### Web interface port

TODO <!-- the port the web interface listens on; _No response_ for a desktop app (selkies serves 3000/3001) -->

### Where it writes state

TODO <!-- every path it writes config, data or caches to, and how to point it at one directory (/config) -->

### Required environment variables

TODO <!-- one per line, KEY=example - what it does; _No response_ when none are required -->

### Database

TODO <!-- exactly one of: Embedded (SQLite or similar) | None needed | Server database baked into the image as a fallback -->

### First run

TODO <!-- the default login or setup wizard, and what "working" looks like on the first visit -->

### Screenshot

TODO <!-- optional: an image link, or _No response_ -->

### Maintainers

{{login}} <!-- GitHub logins, comma separated, no @: credit and who is mentioned, never access -->

### The Labs bar

- [ ] The upstream repository is owned by an organisation, not a personal account
- [ ] It has an approved open-source licence
- [ ] It cuts stable, versioned releases
- [ ] Release asset names stay the same from release to release
- [ ] It works with just this container (no companion containers)
- [ ] It needs no account with a paid vendor service to work
- [ ] Any telemetry is disclosed and can be turned off

<!-- Tick each box only when it is true, with the proof in the answers above. The web form asks again. -->

#!/usr/bin/env python3
"""LinuxServer Labs: turn a proposal issue into a v2 image repository, and prepare a member's accept commands.

Used by `./harness labs try` and `./harness labs accept`; standard library only. Nothing here touches the
network or GitHub: the harness fetches the issue, the upstream repository and its latest release with `gh`
and passes the JSON files in, so the parser and the generator can be tested against fixtures.

    labs.py parse    --issue issue.json                       the form's answers as JSON
    labs.py scaffold --issue issue.json --repo repo.json --release release.json --out DIR [--member LOGIN] [--date D]
    labs.py accept   --dir DIR [--member LOGIN]                write accept.sh, after-merge.sh and the PR body
    labs.py form     --draft FILE --repo OWNER/proposals --body OUT   a filled draft as a prefilled form link

The proposal form is `.github/ISSUE_TEMPLATE/proposal.yml` in linuxserverlabs-playground/proposals. GitHub renders
a submission as "### <label>" blocks, so the parser keys on the labels, never on the field ids.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import shlex
import stat
import sys
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path

LABS_ORG = os.environ.get("HARNESS_LABS_ORG", "linuxserverlabs-playground")
PIPELINE_ORG = os.environ.get("HARNESS_PIPELINE_ORG", "linuxserver-playground")
PROPOSALS = f"{LABS_ORG}/proposals"
TEMPLATE = f"{LABS_ORG}/docker-template"
BASE = f"ghcr.io/{PIPELINE_ORG}"
NO_RESPONSE = {"", "_no response_", "none", "n/a", "-"}

# Form labels (exact text) -> keys. Keep in step with proposal.yml; the parser accepts nothing else.
LABELS = {
    "Image name": "name",
    "Upstream repository": "upstream_repo",
    "Project homepage": "homepage",
    "Licence": "license",
    "Latest stable release": "release_url",
    "How the image installs it": "build_from",
    "amd64 release asset": "asset_amd64",
    "arm64 release asset": "asset_arm64",
    "Application type": "app_type",
    "Runtime and install": "runtime",
    "Working repository": "working_repo",
    "Web interface port": "web_port",
    "Where it writes state": "state_paths",
    "Required environment variables": "env_vars",
    "Database": "database",
    "First run": "first_run",
    "Screenshot": "screenshot",
    "Maintainers": "maintainers",
    "The Labs bar": "bar",
}
REQUIRED = ["name", "upstream_repo", "license", "release_url", "build_from", "app_type", "runtime", "state_paths",
            "database", "first_run", "maintainers"]
BAR = [
    "The upstream repository is owned by an organisation, not a personal account",
    "It has an approved open-source licence",
    "It cuts stable, versioned releases",
    "Release asset names stay the same from release to release",
    "It works with just this container (no companion containers)",
    "It needs no account with a paid vendor service to work",
    "Any telemetry is disclosed and can be turned off",
]
SELKIES = "Desktop application (selkies)"
WEB = "Web application"
SOURCE = "Source release"
DB_FALLBACK = "Server database baked into the image as a fallback"
NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
LOGIN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")
ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
GENERATED = {"README.md", "AGENTS.md", "LICENSE", ".github/FUNDING.yml", "root/donate.txt",
             ".github/workflows/build.yml", ".github/workflows/pr-report.yml"}


class ProposalError(Exception):
    """The issue is not a proposal the scaffold can be built from."""


# ------------------------------------------------------------------------------------------------ parsing


def parse_body(body: str) -> dict[str, str]:
    """The form's answers by key. Unknown headings are kept under their label, so a renamed field shows up."""
    answers: dict[str, str] = {}
    current = None
    lines: list[str] = []

    def flush() -> None:
        if current is not None:
            text = "\n".join(lines).strip()
            answers[current] = "" if text.lower() in NO_RESPONSE else text

    body = re.sub(r"<!--.*?-->", "", body.replace("\r\n", "\n"), flags=re.S)
    for line in body.split("\n"):
        heading = re.match(r"^###\s+(.+?)\s*$", line)
        if heading:
            flush()
            label = heading.group(1)
            current = LABELS.get(label, label)
            lines = []
        elif current is not None:
            lines.append(line)
    flush()
    return answers


def checkboxes(text: str) -> dict[str, bool]:
    return {m.group(2).strip(): m.group(1).lower() == "x" for m in re.finditer(r"^- \[([ xX])\]\s*(.+)$", text, re.M)}


def strip_code(value: str) -> str:
    """Answers pasted in backticks or a code fence still read as plain values."""
    value = value.strip()
    fence = re.match(r"^```[^\n]*\n(.*?)\n```$", value, re.S)
    if fence:
        value = fence.group(1).strip()
    if len(value) > 1 and value.startswith("`") and value.endswith("`"):
        value = value[1:-1].strip()
    return value


@dataclass
class EnvVar:
    name: str
    value: str
    description: str


@dataclass
class Proposal:
    number: int
    url: str
    author: str
    title: str
    labels: list[str]
    answers: dict[str, str]
    problems: list[str] = field(default_factory=list)

    def get(self, key: str) -> str:
        return strip_code(self.answers.get(key, ""))

    @property
    def name(self) -> str:
        return self.get("name").lower()

    @property
    def selkies(self) -> bool:
        return self.get("app_type") == SELKIES

    @property
    def source_build(self) -> bool:
        return self.get("build_from") == SOURCE

    @property
    def maintainers(self) -> list[str]:
        logins = [m.strip().lstrip("@") for m in re.split(r"[,\s]+", self.get("maintainers")) if m.strip()]
        return list(dict.fromkeys(logins))

    @property
    def upstream(self) -> tuple[str, str, str]:
        """(host, owner, repo) from the upstream repository URL."""
        m = re.match(r"^(?:https?://)?(?:www\.)?([^/]+)/([^/\s]+)/([^/\s#?]+?)(?:\.git)?/?(?:[#?].*)?$", self.get("upstream_repo"))
        if not m:
            return ("", "", "")
        return (m.group(1).lower(), m.group(2), m.group(3))

    @property
    def web_port(self) -> int | None:
        if self.selkies:
            return 3001
        m = re.search(r"\d{1,5}", self.get("web_port"))
        return int(m.group(0)) if m and 0 < int(m.group(0)) < 65536 else None

    @property
    def env_vars(self) -> list[EnvVar]:
        out = []
        for raw in self.get("env_vars").splitlines():
            line = raw.strip().lstrip("-*").strip().replace("`", "")
            m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*(?:(=)\s*(\S*)\s*(?:[-#:–]\s*(.*))?|[:–-]\s*(.*))?$", line)
            if not m or m.group(1) in ("PUID", "PGID", "TZ"):
                continue
            value = m.group(3) or ""
            description = (m.group(4) or m.group(5) or "").strip() or f"Set {m.group(1)} (from the proposal)."
            out.append(EnvVar(m.group(1), value, description))
        return out


def load_proposal(issue: dict) -> Proposal:
    body = issue.get("body") or ""
    proposal = Proposal(
        number=int(issue.get("number") or 0),
        url=issue.get("url") or "",
        author=(issue.get("author") or {}).get("login", ""),
        title=issue.get("title") or "",
        labels=[label.get("name", "") for label in issue.get("labels") or []],
        answers=parse_body(body),
    )
    problems = proposal.problems
    if not any(label in proposal.answers for label in ("name", "upstream_repo")):
        raise ProposalError("the issue body has none of the proposal form's fields: is it a proposal?")
    for key in REQUIRED:
        if not proposal.get(key):
            problems.append(f"'{label_of(key)}' is empty")
    if proposal.name and not NAME.match(proposal.name):
        problems.append(f"the image name {proposal.name!r} does not match ^[a-z0-9][a-z0-9-]{{0,62}}$")
    bad = [m for m in proposal.maintainers if not LOGIN.match(m)]
    if bad:
        problems.append(f"maintainers that are not GitHub logins: {', '.join(bad)}")
    if proposal.author and proposal.author not in proposal.maintainers:
        problems.append(f"the proposer ({proposal.author}) is not among the maintainers; the image credits them anyway")
    if proposal.get("app_type") not in (WEB, SELKIES):
        problems.append(f"unknown application type {proposal.get('app_type')!r}")
    if proposal.get("app_type") == WEB and proposal.web_port is None:
        problems.append("a web application needs its web interface port")
    if not proposal.source_build and not proposal.get("asset_amd64"):
        problems.append("a release-asset build needs the amd64 asset")
    ticked = checkboxes(proposal.answers.get("bar", ""))
    missing = [item for item in BAR if not ticked.get(item)]
    if missing:
        problems.append("the bar is not confirmed: " + "; ".join(missing))
    return proposal


def label_of(key: str) -> str:
    return next((label for label, k in LABELS.items() if k == key), key)


# ------------------------------------------------------------------------------------------------ assets


@dataclass
class Asset:
    arch: str
    given: str
    name: str  # the matching asset of the latest release, or "" when nothing matched
    url_template: str  # the download URL with the version arg in shell syntax, or "" (look it up by regex)
    regex: str  # for require_assets
    kind: str  # deb, appimage, tar, zip, binary, rpm, other


def looks_like_regex(text: str) -> bool:
    return bool(re.search(r"[\^$*+?()\[\]{}|\\]", text))


def asset_kind(name: str) -> str:
    lower = name.lower()
    if lower.endswith(".deb"):
        return "deb"
    if lower.endswith(".appimage"):
        return "appimage"
    if re.search(r"\.(tar\.gz|tgz|tar\.xz|txz|tar\.bz2|tar\.zst|tar)$", lower):
        return "tar"
    if lower.endswith(".zip"):
        return "zip"
    if lower.endswith(".rpm"):
        return "rpm"
    if "." not in lower.rsplit("/", 1)[-1] or re.search(r"[-_](amd64|x86_64|x64|arm64|aarch64)$", lower):
        return "binary"
    return "other"


def version_regex(name: str, tag: str) -> str:
    """A require_assets pattern for an asset name: the version part becomes .*, the rest is literal."""
    version = tag[1:] if tag[:1] in "vV" else tag
    for literal in (tag, version):
        if literal and literal in name:
            head, _, tail = name.partition(literal)
            return "^" + re.escape(head) + ".*" + re.escape(tail) + "$"
    return "^" + re.escape(name) + "$"


def resolve_asset(arch: str, given: str, release: dict, download_base: str, version_arg: str) -> Asset:
    given = strip_code(given).rsplit("/", 1)[-1] if not looks_like_regex(strip_code(given)) else strip_code(given)
    tag = release.get("tag_name") or ""
    names = [a.get("name", "") for a in release.get("assets") or []]
    name = ""
    if given in names:
        name = given
    elif looks_like_regex(given):
        try:
            name = next((n for n in names if re.search(given, n)), "")
        except re.error:
            name = ""
    else:
        # A name from an older release: match it with its version part as a wildcard.
        pattern = re.sub(r"\d+(?:\.\d+)+", "__V__", given)
        wild = "^" + re.escape(pattern).replace("__V__", r"\d+(?:\.\d+)+") + "$"
        name = next((n for n in names if re.match(wild, n)), "")
    if not name:
        regex = given if looks_like_regex(given) else version_regex(given, tag)
        return Asset(arch, given, "", "", regex, asset_kind(given))
    version = tag[1:] if tag[:1] in "vV" else tag
    if tag and tag in name:
        templ = name.replace(tag, "${" + version_arg + "}")
    elif version and version in name:
        templ = name.replace(version, "${" + version_arg + "#v}")
    else:
        templ = name
    url = f"{download_base}/${{{version_arg}}}/{templ}"
    return Asset(arch, given, name, url, version_regex(name, tag), asset_kind(name))


# ------------------------------------------------------------------------------------------------ yaml


def q(value: str) -> str:
    """A YAML scalar: plain when safe, single-quoted otherwise."""
    if value == "" or re.search(r"[:#\[\]{},&*!|>'\"%@`]|^[-?\s]|\s$|^(true|false|yes|no|null|~|on|off)$|^[\d.+-]+$", value, re.I):
        return "'" + value.replace("'", "''") + "'"
    return value


def block(text: str, indent: int) -> str:
    pad = " " * indent
    return "|-\n" + "\n".join(pad + line if line.strip() else "" for line in text.strip("\n").splitlines())


# ------------------------------------------------------------------------------------------------ scaffold


@dataclass
class Scaffold:
    proposal: Proposal
    repo: dict
    release: dict
    member: str
    date: str
    todos: list[str] = field(default_factory=list)
    files: dict[str, str] = field(default_factory=dict)
    executable: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        p = self.proposal
        self.name = p.name
        self.arg = re.sub(r"[^A-Z0-9]", "_", self.name.upper()) + "_RELEASE"
        host, owner, repo = p.upstream
        self.host, self.owner, self.repo_name = host, owner, repo
        self.slug = f"{owner}/{repo}"
        self.title = self.repo.get("name") or repo or self.name
        described = re.match(r"^\s*([^:–-]+?)\s*[:–-]", self.repo.get("description") or "")
        if described and described.group(1).lower() == self.title.lower():
            self.title = described.group(1)  # "PhotoCraft: an open-source…" spells the name its own way
        elif self.title.islower():
            self.title = self.title[:1].upper() + self.title[1:]
        self.homepage = p.get("homepage") or self.repo.get("homepage") or p.get("upstream_repo")
        self.tag = self.release.get("tag_name") or ""
        if host == "github.com":
            self.source_type = "github_release"
            self.download_base = f"https://github.com/{self.slug}/releases/download"
            self.latest_api = f"https://api.github.com/repos/{self.slug}/releases/latest"
            self.archive = f"https://github.com/{self.slug}/archive/refs/tags/${{{self.arg}}}.tar.gz"
            self.archive_template = f"https://github.com/{self.slug}/archive/refs/tags/${{VERSION}}.tar.gz"
        elif host == "codeberg.org":
            self.source_type = "codeberg_release"
            self.download_base = f"https://codeberg.org/{self.slug}/releases/download"
            self.latest_api = f"https://codeberg.org/api/v1/repos/{self.slug}/releases/latest"
            self.archive = f"https://codeberg.org/{self.slug}/archive/${{{self.arg}}}.tar.gz"
            self.archive_template = f"https://codeberg.org/{self.slug}/archive/${{VERSION}}.tar.gz"
        else:
            self.source_type = ""
            self.download_base = f"https://{host}/{self.slug}/releases/download"
            self.latest_api = ""
            self.archive = ""
            self.archive_template = ""
            self.todos.append(f"image.yml: the upstream is on {host or 'an unknown host'}; write its version source "
                              "(gitea_release, json, regex…) and require_assets by hand")
        self.assets: dict[str, Asset] = {}
        if not p.source_build:
            for arch in ("amd64", "arm64"):
                given = p.get(f"asset_{arch}")
                if given:
                    asset = resolve_asset(arch, given, self.release, self.download_base, self.arg)
                    self.assets[arch] = asset
                    if not asset.name:
                        self.todos.append(f"{arch}: no asset of {self.tag or 'the latest release'} matches {given!r}; "
                                          "the Dockerfile looks it up by that pattern at build time. Check the name")
        self.platforms = ["amd64", "arm64"] if p.source_build else [a for a in ("amd64", "arm64") if a in self.assets]
        if not self.platforms:
            self.platforms = ["amd64"]
        self.base = self.pick_base()

    # The base image family and its tags per arch.
    def pick_base(self) -> str:
        """selkies for a desktop app; ubuntu for a deb or a native build linked against glibc (most prebuilt Go with
        cgo, Rust, C and C++ binaries); alpine for interpreted runtimes, musl or static builds, and when unsure."""
        p = self.proposal
        if p.selkies:
            self.base_reason = "a desktop application"
            return "selkies"
        kinds = {a.kind for a in self.assets.values()}
        text = (p.get("runtime") + " " + " ".join(a.name or a.given for a in self.assets.values())).lower()
        if "deb" in kinds or re.search(r"(glibc|linux-gnu|gnu libc|\.deb\b|\bdebian\b|\bubuntu\b|\.net\b|dotnet|electron)", text):
            self.base_reason = "a deb, .NET or a glibc build"
            return "ubuntu"
        if re.search(r"(musl|alpine|static|cgo_enabled=0)", text):
            self.base_reason = "a musl or static build"
            return "alpine"
        if re.search(r"\b(node(\.js|js)?|python|php|ruby|java|jvm)\b", text):
            self.base_reason = "an interpreted runtime"
            return "alpine"
        if kinds & {"binary", "tar", "zip", "appimage"} and re.search(r"\b(go|golang|rust|c\+\+|c|binary|native)\b", text):
            self.base_reason = "a prebuilt native binary, which is usually linked against glibc"
            self.todo_once("Dockerfiles: baseimage-ubuntu because a prebuilt native binary is usually linked against glibc; "
                           "use baseimage-alpine (smaller) if upstream ships a static or musl build")
            return "ubuntu"
        self.base_reason = "the default"
        return "alpine"

    def from_line(self, arch: str) -> str:
        prefix = "" if arch == "amd64" else "arm64v8-"
        tags = {"selkies": ("baseimage-selkies", "ubunturesolute"), "ubuntu": ("baseimage-ubuntu", "resolute"),
                "alpine": ("baseimage-alpine", "3.24")}
        image, tag = tags[self.base]
        return f"FROM {BASE}/{image}:{prefix}{tag}"

    # ---------------------------------------------------------------- image.yml

    def image_yml(self) -> str:
        p = self.proposal
        description = (self.repo.get("description") or "").strip().rstrip(".")
        if not description:
            description = "TODO: one or two sentences on what the application does"
            self.todos.append("image.yml: the summary (the upstream repository has no description)")
        if description.lower().startswith(self.title.lower()) and description[len(self.title):][:1] in (":", " ", "-"):
            description = description[len(self.title):].lstrip(" :-–").strip()
        if description[:1].isupper() and description[1:2].islower():
            description = description[:1].lower() + description[1:]
        summary = f"[{self.title}]({self.homepage}): {description}."
        out = [f"# The manifest for docker-{self.name}. Schema: https://github.com/{PIPELINE_ORG}/builder/blob/main/schemas/image.schema.json",
               "schema: 1", f"name: {self.name}", ""]
        if self.title.lower() != self.name:
            out[-1:] = [f"title: {q(self.title)}", ""]
        out += ["summary: " + block(summary, 2), ""]
        out += ["maintainers:"] + [f"- {m}" for m in (p.maintainers or [p.author])] + [""]
        out += ["upstream:", f"  url: {q(self.homepage)}", "  version:"]
        if self.source_type:
            out += [f"    type: {self.source_type}", f"    repo: {self.slug}", "    require_assets:"]
            if p.source_build:
                out.append(f"    - {q(self.archive_template)}")
            else:
                out += [f"    - asset: {q(a.regex)}" for a in self.assets.values()]
            out += ["  notes:", f"    type: {self.source_type}", f"    repo: {self.slug}"]
        else:
            out += ["    type: static  # TODO: a version source that follows the upstream's stable releases",
                    f"    value: {q(self.tag or 'TODO')}"]
        out += ["", "release:", "  branch: main", "  tag: latest", "  channel: stable", ""]
        out += ["build:", f"  base: {self.base}", f"  version_arg: {self.arg}", "  platforms:"]
        out += [f"  - {a}" for a in self.platforms] + [""]
        out += ["test:", "  startup_timeout: 120", "  web:"]
        if p.selkies:
            out += ["    port: 3001", "    scheme: https", "    auth: user:password", "    screenshot_delay: 30"]
        else:
            out += [f"    port: {p.web_port or 80}"]
        out += ["", "runtime:", "  ports:"]
        if p.selkies:
            out += ["  - internal: '3000'", f"    description: {q(self.title + ' desktop gui HTTP, must be proxied.')}",
                    "  - internal: '3001'", f"    description: {q(self.title + ' desktop gui HTTPS.')}"]
        else:
            out += [f"  - internal: '{p.web_port or 80}'", f"    description: {q('The ' + self.title + ' web interface.')}"]
        envs = p.env_vars
        if envs:
            out.append("  env:")
            for env in envs:
                out += [f"  - name: {env.name}", f"    value: {q(env.value)}", f"    description: {q(env.description)}"]
        volume_note = ("Users home directory in the container, stores local files and settings" if p.selkies
                       else f"Where {self.title} keeps its configuration and data")
        out += ["  volumes:", "  - path: /config", f"    host_path: /path/to/{self.name}/config",
                f"    description: {q(volume_note)}"]
        if p.selkies:
            out += ["  custom:", "  - flag: shm-size", "    compose: shm_size", "    value: 1gb",
                    "    description: Recommended for all desktop images."]
        out += ["", "docs:", "  categories:", f"  - {'Desktop' if p.selkies else 'Web'}  # TODO: the category users browse for"]
        self.todo_once("image.yml: docs.categories is a placeholder; pick the category users browse for, and add a "
                       "docs.logo if the project has one")
        setup = []
        if p.selkies:
            setup += ["The application can be accessed at:", "", "* https://yourhost:3001/"]
        else:
            setup += [f"Access the web interface at `http://<your-ip>:{p.web_port or 80}`."]
        first_run = p.get("first_run")
        if first_run:
            setup += ["", first_run]
        out += ["  setup: " + block("\n".join(setup), 4)]
        if p.selkies:
            out += ["  notices:", "    strict_proxy: true", "    selkies:", "      enabled: true", "      nvidia: true"]
        out += ["", "proxy:"]
        if p.selkies:
            out += ["  port: 3001", "  scheme: https", "  subdomain: true", "  subfolder:", "    supported: false"]
        else:
            out += [f"  port: {p.web_port or 80}", "  subdomain: true", "  subfolder:",
                    "    supported: false  # TODO: true, with base_url_note, when the app can serve under a path"]
        out += ["", "changelog:", f"- date: '{self.date}'", "  text: Initial release.", ""]
        return "\n".join(out)

    # ---------------------------------------------------------------- Dockerfiles

    def fetch_lines(self, asset: Asset | None, target: str) -> list[str]:
        """Shell lines (no trailing ' && \\') that download the release asset or source archive to target."""
        p = self.proposal
        lines = []
        if self.latest_api:
            lines += [f"if [ -z ${{{self.arg}+x}} ]; then",
                      f"  {self.arg}=$(curl -sX GET \"{self.latest_api}\" \\",
                      "    | jq -r '.tag_name');",
                      "fi"]
        if p.source_build:
            lines.append(f"curl -o {target} -L \"{self.archive or 'TODO: the source archive URL'}\"")
        elif asset and asset.url_template:
            lines.append(f"curl -o {target} -L \"{asset.url_template}\"")
        elif asset and self.source_type == "github_release":
            lines += [f"ASSET_URL=$(curl -sX GET \"https://api.github.com/repos/{self.slug}/releases/tags/${{{self.arg}}}\" \\",
                      f"  | jq -r '.assets[] | select(.name | test(\"{asset.regex}\")) | .browser_download_url' | head -n1)",
                      f"curl -o {target} -L \"${{ASSET_URL}}\""]
        else:
            lines.append(f"curl -o {target} -L \"TODO: the {asset.arch if asset else ''} asset URL\"")
        return lines

    def install_lines(self, asset: Asset | None) -> tuple[list[str], str, list[str]]:
        """(shell lines, the command that starts the app, extra apt/apk packages) for one architecture."""
        p, name = self.proposal, self.name
        app_dir = f"/opt/{name}" if p.selkies else f"/app/{name}"
        if p.source_build:
            lines = self.fetch_lines(asset, f"/tmp/{name}.tar.gz") + [
                f"mkdir -p {app_dir}",
                f"tar xf /tmp/{name}.tar.gz -C {app_dir} --strip-components=1",
                f"echo 'TODO: build {self.title} from {app_dir} as its README says, installing the toolchain in a build stage' && false"]
            self.todo_once("Dockerfiles: building from the source release is not generated; write the build "
                           "(ideally a multi-stage build on the same base) where the TODO stops the build")
            return lines, self.guess_command(f"{app_dir}/{name}"), []
        kind = asset.kind if asset else "other"
        suffix = {"deb": "deb", "appimage": "AppImage", "zip": "zip", "rpm": "rpm", "binary": "bin"}.get(kind, "tar")
        source_name = (asset.name or asset.given).lower() if asset else ""
        flag = ""
        if kind == "tar":
            for ext, f in ((".tar.gz", "z"), (".tgz", "z"), (".tar.xz", "J"), (".txz", "J"), (".tar.bz2", "j")):
                if source_name.endswith(ext):
                    suffix, flag = ext.lstrip("."), f
            if source_name.endswith(".tar.zst"):
                suffix, flag = "tar.zst", "--zstd "
        fetch = self.fetch_lines(asset, f"/tmp/{name}.{suffix}")
        if kind == "deb":
            return fetch, self.guess_command(f"/usr/bin/{name}"), [f"/tmp/{name}.deb"]
        if kind == "appimage":
            lines = fetch + [f"chmod +x /tmp/{name}.AppImage",
                             f"cd /tmp && ./{name}.AppImage --appimage-extract >/dev/null",
                             f"mv /tmp/squashfs-root {app_dir}",
                             f"chmod -R a+rX {app_dir}"]
            return lines, self.guess_command(f"{app_dir}/AppRun"), []
        # An archive with one top-level directory is unwrapped into app_dir; a flat one is copied as it is.
        unwrap = (f"top=$(ls -A /tmp/unpack) && if [ \"$(ls -A /tmp/unpack | wc -l)\" -eq 1 ] && [ -d \"/tmp/unpack/${{top}}\" ]; "
                  f"then cp -a \"/tmp/unpack/${{top}}/.\" {app_dir}/; else cp -a /tmp/unpack/. {app_dir}/; fi")
        if kind == "tar":
            if flag.startswith("--"):
                tar = f"tar xf /tmp/{name}.{suffix} {flag}-C /tmp/unpack"
            else:
                tar = f"tar x{flag}f /tmp/{name}.{suffix} -C /tmp/unpack"
            lines = fetch + [f"mkdir -p /tmp/unpack {app_dir}", tar, unwrap, self.single_binary(app_dir)]
            return lines, self.guess_command(f"{app_dir}/{name}"), ["zstd"] if flag.startswith("--") else []
        if kind == "zip":
            lines = fetch + [f"mkdir -p /tmp/unpack {app_dir}", f"unzip -q /tmp/{name}.zip -d /tmp/unpack", unwrap,
                             self.single_binary(app_dir)]
            return lines, self.guess_command(f"{app_dir}/{name}"), ["unzip"]
        if kind == "binary":
            lines = fetch + [f"install -Dm755 /tmp/{name}.bin {app_dir}/{name}"]
            return lines, self.guess_command(f"{app_dir}/{name}"), []
        lines = fetch + [f"echo 'TODO: install the {kind} asset' && false"]
        self.todo_once(f"Dockerfiles: the asset type ({asset.name or asset.given if asset else '?'}) has no install "
                       "recipe; write it where the TODO stops the build")
        return lines, self.guess_command(f"{app_dir}/{name}"), []

    def single_binary(self, app_dir: str) -> str:
        """An archive holding one executable (gotify-linux-amd64) gets it as app_dir/<name>, the guessed command."""
        target = f"{app_dir}/{self.name}"
        return (f"if [ ! -e {target} ] && [ \"$(find {app_dir} -maxdepth 1 -type f -perm -u+x | wc -l)\" -eq 1 ]; "
                f"then ln -s \"$(find {app_dir} -maxdepth 1 -type f -perm -u+x)\" {target}; fi")

    def todo_once(self, text: str) -> None:
        if text not in self.todos:
            self.todos.append(text)

    def guess_command(self, fallback: str) -> str:
        """The proposal's runtime answer often quotes the start command in backticks; else the likely binary."""
        for code in re.findall(r"`([^`\n]+)`", self.proposal.get("runtime")):
            if code.startswith("~") or re.match(r"^(apt|apk|dpkg|curl|wget|tar|docker|npm i|pip install|git)\b", code):
                continue
            first = code.split()[0]
            if re.search(r"\.(deb|rpm|tar|gz|tgz|xz|zip|appimage|json|ya?ml|conf|db)$", first, re.I):
                continue
            if re.match(r"^(\./|/|[a-z][\w.-]*(\s|$))", code):
                self.command_from = "the proposal's runtime answer"
                return code.strip()
        self.command_from = ""
        return fallback

    def dockerfile(self, arch: str) -> str:
        p, name = self.proposal, self.name
        asset = self.assets.get(arch)
        lines, command, packages = self.install_lines(asset)
        self.command = command
        maintainer = self.member or (p.maintainers[0] if p.maintainers else "linuxserver")
        out = ["# syntax=docker/dockerfile:1", "", self.from_line(arch), "", "# set version label", "ARG BUILD_DATE",
               "ARG VERSION", f"ARG {self.arg}",
               'LABEL build_version="Linuxserver.io version:- ${VERSION} Build-date:- ${BUILD_DATE}"',
               f'LABEL maintainer="{maintainer}"', ""]
        if p.selkies:
            out += ["# title", f"ENV TITLE={q(self.title) if ' ' not in self.title else json.dumps(self.title)} \\",
                    "    NO_GAMEPAD=true \\", "    PIXELFLUX_WAYLAND=true", ""]
        if p.get("database") == DB_FALLBACK:
            self.todo_once("Dockerfiles and root/: the proposal asks for a server database baked in as a fallback; "
                           "install it and start it from its own init and service (not generated)")
        steps: list[str] = []
        if self.base in ("selkies", "ubuntu"):
            apt = [pkg for pkg in packages if not pkg.startswith("/tmp/")]
            debs = [pkg for pkg in packages if pkg.startswith("/tmp/")]
            if apt:  # tools the install needs (unzip), before the download
                steps += ["echo \"**** install packages ****\"", "apt-get update"]
                steps += continued("apt-get install -y --no-install-recommends", apt)
            steps += [f"echo \"**** install {name} ****\""] + lines
            if debs or p.selkies:
                extra = (["libegl1", "xdg-desktop-portal", "xdg-desktop-portal-gtk"] if p.selkies else []) + debs
                steps += ([] if apt else ["apt-get update"]) + continued("apt-get install -y --no-install-recommends", extra)
            cleanup = ["echo \"**** cleanup ****\""] + (["apt-get autoclean"] if apt or debs or p.selkies else []) + [
                "rm -rf \\", "  /config/.cache \\", "  /var/lib/apt/lists/* \\", "  /var/tmp/* \\", "  /tmp/*"]
        else:
            if packages:
                steps += ["echo \"**** install packages ****\""] + continued("apk add --no-cache", packages)
            steps += [f"echo \"**** install {name} ****\""] + lines
            cleanup = ["echo \"**** cleanup ****\"", "rm -rf \\", "  /tmp/* \\", "  /var/tmp/*"]
        steps += cleanup
        out += ["RUN \\"] + chain(steps) + [""]
        out += ["# add local files", "COPY root/ /", "", "# ports and volumes",
                f"EXPOSE {3001 if p.selkies else p.web_port or 80}", "", "VOLUME /config", ""]
        return "\n".join(out)

    # ---------------------------------------------------------------- root/

    def root_files(self) -> None:
        p, name = self.proposal, self.name
        if p.selkies:
            command = self.command
            self.files["root/defaults/autostart"] = command + "\n"
            self.files["root/defaults/autostart_wayland"] = command + "\n"
            item = (f'<item label="{self.title}"><action name="Execute"><command>{command}</command></action></item>')
            for file, term, icon in (("menu.xml", "xterm", "/usr/share/pixmaps/xterm-color_48x48.xpm"),
                                     ("menu_wayland.xml", "foot", "/usr/share/icons/hicolor/48x48/apps/foot.png")):
                self.files[f"root/defaults/{file}"] = "\n".join([
                    '<?xml version="1.0" encoding="utf-8"?>',
                    '<openbox_menu xmlns="http://openbox.org/3.4/menu">',
                    '<menu id="root-menu" label="MENU">',
                    f'<item label="{term}" icon="{icon}"><action name="Execute"><command>/usr/bin/{term}</command></action></item>',
                    item, "</menu>", "</openbox_menu>", ""])
            if not self.command_from:
                self.todo_once(f"root/defaults/autostart: the start command {command!r} is a guess; check it in the "
                               "running container")
            return
        s6 = "root/etc/s6-overlay/s6-rc.d"
        state = p.get("state_paths").replace("\n", " ")
        init = [
            "#!/usr/bin/with-contenv bash", "# shellcheck shell=bash", "",
            f"# {self.title} keeps its state in /config. From the proposal, it writes state to: {state[:300]}",
            "# TODO: point the application at /config (a flag, an environment variable or a symlink) if it does not",
            "# already write there.", "",
            f"mkdir -p /config/{name}", "",
            "if [[ -z ${LSIO_NON_ROOT_USER} ]]; then",
            "    lsiown -R abc:abc /config",
            "fi", ""]
        self.files[f"{s6}/init-{name}-config/run"] = "\n".join(init)
        self.executable.add(f"{s6}/init-{name}-config/run")
        self.files[f"{s6}/init-{name}-config/type"] = "oneshot\n"
        self.files[f"{s6}/init-{name}-config/up"] = f"/etc/s6-overlay/s6-rc.d/init-{name}-config/run\n"
        self.files[f"{s6}/init-{name}-config/dependencies.d/init-config"] = ""
        self.files[f"{s6}/init-config-end/dependencies.d/init-{name}-config"] = ""
        workdir = f"/app/{name}"
        command = self.command
        note = ("# The start command comes from the proposal's runtime answer: check its flags."
                if self.command_from else
                "# TODO: the start command is a guess from the asset; set the real one, with its data directory under\n"
                "# /config and its port, as the proposal's runtime answer describes.")
        if not self.command_from:
            self.todo_once(f"root/: the start command {command!r} in svc-{name}/run is a guess; set the real one")
        run = ["#!/usr/bin/with-contenv bash", "# shellcheck shell=bash", "", note, "",
               "# Whatever the application writes to its home directory lands in /config too.",
               "export HOME=/config", "",
               "if [[ -z ${LSIO_NON_ROOT_USER} ]]; then",
               "    exec \\", "        s6-notifyoncheck -d -n 300 -w 1000 \\",
               f"            cd {workdir} s6-setuidgid abc {command}",
               "else",
               "    exec \\", "        s6-notifyoncheck -d -n 300 -w 1000 \\",
               f"            cd {workdir} {command}",
               "fi", ""]
        self.files[f"{s6}/svc-{name}/run"] = "\n".join(run)
        self.executable.add(f"{s6}/svc-{name}/run")
        check = ["#!/bin/bash", "", f"# Ready when the web interface answers on port {p.web_port or 80}.",
                 f"curl -so /dev/null \"http://localhost:{p.web_port or 80}/\"", ""]
        self.files[f"{s6}/svc-{name}/data/check"] = "\n".join(check)
        self.executable.add(f"{s6}/svc-{name}/data/check")
        self.files[f"{s6}/svc-{name}/notification-fd"] = "3\n"
        self.files[f"{s6}/svc-{name}/type"] = "longrun\n"
        self.files[f"{s6}/svc-{name}/dependencies.d/init-services"] = ""
        self.files[f"{s6}/user/contents.d/init-{name}-config"] = ""
        self.files[f"{s6}/user/contents.d/svc-{name}"] = ""

    # ---------------------------------------------------------------- all of it

    def build(self) -> None:
        self.files["image.yml"] = self.image_yml()
        self.files["Dockerfile"] = self.dockerfile("amd64")
        if "arm64" in self.platforms:
            self.files["Dockerfile.aarch64"] = self.dockerfile("arm64")
        self.root_files()

    def from_working(self, working: Path, url: str) -> None:
        """The developer's own repository (made from docker-template) instead of a generated image: its image.yml,
        Dockerfiles and root/, with maintainers taken from the form. Symlinks are left out."""
        self.todos = []  # the generated image's guesses do not apply
        for rel in ("image.yml", "Dockerfile", "Dockerfile.aarch64"):
            path = working / rel
            if path.is_file() and not path.is_symlink():
                self.files[rel] = path.read_text(encoding="utf-8")
        if "image.yml" not in self.files or "Dockerfile" not in self.files:
            raise ProposalError(f"the working repository {url} has no image.yml or Dockerfile at its root")
        skipped = []
        root = working / "root"
        for path in sorted(root.rglob("*")) if root.is_dir() else []:
            rel = path.relative_to(working).as_posix()
            if path.is_symlink():
                skipped.append(rel)
            elif path.is_file() and rel != "root/donate.txt":
                data = path.read_bytes()
                try:
                    self.files[rel] = data.decode("utf-8")
                except UnicodeDecodeError:
                    self.files[rel] = data  # type: ignore[assignment]
                if path.stat().st_mode & stat.S_IXUSR:
                    self.executable.add(rel)
        image = self.files["image.yml"]
        maintainers = self.proposal.maintainers or [self.proposal.author]
        block_text = "maintainers:\n" + "".join(f"- {m}\n" for m in maintainers)
        if re.search(r"^maintainers:", image, re.M):
            image = re.sub(r"^maintainers:[^\n]*\n(?:[ \t]*-[^\n]*\n)*", block_text, image, count=1, flags=re.M)
        else:
            image = re.sub(r"^(name:[^\n]*\n)", lambda m: m.group(1) + "\n" + block_text, image, count=1, flags=re.M)
        self.files["image.yml"] = image
        named = re.search(r"^name:\s*['\"]?([\w-]+)", image, re.M)
        if not named or named.group(1) != self.name:
            self.todos.append(f"image.yml in the working repository names the image {named.group(1) if named else '(nothing)'!r}, "
                              f"the proposal {self.name!r}: they must agree")
        # What try and accept need, read from the developer's image.yml.
        base = re.search(r"^  base:\s*([\w-]+)", image, re.M)
        self.base = base.group(1) if base else "other"
        self.base_reason = "from the working repository"
        plat = re.search(r"^  platforms:\s*\n((?:\s*-\s*\w+\s*\n)+)", image, re.M)
        self.platforms = re.findall(r"-\s*(\w+)", plat.group(1)) if plat else ["amd64"]
        self.proposal.answers["app_type"] = SELKIES if self.base == "selkies" else self.proposal.answers.get("app_type", WEB)
        autostart = self.files.get("root/defaults/autostart")
        self.command = autostart.strip().splitlines()[0] if isinstance(autostart, str) and autostart.strip() else ""
        self.command_from = "the working repository"
        self.todos.append(f"the image comes from the working repository {url}: review its Dockerfiles and root/ as "
                          "you would any pull request; nothing in them was generated")
        if skipped:
            self.todos.append("symlinks under root/ were left out: " + ", ".join(skipped))
        if re.search(r"\bTODO\b", "".join(v for v in self.files.values() if isinstance(v, str))):
            self.todos.append("the working repository still has TODO markers (grep TODO)")

    def write(self, out: Path) -> None:
        for rel, text in self.files.items():
            path = out / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(text, bytes):
                path.write_bytes(text)
            else:
                path.write_text(text, encoding="utf-8")
            if rel in self.executable:
                path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def chain(steps: list[str]) -> list[str]:
    """Join shell lines into the body of one RUN. A line ending in a backslash continues the command it starts; an
    if block's lines end in a backslash only; everything else ends in '&& \\' except the last."""
    out = []
    inside = False
    for i, step in enumerate(steps):
        last = i == len(steps) - 1
        if step.endswith("\\"):
            suffix = ""
        elif step.startswith("if ") and not step.endswith("fi"):
            inside, suffix = True, " \\"
        elif inside and step == "fi":
            inside, suffix = False, "" if last else " && \\"
        elif inside:
            suffix = " \\"
        else:
            suffix = "" if last else " && \\"
        out.append(f"  {step}{suffix}")
    return out


def continued(command: str, items: list[str]) -> list[str]:
    """A command with one item per line: 'apt-get install -y \\', '  a \\', '  b'."""
    return [f"{command} \\"] + [f"  {item}" + (" \\" if i < len(items) - 1 else "") for i, item in enumerate(items)]


# ------------------------------------------------------------------------------------------------ accept


def accept_files(meta: dict, member: str) -> dict[str, str]:
    name = meta["name"]
    repo = f"{LABS_ORG}/docker-{name}"
    number = meta["number"]
    issue_url = meta["url"] or f"https://github.com/{PROPOSALS}/issues/{number}"
    credit = meta["author"]
    title = f"Add the {name} image"
    todos = meta.get("todos", [])
    try_result = meta.get("try_result", "")
    pr_body = "\n".join([
        f"Adds {meta['title']} to LinuxServer Labs, built from the proposal {PROPOSALS}#{number} "
        f"by @{credit}, who is credited in `maintainers`." if credit else
        f"Adds {meta['title']} to LinuxServer Labs, built from the proposal {PROPOSALS}#{number}.",
        "",
        f"Closes {PROPOSALS}#{number}",
        "",
        "## What is here",
        "",
        f"- `image.yml`: {meta['source_type'] or 'a hand-written version source'} on `{meta['slug']}` with "
        f"`require_assets`, `{meta['base']}` base, {', '.join(meta['platforms'])}, maintainers "
        f"{', '.join('@' + m for m in meta['maintainers'])}.",
        "- `Dockerfile`" + (" and `Dockerfile.aarch64`" if "arm64" in meta["platforms"] else "") +
        f" on the playground's `baseimage-{meta['base']}`.",
        "- `root/`: " + ("the selkies autostart and menus." if meta["selkies"] else "the init and service for s6."),
        "",
        "The README, AGENTS.md and LICENSE are generated by the live build after merge, and `build.yml` and "
        "`pr-report.yml` are already on `main`, so this pull request carries no generated file.",
        "",
        "## Trial",
        "",
        try_result or "TODO: the result of `./harness labs try " + str(number) + "` (what came up, what was clicked).",
        "",
        "## Still to check",
        "",
        *([f"- [ ] {t}" for t in todos] or ["- nothing the scaffold flagged"]),
        "",
        f"After merge: remove `labs-pending` and dispatch the first build (`.harness/labs/{name}/after-merge.sh`).",
        "",
        "AI use: TODO (tool and model, and what it did; the scaffold came from `./harness labs accept`).",
        "",
    ])
    rel = f".harness/labs/{name}"
    accept = f"""#!/usr/bin/env bash
# Generated by ./harness labs accept {number} for {member or 'a member'} on {datetime.date.today().isoformat()}.
# Elevates {PROPOSALS}#{number} to {repo}. Read every line before running it:
# it creates a public repository, pushes, opens a pull request and comments on the proposal.
# Run it yourself: bash {rel}/accept.sh
set -euo pipefail
cd "$(dirname "$0")/../../.."  # the harness root

repo={repo}
scaffold={rel}
issue={number}
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

# 1. The "Image pending approval" main: docker-template's `pending` branch (the README with its Proposal: line and
#    the generated pr-report.yml, no image.yml), with the proposal linked and the generated build.yml added, so
#    the first pull request touches no generated file (its build fails one that does) and still has a workflow to
#    run. [skip ci]: main has no image.yml to build, and control lists the repo as a helper until the merge.
git clone --quiet --branch pending --single-branch "https://github.com/{TEMPLATE}.git" "$work/repo" ||
  {{ echo "{TEMPLATE} has no pending branch" >&2; exit 1; }}
if grep -q '^Proposal: ' "$work/repo/README.md"; then
  sed -i 's|^Proposal: .*|Proposal: {issue_url}|' "$work/repo/README.md"
else
  printf '\\nProposal: %s\\n' {shlex.quote(issue_url)} >>"$work/repo/README.md"
fi
mkdir -p "$work/repo/.github/workflows"
cp "$scaffold/.github/workflows/build.yml" "$work/repo/.github/workflows/build.yml"
if ! cmp -s "$scaffold/.github/workflows/pr-report.yml" "$work/repo/.github/workflows/pr-report.yml"; then
  cp "$scaffold/.github/workflows/pr-report.yml" "$work/repo/.github/workflows/pr-report.yml"
fi
git -C "$work/repo" add -A
git -C "$work/repo" commit --quiet -m "Link the proposal and add the build workflow [skip ci]"

# 2. The repository, created empty (not from the template, whose main is the developer's starter kit), and that
#    main as its first push.
gh repo create "$repo" --public --description {shlex.quote(meta['description'])}
git -C "$work/repo" remote set-url origin "https://github.com/$repo.git"
git -C "$work/repo" push --quiet origin HEAD:main

# 3. Its Pages site (control cannot change repository settings), deployed from Actions with no branch rule.
gh api -X POST "repos/$repo/pages" -f build_type=workflow
gh api -X PUT "repos/$repo/environments/github-pages" --input - <<<'{{"deployment_branch_policy":null}}'

# 4. Pending approval on the Labs site until the first pull request merges.
gh repo edit "$repo" --add-topic labs-pending

# 5. The image on a branch, and its pull request. Generated files stay out: the live build renders them after merge.
git -C "$work/repo" switch --quiet -c initial
# image.yml, the Dockerfiles and root/ as they stand in the scaffold, with your edits.
(cd "$scaffold" && find image.yml Dockerfile Dockerfile.aarch64 root -type f ! -path root/donate.txt 2>/dev/null || true) >"$work/files"
while read -r file; do
  mkdir -p "$work/repo/$(dirname "$file")"
  cp -p "$scaffold/$file" "$work/repo/$file"
done <"$work/files"
git -C "$work/repo" add -A
git -C "$work/repo" commit --quiet -m {shlex.quote(title)}
git -C "$work/repo" push --quiet -u origin initial
pr=$(gh pr create -R "$repo" --base main --head initial --title {shlex.quote(title)} --body-file "$scaffold/.proposal/pr-body.md")
echo "$pr"

# 6. The proposal: accepted, with a link to the pull request.
gh issue edit "$issue" -R {PROPOSALS} --add-label accepted
gh issue comment "$issue" -R {PROPOSALS} --body "Accepted: {repo} is created and its first pull request holds the image: $pr. Its build posts a report comment there with the tests, screenshots and a pull command. Follow it, and send changes as pull requests from a fork."

echo "done: https://github.com/$repo. After the pull request merges, run: bash $scaffold/after-merge.sh"
"""
    after = f"""#!/usr/bin/env bash
# Generated by ./harness labs accept {number}. Run it after the first pull request of {repo} has merged.
set -euo pipefail
repo={repo}

# The image is live: off the Labs site's pending list.
gh repo edit "$repo" --remove-topic labs-pending

# A brand-new repository runs a workflow for only one of its first pushes: dispatch the first live build
# unless the merge started one.
if [[ -z "$(gh run list -R "$repo" --branch main --workflow build.yml --limit 1 --json databaseId --jq '.[].databaseId')" ]]; then
  gh workflow run build.yml -R "$repo" --ref main -f reason=manual
fi
gh run list -R "$repo" --limit 3
echo "Labs control discovers the image within 30 minutes; the Labs hub and site follow its first release."
"""
    return {"accept.sh": accept, "after-merge.sh": after, ".proposal/pr-body.md": pr_body}


# ------------------------------------------------------------------------------------------------ form


def form_link(draft: str, repo: str) -> tuple[str, str, dict[str, str]]:
    """(prefilled form URL, clean body, answers) for a filled draft. GitHub prefills an issue form's inputs,
    textareas and dropdowns from query parameters named by field id; the bar's checkboxes are the person's to tick."""
    answers = parse_body(draft)
    name = strip_code(answers.get("name", "")).lower()
    params = {"template": "proposal.yml", "title": f"Proposal: {name}"}
    for key, value in answers.items():
        if key in LABELS.values() and key != "bar" and value and "TODO" not in value:
            params[key] = value
    url = f"https://github.com/{repo}/issues/new?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    clean = re.sub(r"[ \t]*<!--.*?-->", "", draft, flags=re.S)
    clean = re.sub(r"\n{3,}", "\n\n", clean).strip() + "\n"
    return url, clean, answers


# ------------------------------------------------------------------------------------------------ main


def read_json(path: str) -> dict:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8")) if path else {}
    except (OSError, ValueError) as error:
        raise ProposalError(f"cannot read {path}: {error}") from error


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_parse = sub.add_parser("parse")
    p_parse.add_argument("--issue", required=True)
    p_scaffold = sub.add_parser("scaffold")
    p_scaffold.add_argument("--issue", required=True)
    p_scaffold.add_argument("--repo", default="")
    p_scaffold.add_argument("--release", default="")
    p_scaffold.add_argument("--out", required=True)
    p_scaffold.add_argument("--member", default="")
    p_scaffold.add_argument("--working", default="", help="a checkout of the proposal's working repository")
    p_scaffold.add_argument("--date", default=datetime.date.today().isoformat())
    p_accept = sub.add_parser("accept")
    p_accept.add_argument("--dir", required=True)
    p_accept.add_argument("--member", default="")
    p_form = sub.add_parser("form")
    p_form.add_argument("--draft", required=True)
    p_form.add_argument("--repo", default=PROPOSALS)
    p_form.add_argument("--body", required=True)
    args = parser.parse_args(argv)
    try:
        if args.cmd == "parse":
            proposal = load_proposal(read_json(args.issue))
            print(json.dumps({"name": proposal.name, "answers": proposal.answers, "problems": proposal.problems,
                              "maintainers": proposal.maintainers, "env": [e.__dict__ for e in proposal.env_vars]},
                             indent=2))
            return 0
        if args.cmd == "scaffold":
            proposal = load_proposal(read_json(args.issue))
            if not proposal.name or not NAME.match(proposal.name):
                raise ProposalError(f"no usable image name in the proposal ({proposal.name!r})")
            scaffold = Scaffold(proposal, read_json(args.repo), read_json(args.release), args.member, args.date)
            if args.working:
                scaffold.command = ""
                scaffold.from_working(Path(args.working), proposal.get("working_repo"))
            else:
                scaffold.build()
            out = Path(args.out)
            scaffold.write(out)
            meta = {
                "number": proposal.number, "url": proposal.url, "author": proposal.author, "name": proposal.name,
                "title": scaffold.title, "slug": scaffold.slug, "source_type": scaffold.source_type,
                "base": scaffold.base, "base_reason": scaffold.base_reason, "platforms": scaffold.platforms, "maintainers": proposal.maintainers,
                "selkies": proposal.selkies, "web_port": proposal.web_port, "command": scaffold.command,
                "first_run": proposal.get("first_run"), "screenshot": proposal.get("screenshot"),
                "description": (scaffold.repo.get("description") or f"{scaffold.title} for LinuxServer Labs")[:300],
                "tag": scaffold.tag, "todos": scaffold.todos, "problems": proposal.problems,
                "files": sorted(scaffold.files),
                "assets": {a: {"name": x.name, "given": x.given, "regex": x.regex, "url": x.url_template, "kind": x.kind}
                           for a, x in scaffold.assets.items()},
            }
            (out / ".proposal").mkdir(parents=True, exist_ok=True)
            (out / ".proposal" / "scaffold.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(meta, indent=2))
            return 0
        if args.cmd == "form":
            url, clean, answers = form_link(Path(args.draft).read_text(encoding="utf-8"), args.repo)
            Path(args.body).write_text(clean, encoding="utf-8")
            todo = [label_of(k) for k, v in answers.items() if "TODO" in v]
            name = strip_code(answers.get("name", "")).lower()
            if todo:
                print("still TODO (left out of the link): " + ", ".join(todo), file=sys.stderr)
            print("File it with the web form, prefilled from the draft (the person reads it, ticks the bar and submits;")
            print("the form labels it 'proposal'):")
            print(f"  {url}")
            if len(url) > 8000:
                print("  (the link is long; if the browser cuts it, shorten the long answers or use the command below)")
            print("Without a browser, the same fields as a plain issue (the check reads it alike, but only the form adds")
            print("the 'proposal' label, so a member may have to add it):")
            print(f"  gh issue create -R {args.repo} --title \"Proposal: {name}\" --body-file {args.body}")
            return 0
        if args.cmd == "accept":
            out = Path(args.dir)
            meta = read_json(str(out / ".proposal" / "scaffold.json"))
            try_file = out / ".proposal" / "try.md"
            if try_file.is_file():
                meta["try_result"] = try_file.read_text(encoding="utf-8").strip()
            for rel, text in accept_files(meta, args.member).items():
                path = out / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")
                if rel.endswith(".sh"):
                    path.chmod(0o755)
            return 0
    except ProposalError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    sys.exit(main())

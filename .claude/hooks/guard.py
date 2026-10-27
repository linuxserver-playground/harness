#!/usr/bin/env python3
"""PreToolUse guard for Bash: steer each role to the right path before GitHub refuses, or before a member
does what the team does by pull request.

Reads the hook input on stdin. Exit 2 with a reason on stderr blocks the command and tells the agent why and
what to do instead; exit 0 lets it through (to the normal permission prompt). It is a steer, not security:
GitHub's permissions are the enforcement. Anything it cannot parse is let through.

Rules (guides/rules.md explains them):
- everyone: no writes to the real linuxserver org; no printing tokens; no new secrets through the agent;
  no --mirror or --all pushes.
- contributors: no pushes to linuxserver-playground remotes (fork first), no workflow runs, reruns, labels,
  releases, repo creation in the org or deletions.
- members: pushes to an existing repo's default or live branch, force pushes there, tag moves, repo and
  package deletion need `./harness allow <action> <repo>` first (the person approves that command), because
  changes to existing repos go up as a pull request. A first push to a brand-new repo is free.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])
STATE = ROOT / ".harness"
SEPARATORS = {"&&", "||", ";", "|", "&", "\n"}
GITHUB = re.compile(r"github\.com[:/]([^/\s]+)/([^/\s]+?)(?:\.git)?/?$")


def block(message: str) -> None:
    print(message, file=sys.stderr)
    sys.exit(2)


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


PROFILE = load_json(STATE / "profile.json")
ROLE = PROFILE.get("role", "unknown")
ORG = PROFILE.get("org") or os.environ.get("HARNESS_ORG") or "linuxserver-playground"
MEMBER = ROLE == "member"


def allowed(action: str, repo: str) -> bool:
    grants = load_json(STATE / "allow.json")
    return grants.get(f"{action} {repo}", 0) > time.time()


def git(cwd: str, *args: str) -> str:
    try:
        out = subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return out.stdout.strip() if out.returncode == 0 else ""


def segments(command: str) -> list[list[str]]:
    lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|")
    lexer.whitespace_split = True
    lexer.commenters = ""
    try:
        tokens = list(lexer)
    except ValueError:
        return []
    out: list[list[str]] = [[]]
    for token in tokens:
        if token in SEPARATORS or set(token) <= set(";&|"):
            out.append([])
        else:
            out[-1].append(token)
    return [s for s in out if s]


def strip_env(seg: list[str]) -> list[str]:
    while seg and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", seg[0]):
        seg = seg[1:]
    return seg


def live_branch(cwd: str, ref: str) -> str:
    text = git(cwd, "show", f"{ref}:image.yml")
    match = re.search(r"^release:\n(?:(?:  .*|\s*)\n)*?  branch:\s*['\"]?([^'\"\s]+)", text, re.M)
    return match.group(1) if match else ""


def check_push(cwd: str, args: list[str]) -> None:
    flags = [a for a in args if a.startswith("-")]
    positional = [a for a in args if not a.startswith("-")]
    if any(f in ("--mirror", "--all") for f in flags):
        block("Pushing every ref (--mirror/--all) is never done from the harness. Push the one branch you mean.")
    force = any(f in ("-f", "--force") or f.startswith("--force-with-lease") or f.startswith("--force-if") for f in flags)
    delete = any(f in ("-d", "--delete") for f in flags)
    current = git(cwd, "branch", "--show-current")
    remote = positional[0] if positional else (git(cwd, "config", f"branch.{current}.remote") or "origin")
    url = remote if "/" in remote and ("github.com" in remote) else git(cwd, "remote", "get-url", remote)
    match = GITHUB.search(url or "")
    if not match:
        return
    owner, repo = match.group(1), match.group(2)
    if owner == "linuxserver":
        block("The real linuxserver org is read-only from here: no pushes, PRs, issues or comments there.")
    if owner != ORG:
        return  # your fork, or another org: GitHub decides
    if not MEMBER:
        block(
            f"You are on the contributor path, so you cannot push to {ORG}/{repo}. Fork it first "
            f"(./harness fork {repo}), push your branch to origin (your fork), then draft the pull request with "
            f"./harness draft pr {repo}. If you were just added to the org, run ./harness whoami --refresh."
        )
    refspecs = positional[1:] or ([current] if current else [])
    if "--tags" in flags:
        if not allowed("tag", repo):
            block(f"Pushing tags to {ORG}/{repo} needs the person's go-ahead: ./harness allow tag {repo}.")
        return
    remote_head = git(cwd, "symbolic-ref", "--short", f"refs/remotes/{remote}/HEAD").split("/", 1)[-1]
    for spec in refspecs:
        spec_force = force or spec.startswith("+")
        spec = spec.lstrip("+")
        src, _, dst = spec.partition(":")
        dst = dst or src
        if dst.startswith("refs/tags/") or git(cwd, "show-ref", "--verify", f"refs/tags/{dst.removeprefix('refs/tags/')}"):
            tag = dst.removeprefix("refs/tags/")
            if spec_force and not allowed("tag", repo):
                block(
                    f"Moving the tag {tag} on {ORG}/{repo} is a release step (release-workflows in guides/playbooks/fleet-ops.md). "
                    f"The person approves it with ./harness allow tag {repo}, then the push goes through."
                )
            continue
        dst = dst.removeprefix("refs/heads/")
        protected = {b for b in (remote_head, live_branch(cwd, src or "HEAD")) if b}
        if dst not in protected:
            continue
        exists = git(cwd, "ls-remote", "--heads", remote, dst)
        if not exists and not delete:
            continue  # the first push of a brand-new repo's default branch
        action = "force-push" if (spec_force or delete) else "push"
        if not allowed(action, repo):
            block(
                f"{dst} is {'the default' if dst == remote_head else 'a live'} branch of {ORG}/{repo}. Changes to an "
                f"existing repo go up as a pull request: push a topic branch (git push -u {remote} <topic>) and run "
                f"./harness draft pr {repo}. If a playbook step really needs this push (a new repo's scaffold, "
                f"release-workflows), the person approves it with ./harness allow {action} {repo}."
            )


def repo_arg(seg: list[str]) -> str:
    for i, token in enumerate(seg):
        if token in ("-R", "--repo") and i + 1 < len(seg):
            return seg[i + 1]
        if token.startswith("--repo="):
            return token.split("=", 1)[1]
    return ""


def check_gh(command: str, seg: list[str]) -> None:
    sub = seg[1:3]
    target = repo_arg(seg)
    words = " ".join(seg)
    writes = {
        ("pr", "create"), ("pr", "comment"), ("pr", "review"), ("pr", "merge"), ("pr", "edit"), ("pr", "close"),
        ("issue", "create"), ("issue", "comment"), ("issue", "edit"), ("issue", "close"), ("repo", "fork"),
    }
    if target.startswith("linuxserver/") or (tuple(sub) in writes and re.search(r"(^|\s|/)linuxserver/", words)):
        if tuple(sub) in writes or sub[:1] == ["api"]:
            block("The real linuxserver org is read-only from here: no pushes, PRs, issues or comments there.")
    if sub == ["auth", "token"] and "$(gh auth token)" not in command and "`gh auth token`" not in command:
        block("Do not print tokens. Pass it inline where a tool needs it: GITHUB_TOKEN=$(gh auth token) <command>.")
    if sub[:2] == ["auth", "status"] and any(a in ("-t", "--show-token") for a in seg):
        block("Do not print tokens; plain gh auth status shows the scopes.")
    if sub[:1] in (["secret"], ["variable"]) and len(sub) > 1 and sub[1] in ("set", "delete", "remove"):
        block("Secrets and variables are set by a maintainer in GitHub's settings, never through the agent. "
              "Write the code so it degrades without the secret and ask for it in the PR.")
    api_delete = sub[:1] == ["api"] and re.search(r"(-X|--method)[ =]?(DELETE)", words)
    if sub == ["repo", "delete"] or api_delete:
        path = target or next((t for t in seg[2:] if "/" in t and not t.startswith("-")), "")
        name = path.split("/")[-1]
        if "/packages/container/" in path:
            # build%2Fsonarr, untrusted-pr%2Fsonarr, sonarr: all belong to docker-sonarr
            name = "docker-" + unquote(name).split("/")[-1]
        if not MEMBER:
            block("Deleting repos or packages is for members only, through the remove-image steps in guides/playbooks/fleet-ops.md.")
        if not allowed("delete", name or "*"):
            block(f"Deletion is the last of the remove-image steps (guides/playbooks/fleet-ops.md). The person approves it with "
                  f"./harness allow delete {name or '<repo>'} after checking nothing depends on it.")
    if MEMBER:
        return
    member_only = {
        ("workflow", "run"), ("workflow", "enable"), ("workflow", "disable"), ("run", "rerun"),
        ("run", "cancel"), ("run", "delete"), ("label", "create"), ("label", "edit"), ("label", "delete"),
        ("release", "create"), ("release", "edit"), ("release", "delete"), ("cache", "delete"),
    }
    if tuple(sub) in member_only:
        block(f"'gh {' '.join(sub)}' needs write access to {ORG}, which members have. On the contributor path, "
              "ask for it in your pull request or issue; a maintainer will run it.")
    if sub == ["repo", "create"]:
        name = next((t for t in seg[3:] if not t.startswith("-")), "")
        if name.startswith(f"{ORG}/") or "--org" in seg:
            block(f"Contributors cannot create repos in {ORG}. New images start as a proposal "
                  "(guides/playbooks/propose-image.md); a scaffold, if you want one, goes in your own account.")


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return
    if data.get("tool_name") != "Bash":
        return
    command = (data.get("tool_input") or {}).get("command", "")
    cwd = data.get("cwd") or os.getcwd()
    if not command:
        return
    for seg in segments(command):
        seg = strip_env(seg)
        if not seg:
            continue
        if seg[0] == "cd" and len(seg) > 1:
            cwd = os.path.normpath(os.path.join(cwd, os.path.expanduser(seg[1])))
            continue
        if seg[0] == "git":
            args = seg[1:]
            here = cwd
            while args and args[0].startswith("-"):
                if args[0] == "-C" and len(args) > 1:
                    here = os.path.normpath(os.path.join(here, os.path.expanduser(args[1])))
                    args = args[2:]
                elif args[0] == "-c" and len(args) > 1:
                    args = args[2:]
                else:
                    args = args[1:]
            if args and args[0] == "push":
                check_push(here, args[1:])
        elif seg[0] == "gh" and len(seg) > 1:
            check_gh(command, seg)


if __name__ == "__main__":
    main()

"""Tests for scripts/labs.py: python3 -m unittest discover -s tests (from the harness root)."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(ROOT / "scripts"))

import labs  # noqa: E402


def fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def scaffold(prefix: str) -> labs.Scaffold:
    issue = fixture(f"{prefix}-issue.json")
    built = labs.Scaffold(labs.load_proposal(issue), fixture(f"{prefix}-repo.json"), fixture(f"{prefix}-release.json"),
                          "member", "2026-11-02")
    built.build()
    return built


class ParseTest(unittest.TestCase):
    def test_reads_every_field_by_its_label(self) -> None:
        proposal = labs.load_proposal(fixture("photocraft-issue.json"))
        self.assertEqual(proposal.name, "photocraft")
        self.assertEqual(proposal.upstream, ("github.com", "storytold", "photocraft"))
        self.assertTrue(proposal.selkies)
        self.assertEqual(proposal.answers["web_port"], "")  # _No response_
        self.assertEqual(proposal.maintainers, ["thelamer"])
        self.assertEqual(proposal.problems, [])

    def test_flags_what_the_form_left_out(self) -> None:
        proposal = labs.load_proposal(fixture("notely-issue.json"))
        self.assertEqual(proposal.maintainers, ["notely-dev", "someone"])
        self.assertEqual(proposal.web_port, 8080)
        self.assertTrue(any("paid vendor" in p for p in proposal.problems), proposal.problems)

    def test_environment_variables_in_the_shapes_people_write(self) -> None:
        envs = labs.load_proposal(fixture("notely-issue.json")).env_vars
        self.assertEqual([(e.name, e.value) for e in envs], [("NOTELY_SECRET", "changeme"), ("NOTELY_BASE_URL", "")])
        self.assertEqual(envs[0].description, "signs session cookies")

    def test_rejects_an_issue_that_is_not_a_proposal(self) -> None:
        with self.assertRaises(labs.ProposalError):
            labs.load_proposal({"body": "It crashes when I click save."})

    def test_html_comments_are_guidance_not_answers(self) -> None:
        answers = labs.parse_body("### Image name\n\nfoo <!-- lowercase -->\n\n### Licence\n\n<!-- SPDX -->\nMIT\n")
        self.assertEqual(answers, {"name": "foo", "license": "MIT"})


class AssetTest(unittest.TestCase):
    release = {"tag_name": "v0.19.0", "assets": [{"name": "photocraft-0.19.0-linux-x86_64.deb"},
                                                 {"name": "photocraft-0.19.0-linux-aarch64.deb"}]}

    def test_a_versioned_name_becomes_a_template_and_a_pattern(self) -> None:
        asset = labs.resolve_asset("amd64", "photocraft-0.19.0-linux-x86_64.deb", self.release, "https://x/download", "A")
        self.assertEqual(asset.url_template, "https://x/download/${A}/photocraft-${A#v}-linux-x86_64.deb")
        self.assertEqual(asset.regex, r"^photocraft\-.*\-linux\-x86_64\.deb$")
        self.assertEqual(asset.kind, "deb")

    def test_a_regex_answer_finds_the_asset(self) -> None:
        asset = labs.resolve_asset("arm64", "photocraft-.*-linux-aarch64.deb", self.release, "https://x/download", "A")
        self.assertEqual(asset.name, "photocraft-0.19.0-linux-aarch64.deb")

    def test_a_name_from_an_older_release_still_matches(self) -> None:
        asset = labs.resolve_asset("amd64", "photocraft-0.18.2-linux-x86_64.deb", self.release, "https://x/download", "A")
        self.assertEqual(asset.name, "photocraft-0.19.0-linux-x86_64.deb")

    def test_a_stable_name_is_used_as_it_is(self) -> None:
        release = {"tag_name": "1.4", "assets": [{"name": "app-linux-amd64"}]}
        asset = labs.resolve_asset("amd64", "app-linux-amd64", release, "https://x/download", "A")
        self.assertEqual(asset.url_template, "https://x/download/${A}/app-linux-amd64")
        self.assertEqual(asset.regex, r"^app\-linux\-amd64$")
        self.assertEqual(asset.kind, "binary")

    def test_an_unknown_asset_is_looked_up_at_build_time(self) -> None:
        asset = labs.resolve_asset("amd64", "nothing-.*\\.zip", self.release, "https://x/download", "A")
        self.assertEqual((asset.name, asset.url_template), ("", ""))


class ScaffoldTest(unittest.TestCase):
    def test_selkies_matches_the_worked_example(self) -> None:
        built = scaffold("photocraft")
        image = built.files["image.yml"]
        self.assertIn("base: selkies", image)
        self.assertIn("version_arg: PHOTOCRAFT_RELEASE", image)
        self.assertIn(r"- asset: '^photocraft\-.*\-linux\-aarch64\.deb$'", image)
        self.assertIn("maintainers:\n- thelamer", image)
        self.assertIn("FROM ghcr.io/linuxserver-playground/baseimage-selkies:ubunturesolute", built.files["Dockerfile"])
        self.assertIn("baseimage-selkies:arm64v8-ubunturesolute", built.files["Dockerfile.aarch64"])
        self.assertIn("/tmp/photocraft.deb", built.files["Dockerfile"])
        # The runtime answer quotes /usr/bin/photocraft: the autostart uses it.
        self.assertEqual(built.files["root/defaults/autostart"], "/usr/bin/photocraft\n")
        self.assertEqual(built.title, "PhotoCraft")

    def test_web_app_gets_an_s6_service_from_the_quoted_start_command(self) -> None:
        built = scaffold("notely")
        self.assertEqual(built.platforms, ["amd64"])
        self.assertNotIn("Dockerfile.aarch64", built.files)
        self.assertEqual(built.base, "ubuntu")  # a prebuilt Go binary: glibc unless it says static
        self.assertTrue(any("baseimage-alpine" in t for t in built.todos), built.todos)
        run = built.files["root/etc/s6-overlay/s6-rc.d/svc-notely/run"]
        self.assertTrue(run.startswith("#!/usr/bin/with-contenv bash\n# shellcheck shell=bash\n"))
        self.assertIn("s6-setuidgid abc /app/notely/notely serve --data /config --port 8080", run)
        self.assertIn("root/etc/s6-overlay/s6-rc.d/user/contents.d/svc-notely", built.files)
        self.assertIn("root/etc/s6-overlay/s6-rc.d/init-config-end/dependencies.d/init-notely-config", built.files)
        self.assertIn("root/etc/s6-overlay/s6-rc.d/svc-notely/run", built.executable)
        self.assertIn("tar xzf /tmp/notely.tar.gz -C /tmp/unpack", built.files["Dockerfile"])
        self.assertIn("    port: 8080", built.files["image.yml"])

    def test_a_static_build_runs_on_alpine(self) -> None:
        issue = fixture("notely-issue.json")
        issue["body"] = issue["body"].replace("A single Go binary", "A single static Go binary")
        built = labs.Scaffold(labs.load_proposal(issue), fixture("notely-repo.json"), fixture("notely-release.json"),
                              "member", "2026-11-02")
        built.build()
        self.assertEqual(built.base, "alpine")
        self.assertIn("FROM ghcr.io/linuxserver-playground/baseimage-alpine:3.24", built.files["Dockerfile"])

    def test_a_guessed_start_command_is_a_todo(self) -> None:
        issue = fixture("notely-issue.json")
        issue["body"] = issue["body"].replace("Start it with `/app/notely/notely serve --data /config --port 8080`.", "")
        built = labs.Scaffold(labs.load_proposal(issue), fixture("notely-repo.json"), fixture("notely-release.json"),
                              "member", "2026-11-02")
        built.build()
        self.assertTrue(any("start command" in t for t in built.todos), built.todos)
        self.assertIn("TODO", built.files["root/etc/s6-overlay/s6-rc.d/svc-notely/run"])

    def test_a_source_build_stops_at_a_todo(self) -> None:
        issue = fixture("notely-issue.json")
        issue["body"] = issue["body"].replace("Release asset\n", "Source release\n")
        built = labs.Scaffold(labs.load_proposal(issue), fixture("notely-repo.json"), fixture("notely-release.json"),
                              "member", "2026-11-02")
        built.build()
        self.assertEqual(built.platforms, ["amd64", "arm64"])
        self.assertIn("archive/refs/tags/${VERSION}.tar.gz", built.files["image.yml"])
        self.assertIn("&& false", built.files["Dockerfile"])

    def test_a_working_repository_is_the_starting_point(self) -> None:
        issue = fixture("photocraft-issue.json")
        issue["body"] = issue["body"].replace("### Web interface port",
                                              "### Working repository\n\nhttps://github.com/dev-org/docker-photocraft\n\n### Web interface port")
        proposal = labs.load_proposal(issue)
        self.assertEqual(proposal.get("working_repo"), "https://github.com/dev-org/docker-photocraft")
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            (work / "root" / "defaults").mkdir(parents=True)
            (work / "image.yml").write_text("schema: 1\nname: photocraft\n\nmaintainers:\n- someone-else\n\n"
                                            "build:\n  base: selkies\n  platforms:\n  - amd64\n")
            (work / "Dockerfile").write_text("FROM ghcr.io/linuxserver-playground/baseimage-selkies:ubunturesolute\n")
            (work / "root" / "defaults" / "autostart").write_text("photocraft --fullscreen\n")
            (work / "root" / "evil").symlink_to("/etc/passwd")
            built = labs.Scaffold(proposal, fixture("photocraft-repo.json"), fixture("photocraft-release.json"), "m", "d")
            built.from_working(work, proposal.get("working_repo"))
        self.assertIn("maintainers:\n- thelamer\n\nbuild:", built.files["image.yml"])
        self.assertEqual((built.base, built.platforms, built.command), ("selkies", ["amd64"], "photocraft --fullscreen"))
        self.assertNotIn("root/evil", built.files)
        self.assertTrue(any("symlinks" in t for t in built.todos), built.todos)

    def test_run_lines_chain(self) -> None:
        self.assertEqual(labs.chain(["a", "if x; then", "  y;", "fi", "b"]),
                         ["  a && \\", "  if x; then \\", "    y; \\", "  fi && \\", "  b"])


class CliTest(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(ROOT / "scripts" / "labs.py"), *args], capture_output=True, text=True)

    def test_scaffold_then_accept(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "photocraft"
            done = self.run_cli("scaffold", "--issue", str(FIXTURES / "photocraft-issue.json"),
                                "--repo", str(FIXTURES / "photocraft-repo.json"),
                                "--release", str(FIXTURES / "photocraft-release.json"), "--out", str(out))
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertTrue((out / "image.yml").is_file())
            done = self.run_cli("accept", "--dir", str(out), "--member", "member")
            self.assertEqual(done.returncode, 0, done.stderr)
            accept = (out / "accept.sh").read_text()
            self.assertIn("gh repo create \"$repo\" --public --description", accept)
            self.assertNotIn("--template", accept)
            self.assertIn("--branch pending", accept)
            self.assertIn("push --quiet origin HEAD:main", accept)
            self.assertIn("--add-topic labs-pending", accept)
            self.assertIn("[skip ci]", accept)
            self.assertIn("--add-label accepted", accept)
            body = (out / ".proposal" / "pr-body.md").read_text()
            self.assertIn("Closes linuxserverlabs-playground/proposals#1", body)
            self.assertIn("@thelamer", body)
            self.assertIn("--remove-topic labs-pending", (out / "after-merge.sh").read_text())
            check = subprocess.run(["bash", "-n", str(out / "accept.sh")], capture_output=True, text=True)
            self.assertEqual(check.returncode, 0, check.stderr)

    def test_form_link_prefills_by_field_id(self) -> None:
        draft = (FIXTURES / "photocraft-issue.json").read_text()
        url, clean, _ = labs.form_link(json.loads(draft)["body"], "o/proposals")
        self.assertTrue(url.startswith("https://github.com/o/proposals/issues/new?template=proposal.yml"))
        self.assertIn("name=photocraft", url)
        self.assertIn("app_type=Desktop%20application%20%28selkies%29", url)
        self.assertNotIn("bar=", url)


if __name__ == "__main__":
    unittest.main()

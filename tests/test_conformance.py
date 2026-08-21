"""The reference implementation against the pinned vectors.

`vectors.json` is the whole point of this repository. A specification that only
describes a derivation can be read two ways by two careful people; a
specification with vectors cannot. Everything here checks that this
implementation is one of the readings the vectors permit -- which is to say, the
only one.

Standard library only, and no network: a conformance suite that has to fetch
something is one that stops working the day the something moves.

    python3 -m unittest discover -s tests -t tests
"""

import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
VECTORS = ROOT / "vectors.json"
REFERENCE = ROOT / "reference" / "js-vectors.js"


def load(name, module):
    spec = importlib.util.spec_from_file_location(module, ROOT / name)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


identicon = load("repository-identicon.py", "repository_identicon")
text_identicon = load("text-identicon.py", "text_identicon")
vectors = json.loads(VECTORS.read_text())


class TestTheVectorsThemselves(unittest.TestCase):

    def test_there_are_some(self):
        self.assertTrue(vectors, "vectors.json is empty")

    def test_each_carries_everything_needed_to_check_an_implementation(self):
        for vector in vectors:
            for field in ("key", "md5", "grid", "foreground"):
                self.assertIn(field, vector)
            self.assertEqual(5, len(vector["grid"]))
            for row in vector["grid"]:
                self.assertRegex(row, r"^[01]{5}$")

    def test_no_two_vectors_share_a_key(self):
        keys = [vector["key"] for vector in vectors]
        self.assertEqual(len(keys), len(set(keys)))


class TestTheImplementationConforms(unittest.TestCase):
    """One test per property the specification fixes.

    Failures here mean the implementation and the vectors disagree, and the
    vectors are the ones generated from the reference library -- so the
    implementation is what moved.
    """

    def test_the_digest_matches(self):
        for vector in vectors:
            with self.subTest(key=vector["key"]):
                self.assertEqual(vector["md5"],
                                 identicon._digest(vector["key"]))

    def test_the_grid_matches(self):
        for vector in vectors:
            with self.subTest(key=vector["key"]):
                rows = ["".join("1" if cell else "0" for cell in row)
                        for row in identicon.identicon_grid(vector["key"])]
                self.assertEqual(vector["grid"], rows)

    def test_the_colour_matches(self):
        """Including the rounding rule. Half up, not half to even -- the one
        place a reimplementation in another language silently diverges."""
        for vector in vectors:
            with self.subTest(key=vector["key"]):
                self.assertEqual(
                    vector["foreground"],
                    identicon.hex_colour(identicon.identicon_colour(vector["key"])))


class TestRemoteNormalisation(unittest.TestCase):
    """Every spelling of one repository must collapse to one key, or an SSH
    checkout and an HTTPS checkout of the same project get different marks."""

    EXPECTED = "github.com/owner/repo"
    SPELLINGS = (
        "https://github.com/Owner/Repo.git",
        "https://github.com/Owner/Repo",
        "https://github.com/owner/repo/",
        "https://token@github.com/Owner/Repo.git",
        "https://user:pass@github.com/Owner/Repo.git",
        "git@github.com:Owner/Repo.git",
        "git@github.com:Owner/Repo",
        "ssh://git@github.com/Owner/Repo.git",
        "ssh://git@github.com:2222/Owner/Repo.git",
        "git://github.com/Owner/Repo.git",
    )

    def test_every_spelling_in_the_specification_collapses_to_one_key(self):
        for url in self.SPELLINGS:
            with self.subTest(url=url):
                self.assertEqual(self.EXPECTED,
                                 identicon.normalise_remote_url(url))

    def test_a_local_path_remote_is_refused(self):
        """It is no more portable than the working directory, so it earns no
        special treatment and must fall through to a path-shaped source."""
        for url in ("/srv/git/repo.git", "file:///srv/git/repo.git", "", None):
            with self.subTest(url=url):
                self.assertIsNone(identicon.normalise_remote_url(url))

    def test_the_host_is_kept_so_forges_stay_distinct(self):
        self.assertNotEqual(identicon.normalise_remote_url("git@github.com:a/b"),
                            identicon.normalise_remote_url("git@gitlab.com:a/b"))


class TestTheTextRendering(unittest.TestCase):

    def test_it_renders_two_lines_for_every_vector(self):
        for vector in vectors:
            with self.subTest(key=vector["key"]):
                grid = identicon.identicon_grid(vector["key"])
                colour = identicon.identicon_colour(vector["key"])
                lines = text_identicon.text(grid, colour).split("\n")
                self.assertEqual(2, len(lines))

    def test_its_own_selftest_passes(self):
        """It re-derives the whole 230-character octant table from the Unicode
        database, which is the only way that table is checkable at all."""
        result = subprocess.run(
            ["python3", str(ROOT / "text-identicon.py"), "--selftest"],
            capture_output=True, text=True, timeout=60)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)


class TestTheVectorsCanBeRegenerated(unittest.TestCase):
    """The reference library is committed rather than fetched, so anyone can
    re-derive the vectors offline, for as long as this repository exists. A
    reference that has to be downloaded is one that can disappear, and one did
    during the week this was written."""

    def test_the_reference_harness_and_library_are_present(self):
        self.assertTrue(REFERENCE.exists())
        for name in ("identicon.js", "pnglib.js", "LICENSE"):
            self.assertTrue((ROOT / "reference" / "vendor" / name).exists(), name)

    def test_regenerating_reproduces_the_committed_vectors(self):
        """Skipped where node is absent: the vectors are committed precisely so
        that checking this implementation never requires it."""
        try:
            probe = subprocess.run(["node", "--version"],
                                   capture_output=True, timeout=30)
        except (OSError, subprocess.SubprocessError):
            self.skipTest("node is not installed")
        if probe.returncode != 0:
            self.skipTest("node is not usable")

        result = subprocess.run(
            ["node", str(REFERENCE), *[v["key"] for v in vectors]],
            capture_output=True, text=True, cwd=str(ROOT / "reference"), timeout=60)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(vectors, json.loads(result.stdout))


class TestInstallingIntoARepository(unittest.TestCase):
    """The thing the project is for: putting the mark in the repository.

    Everything else here checks a derivation. This checks the deliverable --
    that running it in a repository leaves the right files, that running it
    twice changes nothing, and that --check notices when something has drifted
    without touching it.
    """

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        subprocess.run(["git", "init", "-q", self.tmp], check=True, timeout=30)
        subprocess.run(["git", "-C", self.tmp, "remote", "add", "origin",
                        "git@github.com:someone/a-project.git"],
                       check=True, timeout=30)

    def test_it_writes_the_three_artifacts(self):
        result = identicon.install_into_repo(self.tmp)
        self.assertEqual("github.com/someone/a-project", result["key"])
        self.assertEqual("remote", result["source"])
        for name in ("png", "png4x", "svg", "colour"):
            with self.subTest(artifact=name):
                path = pathlib.Path(result["files"][name])
                self.assertTrue(path.is_file(), path)
                self.assertEqual("created", result["changes"][name])

    def test_the_colour_file_is_the_whole_parser(self):
        """A consumer runs `cat`, and that is the entire integration."""
        result = identicon.install_into_repo(self.tmp)
        body = pathlib.Path(result["files"]["colour"]).read_text()
        self.assertEqual(body, result["colour"] + "\n")
        self.assertRegex(body, r"^#[0-9a-f]{6}\n$")

    def test_running_it_twice_on_an_unchanged_key_changes_nothing(self):
        """Idempotent for a *fixed* key, which is the only sense in which it
        is idempotent: the sibling test below renames the remote and expects
        every artifact to be rewritten."""
        first = identicon.install_into_repo(self.tmp)
        again = identicon.install_into_repo(self.tmp)
        self.assertTrue(again["current"])
        self.assertEqual({"unchanged"}, set(again["changes"].values()))
        self.assertEqual(first["colour"], again["colour"])

    def test_check_reports_drift_without_writing(self):
        first = identicon.install_into_repo(self.tmp)
        target = pathlib.Path(first["files"]["colour"])
        target.write_text("not a colour\n")

        checked = identicon.install_into_repo(self.tmp, check=True)
        self.assertFalse(checked["current"])
        self.assertEqual("updated", checked["changes"]["colour"])
        self.assertEqual("not a colour\n", target.read_text(),
                         "--check must not write")

        identicon.install_into_repo(self.tmp)
        self.assertEqual(first["colour"] + "\n", target.read_text())

    def _rename_remote(self, to="git@github.com:someone/renamed.git"):
        subprocess.run(["git", "-C", self.tmp, "remote", "set-url", "origin",
                        to], check=True, timeout=30)

    def test_replaced_files_are_kept_so_a_rollback_is_a_move(self):
        """These are developers. A file beside the new one is the whole
        recovery procedure, and it beats any amount of asking first."""
        before = identicon.install_into_repo(self.tmp, readme=False)
        self._rename_remote()
        after = identicon.install_into_repo(self.tmp, reseed=True,
                                            readme=False)
        self.assertNotEqual(before["colour"], after["colour"])

        for name in ("png", "svg", "colour", "key"):
            with self.subTest(artifact=name):
                kept = identicon.prior_path(after["files"][name])
                self.assertTrue(kept.is_file(), kept)
        colour = identicon.prior_path(after["files"]["colour"])
        self.assertEqual(before["colour"], colour.read_text().strip())
        self.assertEqual(before["key"],
                         identicon.prior_path(after["files"]["key"])
                         .read_text().splitlines()[-1])

    def test_nothing_is_kept_when_nothing_is_replaced(self):
        result = identicon.install_into_repo(self.tmp, readme=False)
        for name in ("png", "svg", "colour", "key"):
            with self.subTest(artifact=name):
                self.assertFalse(
                    identicon.prior_path(result["files"][name]).exists())

    def test_check_keeps_nothing_because_it_replaces_nothing(self):
        identicon.install_into_repo(self.tmp, readme=False)
        self._rename_remote()
        result = identicon.install_into_repo(self.tmp, reseed=True,
                                             readme=False, check=True)
        self.assertFalse(
            identicon.prior_path(result["files"]["colour"]).exists())

    def test_the_seed_is_recorded_on_the_first_run(self):
        result = identicon.install_into_repo(self.tmp)
        self.assertEqual("remote", result["source"])
        self.assertEqual(result["key"], identicon.recorded_seed(self.tmp))

    def test_a_rename_does_not_change_the_mark(self):
        """The whole point of an identity: it does not re-derive itself."""
        before = identicon.install_into_repo(self.tmp)
        self._rename_remote()
        after = identicon.install_into_repo(self.tmp)
        self.assertEqual(before["key"], after["key"])
        self.assertEqual(before["colour"], after["colour"])
        self.assertEqual("seed", after["source"])
        self.assertTrue(after["current"])

    def test_a_rename_is_reported_as_seed_drift(self):
        identicon.install_into_repo(self.tmp)
        self._rename_remote()
        after = identicon.install_into_repo(self.tmp, check=True)
        self.assertEqual("github.com/someone/renamed", after["seed_drift"])

    def test_artifacts_refresh_without_touching_the_seed(self):
        """A better renderer or a different size must reach every repository
        without disturbing anybody's identity."""
        before = identicon.install_into_repo(self.tmp)
        self._rename_remote()
        after = identicon.install_into_repo(self.tmp, size=128)
        self.assertEqual(before["key"], after["key"])
        self.assertEqual("unchanged", after["changes"]["key"])
        self.assertEqual("updated", after["changes"]["png"])

    def test_reseed_is_the_only_thing_that_changes_the_mark(self):
        before = identicon.install_into_repo(self.tmp)
        self._rename_remote()
        after = identicon.install_into_repo(self.tmp, reseed=True)
        self.assertEqual("github.com/someone/renamed", after["key"])
        self.assertNotEqual(before["colour"], after["colour"])
        self.assertEqual("github.com/someone/renamed",
                         identicon.recorded_seed(self.tmp))
        self.assertIsNone(after["seed_drift"])

    def test_an_override_masking_a_renamed_remote_is_reported(self):
        """An override outranks the remote, which is the point of it and the
        one way a rename can pass unnoticed. It is reported, not resolved."""
        pinned = "github.com/someone/a-project"
        (pathlib.Path(self.tmp) / identicon.OVERRIDE_FILENAME).write_text(
            pinned + "\n")
        subprocess.run(["git", "-C", self.tmp, "remote", "set-url", "origin",
                        "git@github.com:someone/moved-on.git"],
                       check=True, timeout=30)

        result = identicon.install_into_repo(self.tmp, check=True)
        self.assertEqual("override", result["source"])
        self.assertEqual(pinned, result["key"])
        self.assertEqual("github.com/someone/moved-on", result["masking"])

    def test_an_override_agreeing_with_the_remote_is_not_reported(self):
        (pathlib.Path(self.tmp) / identicon.OVERRIDE_FILENAME).write_text(
            "github.com/someone/a-project\n")
        result = identicon.install_into_repo(self.tmp, check=True)
        self.assertIsNone(result["masking"])

    def test_git_helpers_accept_a_default_cwd(self):
        """`git -C None` fails and reads as "not a repository", which is the
        wrong answer in the direction that looks right."""
        original = os.getcwd()
        os.chdir(self.tmp)
        self.addCleanup(os.chdir, original)
        self.assertEqual("github.com/someone/a-project",
                         identicon.normalise_remote_url(
                             identicon.repo_remote_url(None)))

    def _readme(self, body):
        path = pathlib.Path(self.tmp) / "README.md"
        path.write_text(body, encoding="utf-8")
        return path

    def test_the_mark_goes_into_the_readme_after_the_title(self):
        readme = self._readme("# Thing\n\nA tool that does a thing.\n")
        result = identicon.install_into_repo(self.tmp)
        self.assertEqual("updated", result["changes"]["readme"])
        self.assertEqual(
            ["# Thing", "", identicon.README_MARK, "",
             "A tool that does a thing.", ""],
            readme.read_text(encoding="utf-8").split("\n"))

    def test_it_goes_in_once(self):
        readme = self._readme("# Thing\n")
        identicon.install_into_repo(self.tmp)
        first = readme.read_text(encoding="utf-8")
        again = identicon.install_into_repo(self.tmp)
        self.assertEqual("unchanged", again["changes"]["readme"])
        self.assertEqual(first, readme.read_text(encoding="utf-8"))

    def test_a_line_the_author_has_reworked_is_left_alone(self):
        """Recognised by the artifact path, so a moved, resized or PNG-pointed
        line counts as present and keeps whatever shape its author gave it."""
        body = ('<img src=".identicon/repository-identicon.png" width="60">\n'
                "\n# Thing\n")
        readme = self._readme(body)
        result = identicon.install_into_repo(self.tmp)
        self.assertEqual("unchanged", result["changes"]["readme"])
        self.assertEqual(body, readme.read_text(encoding="utf-8"))

    def test_a_readme_that_documents_the_path_still_gets_a_mark(self):
        """Found by dogfooding. A README that *describes* these files -- in a
        fenced block, a table, or prose -- is not a README that displays one,
        and matching the bare path meant exactly the projects integrating with
        this never got their own mark."""
        readme = self._readme(
            "# Docs\n\nIt writes:\n\n```\n"
            ".identicon/repository-identicon.svg    vector\n```\n")
        result = identicon.install_into_repo(self.tmp)
        self.assertEqual("updated", result["changes"]["readme"])
        self.assertIn(identicon.README_MARK,
                      readme.read_text(encoding="utf-8"))

    def test_the_mark_shown_as_a_fenced_example_does_not_count(self):
        """The second dogfooding correction: this repository's own README
        shows the markdown in a code block. A mark inside a fence is a mark
        being talked about, not one being displayed."""
        readme = self._readme(
            "# Docs\n\nPut this in your README:\n\n```markdown\n"
            f"{identicon.README_MARK}\n```\n")
        result = identicon.install_into_repo(self.tmp)
        self.assertEqual("updated", result["changes"]["readme"])
        body = readme.read_text(encoding="utf-8")
        self.assertEqual(2, body.count(identicon.README_MARK))

    def test_a_repository_with_no_readme_is_not_given_one(self):
        result = identicon.install_into_repo(self.tmp)
        self.assertNotIn("readme", result["changes"])

    def test_no_readme_option_writes_the_artifacts_only(self):
        readme = self._readme("# Thing\n")
        result = identicon.install_into_repo(self.tmp, readme=False)
        self.assertNotIn("readme", result["changes"])
        self.assertEqual("# Thing\n", readme.read_text(encoding="utf-8"))
        self.assertEqual("created", result["changes"]["png"])

    def test_check_does_not_touch_the_readme(self):
        readme = self._readme("# Thing\n")
        result = identicon.install_into_repo(self.tmp, check=True)
        self.assertEqual("updated", result["changes"]["readme"])
        self.assertEqual("# Thing\n", readme.read_text(encoding="utf-8"))

    def test_a_readme_with_no_heading_takes_the_mark_at_the_top(self):
        readme = self._readme("Just prose, no heading.\n")
        identicon.install_into_repo(self.tmp)
        self.assertTrue(
            readme.read_text(encoding="utf-8").startswith(identicon.README_MARK))

    def test_a_repository_with_no_remote_falls_back_and_says_so(self):
        bare = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, bare, ignore_errors=True)
        subprocess.run(["git", "init", "-q", bare], check=True, timeout=30)
        result = identicon.install_into_repo(bare)
        self.assertNotEqual("remote", result["source"],
                            "no remote, so the key cannot be portable")

    def test_the_command_line_exits_1_on_drift_under_check(self):
        identicon.install_into_repo(self.tmp)
        pathlib.Path(identicon.artifact_paths(self.tmp)["colour"]).write_text("x")
        completed = subprocess.run(
            ["python3", str(ROOT / "repository-identicon.py"), "apply",
             "--check", "--json", self.tmp],
            capture_output=True, text=True, timeout=60)
        self.assertEqual(1, completed.returncode, completed.stdout)
        self.assertFalse(json.loads(completed.stdout)["current"])


class TestTheTwoFilesAreAPair(unittest.TestCase):
    """repository-identicon.py needs text-identicon.py for every text style.

    Deployed without it the tool still runs and still exits 0, because `emit`
    swallows everything so that a hook can never break a turn -- which is
    exactly what turns a missing file into a silent one. So the loader names
    the file instead of failing on a bare path, and `doctor` reports it either
    way. Both are checked here against a copy deployed on its own, because in
    the tree the sibling is always there.
    """

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.alone = self.tmp / "repository-identicon.py"
        shutil.copy(ROOT / "repository-identicon.py", self.alone)

    def doctor(self, script):
        completed = subprocess.run(["python3", str(script), "doctor"],
                                   capture_output=True, text=True, timeout=60)
        self.assertEqual(0, completed.returncode, completed.stderr)
        return completed.stdout

    def test_doctor_gives_the_path_when_the_sibling_is_there(self):
        self.assertIn(str(ROOT / "text-identicon.py"),
                      self.doctor(ROOT / "repository-identicon.py"))

    def test_doctor_says_not_found_and_what_it_costs_when_it_is_not(self):
        report = self.doctor(self.alone)
        self.assertRegex(report, r"text-identicon\.py\s+NOT FOUND")
        self.assertIn("text styles will print nothing", report)

    def test_the_loader_names_the_file_rather_than_failing_on_a_bare_path(self):
        spec = importlib.util.spec_from_file_location("alone", self.alone)
        alone = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(alone)
        with self.assertRaises(FileNotFoundError) as raised:
            alone._text_module()
        self.assertIn("text-identicon.py", str(raised.exception))


if __name__ == "__main__":
    unittest.main()

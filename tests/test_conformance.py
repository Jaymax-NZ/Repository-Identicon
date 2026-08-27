"""The reference implementation against the pinned vectors.

`vectors.json` is the whole point of this repository. A specification that only
describes a derivation can be read two ways by two careful people; a
specification with vectors cannot.

Standard library only, and no network. `git` must be on PATH -- the install
tests run against real repositories -- and only the regeneration test skips,
when node is absent.

    python3 -m unittest discover -s tests -t tests
"""

import hashlib
import importlib.util
import json
import os
import pathlib
import shutil
import struct
import subprocess
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parent.parent
VECTORS = ROOT / "vectors.json"
REFERENCE = ROOT / "reference" / "js-vectors.js"


def load(name, module):
    """Import a script by path -- both are hyphen-named, so `import` cannot."""
    spec = importlib.util.spec_from_file_location(module, ROOT / name)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


identicon = load("repository-identicon.py", "repository_identicon")
text_identicon = load("text-identicon.py", "text_identicon")
vectors = json.loads(VECTORS.read_text())["vectors"]


def pinned_versions():
    """The mapping versions the committed vectors cover."""
    return {identicon.parse_key(v["key"])[0] for v in vectors}


# ---- The vectors and the implementation ----

class TestTheVectorsThemselves(unittest.TestCase):

    def test_there_are_some(self):
        self.assertTrue(vectors, "vectors.json is empty")

    def test_the_version_this_implementation_seeds_at_is_pinned(self):
        """A bump that brings no vectors is a bump nothing checks."""
        self.assertIn(identicon.MAPPING_VERSION, pinned_versions())

    def test_only_the_version_this_implementation_draws_is_pinned(self):
        """One rule, so one version. Retired versions leave with their rule --
        a vector nothing can draw is a vector nothing checks."""
        self.assertEqual({identicon.MAPPING_VERSION}, pinned_versions())

    def test_each_carries_everything_needed_to_check_an_implementation(self):
        for vector in vectors:
            for field in ("key", "md5", "grid", "foreground"):
                self.assertIn(field, vector)
            self.assertEqual(5, len(vector["grid"]),
                             f"{vector['key']}: the grid is not five rows")
            for row in vector["grid"]:
                self.assertRegex(row, r"^[01]{5}$")

    def test_no_two_vectors_share_a_key(self):
        keys = [vector["key"] for vector in vectors]
        self.assertEqual(len(keys), len(set(keys)), "two vectors share a key")

    def test_the_version_is_inside_what_gets_hashed(self):
        """Change the version and the mark moves, because the stamp is part of
        the string being digested. That is why the version has to be a reviewed
        line rather than a note about one."""
        for vector in vectors:
            _version, seed = identicon.parse_key(vector["key"])
            self.assertNotEqual(
                identicon.identicon_grid(vector["key"]),
                identicon.identicon_grid(f"{identicon.MAPPING_VERSION + 1}:{seed}"),
                f"{seed}: restamping did not move the grid")


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


# ---- Remotes and text rendering ----

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


# ---- Regenerating the vectors ----

class TestTheVectorsCanBeRegenerated(unittest.TestCase):
    """The reference library is committed rather than fetched: a reference that
    must be downloaded can vanish, and one did. Anyone can re-derive the vectors
    offline for as long as this repository exists."""

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

        # The library pins the pattern. From mapping version 2 the colour is
        # this project's own rule, which the library cannot produce and has no
        # opinion about, so it is checked against the implementation instead.
        produced = json.loads(result.stdout)["vectors"]
        self.assertEqual([v["key"] for v in vectors],
                         [v["key"] for v in produced])
        for pinned, made in zip(vectors, produced):
            with self.subTest(key=pinned["key"]):
                self.assertEqual(pinned["md5"], made["md5"])
                self.assertEqual(pinned["grid"], made["grid"])
                self.assertNotIn("foreground", made)
                self.assertEqual(
                    pinned["foreground"],
                    identicon.hex_colour(
                        identicon.identicon_colour(pinned["key"])))


# ---- Geometry and colour ----

class TestTheBlocksAndTheCanvas(unittest.TestCase):
    """The block is specified; the canvas is derived.

    `@4x` multiplies the block by four and the border by two: the border is
    chrome, so quadrupling it would spend the new pixels on empty edge. The 4x
    magnifies the *mark*, not the canvas.
    """

    # Any key; a literal one because nothing here asserts a version-dependent value.
    KEY = f"{identicon.MAPPING_VERSION}:github.com/someone/a-project"

    def area(self, rgba, block, border):
        """The GRID x GRID block region, with the border cropped off."""
        edge = identicon.canvas_edge(block, border)
        side = block * identicon.GRID
        rows = []
        for y in range(border, border + side):
            start = (y * edge + border) * 4
            rows.append(rgba[start:start + side * 4])
        return b"".join(rows)

    def magnify(self, pixels, side, scale):
        """Nearest-neighbour upscale of a `side`x`side` RGBA region by `scale`."""
        rows = []
        for y in range(side):
            row = pixels[y * side * 4:(y + 1) * side * 4]
            rows.extend([b"".join(row[x * 4:(x + 1) * 4] * scale
                                  for x in range(side))] * scale)
        return b"".join(rows)

    def test_the_canvas_is_five_blocks_and_two_borders(self):
        self.assertEqual([7, 12, 17, 22, 27],
                         [identicon.canvas_edge(b, 1) for b in identicon.BLOCKS])
        self.assertEqual([24, 44, 64, 84, 104],
                         [identicon.canvas_edge(b * identicon.ARTIFACT_SCALE,
                                                identicon.SCALED_BORDER)
                          for b in identicon.BLOCKS])

    def test_the_scaled_mark_is_the_mark_magnified(self):
        scale, border2 = identicon.ARTIFACT_SCALE, identicon.SCALED_BORDER
        for block in identicon.BLOCKS:
            with self.subTest(block=block):
                one = identicon.render_rgba(self.KEY, block)
                many = identicon.render_rgba(self.KEY, block * scale,
                                             border=border2)
                self.assertEqual(
                    self.magnify(self.area(one, block, identicon.BORDER),
                                 block * identicon.GRID, scale),
                    self.area(many, block * scale, border2))

    def test_the_border_doubles_rather_than_quadrupling(self):
        """The one part of `@4x` that is not a magnification -- not a bug."""
        self.assertEqual(2 * identicon.BORDER, identicon.SCALED_BORDER)
        self.assertNotEqual(identicon.ARTIFACT_SCALE * identicon.BORDER,
                            identicon.SCALED_BORDER)

    def test_the_pngs_declare_the_derived_canvas(self):
        for block in identicon.BLOCKS:
            with self.subTest(block=block):
                png = identicon.render_png(self.KEY, block)
                edge = identicon.canvas_edge(block, identicon.BORDER)
                self.assertEqual((edge, edge),
                                 struct.unpack(">II", png[16:24]))

    def test_a_canvas_somebody_else_fixed_is_filled_exactly(self):
        """The icon theme wants 48 pixels at `48x48/apps/` whatever that
        divides into, so `edge` pads rather than changing the file's size."""
        for edge in identicon.INSTALL_SIZES:
            with self.subTest(edge=edge):
                block = identicon.fit_block(edge)
                self.assertLessEqual(block * identicon.GRID, edge,
                                     f"the block overflows the {edge}px canvas")
                png = identicon.render_png(self.KEY, block, edge=edge)
                self.assertEqual((edge, edge),
                                 struct.unpack(">II", png[16:24]))

    def test_every_large_canvas_is_exact(self):
        for canvas in identicon.LARGE_CANVASES:
            with self.subTest(canvas=canvas):
                block, border = identicon.large_geometry(canvas)
                self.assertEqual(canvas, identicon.canvas_edge(block, border))

    def test_a_canvas_with_no_exact_geometry_is_refused(self):
        for canvas in (16, 48, 100):
            with self.subTest(canvas=canvas):
                with self.assertRaises(ValueError):
                    identicon.large_geometry(canvas)

    def test_the_large_pngs_declare_their_canvas(self):
        wanted = identicon.artifact_bytes(self.KEY)
        for canvas in identicon.LARGE_CANVASES:
            with self.subTest(canvas=canvas):
                self.assertEqual((canvas, canvas),
                                 struct.unpack(">II", wanted[f"png{canvas}"][16:24]))


class TestTheColourRule(unittest.TestCase):
    """One brightness across the wheel, so one file serves both grounds."""

    KEY = f"{identicon.MAPPING_VERSION}:github.com/someone/a-project"

    @staticmethod
    def luminance(rgb):
        def channel(value):
            value /= 255
            return (value / 12.92 if value <= 0.03928
                    else ((value + 0.055) / 1.055) ** 2.4)
        red, green, blue = (channel(v) for v in rgb)
        return 0.2126 * red + 0.7152 * green + 0.0722 * blue

    def contrast(self, a, b):
        first, second = self.luminance(a), self.luminance(b)
        return (max(first, second) + 0.05) / (min(first, second) + 0.05)

    def mark_rgb(self, degrees):
        chroma = identicon.gamut_chroma(degrees)
        return tuple(identicon._encode(c) for c in
                     identicon._oklch_to_linear(identicon.MARK_LIGHTNESS,
                                                chroma, degrees))

    def test_one_file_clears_the_threshold_on_both_grounds(self):
        """The whole reason there is no light and no dark variant."""
        for ground in ((255, 255, 255), (13, 17, 23)):
            worst = min(self.contrast(self.mark_rgb(d), ground)
                        for d in range(0, 360, 5))
            with self.subTest(ground=ground):
                self.assertGreaterEqual(worst, 3.0)

    def test_the_chroma_is_capped_not_flattened(self):
        """Some hues reach the cap and some cannot. Holding every hue to what
        the narrowest can manage costs about half the colour on the wheel."""
        reached = [d for d in range(0, 360, 5)
                   if identicon.gamut_chroma(d) >= identicon.MARK_CHROMA]
        self.assertTrue(reached, "no hue reaches the cap")
        self.assertLess(len(reached), 72, "the cap binds nowhere")

    def test_no_hue_leaves_the_gamut(self):
        for degrees in range(0, 360):
            with self.subTest(degrees=degrees):
                linear = identicon._oklch_to_linear(
                    identicon.MARK_LIGHTNESS, identicon.gamut_chroma(degrees),
                    degrees)
                self.assertTrue(identicon._in_gamut(linear))

    def test_the_gamut_search_is_reproducible(self):
        """Fixed bounds, fixed rounds, rounded off at the end -- because
        'search until it converges' is not something a port can reproduce."""
        self.assertEqual(30, identicon.GAMUT_STEPS)
        for degrees in (0, 137.5, 201, 359.9):
            value = identicon.gamut_chroma(degrees)
            self.assertEqual(value, round(value, 4))

    def test_a_withdrawn_version_is_refused_rather_than_redrawn(self):
        """Versions 0 to 2 were drafts and no release carried them, so they are
        gone. A key stamped at one must raise, not be quietly drawn with
        today's rule -- that would move a mark nobody asked to move, which is
        the failure the stamp exists to prevent."""
        seed = "github.com/justin-maxwell/claude-state-panel"
        for key in (seed, "0:" + seed, "1:" + seed, "2:" + seed):
            with self.subTest(key=key):
                with self.assertRaises(identicon.UnknownMappingVersion):
                    identicon.identicon_colour(key)

    def test_a_version_from_the_future_is_refused_too(self):
        """Symmetric, and for the same reason: an unknown stamp is somebody
        else's rule, and guessing at it draws a mark this build cannot vouch
        for."""
        with self.assertRaises(identicon.UnknownMappingVersion):
            identicon.identicon_colour(
                f"{identicon.MAPPING_VERSION + 1}:github.com/a/b")

    def test_there_is_one_of_each(self):
        """One file per artifact -- what one brightness across the wheel buys."""
        wanted = identicon.artifact_bytes(self.KEY)
        for name in ("png", "png4x", "png128", "png256", "svg", "colour",
                     "grid"):
            self.assertIn(name, wanted)
        self.assertEqual(7, len(wanted))


class TestTheArtifactSet(unittest.TestCase):
    """One list of names feeds both the paths and the bytes."""

    # Any key; a literal one because nothing here asserts a version-dependent value.
    KEY = f"{identicon.MAPPING_VERSION}:github.com/someone/a-project"

    def test_names_and_bytes_cannot_disagree(self):
        self.assertEqual(set(identicon.artifact_paths("/nowhere")),
                         set(identicon.artifact_bytes(self.KEY)))


# ---- Installing into a repository ----

class TestInstallingIntoARepository(unittest.TestCase):
    """The thing the project is for: putting the mark in the repository.

    Everything else here checks a derivation. This checks the deliverable,
    against a real git repository.
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
        self.assertEqual("github.com/someone/a-project", result["seed"])
        # Interpolated, not a literal: a hard-coded "2:" here fails on the next
        # bump while testing nothing that changed.
        self.assertEqual(f"{identicon.MAPPING_VERSION}:github.com/someone/a-project",
                         result["key"])
        self.assertEqual("remote", result["source"])
        for name in ("png", "png4x", "svg", "colour"):
            with self.subTest(artifact=name):
                path = pathlib.Path(result["files"][name])
                self.assertTrue(path.is_file(), path)
                self.assertEqual("created", result["changes"][name])

    def test_a_hand_written_mark_in_any_variant_is_left_alone(self):
        """The mark somebody already placed is theirs. Any of the variants
        counts, in markdown or in HTML, because all of them are the mark."""
        for body in (
            "# T\n\n![](.identicon/repository-identicon-light.svg)\n",
            "# T\n\n![](.identicon/repository-identicon-dark.svg)\n",
            '# T\n\n<img width="64" src=".identicon/repository-identicon-base.svg">\n',
            "# T\n\n![](.identicon/repository-identicon-256.png)\n",
        ):
            with self.subTest(body=body.splitlines()[-1][:44]):
                readme = pathlib.Path(self.tmp) / "README.md"
                readme.write_text(body)
                identicon.install_into_repo(self.tmp)
                self.assertEqual(body, readme.read_text())

    def test_the_colour_file_is_the_whole_parser(self):
        """A consumer runs `cat`, and that is the entire integration."""
        result = identicon.install_into_repo(self.tmp)
        body = pathlib.Path(result["files"]["colour"]).read_text()
        self.assertEqual(body, result["colour"] + "\n")
        self.assertRegex(body, r"^#[0-9a-f]{6}\n$")

    def test_running_it_twice_on_an_unchanged_key_changes_nothing(self):
        """Idempotent for a *fixed* key, which is the only sense in which it is
        idempotent: test_reseed_is_the_only_thing_that_changes_the_mark renames
        the remote and expects the seed, colour and recorded key to move."""
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
        self.assertEqual(before["seed"], "github.com/someone/a-project")

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

    def test_the_key_is_recorded_on_the_first_run(self):
        """The whole key, version stamp included, because the whole key is
        what gets hashed."""
        result = identicon.install_into_repo(self.tmp)
        self.assertEqual("remote", result["source"])
        self.assertEqual(result["key"], identicon.recorded_key(self.tmp))
        self.assertEqual(identicon.MAPPING_VERSION, result["mapping_version"])

    def test_a_rename_does_not_change_the_mark(self):
        """The whole point of an identity: it does not re-derive itself."""
        before = identicon.install_into_repo(self.tmp)
        self._rename_remote()
        after = identicon.install_into_repo(self.tmp)
        self.assertEqual(before["key"], after["key"])
        self.assertEqual(before["colour"], after["colour"])
        self.assertEqual("key", after["source"])
        self.assertTrue(after["current"])

    def test_a_rename_is_reported_as_seed_drift(self):
        identicon.install_into_repo(self.tmp)
        self._rename_remote()
        after = identicon.install_into_repo(self.tmp, check=True)
        self.assertEqual("github.com/someone/renamed", after["seed_drift"])

    def test_artifacts_refresh_without_touching_the_seed(self):
        """A better renderer or a different block must reach every repository
        without disturbing anybody's identity."""
        before = identicon.install_into_repo(self.tmp)
        self._rename_remote()
        after = identicon.install_into_repo(self.tmp, block=3)
        self.assertEqual(before["key"], after["key"])
        self.assertEqual("unchanged", after["changes"]["key"])
        self.assertEqual("updated", after["changes"]["png"])

    def test_reseed_is_the_only_thing_that_changes_the_mark(self):
        before = identicon.install_into_repo(self.tmp)
        self._rename_remote()
        after = identicon.install_into_repo(self.tmp, reseed=True)
        self.assertEqual("github.com/someone/renamed", after["seed"])
        self.assertNotEqual(before["colour"], after["colour"])
        self.assertEqual(f"{identicon.MAPPING_VERSION}:github.com/someone/renamed",
                         identicon.recorded_key(self.tmp))
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
        self.assertEqual(pinned, result["seed"])
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
        """A README that *describes* these files -- in a fenced block, a table,
        or prose -- is not a README that displays one. Matching the bare path
        denied a mark to exactly the projects integrating with this."""
        readme = self._readme(
            "# Docs\n\nIt writes:\n\n```\n"
            ".identicon/repository-identicon.svg    vector\n```\n")
        result = identicon.install_into_repo(self.tmp)
        self.assertEqual("updated", result["changes"]["readme"])
        self.assertIn(identicon.README_MARK,
                      readme.read_text(encoding="utf-8"))

    def test_the_mark_shown_as_a_fenced_example_does_not_count(self):
        """A mark inside a fence is one being talked about, not one being
        displayed -- this repository's own README is the case."""
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


# ---- The key file ----

class TestTheKeyFileWins(unittest.TestCase):
    """The mapping version is in the key, and the key is a tracked file.

    So a repository's mark cannot move because a constant moved in here. It
    moves when that line moves, which is a diff somebody reviews -- which is
    the entire point of putting the version there rather than in the code.
    """

    SEED = "github.com/someone/a-project"

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        subprocess.run(["git", "init", "-q", self.tmp], check=True, timeout=30)
        subprocess.run(["git", "-C", self.tmp, "remote", "add", "origin",
                        f"https://{self.SEED}.git"], check=True, timeout=30)

    def write_key(self, key, preamble="# hand written\n"):
        path = identicon.key_path(self.tmp)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{preamble}{key}\n")
        return path

    def test_an_unstamped_key_is_version_zero_and_hashes_to_itself(self):
        """Keys written before the version existed are still out there. They
        must keep drawing what they always drew, and they do because nothing
        is added at hash time."""
        self.assertEqual((0, self.SEED), identicon.parse_key(self.SEED))
        self.assertEqual(identicon._digest(self.SEED),
                         hashlib.md5(self.SEED.encode()).hexdigest())

    def test_a_seed_containing_a_colon_is_not_mistaken_for_a_stamp(self):
        for seed in ("ssh://git@host/x", "C:/src/project", "host:1234/x"):
            with self.subTest(seed=seed):
                self.assertEqual((0, seed), identicon.parse_key(seed))

    def test_stamping_and_parsing_are_inverses(self):
        for version in (0, 1, 17):
            key = identicon.stamp_key(self.SEED, version)
            self.assertEqual((version, self.SEED), identicon.parse_key(key))

    def test_a_repository_on_a_withdrawn_mapping_is_refused(self):
        """The cost of withdrawing a draft, stated as a test. An unstamped
        repository predates the version and cannot be drawn by a build that
        no longer carries that rule -- and it is refused rather than silently
        redrawn, because redrawing it would move a mark nobody asked to move."""
        self.write_key(self.SEED)
        with self.assertRaises(identicon.UnknownMappingVersion) as caught:
            identicon.install_into_repo(self.tmp, readme=False)
        self.assertIn("remap", str(caught.exception),
                      "the refusal must name the way out")

    def test_the_key_file_is_left_byte_for_byte_alone(self):
        """Including a preamble somebody edited. A run that rewrites this file
        under you makes every run a diff, and this file's job is to be the
        thing that does not move."""
        path = self.write_key(identicon.stamp_key(self.SEED),
                              preamble="# mine, do not touch\n")
        before = path.read_bytes()
        identicon.install_into_repo(self.tmp, readme=False)
        self.assertEqual(before, path.read_bytes())

    def test_a_newer_mapping_strands_a_seeded_repository_until_it_remaps(self):
        """True only while the mapping is a draft. Once a version reaches a
        release its rule stays, and a bump leaves those repositories alone --
        so this test is about the pre-release state and should be revisited
        when `VERSION` leaves `0.0.*`."""
        first = identicon.install_into_repo(self.tmp, readme=False)
        self.assertEqual(identicon.MAPPING_VERSION, first["mapping_version"])
        self.assertIsNone(first["mapping_drift"])

        with mock.patch.object(identicon, "MAPPING_VERSION",
                               identicon.MAPPING_VERSION + 1):
            with self.assertRaises(identicon.UnknownMappingVersion):
                identicon.install_into_repo(self.tmp, readme=False)

    def test_remap_is_what_moves_it_and_keeps_the_seed(self):
        first = identicon.install_into_repo(self.tmp, readme=False)
        with mock.patch.object(identicon, "MAPPING_VERSION",
                               identicon.MAPPING_VERSION + 1):
            after = identicon.install_into_repo(self.tmp, remap=True,
                                                readme=False)
        self.assertEqual(self.SEED, after["seed"])
        self.assertNotEqual(first["key"], after["key"])
        self.assertNotEqual(first["colour"], after["colour"])
        self.assertEqual("updated", after["changes"]["key"])
        self.assertIsNone(after["seed_drift"],
                          "a remap is not a rename and must not read as one")

    def test_remap_under_check_writes_nothing(self):
        first = identicon.install_into_repo(self.tmp, readme=False)
        with mock.patch.object(identicon, "MAPPING_VERSION",
                               identicon.MAPPING_VERSION + 1):
            identicon.install_into_repo(self.tmp, remap=True, readme=False,
                                        check=True)
        self.assertEqual(first["key"], identicon.recorded_key(self.tmp))

    def test_the_read_only_commands_run_in_a_seeded_repository(self):
        """Only an end-to-end run catches this: `show` once looked its source up
        in a table that had never been told about the recorded key, so it
        crashed in every seeded repository -- which is all of them after the
        first run."""
        identicon.install_into_repo(self.tmp, readme=False)
        for command in (["show"], ["render", "--out", os.devnull],
                        ["emit", "--style", "icon"]):
            with self.subTest(command=command[0]):
                done = subprocess.run(
                    ["python3", str(ROOT / "repository-identicon.py"),
                     *command, self.tmp],
                    capture_output=True, text=True, timeout=60)
                self.assertEqual(0, done.returncode, done.stderr)

    def test_show_draws_what_apply_wrote(self):
        """A seeded repository has one mark. The read-only commands resolve
        through the same file, so they cannot report a different one."""
        self.write_key(self.SEED)
        key, source = identicon.resolve_key_for(self.tmp)
        self.assertEqual(self.SEED, key)
        self.assertEqual("key", source)


# ---- The validator, and the pair of files ----

class TestTheValidatorOfferedToPorts(unittest.TestCase):
    """The check this repository offers outward, rather than reaching inward.

    A port in another language cannot run this suite, so `validate` runs the
    port instead and compares it to the vectors. These tests stand in for a
    port with a fake one, because the thing under test is the validator.
    """

    # Echoes the pinned vector back; each negative test corrupts one field.
    CONFORMING_PORT = (
        'import json, sys\n'
        'v = json.load(open({vectors!r}))\n'
        'k = sys.argv[-1]\n'
        'hit = [x for x in v["vectors"] if x["key"] == k][0]\n'
        'print(json.dumps({{"grid": hit["grid"], "colour": hit["foreground"]}}))\n')

    def port(self, body):
        path = pathlib.Path(tempfile.mkdtemp()) / "port.py"
        self.addCleanup(shutil.rmtree, path.parent, ignore_errors=True)
        path.write_text(body.format(vectors=str(VECTORS)))
        return ["python3", str(path)]

    def run_validate(self, argv):
        return identicon.validate_command(argv, vectors)

    def test_a_port_that_reproduces_the_vectors_passes_every_one(self):
        results = self.run_validate(self.port(self.CONFORMING_PORT))
        self.assertEqual(len(vectors), len(results))
        for result in results:
            with self.subTest(key=result["key"]):
                self.assertEqual([], result["problems"])

    def test_a_wrong_colour_fails_and_says_which_key(self):
        body = self.CONFORMING_PORT.replace('hit["foreground"]', '"#010203"')
        failed = [r for r in self.run_validate(self.port(body)) if r["problems"]]
        self.assertEqual(len(vectors), len(failed))
        self.assertIn("#010203", failed[0]["problems"][0])

    def test_a_wrong_grid_fails(self):
        body = self.CONFORMING_PORT.replace('hit["grid"]', '["00000"] * 5')
        failed = [r for r in self.run_validate(self.port(body)) if r["problems"]]
        self.assertTrue(failed)
        self.assertIn("grid", failed[0]["problems"][0])

    def test_output_that_is_not_json_is_reported_rather_than_raised(self):
        results = self.run_validate(self.port('print("not json")\n'))
        self.assertTrue(all(r["problems"] for r in results))
        self.assertIn("not JSON", results[0]["problems"][0])

    def test_a_port_that_crashes_is_reported_with_its_exit_code(self):
        results = self.run_validate(self.port('import sys\nsys.exit(3)\n'))
        self.assertIn("exited 3", results[0]["problems"][0])

    def test_the_grid_may_be_numbers_or_booleans_rather_than_strings(self):
        """Failing a correct port over JSON shape is worse than no validator."""
        for shape in ("[[int(c) for c in r] for r in hit[\"grid\"]]",
                      "[[c == \"1\" for c in r] for r in hit[\"grid\"]]",
                      "[[c for c in r] for r in hit[\"grid\"]]"):
            with self.subTest(shape=shape):
                body = self.CONFORMING_PORT.replace('hit["grid"]', shape)
                results = self.run_validate(self.port(body))
                self.assertEqual([], results[0]["problems"])

    def test_the_command_line_exits_1_when_a_port_disagrees(self):
        body = self.CONFORMING_PORT.replace('hit["foreground"]', '"#010203"')
        completed = subprocess.run(
            ["python3", str(ROOT / "repository-identicon.py"), "validate",
             "--", *self.port(body)],
            capture_output=True, text=True, timeout=120)
        self.assertEqual(1, completed.returncode, completed.stdout)


class TestTheTwoFilesAreAPair(unittest.TestCase):
    """repository-identicon.py needs text-identicon.py for every text style.

    `emit` swallows everything so a hook can never break a turn, which is what
    would turn a missing sibling into a silent one. So the loader names the file
    in its error and `doctor` reports it either way -- both checked against a
    copy deployed alone, since in the tree the sibling is always there.
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

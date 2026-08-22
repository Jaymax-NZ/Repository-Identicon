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
    spec = importlib.util.spec_from_file_location(module, ROOT / name)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


identicon = load("repository-identicon.py", "repository_identicon")
text_identicon = load("text-identicon.py", "text_identicon")
document = json.loads(VECTORS.read_text())
vectors = document["vectors"]


class TestTheVectorsThemselves(unittest.TestCase):

    def test_there_are_some(self):
        self.assertTrue(vectors, "vectors.json is empty")

    def test_the_version_this_implementation_seeds_at_is_pinned(self):
        """A bump that brings no vectors is a bump nothing checks."""
        covered = {identicon.parse_key(v["key"])[0] for v in vectors}
        self.assertIn(identicon.MAPPING_VERSION, covered)

    def test_the_mapping_that_predates_the_version_is_still_pinned(self):
        """Unstamped keys are out there and the file is what wins, so they must
        keep drawing what they always drew. Dropping these vectors is how that
        promise would be broken without anyone noticing."""
        covered = {identicon.parse_key(v["key"])[0] for v in vectors}
        self.assertIn(0, covered)

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

    def test_the_same_seed_at_two_versions_draws_two_marks(self):
        """The whole mechanism in one assertion: change the version and the
        mark moves; that is why the version has to be a reviewed line."""
        by_seed = {}
        for vector in vectors:
            version, seed = identicon.parse_key(vector["key"])
            by_seed.setdefault(seed, {})[version] = vector["md5"]
        shared = [d for d in by_seed.values() if len(d) > 1]
        self.assertTrue(shared, "no seed is pinned at more than one version")
        for digests in shared:
            self.assertEqual(len(digests), len(set(digests.values())))


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
        self.assertEqual(document, json.loads(result.stdout))


class TestTheBlocksAndTheCanvas(unittest.TestCase):
    """The block is specified; the canvas is derived.

    `@4x` multiplies the block by four and the border by two -- the border is
    chrome, so quadrupling it would spend the new pixels on empty edge. That
    makes the 4x a magnification of the *mark*, not of the whole canvas, which
    is the distinction the two assertions below pin.
    """

    KEY = "1:github.com/someone/a-project"

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
        """Stated as a test because it is the one part of `@4x` that is not a
        magnification, and it would otherwise look like a bug."""
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
                self.assertLessEqual(block * identicon.GRID, edge)
                png = identicon.render_png(self.KEY, block, edge=edge)
                self.assertEqual((edge, edge),
                                 struct.unpack(">II", png[16:24]))


class TestTheLargeCanvasesAndTheDarkVariant(unittest.TestCase):
    """Sizes a consumer fixes, and a mark that survives the ground it lands on."""

    KEY = "1:github.com/someone/a-project"

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

    def test_every_large_canvas_is_exact(self):
        """No fitting, no padding, no heuristic: the same rule as block 1."""
        for canvas in identicon.LARGE_CANVASES:
            with self.subTest(canvas=canvas):
                block, border = identicon.large_geometry(canvas)
                self.assertEqual(canvas, identicon.canvas_edge(block, border))
                self.assertAlmostEqual(border / canvas, 1 / 32)

    def test_a_canvas_with_no_exact_geometry_is_refused(self):
        """16 and 48 cannot carry a proportional border on a five-block grid,
        so they are an error rather than a silently fat one."""
        for canvas in (16, 48, 100):
            with self.subTest(canvas=canvas):
                with self.assertRaises(ValueError):
                    identicon.large_geometry(canvas)

    def test_the_variants_differ_in_lightness_alone(self):
        """Hue is the identity, lightness is presentation, and the variants
        must order themselves darkest to lightest or they are not a set."""
        seen = [identicon.identicon_colour(self.KEY, lightness=lightness)
                for _, lightness in identicon.VARIANTS]
        self.assertEqual(len(seen), len(set(seen)))
        base, light, dark = seen
        self.assertLess(self.luminance(light), self.luminance(base))
        self.assertGreater(self.luminance(dark), self.luminance(base))

    def test_base_is_the_reference_lightness_untouched(self):
        """`-base` exists to be exactly what the reference produces. If it
        drifts, the name is a lie and vectors.json disagrees with a file."""
        self.assertEqual(("-base", identicon.LIGHTNESS), identicon.VARIANTS[0])
        self.assertEqual(0.5, identicon.LIGHTNESS)

    def test_the_dark_lightness_clears_every_hue_on_every_dark_ground(self):
        """The reason the constant has the value it has. If somebody lowers it,
        this says which repositories go illegible."""
        grounds = ((13, 17, 23), (30, 30, 30), (34, 39, 46), (0, 0, 0))
        for degrees in range(0, 360, 5):
            red, green, blue = identicon._hsl_to_rgb(
                degrees / 360, identicon.SATURATION,
                dict(identicon.VARIANTS)["-dark"])
            mark = tuple(identicon._quantise(v) for v in (red, green, blue))
            for ground in grounds:
                with self.subTest(hue=degrees, ground=ground):
                    self.assertGreaterEqual(self.contrast(mark, ground), 4.5)

    def test_the_light_mark_is_the_reference_lightness(self):
        """Whatever the dark variant does, conformance is about the light one:
        vectors.json pins 0.5 and this must not drift off it."""
        self.assertEqual(0.5, identicon.LIGHTNESS)

    def test_the_light_variant_is_darker_without_clearing_the_wheel(self):
        """0.44 is a chosen compromise, not a threshold, and saying so here
        stops anybody reading the file as an accessibility guarantee."""
        light = dict(identicon.VARIANTS)["-light"]
        white = (255, 255, 255)
        failing = sum(
            1 for degrees in range(0, 360, 5)
            if self.contrast(
                tuple(identicon._quantise(v) for v in identicon._hsl_to_rgb(
                    degrees / 360, identicon.SATURATION, light)), white) < 3.0)
        self.assertGreater(failing, 0, "0.44 is not claimed to clear 3.0:1")
        self.assertLess(light, identicon.LIGHTNESS)

    def test_names_and_bytes_cannot_disagree(self):
        """Both sides walk one list, so an artifact with a path and no content
        -- or content and no path -- is impossible rather than unlikely."""
        paths = identicon.artifact_paths("/nowhere")
        wanted = identicon.artifact_bytes(self.KEY)
        self.assertEqual(set(paths), set(wanted))

    def test_every_rendered_artifact_has_all_three_variants(self):
        wanted = identicon.artifact_bytes(self.KEY)
        suffixes = [suffix for suffix, _ in identicon.VARIANTS]
        stems = {n[:-len(suffixes[0])] for n in wanted if n.endswith(suffixes[0])}
        self.assertTrue(stems)
        for stem in stems:
            bodies = [wanted[stem + suffix] for suffix in suffixes]
            for suffix in suffixes:
                self.assertIn(stem + suffix, wanted)
            self.assertEqual(len(bodies), len(set(bodies)),
                             f"{stem} does not differ across all three")

    def test_there_is_exactly_one_colour_file(self):
        """The mark has one colour. The variants are how it survives a ground,
        not three identities, and `cat` has to stay the whole integration."""
        wanted = identicon.artifact_bytes(self.KEY)
        self.assertIn("colour", wanted)
        self.assertEqual([n for n in wanted if n.startswith("colour")], ["colour"])
        expected = identicon.hex_colour(
            identicon.identicon_colour(self.KEY, lightness=identicon.LIGHTNESS))
        self.assertEqual(expected + "\n", wanted["colour"].decode())

    def test_the_large_pngs_declare_their_canvas(self):
        wanted = identicon.artifact_bytes(self.KEY)
        for canvas in identicon.LARGE_CANVASES:
            for suffix, _ in identicon.VARIANTS:
                with self.subTest(canvas=canvas, variant=suffix or "light"):
                    png = wanted[f"png{canvas}{suffix}"]
                    self.assertEqual((canvas, canvas),
                                     struct.unpack(">II", png[16:24]))


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
        self.assertEqual("github.com/someone/a-project", result["seed"])
        self.assertEqual("1:github.com/someone/a-project", result["key"])
        self.assertEqual("remote", result["source"])
        for name in ("png-base", "png4x-base", "svg-base", "colour"):
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

        for name in ("png-base", "svg-base", "colour", "key"):
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
        for name in ("png-base", "svg-base", "colour", "key"):
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
        self.assertEqual("updated", after["changes"]["png-base"])

    def test_reseed_is_the_only_thing_that_changes_the_mark(self):
        before = identicon.install_into_repo(self.tmp)
        self._rename_remote()
        after = identicon.install_into_repo(self.tmp, reseed=True)
        self.assertEqual("github.com/someone/renamed", after["seed"])
        self.assertNotEqual(before["colour"], after["colour"])
        self.assertEqual("1:github.com/someone/renamed",
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
        self.assertEqual("created", result["changes"]["png-base"])

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

    def test_an_unstamped_repository_keeps_its_old_mark(self):
        """The end-to-end version of the promise: an existing repository that
        predates all of this is not moved by running today's tool."""
        self.write_key(self.SEED)
        result = identicon.install_into_repo(self.tmp, readme=False)

        self.assertEqual(self.SEED, result["key"])
        self.assertEqual(0, result["mapping_version"])
        self.assertEqual("key", result["source"])
        self.assertEqual("unchanged", result["changes"]["key"])

        pinned = [v for v in vectors if v["key"] == self.SEED]
        if pinned:
            self.assertEqual(pinned[0]["foreground"], result["colour"])

    def test_the_key_file_is_left_byte_for_byte_alone(self):
        """Including a preamble somebody edited. A run that rewrites this file
        under you makes every run a diff, and this file's job is to be the
        thing that does not move."""
        path = self.write_key(self.SEED, preamble="# mine, do not touch\n")
        before = path.read_bytes()
        identicon.install_into_repo(self.tmp, readme=False)
        self.assertEqual(before, path.read_bytes())

    def test_a_newer_mapping_does_not_reach_a_seeded_repository(self):
        """The mechanism, stated as a test: bumping the constant moves nobody.
        It is reported as drift, and drift is never acted on."""
        first = identicon.install_into_repo(self.tmp, readme=False)
        self.assertEqual(identicon.MAPPING_VERSION, first["mapping_version"])
        self.assertIsNone(first["mapping_drift"])

        with mock.patch.object(identicon, "MAPPING_VERSION",
                               identicon.MAPPING_VERSION + 1):
            after = identicon.install_into_repo(self.tmp, readme=False)
            self.assertEqual(first["key"], after["key"])
            self.assertEqual(first["colour"], after["colour"])
            self.assertTrue(after["current"])
            self.assertEqual(identicon.MAPPING_VERSION, after["mapping_drift"])

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
        """`show` looked its source up in a table that had never been told
        about the recorded key, so it crashed in every seeded repository --
        which is all of them after the first run. Nothing exercised the command
        end to end, so nothing caught it."""
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


class TestTheValidatorOfferedToPorts(unittest.TestCase):
    """The check this repository offers outward, rather than reaching inward.

    A port in another language cannot run this suite, so `validate` runs the
    port instead and compares it to the vectors. These tests stand in for a
    port with a fake one, because the thing under test is the validator.
    """

    GOOD = ('import json, sys\n'
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
        results = self.run_validate(self.port(self.GOOD))
        self.assertEqual(len(vectors), len(results))
        for result in results:
            with self.subTest(key=result["key"]):
                self.assertEqual([], result["problems"])

    def test_a_wrong_colour_fails_and_says_which_key(self):
        body = self.GOOD.replace('hit["foreground"]', '"#010203"')
        failed = [r for r in self.run_validate(self.port(body)) if r["problems"]]
        self.assertEqual(len(vectors), len(failed))
        self.assertIn("#010203", failed[0]["problems"][0])

    def test_a_wrong_grid_fails(self):
        body = self.GOOD.replace('hit["grid"]', '["00000"] * 5')
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
                body = self.GOOD.replace('hit["grid"]', shape)
                results = self.run_validate(self.port(body))
                self.assertEqual([], results[0]["problems"])

    def test_the_command_line_exits_1_when_a_port_disagrees(self):
        body = self.GOOD.replace('hit["foreground"]', '"#010203"')
        completed = subprocess.run(
            ["python3", str(ROOT / "repository-identicon.py"), "validate",
             "--", *self.port(body)],
            capture_output=True, text=True, timeout=120)
        self.assertEqual(1, completed.returncode, completed.stdout)


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

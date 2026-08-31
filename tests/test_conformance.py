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
import re
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


def pinned_colour_maps():
    """The colour maps the committed vectors cover."""
    return {v["colourMap"] for v in vectors}


# A colour map this build does not draw, for the tests that need one.
FOREIGN_COLOUR_MAP = 999


# ---- The vectors and the implementation ----

class TestTheVectorsThemselves(unittest.TestCase):

    def test_there_are_some(self):
        self.assertTrue(vectors, "vectors.json is empty")

    def test_the_colour_map_this_implementation_draws_is_pinned(self):
        """A new map that brings no vectors is a map nothing checks."""
        self.assertIn(identicon.COLOUR_MAP_LATEST, pinned_colour_maps())

    def test_only_the_colour_map_this_implementation_draws_is_pinned(self):
        """One map, so one number. A retired map leaves with its vectors --
        a vector nothing can draw is a vector nothing checks."""
        self.assertEqual({identicon.COLOUR_MAP_LATEST}, pinned_colour_maps())

    def test_each_carries_everything_needed_to_check_an_implementation(self):
        for vector in vectors:
            for field in ("seed", "colourMap", "md5", "grid", "foreground"):
                self.assertIn(field, vector)
            self.assertEqual(5, len(vector["grid"]),
                             f"{vector['seed']}: the grid is not five rows")
            for row in vector["grid"]:
                self.assertRegex(row, r"^[01]{5}$")

    def test_no_two_vectors_share_a_seed(self):
        seeds = [vector["seed"] for vector in vectors]
        self.assertEqual(len(seeds), len(set(seeds)), "two vectors share a seed")

    def test_the_colour_map_is_outside_what_gets_hashed(self):
        """The whole point of taking it out of the digest: a repository's
        shape is fixed by its seed, and no colour map can move it. The grid
        never sees the number, so there is nothing to pass and nothing to
        change."""
        for vector in vectors:
            with self.subTest(seed=vector["seed"]):
                self.assertEqual(
                    vector["grid"],
                    identicon.grid_text(
                        identicon.identicon_grid(vector["seed"])).split("\n"),
                    f"{vector['seed']}: the grid moved")

    def test_the_case_of_a_seed_is_part_of_it(self):
        """Two spellings of one project name, pinned as separate vectors. A
        port that case-folds before hashing fails here rather than in the
        wild, which is why the pair is in the file."""
        pair = [v for v in vectors
                if v["seed"].lower() == "jaymax-nz/repository-identicon"]
        self.assertEqual(2, len(pair),
                         "the case pair is missing from vectors.json")
        self.assertNotEqual(pair[0]["md5"], pair[1]["md5"])


class TestTheImplementationConforms(unittest.TestCase):
    """One test per property the specification fixes.

    Failures here mean the implementation and the vectors disagree, and the
    vectors are the ones generated from the reference library -- so the
    implementation is what moved.
    """

    def test_the_digest_matches(self):
        for vector in vectors:
            with self.subTest(seed=vector["seed"]):
                self.assertEqual(vector["md5"],
                                 identicon._digest(vector["seed"]))

    def test_the_grid_matches(self):
        for vector in vectors:
            with self.subTest(seed=vector["seed"]):
                rows = ["".join("1" if cell else "0" for cell in row)
                        for row in identicon.identicon_grid(vector["seed"])]
                self.assertEqual(vector["grid"], rows)

    def test_the_colour_matches(self):
        """Including the rounding rule. Half up, not half to even -- the one
        place a reimplementation in another language silently diverges."""
        for vector in vectors:
            with self.subTest(seed=vector["seed"]):
                self.assertEqual(
                    vector["foreground"],
                    identicon.hex_colour(
                        identicon.identicon_colour(vector["seed"])))


# ---- Remotes and text rendering ----

class TestRemoteNormalisation(unittest.TestCase):
    """Every spelling of one repository must derive one seed, or an SSH
    checkout and an HTTPS checkout of the same project get different marks."""

    EXPECTED = "Owner/Repo"
    SPELLINGS = (
        "https://github.com/Owner/Repo.git",
        "https://github.com/Owner/Repo",
        "https://github.com/Owner/Repo/",
        "https://token@github.com/Owner/Repo.git",
        "https://user:pass@github.com/Owner/Repo.git",
        "git@github.com:Owner/Repo.git",
        "git@github.com:Owner/Repo",
        "ssh://git@github.com/Owner/Repo.git",
        "ssh://git@github.com:2222/Owner/Repo.git",
        "git://github.com/Owner/Repo.git",
    )

    def test_every_spelling_in_the_specification_derives_one_seed(self):
        for url in self.SPELLINGS:
            with self.subTest(url=url):
                self.assertEqual(self.EXPECTED, identicon.extract_repository_name(url))

    def test_a_local_path_remote_is_refused(self):
        """It is no more portable than the working directory, so it earns no
        special treatment and must fall through to a path-shaped source."""
        for url in ("/srv/git/repo.git", "file:///srv/git/repo.git", "", None):
            with self.subTest(url=url):
                self.assertIsNone(identicon.extract_repository_name(url))

    def test_the_host_is_dropped_so_a_move_between_forges_keeps_the_mark(self):
        """The seed names the project, not where it is hosted. Two projects
        that genuinely share an owner and name across forges write their own
        seed into settings.json."""
        self.assertEqual(identicon.extract_repository_name("git@github.com:a/b"),
                         identicon.extract_repository_name("git@gitlab.com:a/b"))

    def test_the_case_of_the_remote_is_carried_through(self):
        """`normalise_seed` strips and never folds. The seed is hashed as the
        file spells it, so a port needs no Unicode case mapping to conform."""
        self.assertEqual("Owner/Repo",
                         identicon.extract_repository_name("git@github.com:Owner/Repo.git"))
        self.assertNotEqual(identicon.extract_repository_name("git@github.com:Owner/Repo"),
                            identicon.extract_repository_name("git@github.com:owner/repo"))


class TestTheOneNormaliser(unittest.TestCase):
    """Whatever ends up in the seed field goes through one function, whether
    this tool derived it or somebody typed it."""

    def test_it_strips_whitespace_and_a_trailing_separator(self):
        for written, wanted in ((" Owner/Repo ", "Owner/Repo"),
                                ("Owner/Repo/", "Owner/Repo"),
                                ("\tOwner/Repo\n", "Owner/Repo"),
                                ("/opt/checkouts/Thing/", "/opt/checkouts/Thing")):
            with self.subTest(written=written):
                self.assertEqual(wanted, identicon.normalise_seed(written))

    def test_it_leaves_case_alone(self):
        self.assertEqual("Jaymax-NZ/Repository-Identicon",
                         identicon.normalise_seed("Jaymax-NZ/Repository-Identicon"))

    def test_a_hand_written_seed_is_normalised_like_a_derived_one(self):
        """Rule 16: hand-editing the seed is supported, so the same rules
        reach it."""
        with tempfile.TemporaryDirectory() as tmp:
            settings = pathlib.Path(tmp) / identicon.IDENTICON_DIR / "settings.json"
            settings.parent.mkdir(parents=True)
            settings.write_text(json.dumps({"identiconSeed": "  Hand/Typed/ "}))
            self.assertEqual("Hand/Typed",
                             identicon.identicon_seed(identicon.read_settings(tmp)))


class TestTheTextRendering(unittest.TestCase):

    def test_it_renders_two_lines_for_every_vector(self):
        for vector in vectors:
            with self.subTest(seed=vector["seed"]):
                grid = identicon.identicon_grid(vector["seed"])
                colour = identicon.identicon_colour(vector["seed"])
                lines = text_identicon.text(grid, colour).split("\n")
                self.assertEqual(2, len(lines))

    def test_both_lattices_hold_the_whole_grid(self):
        """Neither lattice is a reduced version of the other. That is what
        makes the choice between them the host's and not the mark's, so it is
        checked on the pinned seeds rather than asserted in prose."""
        for vector in vectors:
            grid = identicon.identicon_grid(vector["seed"])
            for name, draw in (("sextant", text_identicon.sextant),
                               ("octant", text_identicon.octant)):
                with self.subTest(seed=vector["seed"], lattice=name):
                    lines = draw(grid)
                    self.assertEqual(2, len(lines))
                    self.assertEqual(
                        grid,
                        text_identicon._recover(lines, getattr(
                            text_identicon, f"{name.upper()}_LATTICE")))

    def test_its_own_selftest_passes(self):
        """It re-derives both tables -- 230 octants and 60 sextants -- from the
        Unicode database, which is the only way they are checkable at all."""
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
            ["node", str(REFERENCE), *[v["seed"] for v in vectors]],
            capture_output=True, text=True, cwd=str(ROOT / "reference"), timeout=60)
        self.assertEqual(0, result.returncode, result.stderr)

        # The library pins the pattern. The colour is this project's own rule,
        # which the library cannot produce and has no opinion about, so it is
        # checked against the implementation instead.
        produced = json.loads(result.stdout)["vectors"]
        self.assertEqual([v["seed"] for v in vectors],
                         [v["seed"] for v in produced])
        for pinned, made in zip(vectors, produced):
            with self.subTest(seed=pinned["seed"]):
                self.assertEqual(pinned["md5"], made["md5"])
                self.assertEqual(pinned["grid"], made["grid"])
                self.assertNotIn("foreground", made)
                self.assertEqual(
                    pinned["foreground"],
                    identicon.hex_colour(
                        identicon.identicon_colour(pinned["seed"])))


# ---- Geometry and colour ----

class TestTheBlocksAndTheCanvas(unittest.TestCase):
    """The block is specified; the canvas is derived.

    `@4x` multiplies the block by four and the border by two: the border is
    chrome, so quadrupling it would spend the new pixels on empty edge. The 4x
    magnifies the *mark*, not the canvas.
    """

    # Any key; a literal one because nothing here asserts a version-dependent value.
    SEED = "someone/a-project"

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
                one = identicon.render_rgba(self.SEED, block)
                many = identicon.render_rgba(self.SEED, block * scale,
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
                png = identicon.render_png(self.SEED, block)
                edge = identicon.canvas_edge(block, identicon.BORDER)
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
        wanted = identicon.artifact_bytes(self.SEED)
        for canvas in identicon.LARGE_CANVASES:
            with self.subTest(canvas=canvas):
                self.assertEqual((canvas, canvas),
                                 struct.unpack(">II", wanted[f"png{canvas}"][16:24]))


class TestTheColourRule(unittest.TestCase):
    """One brightness across the wheel, so one file serves both grounds."""

    SEED = "someone/a-project"

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

    def test_a_colour_map_this_build_does_not_have_is_refused(self):
        """Drawing it with the only map there is would produce a mark that
        settings.json does not describe. There is one map, so this reaches a
        repository only through a hand edit."""
        for colour_map in (FOREIGN_COLOUR_MAP, 1, -1):
            with self.subTest(colour_map=colour_map):
                with self.assertRaises(identicon.UnknownColourMap):
                    identicon.identicon_colour(self.SEED, colour_map=colour_map)

    def test_the_colour_map_cannot_reach_the_grid(self):
        """`identicon_grid` takes a seed and nothing else. There is no
        parameter to pass a colour map through, which is the mechanical
        guarantee that a new map repaints and never reshapes."""
        import inspect
        parameters = inspect.signature(identicon.identicon_grid).parameters
        self.assertEqual(["seed"], list(parameters))

    def test_there_is_one_of_each(self):
        """One file per artifact -- what one brightness across the wheel buys."""
        wanted = identicon.artifact_bytes(self.SEED)
        for name in ("png", "png4x", "png128", "png256", "svg", "colour",
                     "grid", "tricolour", "sextant", "octant", "txt"):
            self.assertIn(name, wanted)
        self.assertEqual(11, len(wanted))


class TestTheArtifactSet(unittest.TestCase):
    """One list of names feeds both the paths and the bytes."""

    # Any key; a literal one because nothing here asserts a version-dependent value.
    SEED = "someone/a-project"

    def test_names_and_bytes_cannot_disagree(self):
        self.assertEqual(set(identicon.artifact_paths("/nowhere")),
                         set(identicon.artifact_bytes(self.SEED)))


# ---- Installing into a repository ----

class TestTheDocumentsAndTheCodeAgreeOnTheArtifacts(unittest.TestCase):
    """Every file the specification lists is one the installer writes.

    **This exists because `.txt` was documented and never written.**
    `text-identicon.py` is named for that artifact, its docstring says "the
    artifact is .txt", a day went into the rendering, and nothing put it in a
    repository. A tidy-up pass looked for unused imports and dead constants
    and found nothing wrong, because nothing *was* wrong internally: the code
    was consistent with itself and incomplete against its own documents.

    Reading for dead code and reading for missing output are different
    audits. This is the second one, and a machine can do it.
    """

    def documented(self, path):
        """Every artifact filename the document names, taken whole.

        Whole filenames, not the extension: `@4x.png`, `-128.png` and
        `-256.png` all end in `.png`, so an extension-only comparison passes
        while three of the four rasters go undocumented.
        """
        body = (ROOT / path).read_text(encoding="utf-8")
        return set(re.findall(
            r"\.identicon/(repository-identicon[A-Za-z0-9@-]*\.[a-z0-9]+)",
            body))

    def produced(self):
        """The artifacts. `settings.json` is an input and is not among them,
        so it is matched separately by the two tests below."""
        return {filename for _, filename in identicon.artifact_names()}

    def test_spec_lists_exactly_what_is_written(self):
        self.assertEqual(self.produced(), self.documented("SPEC.md"))

    def test_the_readme_lists_exactly_what_is_written(self):
        self.assertEqual(self.produced(), self.documented("README.md"))

    def test_both_documents_name_the_settings_file(self):
        """It is the only input to a repository's identity, so a document that
        does not name it leaves the reader nowhere to look."""
        for document in ("SPEC.md", "README.md"):
            with self.subTest(document=document):
                body = (ROOT / document).read_text(encoding="utf-8")
                self.assertIn(f".identicon/{identicon.SETTINGS_NAME}", body)
                self.assertIn(identicon.SEED_FIELD, body)

    def test_every_artifact_has_content_derived_from_the_seed(self):
        """Not a placeholder, not empty, and different for a different seed.

        The two seeds are pinned vectors rather than invented ones. The
        tricolour is three emoji chosen from a palette of sixty, so two
        arbitrary seeds can land on the same triple and fail this for a
        reason that is not a defect.
        """
        one = identicon.artifact_bytes(vectors[0]["seed"])
        two = identicon.artifact_bytes(vectors[6]["seed"])
        for name, body in one.items():
            with self.subTest(artifact=name):
                self.assertTrue(body, f"{name} is empty")
                self.assertNotEqual(body, two[name],
                                    f"{name} does not depend on the seed")


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

    def test_it_writes_every_artifact(self):
        result = identicon.install_into_repo(self.tmp)
        self.assertEqual("someone/a-project", result["identiconSeed"])
        self.assertEqual("derived from auto", result["source"])
        for name in ("png", "png4x", "svg", "colour", "grid", "tricolour",
                     "sextant", "octant", "txt"):
            with self.subTest(artifact=name):
                path = pathlib.Path(result["files"][name])
                self.assertTrue(path.is_file(), path)
                self.assertEqual("created", result["changes"][name])

    def test_the_txt_artifact_is_its_own_parts(self):
        """`.txt` composes `.sextant` and `.tricolour`, and a consumer that
        takes one part must get the same characters as one that takes the
        whole. Three files that can drift is what having them separately
        costs, so the composition is checked rather than described."""
        result = identicon.install_into_repo(self.tmp)
        read = lambda name: pathlib.Path(
            result["files"][name]).read_text(encoding="utf-8")
        sextant = read("sextant").rstrip("\n").split("\n")
        whole = read("txt").rstrip("\n").split("\n")
        self.assertEqual(sextant[0], whole[0])
        self.assertEqual(f"{sextant[1]} {read('tricolour').rstrip(chr(10))}",
                         whole[1])

    def test_both_lattices_are_written_and_differ(self):
        """The point of writing both: a host that has one set of glyphs and
        not the other still gets a mark."""
        result = identicon.install_into_repo(self.tmp)
        bodies = {}
        for name in ("sextant", "octant"):
            body = pathlib.Path(
                result["files"][name]).read_text(encoding="utf-8")
            self.assertEqual(2, len(body.rstrip("\n").split("\n")), name)
            bodies[name] = body
        self.assertNotEqual(bodies["sextant"], bodies["octant"])

    def test_the_text_artifact_is_the_text_rendering(self):
        """text-identicon.py is named for this file. Nothing wrote it until
        somebody asked why it was missing."""
        result = identicon.install_into_repo(self.tmp)
        body = pathlib.Path(result["files"]["txt"]).read_text(encoding="utf-8")
        expected = text_identicon.text(
            identicon.identicon_grid(result["identiconSeed"]),
            identicon.identicon_colour(result["identiconSeed"]))
        self.assertEqual(expected + "\n", body)

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
        after = identicon.install_into_repo(self.tmp, reseed="repo",
                                            readme=False)
        self.assertNotEqual(before["colour"], after["colour"])

        # The settings file is an input, not an artifact, so it is not among
        # the files a run keeps a prior copy of.
        for name in ("png", "svg", "colour"):
            with self.subTest(artifact=name):
                kept = identicon.prior_path(after["files"][name])
                self.assertTrue(kept.is_file(), kept)
        colour = identicon.prior_path(after["files"]["colour"])
        self.assertEqual(before["colour"], colour.read_text().strip())
        self.assertFalse(identicon.prior_path(after["files"]["settings"]).exists())
        self.assertEqual(before["identiconSeed"], "someone/a-project")

    def test_nothing_is_kept_when_nothing_is_replaced(self):
        result = identicon.install_into_repo(self.tmp, readme=False)
        for name in ("png", "svg", "colour", "settings"):
            with self.subTest(artifact=name):
                self.assertFalse(
                    identicon.prior_path(result["files"][name]).exists())

    def test_check_keeps_nothing_because_it_replaces_nothing(self):
        identicon.install_into_repo(self.tmp, readme=False)
        self._rename_remote()
        result = identicon.install_into_repo(self.tmp, reseed="repo",
                                             readme=False, check=True)
        self.assertFalse(
            identicon.prior_path(result["files"]["colour"]).exists())

    def test_the_seed_is_written_on_the_first_run(self):
        """The seed by itself, because the seed by itself is what gets
        hashed."""
        result = identicon.install_into_repo(self.tmp)
        self.assertEqual("derived from auto", result["source"])
        self.assertEqual(result["identiconSeed"],
                         identicon.identicon_seed(identicon.read_settings(self.tmp)))
        self.assertEqual(identicon.COLOUR_MAP_LATEST, result["colourMap"])

    def test_a_rename_does_not_change_the_mark(self):
        """The whole point of an identity: it does not re-derive itself."""
        before = identicon.install_into_repo(self.tmp)
        self._rename_remote()
        after = identicon.install_into_repo(self.tmp)
        self.assertEqual(before["identiconSeed"], after["identiconSeed"])
        self.assertEqual(before["colour"], after["colour"])
        self.assertEqual("settings", after["source"])
        self.assertTrue(after["current"])

    def test_artifacts_refresh_without_touching_the_seed(self):
        """A better renderer or a different block must reach every repository
        without disturbing anybody's identity."""
        before = identicon.install_into_repo(self.tmp)
        self._rename_remote()
        after = identicon.install_into_repo(self.tmp, block=3)
        self.assertEqual(before["identiconSeed"], after["identiconSeed"])
        self.assertEqual("unchanged", after["changes"]["settings"])
        self.assertEqual("updated", after["changes"]["png"])

    def test_reseed_is_the_only_thing_that_changes_the_mark(self):
        before = identicon.install_into_repo(self.tmp)
        self._rename_remote()
        after = identicon.install_into_repo(self.tmp, reseed="repo")
        self.assertEqual("someone/renamed", after["identiconSeed"])
        self.assertNotEqual(before["colour"], after["colour"])
        self.assertEqual("someone/renamed",
                         identicon.identicon_seed(identicon.read_settings(self.tmp)))
        self.assertEqual([before["identiconSeed"]],
                         after["identiconSeedHistory"])

    def test_a_literal_seed_is_recorded_like_any_other(self):
        """`--seed` supplies one outright, and is a reseed: the seed it
        replaces goes to the history like every other."""
        before = identicon.install_into_repo(self.tmp)
        after = identicon.install_into_repo(self.tmp, seed="chosen/by-hand")
        self.assertEqual("chosen/by-hand", after["identiconSeed"])
        self.assertEqual("explicit", after["source"])
        self.assertEqual([before["identiconSeed"]],
                         after["identiconSeedHistory"])
        self.assertEqual("chosen/by-hand",
                         identicon.identicon_seed(identicon.read_settings(self.tmp)))

    def test_git_helpers_accept_a_default_cwd(self):
        """`git -C None` fails and reads as "not a repository", which is the
        wrong answer in the direction that looks right."""
        original = os.getcwd()
        os.chdir(self.tmp)
        self.addCleanup(os.chdir, original)
        self.assertEqual("someone/a-project",
                         identicon.extract_repository_name(
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


# ---- The settings file ----

class TestTheSettingsFile(unittest.TestCase):
    """`.identicon/settings.json` is the only input to a repository's identity.

    The seed is derived once, written, and read on every run after that. No
    second file can disagree with it, and no derivation outranks it.
    """

    SEED = "someone/a-project"

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        subprocess.run(["git", "init", "-q", self.tmp], check=True, timeout=30)
        self.set_remote(self.SEED)

    def set_remote(self, seed):
        subprocess.run(["git", "-C", self.tmp, "remote", "remove", "origin"],
                       capture_output=True, timeout=30)
        subprocess.run(["git", "-C", self.tmp, "remote", "add", "origin",
                        f"https://github.com/{seed}.git"], check=True, timeout=30)

    def settings(self):
        return json.loads(identicon.settings_path(self.tmp).read_text())

    def test_the_seed_is_written_on_the_first_run(self):
        result = identicon.install_into_repo(self.tmp, readme=False)
        self.assertEqual(self.SEED, result["identiconSeed"])
        self.assertEqual("derived from auto", result["source"])
        self.assertEqual(self.SEED, self.settings()["identiconSeed"])
        self.assertEqual(identicon.COLOUR_MAP_LATEST,
                         self.settings()["colourMap"])

    def test_the_second_run_reads_rather_than_derives(self):
        identicon.install_into_repo(self.tmp, readme=False)
        again = identicon.install_into_repo(self.tmp, readme=False)
        self.assertEqual("settings", again["source"])
        self.assertEqual("unchanged", again["changes"]["settings"])

    def test_reading_the_seed_runs_no_git(self):
        """The whole hidden-architecture defect, stated as a test. Derivation
        used to run on every command and be discarded whenever a key file
        existed. A seeded repository must not shell out to answer this."""
        identicon.install_into_repo(self.tmp, readme=False)
        with mock.patch.object(identicon, "_git") as never:
            self.assertEqual(self.SEED, identicon.identicon_seed(identicon.read_settings(self.tmp)))
        never.assert_not_called()

    def test_a_rename_does_not_change_the_mark(self):
        first = identicon.install_into_repo(self.tmp, readme=False)
        self.set_remote("someone/renamed")
        after = identicon.install_into_repo(self.tmp, readme=False)
        self.assertEqual(first["identiconSeed"], after["identiconSeed"])
        self.assertEqual(first["colour"], after["colour"])
        self.assertTrue(after["current"])

    def test_a_rename_is_not_reported_by_apply(self):
        """The mark not moving is the design, so `apply` has no subject to
        raise. `doctor` answers when asked, and that is where it belongs."""
        identicon.install_into_repo(self.tmp, readme=False)
        self.set_remote("someone/renamed")
        after = identicon.install_into_repo(self.tmp, readme=False)
        self.assertNotIn("seed_drift", after)
        self.assertNotIn("identiconSeedWouldDeriveAs", after)

    def test_doctor_reports_what_would_derive_when_asked(self):
        identicon.install_into_repo(self.tmp, readme=False)
        self.set_remote("someone/renamed")
        done = subprocess.run(
            ["python3", str(ROOT / "repository-identicon.py"), "doctor",
             self.tmp], capture_output=True, text=True, timeout=60)
        self.assertEqual(0, done.returncode, done.stderr)
        self.assertIn(self.SEED, done.stdout)
        self.assertIn("someone/renamed", done.stdout)

    def test_a_hand_written_seed_outranks_the_remote(self):
        path = identicon.settings_path(self.tmp)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"identiconSeed": "chosen/by-hand"}))
        result = identicon.install_into_repo(self.tmp, readme=False)
        self.assertEqual("chosen/by-hand", result["identiconSeed"])
        self.assertEqual("settings", result["source"])

    def test_an_unreadable_settings_file_is_repaired_rather_than_raised(self):
        path = identicon.settings_path(self.tmp)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{ this is not json")
        result = identicon.install_into_repo(self.tmp, readme=False)
        self.assertEqual(self.SEED, result["identiconSeed"])
        self.assertEqual(self.SEED, self.settings()["identiconSeed"])

    def test_a_colour_map_this_build_lacks_stops_the_run(self):
        path = identicon.settings_path(self.tmp)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"identiconSeed": self.SEED,
                                    "colourMap": FOREIGN_COLOUR_MAP}))
        with self.assertRaises(identicon.UnknownColourMap):
            identicon.install_into_repo(self.tmp, readme=False)

    # ---- reseeding ----

    def test_reseed_retires_the_current_seed_and_derives_a_new_one(self):
        identicon.install_into_repo(self.tmp, readme=False)
        self.set_remote("someone/renamed")
        after = identicon.install_into_repo(self.tmp, reseed="repo",
                                            readme=False)
        self.assertEqual("someone/renamed", after["identiconSeed"])
        self.assertEqual([self.SEED], after["identiconSeedHistory"])

    def test_the_history_is_most_recent_first(self):
        identicon.install_into_repo(self.tmp, readme=False)
        self.set_remote("someone/second")
        identicon.install_into_repo(self.tmp, reseed="repo", readme=False)
        self.set_remote("someone/third")
        after = identicon.install_into_repo(self.tmp, reseed="repo",
                                            readme=False)
        self.assertEqual(["someone/second", self.SEED],
                         after["identiconSeedHistory"])

    def test_blanking_the_seed_by_hand_is_the_same_as_reseeding(self):
        """Rule 4 is one rule applied to an emptied field, not a second way of
        setting one: `--reseed` blanks the seed and the ordinary path fills
        it. Somebody who blanks it in an editor gets the same outcome."""
        identicon.install_into_repo(self.tmp, readme=False)
        path = identicon.settings_path(self.tmp)
        settings = json.loads(path.read_text())
        settings["identiconSeed"] = ""
        path.write_text(json.dumps(settings))
        self.set_remote("someone/renamed")
        after = identicon.install_into_repo(self.tmp, readme=False)
        self.assertEqual("someone/renamed", after["identiconSeed"])

    def test_reseed_uuid_derives_from_nothing(self):
        identicon.install_into_repo(self.tmp, readme=False)
        after = identicon.install_into_repo(self.tmp, reseed="uuid",
                                            readme=False)
        self.assertRegex(after["identiconSeed"],
                         r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-"
                         r"[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
        self.assertEqual([self.SEED], after["identiconSeedHistory"])

    def test_reseed_path_uses_the_directory(self):
        identicon.install_into_repo(self.tmp, readme=False)
        after = identicon.install_into_repo(self.tmp, reseed="path",
                                            readme=False)
        self.assertEqual(identicon.path_seed(self.tmp), after["identiconSeed"])

    def test_a_named_source_that_cannot_answer_raises(self):
        """`--reseed repo` with no remote is a question with no answer.
        Falling back to the path would hand somebody a seed they did not ask
        for, which is the class of hidden behaviour this branch exists to
        remove."""
        bare = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, bare, ignore_errors=True)
        subprocess.run(["git", "init", "-q", bare], check=True, timeout=30)
        with self.assertRaises(ValueError) as caught:
            identicon.install_into_repo(bare, reseed="repo", readme=False)
        self.assertIn("no git remote", str(caught.exception))

    def test_an_unknown_source_raises(self):
        with self.assertRaises(ValueError):
            identicon.derive_identicon_seed(self.tmp, "telepathy")

    # ---- the read-only commands ----

    def test_the_read_only_commands_run_in_a_seeded_repository(self):
        """Only an end-to-end run catches this: `show` once looked its source
        up in a table that had never been told about the recorded key, so it
        crashed in every seeded repository -- which is all of them after the
        first run."""
        identicon.install_into_repo(self.tmp, readme=False)
        for command in (["show"], ["render", "--out", os.devnull],
                        ["doctor"]):
            with self.subTest(command=command[0]):
                done = subprocess.run(
                    ["python3", str(ROOT / "repository-identicon.py"),
                     *command, self.tmp],
                    capture_output=True, text=True, timeout=60)
                self.assertEqual(0, done.returncode, done.stderr)

    def test_show_draws_what_apply_wrote(self):
        """One resolver, so the read-only commands cannot report a mark the
        artifacts do not have."""
        applied = identicon.install_into_repo(self.tmp, readme=False)
        self.assertEqual(applied["identiconSeed"],
                         identicon.identicon_seed(identicon.read_settings(self.tmp)))


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
        'hit = [x for x in v["vectors"] if x["seed"] == k][0]\n'
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
            with self.subTest(seed=result["seed"]):
                self.assertEqual([], result["problems"])

    def test_a_wrong_colour_fails_and_says_which_seed(self):
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
    """repository-identicon.py needs text-identicon.py to write four artifacts.

    `.tricolour`, `.sextant`, `.octant` and `.txt` all come from the sibling, so
    a deployment missing it writes a partial `.identicon/` rather than failing
    outright. The loader names the file in its error and `doctor` reports it
    either way -- both checked against a copy deployed alone, since in the tree
    the sibling is always there.
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
        self.assertIn("cannot write the text artifacts", report)

    def test_the_loader_names_the_file_rather_than_failing_on_a_bare_path(self):
        spec = importlib.util.spec_from_file_location("alone", self.alone)
        alone = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(alone)
        with self.assertRaises(FileNotFoundError) as raised:
            alone._text_module()
        self.assertIn("text-identicon.py", str(raised.exception))


class TestScope(unittest.TestCase):
    """SPEC.md § Scope: a pure function from key to bytes, name or string is in;
    a side effect is out. Both halves are checked, because a rule only stated in
    prose is a rule that drifts."""

    def test_nothing_here_addresses_a_terminal(self):
        """These went to Console-Colophon with `emit`. An escape sequence is
        addressed to one terminal, and picking which one it can read is a
        decision about somebody's terminal, not about the mark."""
        for gone in ("render", "render_inline", "render_text", "render_banner",
                     "render_line", "iterm2_image", "kitty_image",
                     "resolve_protocol", "resolve_colour_depth", "_fg",
                     "_xterm256", "STYLES", "PROTOCOLS", "INLINE_SIZE"):
            self.assertFalse(hasattr(identicon, gone),
                             f"{gone} belongs to Console-Colophon")

    def test_nothing_here_registers_a_hook(self):
        """The Claude Code hook is gone entirely rather than moved: a hook
        registration writes to somebody's settings file, and Claude-Colophon
        shipped without one."""
        for gone in ("cmd_emit", "cmd_hooks", "payload_cwd", "open_output",
                     "RETURN_OF_CONTROL_EVENTS"):
            self.assertFalse(hasattr(identicon, gone), f"{gone} should be gone")
        source = (ROOT / "repository-identicon.py").read_text(encoding="utf-8")
        self.assertNotIn("/dev/tty", source)

    def test_the_commands_are_the_ones_the_readme_documents(self):
        """A subcommand that survives a split without being documented is how
        the last one grew three jobs."""
        completed = subprocess.run(
            ["python3", str(ROOT / "repository-identicon.py"), "--help"],
            capture_output=True, text=True, timeout=60)
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertIn("{apply,show,render,validate,doctor}", completed.stdout)

    def test_the_renderings_still_reach_a_file(self):
        """Losing the escape sequences must not lose the renderings. SPEC.md
        mandates them, so every one still has to arrive as bytes on disk."""
        wanted = identicon.artifact_bytes("someone/a-project")
        for name in ("png", "svg", "tricolour", "sextant", "octant", "txt"):
            self.assertIn(name, wanted)


if __name__ == "__main__":
    unittest.main()

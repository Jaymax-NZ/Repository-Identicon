"""Every artifact, byte for byte, against frozen fixtures.

**What this file owns, and what `vectors.json` owns.**

`vectors.json` pins the *mapping*: key to MD5 digest, digest to grid, digest to
foreground colour. It is the contract another implementation has to meet, and
it stops at the three values a reimplementation can compute without agreeing to
produce any particular file.

This file pins the *serialisation*: the exact bytes this implementation writes
into `.identicon/` for a given key. A port is not asked to reproduce these. The
reference implementation is, on every machine that runs it.

The two do not overlap. No key here appears in `vectors.json`, and a test
enforces that: a grid that changed would break the vectors, and a file layout
that changed breaks only these fixtures. Reading a failure is then unambiguous.
The mapping moved, or the writer did.

**Why the bytes and not their hashes.** A digest that disagrees says only that
something disagrees. `.txt`, `.grid`, `.svg` and the rest are text, and a
failing test prints the diff.

**Regenerating.** The command is:

    python3 tests/test_bytes.py --write

It rewrites every fixture file from the current code.

Running it is legitimate when the mapping version changes deliberately, or
when a seed in `FIXTURE_SEEDS` is deliberately changed or replaced. Those are
the two edits that change what the correct bytes are. Make the edit, run the
command, and review the diff.

Running it is not legitimate as a way to make a failing test pass. A failure
with `FIXTURE_MAPPING_VERSION` and `FIXTURE_SEEDS` untouched means the writer
changed, and reporting that is the whole purpose of this suite. Regenerating
then deletes the evidence rather than fixing anything.

The mapping version is written once, in `FIXTURE_MAPPING_VERSION`, and each
seed is written once, in `FIXTURE_SEEDS`. Nothing below repeats either, so a
version bump is a one-line edit and a regeneration.

    python3 -m unittest discover -s tests -t tests
"""

import importlib.util
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"


def load(name, module):
    """Import a script by path -- both are hyphen-named, so `import` cannot."""
    spec = importlib.util.spec_from_file_location(module, ROOT / name)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


identicon = load("repository-identicon.py", "repository_identicon")

# **The mapping version, written once.** Every fixture key is stamped with
# this and nothing below repeats the literal. Changing the mapping is then a
# one-line edit here plus a regeneration, and the assertion in
# `test_the_fixtures_are_stamped_at_the_version_this_build_draws` is what makes
# a bump announce itself instead of passing quietly.
FIXTURE_MAPPING_VERSION = "0.3"

# **Four seeds, each covering something the others do not.**
#
# Seeds, not keys: the version is added by `fixture_key`, so it lives in one
# place. The set is small on purpose. Every seed multiplies twelve files, and a
# fixture nobody can say the purpose of is a fixture nobody dares change.
#
# The colours named below are what these seeds produce at mapping version 0.3.
# A new mapping moves them, and the property each seed was chosen for is
# asserted in `test_the_seeds_cover_both_branches_of_the_chroma_rule` rather
# than left to these comments -- so a bump that costs the set its coverage
# fails rather than rots.
FIXTURE_SEEDS = (
    (
        "ordinary-remote",
        "github.com/octocat/hello-world",
        # The common case: `host/owner/repo`, lowercased, which is what
        # `normalise_remote_url` returns for an SSH or an HTTPS checkout of the
        # same project. Colour #df3f00, whose blue channel is 0.
        "a git remote, normalised",
    ),
    (
        "recorded-key-override",
        "my-local-project",
        # A bare name. `normalise_remote_url` returns None for a string with no
        # host and no path, so no git remote produces this seed: it can only
        # come from a committed `.repository-identicon` or from `--seed`. It is
        # also the one seed here whose colour reaches the chroma cap, so it
        # takes `gamut_chroma`'s early return while the other three run the
        # binary search. Colour #b335eb, no channel at 0 or 255.
        "a committed override, and the uncapped chroma branch",
    ),
    (
        "non-ascii-seed",
        "github.com/日本語/リポジトリ",
        # Every non-ASCII character here is three bytes of UTF-8. The fixtures
        # fail if the key is hashed as anything but UTF-8, and the `.key`
        # fixture fails if the file is written or read back in another
        # encoding. Colour #9e7b00.
        "a seed outside ASCII, three bytes per character",
    ),
    (
        "gamut-edge",
        "github.com/widgets-inc/quarry",
        # The most strongly clamped colour found in a scan of remote-shaped
        # seeds: `gamut_chroma` searches down to 0.1020 against a cap of 0.26,
        # and the red channel lands on exactly 0. Colour #009299.
        "a colour clamped hard onto the sRGB boundary",
    ),
)

# None of these seeds names a real account this project controls, so a forge
# rename moves the repository's own `.identicon/` and leaves the fixtures
# alone.


def fixture_key(seed):
    """The key a fixture seed is frozen under: the pinned version, then it."""
    return identicon.stamp_key(seed, FIXTURE_MAPPING_VERSION)


# `.key` is written by `install_into_repo`, not by `artifact_bytes`, so
# `expected_bytes` adds it. Twelve files per key.
#
# Artifacts compared as text, so a failure prints a diff. Everything else is
# compared as bytes and reported by length.
TEXT_SUFFIXES = (".key", ".grid", ".colour", ".octant", ".sextant",
                 ".tricolour", ".txt", ".svg")


def expected_bytes(key):
    """Every artifact for `key` as {filename: bytes}, the `.key` file included."""
    built = identicon.artifact_bytes(key)
    wanted = {filename: built[name]
              for name, filename in identicon.artifact_names()}
    wanted[identicon.KEY_NAME] = (
        identicon.KEY_FILE_TEMPLATE.format(key=key).encode("utf-8"))
    return wanted


def fixture_dir(slug):
    return FIXTURES / slug


class TestTheFixtureSet(unittest.TestCase):
    """The shape of the set, before any byte is compared."""

    def test_the_fixtures_are_stamped_at_the_version_this_build_draws(self):
        """A mapping bump moves every key, so it must land here as a failure.

        The way through is to change `FIXTURE_MAPPING_VERSION` and regenerate,
        which is a reviewed decision. See the module docstring.
        """
        self.assertEqual(
            FIXTURE_MAPPING_VERSION, identicon.MAPPING_VERSION,
            "the fixtures are frozen at a different mapping version than this "
            "build draws; see the regeneration note in the module docstring")

    def test_no_two_fixtures_share_a_seed_or_a_slug(self):
        slugs = [slug for slug, _seed, _reason in FIXTURE_SEEDS]
        seeds = [seed for _slug, seed, _reason in FIXTURE_SEEDS]
        self.assertEqual(len(slugs), len(set(slugs)))
        self.assertEqual(len(seeds), len(set(seeds)))

    def test_every_seed_says_why_it_is_here(self):
        for slug, _seed, reason in FIXTURE_SEEDS:
            with self.subTest(slug=slug):
                self.assertTrue(reason.strip(), f"{slug} has no reason")

    def test_the_fixtures_do_not_restate_the_vectors(self):
        """The boundary, enforced. `vectors.json` owns the mapping and this
        file owns the serialisation, so a key belongs to one or the other."""
        pinned = {vector["key"] for vector
                  in json.loads((ROOT / "vectors.json").read_text())["vectors"]}
        for slug, seed, _reason in FIXTURE_SEEDS:
            with self.subTest(slug=slug):
                self.assertNotIn(fixture_key(seed), pinned)

    def test_each_fixture_directory_holds_exactly_the_artifact_set(self):
        """A file that stopped being written must not linger as a fixture."""
        wanted = {filename for _name, filename in identicon.artifact_names()}
        wanted.add(identicon.KEY_NAME)
        for slug, _seed, _reason in FIXTURE_SEEDS:
            with self.subTest(slug=slug):
                directory = fixture_dir(slug)
                self.assertTrue(directory.is_dir(),
                                f"{directory} is missing; run --write")
                found = {path.name for path in directory.iterdir()}
                self.assertEqual(wanted, found)

    def test_the_seeds_cover_both_branches_of_the_chroma_rule(self):
        """One seed reaches the cap and at least one is clamped below it.

        The set would otherwise exercise the binary search only. A new mapping
        moves every colour, so this is the test that says whether the four
        seeds still earn their places or need reselecting.
        """
        chromas = []
        for _slug, seed, _reason in FIXTURE_SEEDS:
            key = fixture_key(seed)
            degrees = identicon.warp_hue(identicon.identicon_hue(key) * 360.0)
            chromas.append(identicon.gamut_chroma(degrees))
        cap = identicon.MARK_CHROMA
        self.assertTrue(any(value >= cap for value in chromas),
                        "no fixture seed reaches the chroma cap; reselect")
        self.assertTrue(any(value < cap for value in chromas),
                        "no fixture seed is clamped by the gamut; reselect")


class TestTheFrozenBytes(unittest.TestCase):
    """Regenerating every artifact must reproduce the committed fixture.

    This is the two-machine claim. The fixtures were written on one machine and
    CI runs on another; a difference in the PNG encoder, the SVG text, the
    lattices or the key file shows up here and nowhere else.
    """

    def test_every_artifact_matches_its_fixture(self):
        for slug, seed, _reason in FIXTURE_SEEDS:
            directory = fixture_dir(slug)
            wanted = expected_bytes(fixture_key(seed))
            for filename in sorted(wanted):
                with self.subTest(slug=slug, artifact=filename):
                    frozen = directory / filename
                    self.assertTrue(frozen.is_file(),
                                    f"{frozen} is missing; run --write")
                    committed = frozen.read_bytes()
                    built = wanted[filename]
                    if filename.endswith(TEXT_SUFFIXES):
                        self.assertEqual(committed.decode("utf-8"),
                                         built.decode("utf-8"))
                    else:
                        self.assertEqual(
                            committed, built,
                            f"{filename}: {len(committed)} bytes frozen, "
                            f"{len(built)} bytes built")

    def test_building_twice_gives_the_same_bytes(self):
        """Determinism within one process, which the fixtures assume and no
        comparison against a stored file can show."""
        for slug, seed, _reason in FIXTURE_SEEDS:
            with self.subTest(slug=slug):
                key = fixture_key(seed)
                self.assertEqual(expected_bytes(key), expected_bytes(key))


class TestThePngEncoderIsThisFilesOwn(unittest.TestCase):
    """The rasters must not depend on which deflate the platform linked.

    `zlib.compress` picks different matches under zlib-ng than under stock
    zlib at the same level, which is what made two of these files differ
    between a laptop and a runner. `_deflate` is written out in
    `repository-identicon.py` so the output depends on the input alone.
    """

    def test_the_stream_is_a_valid_zlib_stream(self):
        import zlib
        for case in (b"", b"a", bytes(range(256)) * 8, b"\x00" * 70000):
            with self.subTest(length=len(case)):
                self.assertEqual(
                    case, zlib.decompress(identicon._zlib_stream(case)))

    def test_the_rasters_decode_to_the_pixels_that_were_rendered(self):
        """The encoder is lossless: what comes back out is what went in."""
        import struct
        import zlib
        key = fixture_key(FIXTURE_SEEDS[0][1])
        for block, border in ((identicon.ARTIFACT_BLOCK, identicon.BORDER),
                              (identicon.ARTIFACT_BLOCK
                               * identicon.ARTIFACT_SCALE,
                               identicon.SCALED_BORDER)):
            with self.subTest(block=block):
                edge = identicon.canvas_edge(block, border)
                rgba = identicon.render_rgba(key, block, border=border)
                png = identicon.encode_png(rgba, edge, edge)
                idat = b""
                pos = 8
                while pos < len(png):
                    (length,) = struct.unpack(">I", png[pos:pos + 4])
                    if png[pos + 4:pos + 8] == b"IDAT":
                        idat += png[pos + 8:pos + 8 + length]
                    pos += 12 + length
                raw = zlib.decompress(idat)
                stride = edge * 4
                back = b"".join(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)]
                                for y in range(edge))
                self.assertEqual(rgba, back)

    def test_nothing_calls_zlib_compress(self):
        """The guard against the fix being undone by a tidy-up.

        Parsed rather than grepped, so the comment explaining why the call is
        gone does not read as the call coming back.
        """
        import ast
        tree = ast.parse((ROOT / "repository-identicon.py")
                         .read_text(encoding="utf-8"))
        called = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in ("compress", "compressobj")
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "zlib"
        ]
        self.assertEqual([], [node.lineno for node in called])


def write_fixtures():
    """Rewrite every fixture directory from the current code.

    **When running this is legitimate.** When the mapping version changes
    deliberately, or a seed in `FIXTURE_SEEDS` is deliberately changed or
    replaced. Both alter what the correct bytes are, and no stored file can
    know that; a person has to say so. Edit the constant or the table first,
    run this, and review the diff.

    **When it is not.** As a way to make a failing test pass. A failure with
    the version and the seeds untouched means the writer changed, which is the
    single thing this suite exists to report. Regenerating then does not fix
    it, it deletes the evidence.
    """
    for slug, seed, reason in FIXTURE_SEEDS:
        directory = fixture_dir(slug)
        directory.mkdir(parents=True, exist_ok=True)
        key = fixture_key(seed)
        wanted = expected_bytes(key)
        if directory.is_dir():
            for stale in directory.iterdir():
                if stale.name not in wanted:
                    stale.unlink()
        for filename, blob in sorted(wanted.items()):
            (directory / filename).write_bytes(blob)
        print(f"{slug:24} {len(wanted):2} files  {key}  ({reason})")


if __name__ == "__main__":
    if "--write" in sys.argv:
        write_fixtures()
    else:
        unittest.main()

#!/usr/bin/env python3
"""Reference implementation of the repository identicon specification.

A seed -- `owner/repo`, or a path where there is no remote -- becomes a 5x5
matrix and one colour, and then the eleven files a repository commits. The seed
is read from `.identicon/settings.json`, which is the only place a
repository's identity is written down; it is derived and written once, and
read on every run after that. Run `python3 repository-identicon.py apply`
inside a repository.

The seed alone is hashed. The colour map is a setting beside it and never
reaches the digest, so a better colour map repaints every mark and moves
none of them.

  apply     write .identicon/, and put the mark in the README
  show      the derived names and a preview
  render    one image, to a file or stdout
  validate  run another implementation against the pinned vectors
  doctor    what this depends on that is not in this file

**Nothing here writes outside the repository it is run in, and nothing here
addresses a terminal.** Putting the mark on a desktop or into an escape
sequence is a side effect, which SPEC.md's Scope section puts out of the
specification; that half lives in Console-Colophon and is reached by vendoring
this derivation, not by importing it. `work-in-progress/scope-split.md` records
where each routine went.

`text-identicon.py` must sit beside this file: four of the eleven artifacts --
`.tricolour`, `.sextant`, `.octant` and `.txt` -- come from its lattices and
emoji palette.

Standard library only. The only subprocess is git, invoked with an argument
list.
"""

import argparse
import hashlib
import json
import math
import os
import pathlib
import re
import struct
import subprocess
import sys
import uuid
import zlib

# ---- Identicon derivation ----
#
# GitHub-style: a 5x5 matrix, left three columns drawn from the digest and
# mirrored onto the right two, so every identicon is vertically symmetric.
# The rule below is ours and is pinned by the test suite; it is not claimed to
# reproduce GitHub's output byte for byte.

MATRIX_SIZE = 5

# The block sizes `--block` accepts. The canvas follows from the block, never
# the other way round; see `canvas_edge`.
BLOCKS = (1, 2, 3, 4, 5)
BORDER = 1
ARTIFACT_BLOCK = 5

# The 4x artifact multiplies the block by four and the border by two. The
# border is chrome rather than content, so quadrupling it would spend the new
# pixels on empty edge instead of on the mark.
ARTIFACT_SCALE = 4
SCALED_BORDER = 2

# **Canvases a consumer fixes rather than derives.** They need no fitting and
# no heuristic, because they come out of the same rule as everything else. For
# any canvas that is a multiple of 32,
#
#     block = 3 * canvas / 16      border = canvas / 32
#
# is exact, and the border is 3.1% of the canvas at every size -- near enough
# the 3.7% at block 5 that the mark reads the same across the whole range.
#
# 16 and 48 are deliberately absent. The block must match the canvas in parity,
# so the thinnest border they can carry is 18.8% and 8.3% -- several times the
# family ratio, which would make them look like different marks. Anything that
# needs those should take the SVG or downscale one of these.
LARGE_CANVASES = (128, 256)


def large_geometry(canvas):
    """The (block, border) for a canvas somebody else fixed. Exact or nothing."""
    block, border = 3 * canvas // 16, canvas // 32
    if MATRIX_SIZE * block + 2 * border != canvas:
        raise ValueError(f"{canvas} is not a multiple of 32 and has no exact "
                         f"block and border on a {MATRIX_SIZE}x{MATRIX_SIZE} matrix")
    return block, border


# ---- The seed ----
#
# Three functions, and the split between them is the point. `extract_repository_name` and
# `extract_repository_path` each turn one kind of thing into a candidate seed and do nothing
# else. `normalise_seed` is the single normaliser, and it runs on every seed
# whatever produced it -- derived from a remote, derived from a path, or typed
# into `settings.json` by hand.


def normalise_seed(value):
    """The one normalisation applied to every seed.

    Whitespace off both ends, and no trailing separator, so that `owner/repo`,
    ` owner/repo ` and `owner/repo/` are one seed.

    **Case is left alone.** The seed is the string that gets hashed, and a
    port in another language reproduces a mark by hashing what the file says,
    exactly as it reads. Specifying a case fold instead would make every port
    reimplement Unicode case mapping to stay conformant, and a port that got
    Turkish dotless i wrong would draw a different mark. Leaving case alone
    also keeps the field readable: `Jaymax-NZ/Repository-Identicon` is the
    name its owner recognises.
    """
    return str(value).strip().rstrip("/").rstrip(os.sep) or os.sep


def extract_repository_name(repository_url):
    """The `owner/repo` a git remote URL names, or None.

    Every way of naming one repository collapses to one seed, so an SSH
    checkout and an HTTPS checkout of the same project derive alike:

        git@github.com:Owner/Repo.git
        https://github.com/Owner/Repo.git
        https://token@github.com/Owner/Repo
        ssh://git@github.com:2222/Owner/Repo.git   ->  Owner/Repo

    The host is parsed, used to reject a URL that has none, and then dropped,
    so a project keeps its mark across a move between forges. `github.com/a/b`
    and `gitlab.com/a/b` therefore derive the same seed; a repository that
    needs to differ writes its own seed into `.identicon/settings.json`.

    Returns None for a local-path remote, which is no more portable than the
    working directory and so earns no special treatment.
    """
    if not repository_url:
        return None
    repository_url = repository_url.strip().rstrip("/")
    if (not repository_url or repository_url.startswith("/")
            or repository_url.startswith("file://")):
        return None

    if "://" in repository_url:
        scheme, _, rest = repository_url.partition("://")
        if scheme.lower() == "file":
            return None
        authority, _, path = rest.partition("/")
    elif ":" in repository_url:
        # scp-like: [user@]host:path
        authority, _, path = repository_url.partition(":")
    else:
        return None

    if "@" in authority:
        authority = authority.rpartition("@")[2]
    host = authority.partition(":")[0]  # drop any port

    path = path.strip("/")
    if path.lower().endswith(".git"):
        path = path[: -len(".git")]

    parts = [part for part in path.split("/") if part]
    if not host or not parts:
        return None
    return normalise_seed("/".join(parts))


def extract_repository_path( repository_root):
    """The absolute path a repository sits at, or None where none was given.

    Expanded and made absolute, so `~/src/foo` and a relative path to the same
    place give one string. A path names one checkout on one machine where a
    name names the project, which is why `extract_repository_name` is tried
    first; once stored, either travels with the repository alike.
    """
    if not repository_root:
        return None
    absolute = os.path.abspath(os.path.expanduser(str( repository_root)))
    return normalise_seed( absolute)


def _git(args, cwd=None):
    """Run a git command, returning stripped stdout or None if it fails.

    `cwd` of None means the current directory, and must never reach `git -C`
    as None: that fails, and the failure is indistinguishable from "not a
    repository".
    """
    try:
        completed = subprocess.run(
            ["git", "-C", str(cwd if cwd else os.getcwd()), *args],
            capture_output=True, text=True
        )
    except OSError:
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip() or None


def locate_repository_root(working_directory=None):
    """The directory holding `.identicon/`: the nearest ancestor with a `.git`.

    Walks up from `working_directory`, or from the process's own. Returns the
    starting directory where no ancestor has one, so a directory outside a
    repository still has somewhere to keep its settings.

    A worktree has a `.git` file where a main checkout has a `.git` directory,
    and both sit at the root that owns the `.identicon/`, so `exists` answers
    for both. `git rev-parse --show-toplevel` returns the same directory and
    costs a subprocess; walking is what lets a seeded repository resolve its
    seed without running git at all.
    """
    directory = pathlib.Path(os.path.abspath(os.path.expanduser(
        str(working_directory) if working_directory else os.getcwd())))
    for candidate in (directory, *directory.parents):
        if (candidate / ".git").exists():
            return str(candidate)
    return str(directory)


def repo_remote_url( repository_root):
    """Invokes `git remote get-url origin`, and returns what it prints.

    Falls back to `git remote` and then `git remote get-url <first>` where
    there is no origin.
    """
    url = _git( ["remote", "get-url", "origin"], repository_root)
    if url:
        return url
    remotes = _git( ["remote"], repository_root)
    if not remotes:
        return None
    return _git( ["remote", "get-url", remotes.splitlines()[0].strip()],
                repository_root)


# What `--reseed` accepts, and what `derive_identicon_seed` derives from.
SEED_SOURCES = ("auto", "repo", "path", "uuid")


def derive_identicon_seed(repository_root, derive_from="auto"):
    """Derive a seed for a repository, from one of four things.

    `derive_from` names which:

      auto   the git remote if there is one, otherwise the path
      repo   the git remote, as `owner/repo`
      path   the repository directory
      uuid   a fresh uuid4

    A named source that cannot answer raises. Asking for `repo` where there is
    no remote is a question with no answer, and returning a path instead would
    answer a different question. `auto` is the one source that chooses.

    This runs on the first `apply` in a repository, and again in `doctor` to
    report what the repository would derive today.
    """
    if derive_from not in SEED_SOURCES:
        raise ValueError(f"unknown seed source {derive_from!r}; expected one "
                         f"of {', '.join(SEED_SOURCES)}")

    if derive_from == "uuid":
        return str(uuid.uuid4())

    if derive_from in ("auto", "repo"):
        url = repo_remote_url(repository_root)
        derived = extract_repository_name(url) if url else None
        if derived:
            return derived
        if derive_from == "repo":
            raise ValueError(f"{repository_root} has no git remote, so there "
                             f"is no `repo` seed to derive")

    return extract_repository_path(repository_root)


# ---- The colour map ----

# **The colour map never reaches the digest.** The seed alone is hashed, so
# the matrix and the hue a repository draws are fixed by its seed for good. A
# better colour map -- a wider gamut, a palette gaining a colour Unicode did
# not have -- changes what colour a mark is drawn in and can never change its
# shape. Shipping a new map is a deliberate, separate piece of work.
#
# **Newest shipped map, and what a repository is seeded with.** An integer,
# because the maps are a numbered sequence that is counted and compared and
# nothing else. A repository records the one it was seeded under, in
# `colourMap`, and keeps it: see rule 11 in
# `work-in-progress/identity-change-set.md`.
#
# There is one map. When a second ships, each map is a file carrying its
# number in the filename and a build learns which it has by seeing which files
# are present. Nothing discovers anything while the answer is `0`.
COLOUR_MAP_LATEST = 0

# **Two numbers, and they count different things.**
#
#   VERSION            this tool, as a release. Nothing is released.
#   COLOUR_MAP_LATEST  the colour rule, and the wheel of tricolours in
#                      `work-in-progress/wheel.tsv` that stands over the same
#                      gamut. One number, so the two cannot disagree.
VERSION = "0.0.build"


def _digest(seed):
    """MD5 of the seed as lowercase hex. Nothing is prepended or appended.

    The only hash in this repository. The matrix reads its first 15 characters
    and the hue reads its last 7, so pattern and colour cannot come apart.

    Hex rather than bytes because the reference consumes the digest as *hex
    characters* -- one nibble per matrix cell, and the last seven characters as
    the hue.

    **The seed is hashed exactly as `settings.json` spells it.** No case fold,
    no trimming, no prefix: a port reproduces a mark by hashing the string the
    file holds, which is a rule that needs no Unicode support to implement.
    MD5 stays because the reference consumes MD5 hex; its collision weakness
    matters where forging a match gains something, and nothing is gained by
    finding two repository names that draw alike.
    """
    return hashlib.md5(seed.encode("utf-8")).hexdigest()


def identicon_matrix(seed):
    """Return the 5x5 matrix as a list of rows of bools.

    Conforms to stewartlord/identicon.js, whose own comment reads:

        the first 15 characters of the hash control the pixels (even/odd)
        they are drawn down the middle first, then mirrored outwards

    So characters 0-4 fill the centre column top to bottom, 5-9 fill column 1
    and mirror it to 3, and 10-14 fill column 0 and mirror it to 4. Even is
    foreground. Pinned in vectors.json.
    """
    digest = _digest(seed)
    matrix = [[False] * MATRIX_SIZE for _ in range(MATRIX_SIZE)]
    for index in range(15):
        painted = int(digest[index], 16) % 2 == 0
        column, row = divmod(index, MATRIX_SIZE)
        matrix[row][2 - column] = painted
        matrix[row][2 + column] = painted
    return matrix


def matrix_text(matrix):
    """The matrix as five lines of `01010`, the spelling `vectors.json` uses.

    Rows of characters rather than JSON, to match the `.colour` artifact beside
    it: both are a bare value a reader can take in at a glance and a shell can
    handle without a parser.
    """
    return "\n".join("".join("1" if cell else "0" for cell in row)
                     for row in matrix)


def identicon_hue(seed):
    """Hue as a fraction of a turn, from the last seven hex characters.

    28 bits over 0xfffffff, per the reference. Read from the same digest as
    the matrix, so one seed gives one pattern and one hue together.
    """
    return int(_digest(seed)[-7:], 16) / 0xFFFFFFF


def _quantise(value):
    """Round half up, not half to even.

    Specified this way because the spec has to be reimplementable in languages
    whose native rounding is half up. Python's round() is half to even, so
    following it would have made the spec quietly unportable.
    """
    return int(value * 255 + 0.5)


# ---- The colour ----
#
# **One brightness for every hue, which is what lets one file serve both a
# light page and a dark one.** HSL lightness does not control brightness: at
# the reference's 0.5, yellow carries several times the light of blue. 34 of 72
# sampled hues fell below 3:1 against white, and 10 fell below it against
# GitHub's dark canvas.
#
# Oklab lightness does control brightness, so holding it fixed holds contrast
# fixed. Every hue then sits at 3.6:1 or better against white and 4.0:1 or
# better against near-black, from one file.
#
# The chroma is capped rather than flattened. Flattening -- every hue held to
# what the narrowest can manage -- costs about half the colour on the wheel to
# buy a uniformity nobody asked for.
#
# The hue draw is unchanged: the same 28 bits from the same digest, read as an
# angle in Oklab rather than in HSL. That also removes the crowding the old
# mapping had, where a fifth of all projects landed in a band of green worth
# about six perceptual degrees.

MARK_LIGHTNESS = 0.60
MARK_CHROMA = 0.26

# ---- The hue draw, compressed around blue-green ----
#
# **Every hue still exists; what changes is how many projects land on one.** The
# draw off the digest is uniform over the circle, but the emoji palette has no
# colour between green and blue, so every mixture of the two reads at
# essentially one hue. That is a fact about the palette, not about the
# colour, and it cannot be fixed by placement -- see
# `work-in-progress/README.md`.
#
# So that arc is given less of the draw than its width suggests. The hue advances
# faster through it, and the projects saved land where the vocabulary can tell
# them apart.
#
# The speed function is a raised cosine -- one full cosine period, centred, with
# zero derivative at both ends -- so no project sits on a discontinuity. Its
# integral is elementary, and that matters more than it looks: this has to be
# reimplementable, and a closed form with one sine in it is a paragraph of
# specification where a spline would be a page.
#
# (centre, half-width, peak) in degrees of Oklab hue. `peak` is how much faster
# the hue advances at the centre, so the share landing there falls by roughly
# that factor. These are the values the wheel was solved against.
HUE_WARP = (215.0, 50.0, 4.0)


def _warp_bump(turned, half):
    """The integral of the raised-cosine bump, from its start to `turned`.

    Flat at zero before the bump begins and flat at `half` after it ends, which
    is what makes `warp_hue` monotonic with continuous ends.
    """
    if turned <= -half:
        return 0.0
    if turned >= half:
        return half
    return (0.5 * (turned + half)
            + (half / (2 * math.pi)) * math.sin(math.pi * turned / half))


def warp_hue(degrees, warp=HUE_WARP):
    """A uniform draw in degrees, to the hue it names. Monotonic, onto [0, 360).

    `None` for `warp` is the uniform draw, which the three withdrawn drafts
    before this colour map used.
    """
    if warp is None:
        return degrees % 360.0
    centre, half, peak = warp
    degrees %= 360.0
    total = 360.0 + (peak - 1.0) * half
    return 360.0 * (degrees
                    + (peak - 1.0) * _warp_bump(degrees - centre, half)) / total


# The bisection that finds how much chroma a hue can take. Fixed bounds and a
# fixed iteration count, because "search until it converges" is not a
# specification -- two implementations would stop in different places. The
# result is rounded to four decimals so that a port whose cube roots differ in
# the last bits still lands on the same number.
GAMUT_STEPS = 30
GAMUT_CEILING = 0.4


def _oklch_to_linear(lightness, chroma, degrees):
    """OkLCh to linear-light RGB, unclamped so the caller can test the range."""
    radians = math.radians(degrees)
    a = chroma * math.cos(radians)
    b = chroma * math.sin(radians)
    long_ = (lightness + 0.3963377774 * a + 0.2158037573 * b) ** 3
    medium = (lightness - 0.1055613458 * a - 0.0638541728 * b) ** 3
    short = (lightness - 0.0894841775 * a - 1.2914855480 * b) ** 3
    return (4.0767416621 * long_ - 3.3077115913 * medium + 0.2309699292 * short,
            -1.2684380046 * long_ + 2.6097574011 * medium - 0.3413193965 * short,
            -0.0041960863 * long_ - 0.7034186147 * medium + 1.7076147010 * short)


def _in_gamut(linear):
    return all(-1e-4 <= channel <= 1 + 1e-4 for channel in linear)


def gamut_chroma(degrees, lightness=MARK_LIGHTNESS, cap=MARK_CHROMA):
    """The chroma this hue actually gets: the cap, or the most sRGB allows."""
    if _in_gamut(_oklch_to_linear(lightness, cap, degrees)):
        return cap
    low, high = 0.0, GAMUT_CEILING
    for _ in range(GAMUT_STEPS):
        middle = (low + high) / 2
        if _in_gamut(_oklch_to_linear(lightness, middle, degrees)):
            low = middle
        else:
            high = middle
    return min(cap, int(low * 10000) / 10000)


def _encode(channel):
    """Linear light to an sRGB component, 0-255, rounded half up."""
    channel = max(0.0, min(1.0, channel))
    encoded = (1.055 * channel ** (1 / 2.4) - 0.055
               if channel > 0.0031308 else 12.92 * channel)
    return _quantise(encoded)


class UnknownColourMap(ValueError):
    """A colour map this build does not implement."""


def identicon_colour(seed, chroma=MARK_CHROMA, lightness=MARK_LIGHTNESS,
                     colour_map=COLOUR_MAP_LATEST):
    """Return the foreground colour as an (r, g, b) triple of 0-255 ints.

    The angle from the digest, warped, then Oklab at one lightness with the
    chroma capped.

    **The shape does not depend on this.** `identicon_matrix` reads the same
    digest and never sees `colour_map`, so replacing a colour map repaints
    every mark and moves none of them.

    A `colour_map` this build does not implement raises rather than drawing
    with the only map there is, which would produce a mark that
    `settings.json` does not describe. There is one map, so this reaches a
    repository only through a hand edit.
    """
    if colour_map != COLOUR_MAP_LATEST:
        raise UnknownColourMap(
            f"colour map {colour_map!r} is not implemented by this build, "
            f"which draws colour map {COLOUR_MAP_LATEST}")

    degrees = warp_hue(identicon_hue(seed) * 360.0)
    return tuple(_encode(channel) for channel in
                 _oklch_to_linear(lightness, gamut_chroma(degrees, lightness,
                                                          chroma), degrees))


def _colour_for(seed, kwargs):
    """`identicon_colour` with chroma and lightness taken from render kwargs.

    `.get` with the defaults, never `kwargs["chroma"]`: the callers are handed
    kwargs that may carry neither.
    """
    return identicon_colour(seed, kwargs.get("chroma", MARK_CHROMA),
                            kwargs.get("lightness", MARK_LIGHTNESS))


# ---- Names derived from the seed ----


def hex_colour(rgb):
    return "#{:02x}{:02x}{:02x}".format(*rgb)


# The Konsole profile names -- profile_name, profile_filename, profile_body --
# were here and are now in Console-Colophon.
#
# The derived names were here too, and are gone: short_hash and icon_name,
# because nothing in this repository installs an icon; project_name and
# badge_label, because neither is derived from the mark. Two implementations
# shortening a project's name differently collide with nothing, so the
# specification has no reason to fix either.


# ---- Rendering ----


def canvas_edge(block, border):
    """The square canvas a block and a border imply: MATRIX_SIZE blocks plus a border.

    The block is the specified thing and the canvas is derived, never the other
    way round. Deriving the block from a canvas needs a heuristic, a heuristic
    does not scale linearly, and a mark that lands on a different block at a
    different scale is two drawings rather than one.
    """
    return MATRIX_SIZE * block + 2 * border


def render_rgba(seed, block, border=BORDER, chroma=MARK_CHROMA,
                lightness=MARK_LIGHTNESS, background=None):
    """Return raw RGBA bytes for a square identicon of `block`-pixel blocks.

    The canvas is derived from the block and the border, never given. A caller
    that has to fill a canvas somebody else fixed uses `large_geometry`, which
    returns a block and a border that land on that canvas exactly.
    """
    matrix = identicon_matrix(seed)
    red, green, blue = identicon_colour(seed, chroma, lightness)
    edge, margin = canvas_edge(block, border), border

    if background is None:
        back = bytes((0, 0, 0, 0))
    else:
        back = bytes(tuple(background) + (255,))
    fore = bytes((red, green, blue, 255))

    rows = []
    for y in range(edge):
        row = bytearray()
        matrix_y = (y - margin) // block if block else -1
        inside_y = margin <= y < margin + block * MATRIX_SIZE
        for x in range(edge):
            matrix_x = (x - margin) // block if block else -1
            inside_x = margin <= x < margin + block * MATRIX_SIZE
            if inside_x and inside_y and matrix[matrix_y][matrix_x]:
                row += fore
            else:
                row += back
        rows.append(bytes(row))
    return b"".join(rows)


def _png_chunk(tag, data):
    return (
        struct.pack(">I", len(data))
        + tag
        + data
        + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


# ---- A deflate encoder this file owns ----
#
# **`zlib.compress` cannot be used here, at any level.** The PNG bytes are
# committed to the repository and `apply --check` compares them, so two
# machines running the same version must produce the same file. The
# compression level was already pinned to 9 and the filter to 0, and the
# rasters still differed: CPython links whichever deflate the platform
# supplies, and zlib-ng picks different matches from stock zlib at the same
# level. The level is an input to the search, not a description of its
# output. So the search is written out here, where its result is a fact about
# this file rather than about the machine.
#
# The trade is size. Fixed Huffman codes cost about 13 bits for the
# length-distance pair that a flat colour run turns into, where zlib's dynamic
# codes cost two or three. The 256-pixel raster is roughly four times the size
# it was. Dynamic Huffman would win those bytes back and is the obvious
# extension if the weight ever matters; it is a few hundred lines of
# code-length alphabet and canonical code construction, and the rasters are
# still a few kilobytes without it.
#
# `zlib.crc32` and `zlib.adler32` stay. They are checksums with one defined
# answer, not searches.

_DEFLATE_WINDOW = 32768
_DEFLATE_MAX_MATCH = 258
_DEFLATE_MIN_MATCH = 3

# How many earlier positions a match search considers. Bounded so the encoder
# is linear, and fixed so the bound is part of the format this file defines.
_DEFLATE_MAX_CHAIN = 32

# (code, extra bits, smallest length that uses the code), longest first.
_LENGTH_CODES = [
    (285, 0, 258), (284, 5, 227), (283, 5, 195), (282, 5, 163), (281, 5, 131),
    (280, 4, 115), (279, 4, 99), (278, 4, 83), (277, 4, 67), (276, 3, 59),
    (275, 3, 51), (274, 3, 43), (273, 3, 35), (272, 2, 31), (271, 2, 27),
    (270, 2, 23), (269, 2, 19), (268, 1, 17), (267, 1, 15), (266, 1, 13),
    (265, 1, 11), (264, 0, 10), (263, 0, 9), (262, 0, 8), (261, 0, 7),
    (260, 0, 6), (259, 0, 5), (258, 0, 4), (257, 0, 3),
]

# (code, extra bits, smallest distance that uses the code), longest first.
_DISTANCE_CODES = [
    (29, 13, 24577), (28, 13, 16385), (27, 12, 12289), (26, 12, 8193),
    (25, 11, 6145), (24, 11, 4097), (23, 10, 3073), (22, 10, 2049),
    (21, 9, 1537), (20, 9, 1025), (19, 8, 769), (18, 8, 513), (17, 7, 385),
    (16, 7, 257), (15, 6, 193), (14, 6, 129), (13, 5, 97), (12, 5, 65),
    (11, 4, 49), (10, 4, 33), (9, 3, 25), (8, 3, 17), (7, 2, 13), (6, 2, 9),
    (5, 1, 7), (4, 1, 5), (3, 0, 4), (2, 0, 3), (1, 0, 2), (0, 0, 1),
]


class _BitWriter:
    """Deflate bit order: elements enter at the low bit, codes high bit first."""

    def __init__(self):
        self.out = bytearray()
        self.bits = 0
        self.count = 0

    def add(self, value, width):
        """Write `width` bits of `value`, least significant bit first."""
        self.bits |= (value & ((1 << width) - 1)) << self.count
        self.count += width
        while self.count >= 8:
            self.out.append(self.bits & 0xFF)
            self.bits >>= 8
            self.count -= 8

    def code(self, code, width):
        """Write a Huffman code of `width` bits, most significant bit first."""
        for shift in range(width - 1, -1, -1):
            self.add((code >> shift) & 1, 1)

    def finish(self):
        if self.count:
            self.out.append(self.bits & 0xFF)
            self.bits = 0
            self.count = 0
        return bytes(self.out)


def _fixed_literal(value):
    """The fixed-Huffman code and width for a literal or length symbol."""
    if value < 144:
        return 0x30 + value, 8
    if value < 256:
        return 0x190 + value - 144, 9
    if value < 280:
        return value - 256, 7
    return 0xC0 + value - 280, 8


def _split(table, value):
    for code, extra, base in table:
        if value >= base:
            return code, extra, value - base
    raise ValueError(value)


def _deflate(data):
    """One fixed-Huffman deflate block holding all of `data`.

    Greedy longest match, most recent position on a tie, search bounded to
    `_DEFLATE_MAX_CHAIN` candidates. Every choice is written here, so the
    output depends on the input alone.
    """
    writer = _BitWriter()
    writer.add(1, 1)  # BFINAL: this is the only block.
    writer.add(1, 2)  # BTYPE 01: fixed Huffman codes.

    size = len(data)
    seen = {}
    pos = 0
    while pos < size:
        best_length = 0
        best_distance = 0
        if pos + _DEFLATE_MIN_MATCH <= size:
            chain = seen.get(data[pos:pos + _DEFLATE_MIN_MATCH])
            if chain:
                oldest = pos - _DEFLATE_WINDOW
                ceiling = min(_DEFLATE_MAX_MATCH, size - pos)
                for candidate in reversed(chain[-_DEFLATE_MAX_CHAIN:]):
                    if candidate < oldest:
                        continue
                    length = 0
                    # The match may run past `pos`; deflate copies byte by
                    # byte, which is what turns a colour run into one pair.
                    while (length < ceiling
                           and data[candidate + length] == data[pos + length]):
                        length += 1
                    if length > best_length:
                        best_length = length
                        best_distance = pos - candidate
                        if length == ceiling:
                            break

        if best_length >= _DEFLATE_MIN_MATCH:
            symbol, extra, offset = _split(_LENGTH_CODES, best_length)
            writer.code(*_fixed_literal(symbol))
            if extra:
                writer.add(offset, extra)
            symbol, extra, offset = _split(_DISTANCE_CODES, best_distance)
            writer.code(symbol, 5)
            if extra:
                writer.add(offset, extra)
            step = best_length
        else:
            writer.code(*_fixed_literal(data[pos]))
            step = 1

        for index in range(pos, min(pos + step, size - _DEFLATE_MIN_MATCH + 1)):
            seen.setdefault(data[index:index + _DEFLATE_MIN_MATCH],
                            []).append(index)
        pos += step

    writer.code(*_fixed_literal(256))  # end of block
    return writer.finish()


def _zlib_stream(data):
    """`data` wrapped as a zlib stream: header, deflate block, Adler-32."""
    # 0x78 0x9C is CM=8, a 32K window, no preset dictionary, and the check bits
    # that make the pair divide by 31.
    return (b"\x78\x9c" + _deflate(data)
            + struct.pack(">I", zlib.adler32(data) & 0xFFFFFFFF))


def encode_png(rgba, width, height):
    """Minimal 8-bit RGBA PNG encoder. Every row carries filter type 0.

    The bytes are reproducible on any machine running this file: the filter is
    fixed here and the deflate search is `_deflate`, not the platform's.
    """
    stride = width * 4
    raw = b"".join(b"\x00" + rgba[y * stride:(y + 1) * stride] for y in range(height))
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", header)
        + _png_chunk(b"IDAT", _zlib_stream(raw))
        + _png_chunk(b"IEND", b"")
    )


def render_png(seed, block, **kwargs):
    edge = canvas_edge(block, kwargs.get("border", BORDER))
    return encode_png(render_rgba(seed, block, **kwargs), edge, edge)


def render_svg(seed, block=ARTIFACT_BLOCK, border=BORDER, chroma=MARK_CHROMA,
               lightness=MARK_LIGHTNESS, background=None):
    matrix = identicon_matrix(seed)
    colour = hex_colour(identicon_colour(seed, chroma, lightness))
    size = canvas_edge(block, border)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 {size} {size}">'
    ]
    if background is not None:
        parts.append(f'<rect width="{size}" height="{size}" '
                     f'fill="{hex_colour(background)}"/>')
    for row in range(MATRIX_SIZE):
        for column in range(MATRIX_SIZE):
            if matrix[row][column]:
                x = border + column * block
                y = border + row * block
                parts.append(
                    f'<rect x="{x}" y="{y}" width="{block}" height="{block}" fill="{colour}"/>'
                )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


# The text rendering lives in text-identicon.py, which takes a matrix and a colour
# and nothing else. Loaded by path because the file name carries a hyphen.
#
# **These two files are a pair and must be deployed together**: the sextant
# table and the emoji palette live next door. `apply` cannot write `.tricolour`,
# `.sextant`, `.octant` or `.txt` without it, so `doctor` reports whether it is
# there.
TEXT_MODULE = "text-identicon.py"
_TEXT = None


def text_module_path():
    return pathlib.Path(__file__).with_name(TEXT_MODULE)


def _text_module():
    global _TEXT
    if _TEXT is None:
        import importlib.util
        path = text_module_path()
        if not path.is_file():
            raise FileNotFoundError(
                f"{TEXT_MODULE} must sit beside {pathlib.Path(__file__).name}; "
                f"the text renderings need its sextant table")
        spec = importlib.util.spec_from_file_location("text_identicon", path)
        _TEXT = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_TEXT)
    return _TEXT


# **The escape-sequence renderings are in `Console-Colophon`**, with `emit`.
# SPEC.md §§ Renderings, Terminal and Text still define and rank them -- inline
# image, then a lattice with the tricolour, then the tricolour alone -- and
# `artifact_bytes` below writes every one of them to a file. What is not here is
# wrapping those bytes for a particular terminal: the iTerm2 and kitty
# protocols, the ANSI foreground colours, the environment sniffing that picks
# between them. § Scope puts all of that on the far side of the line, because
# choosing what this terminal can read is a decision about somebody's terminal.
#
# `.txt` is what a consumer in that position needs from here. It is `cat`.


# ---- Installing the identicon into a repository ----
#
# This is what the project is for. Everything above derives a mark; this puts
# it in the repository it belongs to, in forms a consumer that knows nothing
# about this tool can use without parsing anything.
#
# The mark is a constant for a repository -- derived from the remote, not
# stored anywhere -- so these files are a cache, not a source. They exist
# because a README, a shell prompt or a forge cannot run a derivation.

IDENTICON_DIR = ".identicon"
ARTIFACT_STEM = "repository-identicon"

# **Each filename repeats the directory deliberately.** The directory is
# context, and context is what does not travel: copied out, fetched from a raw
# URL or dropped into `docs/`, a file called `icon.png` describes nothing. The
# prefix also anticipates a repository carrying more than one mark, at which
# point the unqualified name is the ambiguous one.


def artifact_names():
    """Every artifact as (name, filename).

    One list, walked by both the path builder and the byte builder, so a file
    that exists in one and not the other cannot happen.
    """
    yield "png", f"{ARTIFACT_STEM}.png"
    yield "png4x", f"{ARTIFACT_STEM}@{ARTIFACT_SCALE}x.png"
    for canvas in LARGE_CANVASES:
        yield f"png{canvas}", f"{ARTIFACT_STEM}-{canvas}.png"
    yield "svg", f"{ARTIFACT_STEM}.svg"
    yield "colour", f"{ARTIFACT_STEM}.colour"
    yield "matrix", f"{ARTIFACT_STEM}.matrix"
    yield "tricolour", f"{ARTIFACT_STEM}.tricolour"
    yield "sextant", f"{ARTIFACT_STEM}.sextant"
    yield "octant", f"{ARTIFACT_STEM}.octant"
    yield "txt", f"{ARTIFACT_STEM}.txt"


def artifact_paths(root):
    directory = pathlib.Path(root) / IDENTICON_DIR
    return {name: directory / filename for name, filename in artifact_names()}


# **The one place a repository's identity is written down.** The seed lives
# here and nowhere else: there is no second file to disagree with it, and no
# derivation that outranks it. JSON, so a consumer reads it with a parser
# rather than a convention, and inside `.identicon/` so every file this tool
# owns sits in one directory.
#
# It is committed, with the rest of `.identicon/`. That is what makes a stored
# seed survive a clone whatever it was derived from, and it is why derivation
# runs once in a repository's life rather than on every run.
SETTINGS_NAME = "settings.json"

# **The field names spell out what they hold.** Somebody opening this file has
# not read SPEC.md, and `seed` alone does not say a seed for what. The code
# uses Python's snake_case and the file uses JSON's camelCase; the two spell
# one concept, so `identiconSeed` in the file is `identicon_seed` in the code.
SEED_FIELD = "identiconSeed"
HISTORY_FIELD = "identiconSeedHistory"
COLOUR_MAP_FIELD = "colourMap"


def settings_path(repository_root):
    return pathlib.Path(repository_root) / IDENTICON_DIR / SETTINGS_NAME


def read_settings(repository_root):
    """The settings mapping, or an empty one where there is no usable file.

    An unreadable or malformed file reads as empty rather than raising. The
    next `apply` then writes a good one, which is the repair a developer would
    otherwise do by hand.
    """
    try:
        loaded = json.loads(
            settings_path(repository_root).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def identicon_seed(settings):
    """The seed a settings mapping holds, or None where none is set.

    Three rules, which is why this is not a key lookup. A non-string is not a
    seed. An empty string counts as unset, so `clear_identicon_seed` empties
    the field and the ordinary rule writes the next one -- that is what makes
    a reseed one rule rather than two. And a hand-edited value is normalised
    on the way out, so typing a seed into the file is as supported as deriving
    one.

    Takes the mapping rather than a directory because `apply` asks it about
    settings it has just emptied in memory. Reading the file there would
    return the seed being retired.
    """
    seed = settings.get(SEED_FIELD)
    if not isinstance(seed, str) or not seed.strip():
        return None
    return normalise_seed(seed)


def read_colour_map(repository_root):
    """The colour map a repository was seeded under.

    A repository with no settings file, or none recorded, takes this build's.
    """
    colour_map = read_settings(repository_root).get(COLOUR_MAP_FIELD)
    return colour_map if isinstance(colour_map, int) else COLOUR_MAP_LATEST


def settings_bytes(settings):
    """The exact file bytes for a settings mapping.

    Sorted keys, two-space indent and a trailing newline, so two runs that
    agree about the settings write the same bytes.
    """
    return (json.dumps(settings, indent=2, sort_keys=True)
            + "\n").encode("utf-8")


def prior_path(target):
    """Where the version being replaced is kept: stem.prior.suffix."""
    target = pathlib.Path(target)
    return target.with_name(f"{target.stem}.prior{target.suffix}")


def keep_prior(target, current):
    """Set the outgoing bytes aside so a rollback is a `mv`.

    One level, overwritten each time. Anyone who wants history has git; what
    this is for is the moment *before* a commit, when a run has replaced a
    mark and the previous one is not anywhere yet. These are developers -- a
    file beside the new one is the whole recovery procedure, and it beats any
    amount of asking first.
    """
    if current is None:
        return None
    keep = prior_path(target)
    keep.write_bytes(current)
    return keep


def write_settings(repository_root, settings):
    """Write the settings file. Returns the bytes written."""
    path = settings_path(repository_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    wanted = settings_bytes(settings)
    path.write_bytes(wanted)
    return wanted


def clear_identicon_seed(repository_root, check=False):
    """Move the seed to the front of the history and empty the field, on disk.

    Reads the file, rewrites it, and returns what it wrote, so a caller can
    read the file back and get the same thing. There is no settings mapping
    held across the change that could disagree with what is stored.

    This is the whole of a reseed. An empty seed is an unset seed, so the rule
    that seeds a fresh repository writes the next one -- one rule for both,
    rather than two that have to agree.

    `check` is the dry run: the cleared settings are returned and the file is
    left alone, because `apply --check` writes nothing.
    """
    settings = read_settings(repository_root)
    history = settings.get(HISTORY_FIELD)
    history = [entry for entry in history if isinstance(entry, str)] \
        if isinstance(history, list) else []
    current = settings.get(SEED_FIELD)
    settings[HISTORY_FIELD] = ([current] + history
                               if isinstance(current, str) and current.strip()
                               else history)
    settings[SEED_FIELD] = ""
    if not check:
        write_settings(repository_root, settings)
    return settings


def artifact_bytes(seed, block=ARTIFACT_BLOCK, **render_kwargs):
    """What each artifact should contain for this seed.

    Separate files rather than one blob: a README cannot address a fragment
    inside a blob, and `$(cat …/*.colour)` has to stay a cat.

    **The text rendering is written in parts and whole.** `.tricolour` is the
    three emoji, `.sextant` and `.octant` are the pattern on each
    lattice, and `.txt` is the sextant lattice with the tricolour ending its
    lower line. A consumer that wants the mark runs `cat` on `.txt`; one that
    is building a line of its own -- a prompt, a tab title, a status field --
    takes the part it has room for and does not have to split anything.

    Both lattices are written because which one renders is a fact about the
    host's fonts, not about the mark, and this file cannot know it.
    """
    wanted = {
        "png": render_png(seed, block, **render_kwargs),
        "png4x": render_png(seed, block * ARTIFACT_SCALE, border=SCALED_BORDER,
                            **render_kwargs),
        "svg": render_svg(seed, block, **render_kwargs).encode("utf-8"),
    }
    for canvas in LARGE_CANVASES:
        large_block, large_border = large_geometry(canvas)
        wanted[f"png{canvas}"] = render_png(seed, large_block,
                                            border=large_border, **render_kwargs)
    colour = _colour_for(seed, render_kwargs)
    matrix = identicon_matrix(seed)
    text = _text_module()
    wanted["colour"] = (hex_colour(colour) + "\n").encode("utf-8")
    wanted["matrix"] = (matrix_text(matrix) + "\n").encode("utf-8")
    wanted["tricolour"] = (text.tricolour(colour, matrix) + "\n").encode("utf-8")
    for name, lines in (("sextant", text.sextant(matrix)),
                        ("octant", text.octant(matrix))):
        wanted[name] = ("\n".join(lines) + "\n").encode("utf-8")
    wanted["txt"] = (text.text(matrix, colour) + "\n").encode("utf-8")
    return wanted


# The artifacts are inert until something points at them, and the one thing
# every repository already has is a README. So the line goes in by default and
# --no-readme is the way out, rather than the other way round: an identicon
# nobody put on the page is an identicon nobody sees.
README_MARK = f"![]({IDENTICON_DIR}/{ARTIFACT_STEM}.svg)"

# **What counts as the mark already being there.** Strip fenced code first,
# then look for an image reference: a README that *documents* these paths is
# not one that displays them, and a mark inside a code fence is a mark being
# talked about. No trailing dot on the path, so a mark somebody pointed at one
# of the sized rasters, or at a variant from an older version of this tool,
# still counts and is not duplicated.
README_NEEDLE = re.compile(
    r"!\[[^\]]*\]\([^)]*{path}|<img[^>]+src\s*=\s*[\"'][^\"']*{path}".format(
        path=re.escape(f"{IDENTICON_DIR}/{ARTIFACT_STEM}")))
README_FENCE = re.compile(r"^(```|~~~)", re.MULTILINE)


def without_code_fences(body):
    """The prose of a markdown file, with fenced blocks blanked out.

    Blanked rather than deleted so line numbers survive, which matters for
    anything that reports a position later.
    """
    out, inside = [], False
    for line in body.split("\n"):
        if README_FENCE.match(line):
            inside = not inside
            out.append("")
            continue
        out.append("" if inside else line)
    return "\n".join(out)


def find_readme(root):
    """The repository's own README, or None. Markdown only, top level only.

    Case is not decided by the filesystem here -- README.md and readme.md are
    both common -- so match on the lowered name rather than trusting a glob.
    """
    root = pathlib.Path(root)
    if not root.is_dir():
        return None
    candidates = [entry for entry in root.iterdir()
                  if entry.is_file() and entry.suffix.lower() == ".md"
                  and entry.stem.lower() == "readme"]
    if not candidates:
        return None
    exact = [entry for entry in candidates if entry.name == "README.md"]
    return (exact or sorted(candidates))[0]


def readme_state(root, check=False):
    """Put the mark in the README, once, and report what happened.

    Inserted after the first heading rather than above it, so the file still
    opens with what the project is called. A line an author has moved, resized
    with an <img> tag, or pointed at another artifact is left where they put
    it: this writes once and then keeps out of the way.
    """
    readme = find_readme(root)
    if readme is None:
        return "absent", None

    body = readme.read_text(encoding="utf-8", errors="replace")
    prose = without_code_fences(body)
    if README_NEEDLE.search(prose):
        return "unchanged", readme

    lines = body.split("\n")
    at = 0
    for index, line in enumerate(prose.split("\n")):
        if line.startswith("# "):
            at = index + 1
            break
    while at < len(lines) and not lines[at].strip():
        at += 1

    block = [README_MARK, ""]
    if at > 0 and lines[at - 1].strip():
        block.insert(0, "")
    if not check:
        readme.write_text("\n".join(lines[:at] + block + lines[at:]),
                          encoding="utf-8")
    return "updated", readme


def install_into_repo(path=None, seed=None, block=ARTIFACT_BLOCK, check=False,
                      reseed=None, readme=True, **render_kwargs):
    """Create or update the identicon artifacts in one repository.

    **The seed is written once and read on every run after it.** Refreshing
    the artifacts therefore reaches every repository without touching any
    identity, and a rename, a move between forges or a clone to another path
    changes nothing about the mark.

    `reseed` names a source from `SEED_SOURCES` and is the one way to change
    an identity. It pushes the current seed onto `identiconSeedHistory`,
    blanks the seed field, and lets this run derive and write a new one from
    the source named.

    `seed` supplies a literal seed outright and is likewise a reseed.

    For a fixed seed this writes identical bytes on every run and reports
    nothing changed. `check` writes nothing at all, and on an unseeded
    repository reports the seed it would have written.

    Returns a dict describing what happened, suitable for --json.
    """
    root = locate_repository_root(path)

    # **`apply` is the only command that derives or writes a seed.** `show`
    # and `render` read the stored one and stop; `doctor` reads and derives
    # separately, to report both. Keeping derivation here is what stops a
    # command whose job is to draw from deciding what to draw it from.
    #
    # **A reseed empties the field on disk first, and then this reads the
    # file.** Emptying a copy in memory instead would leave a settings mapping
    # that says one thing while the file says another, for as long as the run
    # lasts. Under `--check` nothing is written, so the cleared settings are
    # handed straight back -- a dry run has no file to re-read.
    if seed or reseed:
        settings = clear_identicon_seed(root, check)
        if not check:
            settings = read_settings(root)
    else:
        settings = read_settings(root)

    if seed:
        resolved_seed, source = normalise_seed(seed), "explicit"
    else:
        stored = identicon_seed(settings)
        if stored is not None:
            resolved_seed, source = stored, "settings"
        else:
            derive_from = reseed or "auto"
            resolved_seed = derive_identicon_seed(root, derive_from)
            source = f"derived from {derive_from}"

    colour_map = settings.get(COLOUR_MAP_FIELD)
    if not isinstance(colour_map, int):
        colour_map = COLOUR_MAP_LATEST
    if colour_map != COLOUR_MAP_LATEST:
        raise UnknownColourMap(
            f"{settings_path(root)} names colour map "
            f"{colour_map!r}; this build draws colour map "
            f"{COLOUR_MAP_LATEST}")

    settings[SEED_FIELD] = resolved_seed
    settings.setdefault(HISTORY_FIELD, [])
    settings[COLOUR_MAP_FIELD] = colour_map

    paths = artifact_paths(root)
    wanted = artifact_bytes(resolved_seed, block, **render_kwargs)

    changes = {}
    for name, target in paths.items():
        current = target.read_bytes() if target.is_file() else None
        if current == wanted[name]:
            changes[name] = "unchanged"
        else:
            changes[name] = "created" if current is None else "updated"
            if not check:
                target.parent.mkdir(parents=True, exist_ok=True)
                keep_prior(target, current)
                target.write_bytes(wanted[name])

    # **The settings file is written last, and only when the artifacts it
    # describes are already there**, so a half-written directory never claims
    # to be seeded.
    #
    # It is an input and not an artifact: it is not in `artifact_names`, and a
    # run that changes nothing else leaves it byte-for-byte alone.
    #
    # A reseed writes it twice: `clear_identicon_seed` empties the field and
    # this puts the new seed in. Two writes of a file this size cost nothing,
    # and the alternative is carrying a cleared copy in memory for the length
    # of the run.
    settings_file = settings_path(root)
    current_settings = (settings_file.read_bytes()
                        if settings_file.is_file() else None)
    settings_wanted = settings_bytes(settings)
    settings_state = ("created" if current_settings is None
                      else "unchanged" if current_settings == settings_wanted
                      else "updated")
    if settings_state != "unchanged" and not check:
        write_settings(root, settings)
    changes["settings"] = settings_state
    paths["settings"] = settings_file

    if readme:
        state, readme_file = readme_state(root, check)
        if readme_file is not None:
            changes["readme"] = state
            paths["readme"] = readme_file

    colour = _colour_for(resolved_seed, render_kwargs)
    return {
        "identiconSeed": resolved_seed,
        "identiconSeedHistory": settings[HISTORY_FIELD],
        "colourMap": colour_map,
        "source": source,
        "root": str(root),
        "colour": hex_colour(colour),
        "files": {name: str(target) for name, target in paths.items()},
        "changes": changes,
        "current": all(state == "unchanged" for state in changes.values()),
        "checked": bool(check),
    }


# ---- Commands ----


class NotSeeded(ValueError):
    """A read-only command run where no seed is set."""


def _seed_to_draw(args):
    """The seed `show` and `render` draw, from `--seed` or the settings file.

    These two report a repository's mark. Deriving one here would let a
    command whose job is to draw decide what to draw from, and would print a
    mark that `apply` had never written. `apply` seeds; these two read.
    """
    explicit = getattr(args, "seed", None)
    if explicit:
        return normalise_seed(explicit)
    root = locate_repository_root(getattr(args, "path", None))
    stored = identicon_seed(read_settings(root))
    if stored is None:
        raise NotSeeded(f"{root} has no seed set in "
                        f"{IDENTICON_DIR}/{SETTINGS_NAME}")
    return stored


def _render_kwargs(args):
    background = None
    if getattr(args, "background", None):
        text = args.background.lstrip("#")
        if len(text) != 6:
            raise SystemExit("--background wants a six digit hex colour")
        background = tuple(int(text[i:i + 2], 16) for i in (0, 2, 4))
    return {
        "chroma": args.chroma,
        "lightness": args.lightness,
        "background": background,
    }


def cmd_show(args):
    seed = _seed_to_draw(args)
    print(f"seed      {seed}")
    print(f"colour    "
          f"{hex_colour(identicon_colour(seed, args.chroma, args.lightness))}")
    return 0


def cmd_render(args):
    seed = _seed_to_draw(args)
    kwargs = _render_kwargs(args)
    block, extra = args.block, {}
    if args.format == "svg":
        data = render_svg(seed, block, **kwargs).encode("utf-8")
    else:
        data = render_png(seed, block, **extra, **kwargs)
    if args.out == "-":
        sys.stdout.buffer.write(data)
    else:
        pathlib.Path(args.out).write_bytes(data)
        print(f"wrote {args.out}")
    return 0


def cmd_apply(args):
    """Create or update the identicon in the repository at `path`.

    The primary command. Exits 0 when the repository is current afterwards,
    and 1 under --check when it is not, so a CI job or a dependent tool can
    branch on it without parsing anything.
    """
    result = install_into_repo(args.path, args.seed, args.block, args.check,
                               args.reseed, not args.no_readme,
                               **_render_kwargs(args))
    if args.json:
        print(json.dumps(result, indent=2))
        return 0 if result["current"] or not args.check else 1

    verb = "would be" if args.check else ""
    print(f"seed       {result['identiconSeed']}  ({result['source']})")
    print(f"colourMap  {result['colourMap']}")
    print(f"colour     {result['colour']}")
    for name, state in sorted(result["changes"].items()):
        mark = " " if state == "unchanged" else "*"
        print(f" {mark} {result['files'][name]}  {verb} {state}".rstrip())
    if result["identiconSeedHistory"]:
        print()
        print("Previously seeded as: "
              + ", ".join(result["identiconSeedHistory"]))
    return 0 if result["current"] or not args.check else 1


# **There was a Claude Code hook here**, and there is not any more: `emit`,
# `hooks`, and the three helpers that read a cwd out of a hook payload, opened
# the controlling terminal and swallowed every error to exit 0. A hook
# registration is a side effect in somebody's settings file, which § Scope puts
# out; the renderings it wrapped went to `Console-Colophon`.
#
# The plan had been for `Claude-Colophon` to take them. It shipped without a
# hook at all -- the skill writes an instruction into the target's CLAUDE.md and
# Claude reads it -- so nothing was ever going to call this.


# ---- Conformance validator ----
#
# CONTRIBUTING.md asks a port for three things and says the vectors are the
# whole conformance test. But a port in Rust cannot run this repository's
# unittest suite, so "check yourself against the vectors" has meant "write your
# own harness" -- which is work this project can do once instead of every
# implementer doing it differently.
#
# So the check is offered outward: point `validate` at your implementation and
# it reports which vectors you reproduce. It reaches into nothing, runs what it
# is given, and compares stdout to `vectors.json`.
#
# Grid and colour only. Those are what the vectors pin and what CONTRIBUTING.md
# calls a complete port; renderings are explicitly optional and are not checked.

VECTORS_NAME = "vectors.json"


def vectors_path():
    return pathlib.Path(__file__).with_name(VECTORS_NAME)


def load_vectors(path=None):
    path = pathlib.Path(path) if path else vectors_path()
    if not path.is_file():
        raise FileNotFoundError(
            f"{path} not found; {VECTORS_NAME} is the contract and validate "
            f"cannot run without it")
    document = json.loads(path.read_text())
    vectors = document.get("vectors")
    if not isinstance(vectors, list) or not vectors:
        raise ValueError(f"{path} has no vectors")

    # One colour map, so one number, and every vector must name it. A new map
    # that does not bring its vectors fails here rather than in the wild.
    #
    # The matrix and the digest in each vector do not depend on the colour map
    # at all -- only `foreground` does -- but a vector is checked whole, so
    # the file states which map its colours were drawn under.
    covered = sorted({vector.get(COLOUR_MAP_FIELD, COLOUR_MAP_LATEST)
                      for vector in vectors})
    if covered != [COLOUR_MAP_LATEST]:
        raise ValueError(
            f"{path} pins colour maps {covered} and this implementation "
            f"draws colour map {COLOUR_MAP_LATEST} only; a new map has to "
            f"bring its vectors with it, and retired maps have to leave")
    return document


def _cell(value):
    """One cell as "0" or "1".

    A string cell is read by value, not by truthiness. `"0"` is a true Python
    string, so a port emitting `[["0", "1", ...], ...]` -- a perfectly
    reasonable shape -- would otherwise be told its matrix was solid, which is
    a wrong answer dressed up as a real one.
    """
    if isinstance(value, str):
        text = value.strip()
        if text not in ("0", "1"):
            raise TypeError(f"cell {value!r} is neither 0 nor 1")
        return text
    return "1" if value else "0"


def _normalise_matrix(value):
    """Accept the shapes a port might reasonably emit, reject the rest.

    A validator that fails a correct implementation over JSON shape is worse
    than no validator, so a row may be "01101" or [0,1,1,0,1] or booleans or
    ["0","1",...].
    """
    rows = []
    for row in value:
        if isinstance(row, str):
            rows.append(row.strip())
        else:
            rows.append("".join(_cell(cell) for cell in row))
    return rows


def check_output(text, vector):
    """Compare one implementation's output for one seed. Returns a problem list."""
    try:
        got = json.loads(text)
    except ValueError as error:
        return [f"output is not JSON: {error}"]
    if not isinstance(got, dict):
        return ["output is not a JSON object"]

    problems = []
    if "matrix" not in got:
        problems.append("no 'matrix' in output")
    else:
        try:
            rows = _normalise_matrix(got["matrix"])
        except TypeError:
            problems.append("'matrix' is not five rows of five cells")
            rows = None
        if rows is not None and rows != vector["matrix"]:
            problems.append(f"matrix {rows} != {vector['matrix']}")

    colour = got.get("colour", got.get("color"))
    if colour is None:
        problems.append("no 'colour' in output")
    else:
        wanted = vector["foreground"].lower()
        if str(colour).lower().lstrip("#") != wanted.lstrip("#"):
            problems.append(f"colour {colour} != {vector['foreground']}")
    return problems


def validate_command(argv, vectors, timeout=30):
    """Run `argv + [seed]` once per vector and collect the results.

    The seed is the whole of what a port is handed, because the seed is the
    whole of what is hashed. A port needs no notion of a colour map to
    reproduce a matrix, and needs only this build's map to reproduce a colour.
    """
    results = []
    for vector in vectors:
        seed = vector["seed"]
        try:
            completed = subprocess.run([*argv, seed],
                                       capture_output=True, text=True,
                                       timeout=timeout)
        except (OSError, subprocess.SubprocessError) as error:
            results.append({"seed": seed, "problems": [str(error)]})
            continue
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()
            results.append({"seed": seed,
                            "problems": [f"exited {completed.returncode}: {detail}"]})
            continue
        results.append({"seed": seed,
                        "problems": check_output(completed.stdout, vector)})
    return results


def cmd_validate(args):
    vectors = load_vectors(args.vectors)["vectors"]
    if not args.command:
        print("give the command that runs your implementation, for example:\n"
              "  repository-identicon validate -- ./my-identicon --json\n"
              "It is run once per vector with the seed as its last argument,\n"
              "and must print {\"matrix\": [...], \"colour\": \"#rrggbb\"} on stdout.",
              file=sys.stderr)
        return 2

    results = validate_command(args.command, vectors)
    failed = [r for r in results if r["problems"]]
    if args.json:
        print(json.dumps({"vectors": len(results),
                          "passed": len(results) - len(failed),
                          "results": results}, indent=2))
    else:
        for result in results:
            if result["problems"]:
                print(f"FAIL {result['seed']}")
                for problem in result["problems"]:
                    print(f"       {problem}")
            else:
                print(f"ok   {result['seed']}")
        print()
        print(f"{len(results) - len(failed)}/{len(results)} vectors reproduced")
        if failed:
            print("This is not a repository identicon until they all pass.")
    return 1 if failed else 0


def cmd_doctor(args):
    """Report the sibling module, the vectors, the colour map, and both seeds.

    Everything here is something `apply` needs; this command reads the same
    things and prints them instead of using them. That is why the derivation
    lives here as well as in `apply` and nowhere else -- a repository's stored
    seed and the seed it would derive today are two facts, and this is where
    somebody comes to ask for them.
    """
    sibling = text_module_path()
    print(f"{TEXT_MODULE:16} " + (str(sibling) if sibling.is_file()
                                  else "NOT FOUND - apply cannot write the "
                                       "text artifacts"))
    vectors = vectors_path()
    print(f"{VECTORS_NAME:16} " + (str(vectors) if vectors.is_file()
                                   else "NOT FOUND - validate cannot run"))
    print(f"{'colour map':16} {COLOUR_MAP_LATEST}")

    root = locate_repository_root(getattr(args, "path", None))
    stored = identicon_seed(read_settings(root))
    print(f"{'seed here':16} "
          + (f"{stored}  (settings)" if stored is not None else "not seeded"))

    # **Asked, not announced.** `apply` reports the seed it used and stops.
    # The comparison lives here because this is the command somebody runs to
    # ask a question, and `apply --reseed` is the command that acts on the
    # answer.
    derived = derive_identicon_seed(root)
    print(f"{'would derive':16} {derived}")
    if stored is not None and stored != derived:
        print(f"{'':16} the two differ; `apply --reseed repo` adopts the "
              f"derived one")
    return 0


# ---- Command line ----


def build_parser():
    parser = argparse.ArgumentParser(
        prog="repository-identicon",
        description="A deterministic visual identity for a software project, "
                    "derived from the project and from nothing else. This is "
                    "the reference implementation of the specification in "
                    "SPEC.md; `apply` is the command you want.",
    )
    # Both numbers, because the one people need is usually the other one: a bug
    # report about a colour is about the colour map, not the release.
    parser.add_argument("--version", action="version",
                        version=f"repository-identicon {VERSION} "
                                f"(colour map {COLOUR_MAP_LATEST})")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(target, *, path=True, render=False):
        if path:
            target.add_argument("path", nargs="?", help="project path (default: cwd)")
            target.add_argument("--seed", dest="seed",
                                help="use this seed literally, instead of the "
                                     "stored or derived one")
        else:
            target.set_defaults(seed=None)
        if render:
            target.add_argument("--chroma", type=float, default=MARK_CHROMA)
            target.add_argument("--lightness", type=float, default=MARK_LIGHTNESS)
            target.add_argument("--background", help="six digit hex; default transparent")
        else:
            target.set_defaults(chroma=MARK_CHROMA, lightness=MARK_LIGHTNESS, background=None)

    apply_cmd = sub.add_parser(
        "apply", help="create or update the identicon files in a repository")
    # `apply` writes the committed artifacts, so it takes no drawing options.
    # Another chroma, lightness, background or block writes files the stored
    # seed does not derive, and the output is indistinguishable from
    # conforming output. `render` and `show` keep all four: their output is not
    # committed.
    add_common(apply_cmd, render=False)
    apply_cmd.set_defaults(block=ARTIFACT_BLOCK)
    apply_cmd.add_argument("--check", action="store_true",
                           help="report what would change, write nothing, and "
                                "exit 1 if not current")
    # A source, not a flag: the four sources are what a person is choosing
    # between when they decide to change an identity, and `--reseed` alone
    # means the same `auto` that seeded the repository in the first place.
    apply_cmd.add_argument("--reseed", nargs="?", const="auto",
                           choices=SEED_SOURCES, metavar="SOURCE",
                           help="retire the current seed to "
                                "identiconSeedHistory and derive a new one "
                                f"from: {', '.join(SEED_SOURCES)} "
                                "(default: auto)")
    apply_cmd.add_argument("--no-readme", action="store_true",
                           help="do not add the mark to the README")
    apply_cmd.add_argument("--json", action="store_true",
                           help="machine-readable result, for a dependent tool")
    apply_cmd.set_defaults(func=cmd_apply)

    show = sub.add_parser("show", help="print the derived names and a terminal preview")
    add_common(show, render=True)
    show.set_defaults(func=cmd_show)

    render = sub.add_parser("render", help="write one identicon image")
    add_common(render, render=True)
    render.add_argument("--block", type=int, default=ARTIFACT_BLOCK,
                        choices=BLOCKS, help="block size in pixels")
    render.add_argument("--format", choices=("png", "svg"), default="png")
    render.add_argument("--out", default="-", help="output file, or - for stdout")
    render.set_defaults(func=cmd_render)

    validate = sub.add_parser(
        "validate",
        help="check another implementation against the pinned vectors",
        description="Runs your implementation once per vector with the seed "
                    "as its last argument. It must print "
                    '{"matrix": [...], "colour": "#rrggbb"} on stdout.')
    add_common(validate, path=False)
    validate.add_argument("--vectors", help=f"default: {VECTORS_NAME} beside this script")
    validate.add_argument("--json", action="store_true")
    validate.add_argument("command", nargs="*", help="the command to run")
    validate.set_defaults(func=cmd_validate)

    doctor = sub.add_parser("doctor", help="environment report")
    add_common(doctor)
    doctor.set_defaults(func=cmd_doctor)

    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except UnknownColourMap as error:
        # A hand edit naming a map that does not exist is an ordinary mistake
        # with a known answer, not a crash. Say the answer rather than
        # printing a traceback at it.
        print(f"error: {error}", file=sys.stderr)
        print(f"       edit colourMap in .identicon/{SETTINGS_NAME}",
              file=sys.stderr)
        return 1
    except NotSeeded as error:
        # `show` and `render` read a seed and never derive one, so an unseeded
        # repository is a question for `apply`.
        print(f"error: {error}", file=sys.stderr)
        print("       repository-identicon apply", file=sys.stderr)
        return 1
    except ValueError as error:
        # `--reseed repo` where there is no remote, and the like: the user
        # named a source that cannot answer.
        print(f"error: {error}", file=sys.stderr)
        return 1
    except BrokenPipeError:
        # Piping into head closes the pipe early. Retarget stdout at devnull so
        # the interpreter's own flush at exit does not report it a second time.
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Reference implementation of the repository identicon specification.

A key -- `<mapping version>:host/owner/repo` -- becomes a 5x5 grid and one
colour, plus the artifacts a repository commits and the renderings a terminal
can show. Run `python3 repository-identicon.py apply` inside a repository.

  repository  apply, show, render, validate, doctor
  hook        emit, hooks

**Nothing here writes outside the repository it is run in.** Putting the mark
on a desktop -- the XDG icon theme, a Konsole tab -- is a side effect, which
SPEC.md's Scope section puts out of the specification; that half lives in
Console-Colophon and is reached by vendoring this derivation, not by importing
it. `work-in-progress/scope-split.md` records where each symbol went.

Standard library only. The only subprocess is git, invoked with an argument
list.
"""

import argparse
import base64
import hashlib
import json
import math
import os
import pathlib
import re
import struct
import subprocess
import sys
import zlib

# ---- Identicon derivation ----
#
# GitHub-style: a 5x5 grid, left three columns drawn from the digest and
# mirrored onto the right two, so every identicon is vertically symmetric.
# The rule below is ours and is pinned by the test suite; it is not claimed to
# reproduce GitHub's output byte for byte.

GRID = 5

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
    if GRID * block + 2 * border != canvas:
        raise ValueError(f"{canvas} is not a multiple of 32 and has no exact "
                         f"block and border on a {GRID}x{GRID} grid")
    return block, border


# An icon *theme* namespace, not a filename. **This is the one value a
# vendoring tool is expected to change**, so two tools installing icons for one
# project do not collide -- Console-Colophon's copy says `console-colophon` and
# Claude-State-Panel's says `claude-state-identicon`. Nothing in this file
# installs an icon; the prefix is here because SPEC.md fixes the name it forms.
ICON_PREFIX = "repository-identicon"


# ---- Seed and key ----

# An optional one-line seed at the repository top level, overriding the derived
# key. Committing it makes a project's identicon travel with the repository.
#
# `.claude-state-identicon` is still honoured on read: it is committed into
# other people's repositories, so dropping it would silently change their
# identicon, which is the one thing an override exists to prevent.
OVERRIDE_FILENAME = ".repository-identicon"
LEGACY_OVERRIDE_FILENAMES = (".claude-state-identicon",)


def normalise_seed(path):
    """Reduce a filesystem path to a stable string.

    Expanded, made absolute, and stripped of any trailing separator, so that
    `~/src/foo`, `~/src/foo/` and a relative path to the same place all agree.

    This is the *fallback* seed. Prefer resolve_seed, which reaches the
    repository identity first — a path is not stable across machines,
    containers, or the per-session git worktrees the desktop app creates.
    """
    expanded = os.path.expanduser(str(path))
    absolute = os.path.abspath(expanded)
    return absolute.rstrip(os.sep) or os.sep


def normalise_remote_url(url):
    """Reduce a git remote URL to `host/owner/repo`, lowercased.

    Every way of naming one repository must collapse to one key, so an SSH
    checkout and an HTTPS checkout of the same project share an identicon:

        git@github.com:Owner/Repo.git
        https://github.com/Owner/Repo.git
        https://token@github.com/Owner/Repo
        ssh://git@github.com:2222/Owner/Repo.git   ->  github.com/owner/repo

    The host is kept, so `github.com/a/b` and `gitlab.com/a/b` stay distinct.
    Returns None for a local-path remote, which is no more portable than the
    working directory and so earns no special treatment.
    """
    if not url:
        return None
    url = url.strip().rstrip("/")
    if not url or url.startswith("/") or url.startswith("file://"):
        return None

    if "://" in url:
        scheme, _, rest = url.partition("://")
        if scheme.lower() == "file":
            return None
        authority, _, path = rest.partition("/")
    elif ":" in url:
        # scp-like: [user@]host:path
        authority, _, path = url.partition(":")
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
    return "/".join([host] + parts).lower()


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


def repo_toplevel(path):
    """The working tree root, or None outside a repository.

    In a worktree this is the worktree's own root, not the main checkout — which
    is exactly why it is not the key.
    """
    return _git(["rev-parse", "--show-toplevel"], path)


def repo_remote_url(path):
    """The origin URL, falling back to whichever remote is listed first."""
    url = _git(["remote", "get-url", "origin"], path)
    if url:
        return url
    remotes = _git(["remote"], path)
    if not remotes:
        return None
    return _git(["remote", "get-url", remotes.splitlines()[0].strip()], path)


def override_seed(directory):
    """The committed seed at `directory`, if there is a usable one.

    The current name wins; a legacy name is honoured only when the current one
    is absent, so a repository carrying both is not left guessing.
    """
    if not directory:
        return None
    for name in (OVERRIDE_FILENAME, *LEGACY_OVERRIDE_FILENAMES):
        try:
            text = (pathlib.Path(directory) / name).read_text()
        except (OSError, UnicodeDecodeError):
            continue
        for line in text.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                return line
    return None


def resolve_seed(path=None, explicit=None):
    """Return (seed, source) for a project directory.

    The seed is the identity -- `github.com/owner/repo`. It is not the key:
    `stamp_key` adds the mapping version to make one, and once a repository is
    seeded the recorded key outranks anything derived here.

    Precedence, most specific first:

      explicit   given on the command line
      override   a committed .repository-identicon at the repository root
      remote     host/owner/repo from the git remote -- the portable one
      toplevel   the repository root path, for a repository with no remote
      path       the directory itself, outside a repository

    Only `remote` and `override` survive being cloned somewhere else. The two
    path-shaped sources are honest fallbacks, not equivalents.
    """
    directory = normalise_seed(path if path else os.getcwd())
    if explicit:
        return explicit, "explicit"

    toplevel = repo_toplevel(directory)

    committed = override_seed(toplevel or directory)
    if committed:
        return committed, "override"

    if toplevel:
        remote = normalise_remote_url(repo_remote_url(directory))
        if remote:
            return remote, "remote"
        return normalise_seed(toplevel), "toplevel"

    return directory, "path"


# **The mapping version lives in the key file, and the file wins.** It is
# written *into* the key -- `<version>:github.com/owner/repo` -- and the key is
# hashed verbatim, so a mark cannot move unless that tracked line moves. This
# constant only says what a *newly seeded* repository is stamped with;
# `apply --remap` is the only thing that moves an existing one. The version
# sits outside the seed, so drift is compared on seeds and a remap never reads
# as a rename. An unstamped key is version 0 and still draws what it always
# drew. Conformance is unaffected: the reference consumes a digest, and only
# the string being digested changed.
MAPPING_VERSION = 3

# **Three version numbers, and they count different things.**
#
#   VERSION          this tool, as a release. Nothing is released.
#   MAPPING_VERSION  the colour rule, stamped into every key. An integer,
#                    because the key format is `<digits>:seed`.
#   wheel version    which tricolours stand over the gamut, in
#                    `work-in-progress/wheel.tsv`. Currently 0.3, and not read
#                    by this file at all.
VERSION = "0.0.build"

# `<digits>:` and nothing else, anchored, so a seed that happens to contain a
# colon -- a scheme, a Windows path -- is never mistaken for a stamped key.
KEY_STAMP = re.compile(r"^([0-9]+):(.*)$", re.DOTALL)


def stamp_key(seed, version=None):
    """The key a freshly seeded repository records: version, colon, seed.

    The default is read at call time rather than bound to the signature, so
    there is exactly one place the current version lives.
    """
    if version is None:
        version = MAPPING_VERSION
    return f"{version}:{seed}"


def parse_key(key):
    """Split a key into (mapping_version, seed).

    An unstamped key is version 0 -- the mapping that existed before the
    version did -- and is its own seed.
    """
    match = KEY_STAMP.match(key)
    if not match:
        return 0, key
    return int(match.group(1)), match.group(2)


def _digest(key):
    """MD5 of the key as lowercase hex. Nothing is prepended here.

    Hex rather than bytes because the reference consumes the digest as *hex
    characters* -- one nibble per grid cell, and the last seven characters as
    the hue.
    """
    return hashlib.md5(key.encode("utf-8")).hexdigest()


def identicon_grid(key):
    """Return the 5x5 grid as a list of rows of bools.

    Conforms to stewartlord/identicon.js, whose own comment reads:

        the first 15 characters of the hash control the pixels (even/odd)
        they are drawn down the middle first, then mirrored outwards

    So characters 0-4 fill the centre column top to bottom, 5-9 fill column 1
    and mirror it to 3, and 10-14 fill column 0 and mirror it to 4. Even is
    foreground. Pinned in vectors.json.
    """
    digest = _digest(key)
    grid = [[False] * GRID for _ in range(GRID)]
    for index in range(15):
        painted = int(digest[index], 16) % 2 == 0
        column, row = divmod(index, GRID)
        grid[row][2 - column] = painted
        grid[row][2 + column] = painted
    return grid


def grid_text(grid):
    """The grid as five lines of `01010`, the spelling `vectors.json` uses.

    Rows of characters rather than JSON, to match the `.colour` artifact beside
    it: both are a bare value a reader can take in at a glance and a shell can
    handle without a parser.
    """
    return "\n".join("".join("1" if cell else "0" for cell in row)
                     for row in grid)


def identicon_hue(key):
    """Hue as a fraction of a turn, from the last seven hex characters.

    28 bits over 0xfffffff, per the reference. Drawn from the same digest as
    the grid, so colour and pattern cannot drift apart.
    """
    return int(_digest(key)[-7:], 16) / 0xFFFFFFF


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
# draw off the digest is uniform over the circle, but the emoji-square
# vocabulary has nothing between green and blue, so every mixture of the two
# reads at essentially one hue. That is a fact about the palette, not about the
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

    `None` for `warp` is the uniform draw, which is what mapping versions
    before 3 use.
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


class UnknownMappingVersion(ValueError):
    """A key stamped at a version this build does not implement."""


def identicon_colour(key, chroma=MARK_CHROMA, lightness=MARK_LIGHTNESS):
    """Return the foreground colour as an (r, g, b) triple of 0-255 ints.

    The angle from the digest, warped, then Oklab at one lightness with the
    chroma capped.

    **No rule that reaches a release retires; a draft may be withdrawn.**
    Versions 0 to 2 were drafts -- HSL, then Oklab without the warp -- and no
    release carried them, so they are gone. Once `VERSION` leaves `0.0.*` this
    stops being true and every shipped rule has to stay.

    A key stamped at a version this build does not draw is refused rather than
    redrawn: drawing it with today's rule would move a mark without anyone
    asking, which is what the stamp exists to prevent. `remap` moves such a
    repository across deliberately.
    """
    version, _ = parse_key(key)
    if version != MAPPING_VERSION:
        raise UnknownMappingVersion(
            f"key is stamped at mapping version {version}; this build "
            f"implements {MAPPING_VERSION} only. Use `remap` to move it.")

    degrees = warp_hue(identicon_hue(key) * 360.0)
    return tuple(_encode(channel) for channel in
                 _oklch_to_linear(lightness, gamut_chroma(degrees, lightness,
                                                          chroma), degrees))


def _colour_for(key, kwargs):
    """`identicon_colour` with chroma and lightness taken from render kwargs.

    `.get` with the defaults, never `kwargs["chroma"]`: the callers are handed
    kwargs that may carry neither.
    """
    return identicon_colour(key, kwargs.get("chroma", MARK_CHROMA),
                            kwargs.get("lightness", MARK_LIGHTNESS))


# ---- Names derived from the key ----


def hex_colour(rgb):
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def short_hash(key, length=12):
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:length]


def icon_name(key):
    """Theme icon name. Konsole's profile Icon= is a theme name, not a path."""
    return f"{ICON_PREFIX}-{short_hash(key)}"


def project_name(key):
    """The last segment of the key, or the whole key if it has no separator."""
    return os.path.basename(key) or key


def badge_label(key, limit=2):
    """A one or two character label for the badge overlay.

    Initials where the project name has separators, otherwise the leading
    characters. Upper-cased, because the badge is small.
    """
    name = project_name(key)
    flat = name
    for separator in ("_", ".", " "):
        flat = flat.replace(separator, "-")
    words = [part for part in flat.split("-") if part]
    if len(words) >= 2:
        return "".join(word[0] for word in words[:limit]).upper()
    return name[:limit].upper()


# The Konsole profile names -- profile_name, profile_filename, profile_body --
# were here and are now in Console-Colophon. SPEC.md fixes the short id, the
# icon theme name and the badge label; it says nothing about how a terminal
# emulator names a profile, and neither should this file.


# ---- Rendering ----


def canvas_edge(block, border):
    """The square canvas a block and a border imply: GRID blocks plus a border.

    The block is the specified thing and the canvas is derived, never the other
    way round. Deriving the block from a canvas needs a heuristic, a heuristic
    does not scale linearly, and a mark that lands on a different block at a
    different scale is two drawings rather than one.
    """
    return GRID * block + 2 * border


def fit_block(edge, border=1):
    """The largest block that fits a canvas somebody else fixed.

    For the XDG icon theme, where the file at `48x48/apps/` has to be 48 pixels
    whatever that divides into, and for a terminal handed a pixel budget.
    """
    block = (edge - 2 * border) // GRID
    if block < 1:
        block = max(1, edge // GRID)
    return block


def render_rgba(key, block, border=BORDER, chroma=MARK_CHROMA,
                lightness=MARK_LIGHTNESS, background=None, edge=None):
    """Return raw RGBA bytes for a square identicon of `block`-pixel blocks.

    `edge` is for the callers who do not get to choose their canvas -- the icon
    theme, a terminal -- and pads the grid into a fixed square. Left alone the
    canvas is derived from the block and the border, which is the normal case
    and the only one the artifacts use.
    """
    grid = identicon_grid(key)
    red, green, blue = identicon_colour(key, chroma, lightness)
    if edge is None:
        edge, margin = canvas_edge(block, border), border
    else:
        margin = (edge - block * GRID) // 2

    if background is None:
        back = bytes((0, 0, 0, 0))
    else:
        back = bytes(tuple(background) + (255,))
    fore = bytes((red, green, blue, 255))

    rows = []
    for y in range(edge):
        row = bytearray()
        grid_y = (y - margin) // block if block else -1
        inside_y = margin <= y < margin + block * GRID
        for x in range(edge):
            grid_x = (x - margin) // block if block else -1
            inside_x = margin <= x < margin + block * GRID
            if inside_x and inside_y and grid[grid_y][grid_x]:
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


def encode_png(rgba, width, height):
    """Minimal 8-bit RGBA PNG encoder. Flat colour blocks compress to nothing."""
    stride = width * 4
    raw = b"".join(b"\x00" + rgba[y * stride:(y + 1) * stride] for y in range(height))
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", header)
        + _png_chunk(b"IDAT", zlib.compress(raw, 9))
        + _png_chunk(b"IEND", b"")
    )


def render_png(key, block, **kwargs):
    edge = kwargs.get("edge") or canvas_edge(block, kwargs.get("border", BORDER))
    return encode_png(render_rgba(key, block, **kwargs), edge, edge)


def render_svg(key, block=ARTIFACT_BLOCK, border=BORDER, chroma=MARK_CHROMA,
               lightness=MARK_LIGHTNESS, background=None):
    grid = identicon_grid(key)
    colour = hex_colour(identicon_colour(key, chroma, lightness))
    size = canvas_edge(block, border)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 {size} {size}">'
    ]
    if background is not None:
        parts.append(f'<rect width="{size}" height="{size}" '
                     f'fill="{hex_colour(background)}"/>')
    for row in range(GRID):
        for column in range(GRID):
            if grid[row][column]:
                x = border + column * block
                y = border + row * block
                parts.append(
                    f'<rect x="{x}" y="{y}" width="{block}" height="{block}" fill="{colour}"/>'
                )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_ansi(key):
    """Terminal preview, two spaces per cell on a background colour."""
    grid = identicon_grid(key)
    red, green, blue = identicon_colour(key)
    lines = []
    for row in grid:
        line = ""
        for filled in row:
            line += f"\033[48;2;{red};{green};{blue}m  \033[0m" if filled else "  "
        lines.append(line)
    return "\n".join(lines)


# ---- Terminal colour ----

TRUECOLOR = "truecolor"
INDEXED = "256"
NONE = "none"
COLOUR_DEPTHS = (TRUECOLOR, INDEXED, NONE)


def resolve_colour_depth(requested=None, environ=None):
    """Pick a colour depth. NO_COLOR wins over everything, per no-color.org."""
    environ = os.environ if environ is None else environ
    if environ.get("NO_COLOR") is not None:
        return NONE
    if requested and requested != "auto":
        return requested
    if environ.get("COLORTERM", "").lower() in ("truecolor", "24bit"):
        return TRUECOLOR
    return INDEXED


def _xterm256(rgb):
    """Nearest colour in the xterm 6x6x6 cube."""
    red, green, blue = (int(component * 5 / 255 + 0.5) for component in rgb)
    return 16 + 36 * red + 6 * green + blue


def _fg(rgb, depth):
    if depth == NONE:
        return ""
    if depth == TRUECOLOR:
        return "\033[38;2;{};{};{}m".format(*rgb)
    return f"\033[38;5;{_xterm256(rgb)}m"


RESET = "\033[0m"

CHIP = "█"

# The text rendering lives in text-identicon.py, which takes a grid and a colour
# and nothing else. Loaded by path because the file name carries a hyphen.
#
# **These two files are a pair and must be deployed together**: the octant table
# and the emoji palette live next door. `doctor` reports whether the sibling is
# present, because `emit` swallows every error and exits 0.
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
                f"the text renderings need its octant table")
        spec = importlib.util.spec_from_file_location("text_identicon", path)
        _TEXT = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_TEXT)
    return _TEXT


def render_text(key, chroma=MARK_CHROMA, lightness=MARK_LIGHTNESS):
    """The identicon as two lines of three characters: the octant grid, then
    the emoji triple.

    One glyph covers four cells, so the colour lives in the emoji squares
    rather than in an escape sequence.
    """
    grid = identicon_grid(key)
    colour = identicon_colour(key, chroma, lightness)
    return _text_module().text(grid, colour).split("\n")


def render_banner(key, source=None, depth=TRUECOLOR, **kwargs):
    """The identicon with the project name beside it."""
    rows = render_text(key, kwargs.get("chroma", MARK_CHROMA),
                       kwargs.get("lightness", MARK_LIGHTNESS))
    colour = _colour_for(key, kwargs)
    name = project_name(key)
    if depth != NONE:
        name = f"{_fg(colour, depth)}{name}{RESET}"
    labels = [name, key if source != "path" else ""]
    return [f"{row}  {label}".rstrip() for row, label in zip(rows, labels)]


def render_line(key, depth=TRUECOLOR, **kwargs):
    """One line: the colour, then the project name. For the tightest prompts.

    The grid cannot be one line -- five rows over a two-by-four lattice is two
    text lines and no arrangement makes it one -- so anything that affords a
    single line loses the pattern and keeps only the colour. A coloured chip
    where escape sequences work, the emoji triple where they do not.
    """
    colour = _colour_for(key, kwargs)
    mark = (f"{_fg(colour, depth)}{CHIP}{RESET}" if depth != NONE
            else _text_module().emoji_triple(colour))
    return [f"{mark} {project_name(key)}"]


# ---- Inline images ----
#
# The blocks above are an approximation. Where the terminal can take a real
# image, send the PNG itself, base64 in an escape sequence.
#
# Konsole implements the iTerm2 file protocol: Vt102Emulation::osc_put matches
# the literal "1337;File=" and then waits for the ":" terminator, so arguments
# between the two are tolerated and ignored. It also handles kitty APC graphics
# and sixel.

ITERM2 = "iterm2"
KITTY = "kitty"
TEXT = "text"
PROTOCOLS = (ITERM2, KITTY, TEXT)

# Native pixel size for the inline image. Konsole ignores the protocol's own
# width and height arguments, so the PNG's own size is what decides how big it
# lands: five cells of eight pixels, about two text rows tall.
INLINE_SIZE = 40


def resolve_protocol(requested=None, environ=None):
    """Pick a graphics protocol from the environment.

    Detection is by environment variable rather than by querying the terminal,
    because a hook that waits on a terminal reply can hang a turn if nothing
    answers.
    """
    environ = os.environ if environ is None else environ
    if requested and requested != "auto":
        return requested
    if environ.get("NO_COLOR") is not None:
        return TEXT
    if environ.get("KITTY_WINDOW_ID") or "kitty" in environ.get("TERM", "").lower():
        return KITTY
    if environ.get("KONSOLE_VERSION") or environ.get("KONSOLE_DBUS_SESSION"):
        return ITERM2
    if environ.get("TERM_PROGRAM", "") in ("iTerm.app", "WezTerm", "ghostty", "vscode"):
        return ITERM2
    return TEXT


def iterm2_image(png):
    """OSC 1337 File, the iTerm2 inline image protocol.

    No argument may contain a colon, since the colon is what terminates the
    argument list and begins the payload.
    """
    payload = base64.b64encode(png).decode("ascii")
    args = ";".join(["inline=1", f"size={len(png)}", "preserveAspectRatio=1"])
    return f"\033]1337;File={args}:{payload}\a"


def kitty_image(png, chunk_size=4096):
    """APC _G, the kitty graphics protocol. Chunked, as the protocol requires."""
    payload = base64.b64encode(png).decode("ascii")
    chunks = [payload[i:i + chunk_size] for i in range(0, len(payload), chunk_size)] or [""]
    out = []
    for index, chunk in enumerate(chunks):
        more = 1 if index < len(chunks) - 1 else 0
        control = f"a=T,f=100,m={more}" if index == 0 else f"m={more}"
        out.append(f"\033_G{control};{chunk}\033\\")
    return "".join(out)


def render_inline(key, protocol, size=INLINE_SIZE, **kwargs):
    """The identicon as a real image, or None if the protocol cannot carry one."""
    if protocol not in (ITERM2, KITTY):
        return None
    png = render_png(key, fit_block(size), edge=size, **kwargs)
    return iterm2_image(png) if protocol == ITERM2 else kitty_image(png)


# The lambdas normalise the signatures: `render` hands every style `source` and
# `depth`, and only `banner` wants both.
_TEXT_STYLES = {
    TEXT: lambda key, source=None, depth=TRUECOLOR, **kw: render_text(
        key, kw.get("chroma", MARK_CHROMA), kw.get("lightness", MARK_LIGHTNESS)),
    "full": lambda key, source=None, depth=TRUECOLOR, **kw: render_ansi(key).splitlines(),
    "banner": render_banner,
    "line": lambda key, source=None, depth=TRUECOLOR, **kw: render_line(key, depth, **kw),
}

STYLES = ("icon", "image", TEXT, "full", "banner", "line")


def render(key, style="icon", source=None, depth=TRUECOLOR, protocol=TEXT,
           size=INLINE_SIZE, **kwargs):
    """Return everything to write for one identicon, trailing newline included.

    The default is the icon and nothing else — no project name, no key. The
    identicon is the message; anything beside it is the terminal's own business.
    """
    if style == "icon":
        inline = render_inline(key, protocol, size, **kwargs)
        if inline is not None:
            return inline + "\n"
        style = TEXT

    if style == "image":
        inline = render_inline(key, protocol if protocol != TEXT else ITERM2,
                               size, **kwargs)
        return (inline or "") + "\n"

    lines = _TEXT_STYLES[style](key, source=source, depth=depth, **kwargs)
    return "".join(line + "\n" for line in lines)


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
    """Every artifact as (key, filename).

    One list, walked by both the path builder and the byte builder, so a file
    that exists in one and not the other cannot happen.
    """
    yield "png", f"{ARTIFACT_STEM}.png"
    yield "png4x", f"{ARTIFACT_STEM}@{ARTIFACT_SCALE}x.png"
    for canvas in LARGE_CANVASES:
        yield f"png{canvas}", f"{ARTIFACT_STEM}-{canvas}.png"
    yield "svg", f"{ARTIFACT_STEM}.svg"
    yield "colour", f"{ARTIFACT_STEM}.colour"
    yield "grid", f"{ARTIFACT_STEM}.grid"
    yield "txt", f"{ARTIFACT_STEM}.txt"


def artifact_paths(root):
    directory = pathlib.Path(root) / IDENTICON_DIR
    return {name: directory / filename for name, filename in artifact_names()}


# The whole key, mapping version included, hashed verbatim: this file is not a
# record of what the mark was built from, it *is* what the mark is built from.
KEY_NAME = f"{ARTIFACT_STEM}.key"

# Written once, at seeding. The payload line is the key; everything above it is
# for whoever opens the file wondering what they are looking at.
KEY_FILE_TEMPLATE = (
    "# This repository's identicon is derived from the line below, hashed\n"
    "# exactly as it reads. `<version>:<seed>` -- the mapping version, then\n"
    "# the identity. Nothing changes this mark except changing this line.\n"
    "{key}\n"
)


def key_path(root):
    return pathlib.Path(root) / IDENTICON_DIR / KEY_NAME


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


def recorded_key(root):
    """The recorded key, verbatim, or None if this repository is not seeded."""
    path = key_path(root)
    if not path.is_file():
        return None
    for line in path.read_text(errors="replace").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return line
    return None


def resolve_key_for(path=None, explicit=None):
    """Return (key, source) for a directory: what it actually draws with.

    A seeded repository's recorded key outranks any re-derivation, here as in
    `apply`, so `show`, `render` and the hook cannot disagree with what is on
    disk -- including about which mapping version drew it.
    """
    seed, source = resolve_seed(path, explicit)
    if not explicit:
        recorded = recorded_key(repo_toplevel(path) or (path or os.getcwd()))
        if recorded is not None:
            return recorded, "key"
    return stamp_key(seed), source


def artifact_bytes(key, block=ARTIFACT_BLOCK, **render_kwargs):
    """What each artifact should contain for this key.

    Separate files rather than one blob: a README cannot address a fragment
    inside a blob, and `$(cat …/*.colour)` has to stay a cat.

    `.txt` is the text rendering, for a medium that will take neither an image
    nor an escape sequence. `text-identicon.py` is named for this artifact
    rather than for its technique, and then nothing wrote it: the installer was
    built around the three files that already existed, so the module and the
    directory disagreed about what the set was.
    """
    wanted = {
        "png": render_png(key, block, **render_kwargs),
        "png4x": render_png(key, block * ARTIFACT_SCALE, border=SCALED_BORDER,
                            **render_kwargs),
        "svg": render_svg(key, block, **render_kwargs).encode("utf-8"),
    }
    for canvas in LARGE_CANVASES:
        large_block, large_border = large_geometry(canvas)
        wanted[f"png{canvas}"] = render_png(key, large_block,
                                            border=large_border, **render_kwargs)
    colour = _colour_for(key, render_kwargs)
    grid = identicon_grid(key)
    wanted["colour"] = (hex_colour(colour) + "\n").encode("utf-8")
    wanted["grid"] = (grid_text(grid) + "\n").encode("utf-8")
    wanted["txt"] = (_text_module().text(grid, colour) + "\n").encode("utf-8")
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
                      reseed=False, remap=False, readme=True, **render_kwargs):
    """Create or update the identicon artifacts in one repository.

    **Two things you might want from a re-run, and they are separate.** The key
    is recorded on the first run and reused verbatim on every run after it, so
    refreshing the artifacts reaches every repository without disturbing any
    identity. `reseed` adopts today's seed at today's mapping version; `remap`
    keeps the recorded seed and moves it to today's mapping.

    Renaming the repository, moving forges, cloning to a path that would
    resolve differently, or a new mapping version shipping here all change what
    the key *would* be; that is reported as `seed_drift`/`mapping_drift` and
    never acted on.

    For a fixed key this writes identical bytes on every run and reports
    nothing changed. `check` writes nothing at all.

    Returns a dict describing what happened, suitable for --json.
    """
    root = repo_toplevel(path) or (path or os.getcwd())
    derived_seed, derived_source = resolve_seed(path, seed)

    recorded = None if seed else recorded_key(root)
    if seed or reseed or recorded is None:
        # Nothing recorded, or something asked for today's seed: stamp it with
        # the version this implementation seeds at.
        key, source = stamp_key(derived_seed), derived_source
    elif remap:
        # The identity stands; only the mapping moves.
        key, source = stamp_key(parse_key(recorded)[1]), "remap"
    else:
        # The file wins, prefix and all.
        key, source = recorded, "key"

    mapping_version, resolved_seed = parse_key(key)

    # **A withdrawn mapping stops here, with the way out named.** Drawing the
    # repository with today's rule would move its mark without anyone asking.
    # Only drafts are ever withdrawn, so this strands only repositories seeded
    # from a pre-release build -- after a release the old rule stays and this
    # branch becomes unreachable for that version.
    if mapping_version != MAPPING_VERSION:
        raise UnknownMappingVersion(
            f"{root} is recorded at mapping version {mapping_version} and this "
            f"build draws {MAPPING_VERSION} only. `remap` keeps the seed and "
            f"moves it; nothing else will.")

    # What this repository would derive today, reported and never acted on: an
    # identity that changes itself is not one, and neither is a mark that
    # redraws itself because a constant moved somewhere else.
    seed_drift = derived_seed if derived_seed != resolved_seed else None
    mapping_drift = (MAPPING_VERSION if mapping_version != MAPPING_VERSION
                     else None)

    # An override outranks the remote, which is the point of it. Where one is
    # in force and the remote disagrees, say so rather than resolve it -- the
    # file is the record of a decision somebody made on purpose.
    masking = None
    if derived_source == "override":
        url = repo_remote_url(path)
        remote_seed = normalise_remote_url(url) if url else None
        if remote_seed and remote_seed != derived_seed:
            masking = remote_seed

    paths = artifact_paths(root)
    wanted = artifact_bytes(key, block, **render_kwargs)

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

    # The key is written last and only when the artifacts it describes are
    # there, so a half-written directory never claims to be seeded.
    #
    # An already-seeded repository is left byte-for-byte alone, comment lines
    # included. Rewriting the preamble under somebody would make every run a
    # diff, and this file's whole job is to be the thing that does not move.
    key_file = key_path(root)
    current_key_bytes = key_file.read_bytes() if key_file.is_file() else None
    if current_key_bytes is not None and recorded == key:
        key_state = "unchanged"
    else:
        key_wanted = KEY_FILE_TEMPLATE.format(key=key).encode("utf-8")
        key_state = ("created" if current_key_bytes is None
                     else "unchanged" if current_key_bytes == key_wanted
                     else "updated")
        if key_state != "unchanged" and not check:
            key_file.parent.mkdir(parents=True, exist_ok=True)
            keep_prior(key_file, current_key_bytes)
            key_file.write_bytes(key_wanted)
    changes["key"] = key_state
    paths["key"] = key_file

    if readme:
        state, readme_file = readme_state(root, check)
        if readme_file is not None:
            changes["readme"] = state
            paths["readme"] = readme_file

    colour = _colour_for(key, render_kwargs)
    return {
        "key": key,
        "seed": resolved_seed,
        "mapping_version": mapping_version,
        "source": source,
        "root": str(root),
        "colour": hex_colour(colour),
        "files": {name: str(target) for name, target in paths.items()},
        "changes": changes,
        "current": all(state == "unchanged" for state in changes.values()),
        "checked": bool(check),
        "masking": masking,
        "seed_drift": seed_drift,
        "mapping_drift": mapping_drift,
        "reseeded": bool(reseed),
        "remapped": bool(remap),
    }


# ---- Commands ----


def _resolve_from_args(args):
    return resolve_key_for(getattr(args, "path", None),
                           getattr(args, "seed", None))


def _key_from_args(args):
    return _resolve_from_args(args)[0]


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


SOURCE_NOTES = {
    "key": "the recorded key, which outranks all of the below",
    "remap": "the recorded seed, restamped at this mapping version",
    "explicit": "given on the command line",
    "override": f"committed {OVERRIDE_FILENAME}",
    "remote": "git remote, portable across checkouts",
    "toplevel": "repository root path, no remote to use",
    "path": "not a repository, so the path is all there is",
}


def cmd_show(args):
    key, source = _resolve_from_args(args)
    print(f"key       {key}")
    note = SOURCE_NOTES.get(source)
    print(f"source    {source}" + (f"  ({note})" if note else ""))
    print(f"project   {project_name(key)}")
    print(f"icon      {icon_name(key)}")
    print(f"badge     {badge_label(key)}")
    print(f"colour    {hex_colour(identicon_colour(key, args.chroma, args.lightness))}")
    print()
    print(render_ansi(key))
    return 0


def cmd_render(args):
    key = _key_from_args(args)
    kwargs = _render_kwargs(args)
    if args.edge:
        block, extra = fit_block(args.edge), {"edge": args.edge}
    else:
        block, extra = args.block, {}
    if args.format == "svg":
        data = render_svg(key, block, **kwargs).encode("utf-8")
    else:
        data = render_png(key, block, **extra, **kwargs)
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
                               args.reseed, args.remap, not args.no_readme,
                               **_render_kwargs(args))
    if args.json:
        print(json.dumps(result, indent=2))
        return 0 if result["current"] or not args.check else 1

    verb = "would be" if args.check else ""
    print(f"key      {result['key']}  ({result['source']})")
    print(f"seed     {result['seed']}")
    print(f"mapping  {result['mapping_version']}")
    print(f"colour   {result['colour']}")
    for name, state in sorted(result["changes"].items()):
        mark = " " if state == "unchanged" else "*"
        print(f" {mark} {result['files'][name]}  {verb} {state}".rstrip())
    if result["seed_drift"]:
        print()
        print(f"The recorded seed is {result['seed']}, but this repository "
              f"would seed as {result['seed_drift']} today.")
        print("The identicon is unchanged, which is the point: a mark that "
              "re-derived itself would not be an identity. Run "
              "`apply --reseed` to adopt the new seed and change the mark.")
    elif result["masking"]:
        print()
        print(f"{OVERRIDE_FILENAME} pins this repository to "
              f"{result['seed']}, but its remote now says "
              f"{result['masking']}.")
        print("The override wins, which is what it is for. If the move was "
              "meant to change the identity, delete the file and re-run; if "
              "it was not, nothing needs doing.")
    elif result["source"] not in ("remote", "override", "key", "remap"):
        print()
        print(f"This repository has no usable git remote, so the seed is a "
              f"path and will not survive being cloned elsewhere. Commit a "
              f"{OVERRIDE_FILENAME} file holding the seed to pin it.")
    if result["mapping_drift"]:
        print()
        print(f"This repository is drawn by mapping version "
              f"{result['mapping_version']}; this implementation seeds new "
              f"repositories at version {result['mapping_drift']}.")
        print("Nothing is out of date. The recorded key is what the mark is, "
              "so a newer mapping reaches this repository only when somebody "
              "decides it should: run `apply --remap`, and the changed line "
              "in the key file is the record of that decision.")
    return 0 if result["current"] or not args.check else 1


# Hook events at which control comes back to the human. Notification is left
# out deliberately: idle_prompt fires exactly 60s after Stop, so registering it
# would print the same identicon twice, a minute apart.
RETURN_OF_CONTROL_EVENTS = ("Stop", "PermissionRequest", "Elicitation", "SessionEnd")


def payload_cwd(stream):
    """The cwd from a hook payload on stdin, or None.

    Every hook payload carries cwd, session_id and hook_event_name — the probe
    confirmed that across 27 records. Nothing else here is read, and in
    particular nothing that could carry prompt or tool text.
    """
    try:
        payload = json.load(stream)
    except (ValueError, OSError, UnicodeDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    cwd = payload.get("cwd")
    return cwd if isinstance(cwd, str) and cwd else None


def open_output():
    """The controlling terminal if there is one, else stdout.

    A hook's stdout is not reliably shown, and for some events it is fed back to
    the model instead. The terminal is where a return-of-control marker belongs,
    so go there directly when it exists.
    """
    try:
        return open("/dev/tty", "w"), True
    except OSError:
        return sys.stdout, False


def cmd_emit(args):
    """Print the identicon. Intended for a return-of-control hook.

    Exits 0 whatever happens. A hook that fails must not disturb the session,
    and a missing identicon is not worth a broken turn.
    """
    try:
        path = args.path
        if not path and not sys.stdin.isatty():
            path = payload_cwd(sys.stdin)
        key, source = resolve_key_for(path, args.seed)

        text = render(
            key,
            style=args.style,
            source=source,
            depth=resolve_colour_depth(args.colour),
            protocol=resolve_protocol(args.protocol),
            size=args.size,
            chroma=args.chroma,
            lightness=args.lightness,
        )

        stream, is_tty = open_output()
        try:
            stream.write(text)
            stream.flush()
        finally:
            if is_tty:
                stream.close()
    except Exception:  # noqa: BLE001 - a hook must never break the session
        pass
    return 0


def cmd_hooks(args):
    """Print the registration to paste into settings, rather than writing it.

    Deliberately not self-installing. The Phase 0 probe is registered on these
    same events right now, and silently editing settings from here could not be
    tested against a running Claude Code.
    """
    command = str(pathlib.Path(__file__).resolve())
    entry = {
        "hooks": [{
            "type": "command",
            "command": command,
            "args": ["emit", "--style", args.style],
        }]
    }
    print(json.dumps({event: [entry] for event in RETURN_OF_CONTROL_EVENTS}, indent=2))
    print()
    print("Merge into the hooks object in ~/.claude/settings.json.")
    print("Notification is omitted on purpose: idle_prompt fires 60s after Stop,")
    print("so registering both prints the same identicon twice.")
    print()
    print("The Phase 0 probe is registered on these events too. Check for a")
    print("collision before adding these, per the README.")
    return 0


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

    # One rule, so one version, and every vector must be stamped at it. A bump
    # that does not bring its vectors fails here rather than in the wild.
    covered = sorted({parse_key(vector["key"])[0] for vector in vectors})
    if covered != [MAPPING_VERSION]:
        raise ValueError(
            f"{path} pins mapping versions {covered} and this implementation "
            f"draws {MAPPING_VERSION} only; a bump has to bring its vectors "
            f"with it, and retired versions have to leave")
    return document


def _cell(value):
    """One cell as "0" or "1".

    A string cell is read by value, not by truthiness. `"0"` is a true Python
    string, so a port emitting `[["0", "1", ...], ...]` -- a perfectly
    reasonable shape -- would otherwise be told its grid was solid, which is
    a wrong answer dressed up as a real one.
    """
    if isinstance(value, str):
        text = value.strip()
        if text not in ("0", "1"):
            raise TypeError(f"cell {value!r} is neither 0 nor 1")
        return text
    return "1" if value else "0"


def _normalise_grid(value):
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
    """Compare one implementation's output for one key. Returns a problem list."""
    try:
        got = json.loads(text)
    except ValueError as error:
        return [f"output is not JSON: {error}"]
    if not isinstance(got, dict):
        return ["output is not a JSON object"]

    problems = []
    if "grid" not in got:
        problems.append("no 'grid' in output")
    else:
        try:
            rows = _normalise_grid(got["grid"])
        except TypeError:
            problems.append("'grid' is not five rows of five cells")
            rows = None
        if rows is not None and rows != vector["grid"]:
            problems.append(f"grid {rows} != {vector['grid']}")

    colour = got.get("colour", got.get("color"))
    if colour is None:
        problems.append("no 'colour' in output")
    else:
        wanted = vector["foreground"].lower()
        if str(colour).lower().lstrip("#") != wanted.lstrip("#"):
            problems.append(f"colour {colour} != {vector['foreground']}")
    return problems


def validate_command(argv, vectors, timeout=30):
    """Run `argv + [key]` once per vector and collect the results.

    The key, not the seed. A port hashes what it is handed and has no business
    knowing about mapping versions -- that is the point of putting the version
    in the key rather than in everybody's code.
    """
    results = []
    for vector in vectors:
        key = vector["key"]
        try:
            completed = subprocess.run([*argv, key],
                                       capture_output=True, text=True,
                                       timeout=timeout)
        except (OSError, subprocess.SubprocessError) as error:
            results.append({"key": key, "problems": [str(error)]})
            continue
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()
            results.append({"key": key,
                            "problems": [f"exited {completed.returncode}: {detail}"]})
            continue
        results.append({"key": key,
                        "problems": check_output(completed.stdout, vector)})
    return results


def cmd_validate(args):
    vectors = load_vectors(args.vectors)["vectors"]
    if not args.command:
        print("give the command that runs your implementation, for example:\n"
              "  repository-identicon validate -- ./my-identicon --json\n"
              "It is run once per vector with the key as its last argument, and\n"
              "must print {\"grid\": [...], \"colour\": \"#rrggbb\"} on stdout.",
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
                print(f"FAIL {result['key']}")
                for problem in result["problems"]:
                    print(f"       {problem}")
            else:
                print(f"ok   {result['key']}")
        print()
        print(f"{len(results) - len(failed)}/{len(results)} vectors reproduced")
        if failed:
            print("This is not a repository identicon until they all pass.")
    return 1 if failed else 0


def cmd_doctor(args):
    """Report what this tool depends on that is not in this file.

    Short, because there is little left to depend on: the sibling module and
    the vectors. Anything about a desktop belongs to Console-Colophon, which
    has a `doctor` of its own.
    """
    sibling = text_module_path()
    print(f"{TEXT_MODULE:16} " + (str(sibling) if sibling.is_file()
                                  else "NOT FOUND - text styles will print nothing"))
    vectors = vectors_path()
    print(f"{VECTORS_NAME:16} " + (str(vectors) if vectors.is_file()
                                   else "NOT FOUND - validate cannot run"))
    print(f"{'mapping version':16} {MAPPING_VERSION}")
    key, source = resolve_key_for(getattr(args, "path", None))
    print(f"{'key here':16} {key}  ({source})")
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
    # report about a colour is about the mapping version, not the release.
    parser.add_argument("--version", action="version",
                        version=f"repository-identicon {VERSION} "
                                f"(mapping version {MAPPING_VERSION})")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(target, *, path=True, render=False):
        if path:
            target.add_argument("path", nargs="?", help="project path (default: cwd)")
            # `--key` was the published name for this before the key and the
            # seed became different things. It has always meant the identity,
            # which is the seed, so it stays as an alias rather than breaking.
            target.add_argument("--seed", "--key", dest="seed",
                                help="override the derived seed outright")
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
    add_common(apply_cmd, render=True)
    apply_cmd.add_argument("--block", type=int, default=ARTIFACT_BLOCK,
                           choices=BLOCKS,
                           help=f"block size in pixels; default "
                                f"{ARTIFACT_BLOCK}. The canvas follows.")
    apply_cmd.add_argument("--check", action="store_true",
                           help="report what would change, write nothing, and "
                                "exit 1 if not current")
    apply_cmd.add_argument("--reseed", action="store_true",
                           help="re-derive the seed and change the mark")
    apply_cmd.add_argument("--remap", action="store_true",
                           help=f"keep the seed, move it to mapping version "
                                f"{MAPPING_VERSION}, and change the mark")
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
    render.add_argument("--edge", type=int,
                        help="fit the grid to this exact canvas instead, for "
                             "somewhere the size is not ours to choose")
    render.add_argument("--format", choices=("png", "svg"), default="png")
    render.add_argument("--out", default="-", help="output file, or - for stdout")
    render.set_defaults(func=cmd_render)

    emit = sub.add_parser(
        "emit",
        help="print the identicon; for a return-of-control hook",
        description="Reads a hook payload on stdin and uses its cwd. Writes to "
                    "the controlling terminal when there is one. Always exits 0.",
    )
    add_common(emit, render=True)
    emit.add_argument("--style", choices=STYLES, default="icon",
                      help="icon sends a real image where the terminal takes one")
    emit.add_argument("--protocol", choices=("auto", *PROTOCOLS), default="auto")
    emit.add_argument("--size", type=int, default=INLINE_SIZE,
                      help="inline image side in pixels")
    emit.add_argument("--colour", choices=("auto", *COLOUR_DEPTHS), default="auto")
    emit.set_defaults(func=cmd_emit)

    hooks = sub.add_parser("hooks", help="print the hook registration to paste")
    add_common(hooks, path=False)
    hooks.add_argument("--style", choices=STYLES, default="icon")
    hooks.set_defaults(func=cmd_hooks)

    validate = sub.add_parser(
        "validate",
        help="check another implementation against the pinned vectors",
        description="Runs your implementation once per vector with the key as "
                    "its last argument. It must print "
                    '{"grid": [...], "colour": "#rrggbb"} on stdout.')
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
    except UnknownMappingVersion as error:
        # A stranded repository is an ordinary situation with a known answer,
        # not a crash. Say the answer rather than printing a traceback at it.
        print(f"error: {error}", file=sys.stderr)
        print("       repository-identicon apply --remap", file=sys.stderr)
        return 1
    except BrokenPipeError:
        # Piping into head closes the pipe early. Retarget stdout at devnull so
        # the interpreter's own flush at exit does not report it a second time.
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        return 0


if __name__ == "__main__":
    sys.exit(main())

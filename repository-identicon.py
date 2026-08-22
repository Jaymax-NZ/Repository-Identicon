#!/usr/bin/env python3
"""Per-project identicons for Konsole tabs.

A testbed for the two compile-free routes to a per-tab project marker, both
reached over Konsole's session D-Bus interface:

  badge    org.kde.konsole.Session exposes setBadgeText, setBadgeColor and
           friends as Q_SCRIPTABLE. Paints over the terminal view.
  profile  setProfile is Q_SCRIPTABLE while setIconName is not, so the tab-bar
           icon is reachable only by generating a profile that carries Icon=.

The third route, an identicon on the session toolbar itself, needs a C++
IKonsolePlugin. Konsole installs no plugin headers, so that one cannot be built
out of tree at all. See docs/konsole-identicons.md.

Standard library only. Every subprocess is invoked with an argument list.
"""

import argparse
import base64
import hashlib
import json
import math
import os
import pathlib
import re
import shutil
import struct
import subprocess
import sys
import zlib

# ---------------------------------------------------------------------------
# Identicon derivation
#
# GitHub-style: a 5x5 grid, left three columns drawn from the digest and
# mirrored onto the right two, so every identicon is vertically symmetric.
# The rule below is ours and is pinned by the test suite; it is not claimed to
# reproduce GitHub's output byte for byte.
# ---------------------------------------------------------------------------

GRID = 5

# **The block is specified and the canvas is derived, never the other way
# round.** A canvas-first tool has to guess the block back out, the guess does
# not scale linearly, and a mark that lands on a different block at a different
# scale is two drawings of one thing.
BLOCKS = (1, 2, 3, 4, 5)
BORDER = 1
ARTIFACT_BLOCK = 5

# The 4x artifact multiplies the block by four and the border by two. The
# border is chrome rather than content, so quadrupling it would spend the new
# pixels on empty edge instead of on the mark.
ARTIFACT_SCALE = 4
SCALED_BORDER = 2

# **Canvases a consumer fixes rather than derives.** A forge that asks for a
# logo of a certain size, a desktop with sized icon directories, an .ico or an
# .icns member: none of them will take a 27-pixel raster or a vector.
#
# They need no fitting and no heuristic, because they come out of the same rule
# as everything else. For any canvas that is a multiple of 32,
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

# An icon *theme* namespace, not a filename: it prefixes every PNG installed
# into the user's theme and every Konsole profile written.
#
# **This is the one value a vendoring tool is expected to change.** The
# specification fixes the short id and leaves the prefix to the implementing
# tool, precisely so two tools installing icons for one project do not collide.
# Claude-State-Panel's copy says `claude-state-identicon`, and changing it there
# would orphan every icon already installed under that name. Conformance between
# copies is established by `vectors.json`, which is about the derivation; this
# line is not part of it.
ICON_PREFIX = "repository-identicon"
INSTALL_SIZES = (16, 22, 24, 32, 48, 64, 128, 256)

# An optional one-line seed at the repository top level, overriding the derived
# key. Committing it makes a project's identicon travel with the repository.
#
# Renamed away from `.claude-state-identicon`, which named one consumer of a
# specification that has several and none of which is Claude. The old name is
# still honoured on read: it is a file committed into other people's
# repositories, so dropping it would silently change their identicon, which is
# the one thing an override exists to prevent.
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

    `cwd` of None means the current directory. It used to be interpolated
    straight into `git -C`, so a caller that passed None ran `git -C None`,
    which fails and comes back indistinguishable from "not a repository" --
    silent, and wrong in the direction that looks like a valid answer.
    `resolve_seed` never hit it because it normalises the path first; anything
    calling these helpers directly did.
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


# **The mapping version lives in the key file, and the file wins.**
#
# A change to the derivation is a change to every project's identity, and
# nothing stopped one happening quietly: edit a constant, regenerate the
# vectors in the same commit, and CI goes green while every mark in the world
# moves. Discipline was the only guard, and discipline is not a mechanism.
#
# So the version is written *into* the key -- `1:github.com/owner/repo` -- and
# the key is hashed verbatim, prefix and all. A repository's mark cannot
# change unless that line changes, and that line is a tracked file, so the
# change is a diff somebody reviews. The constant below does not reach
# anybody: it only says what a *newly seeded* repository is stamped with.
# `apply --remap` is the deliberate act that moves an existing one.
#
# The version is *outside* the seed. The seed -- `github.com/owner/repo` -- is
# the identity, so drift is compared on seeds alone and a remap never reads as
# a rename.
#
# A key file written before any of this has no prefix. That is version 0, it
# hashes to itself, and it therefore still produces the mark it always did.
# Backward compatibility is not a special case here; it is what "the file
# wins" already means.
#
# The vendored library is untouched by any of it: it consumes a digest, and
# only the string being digested has changed. Conformance to
# `stewartlord/identicon.js` is exactly as it was.
MAPPING_VERSION = 2

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
    """MD5 of the key as lowercase hex.

    The key is hashed exactly as recorded. Nothing is prepended here, and that
    is the whole mechanism: what the file says is what the mark is.

    Hex rather than bytes because the reference consumes the digest as *hex
    characters* -- one nibble per grid cell, and the last seven characters as
    the hue. Working in hex keeps this readable next to the reference instead
    of turning every rule into shifts and masks.
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


# ---------------------------------------------------------------------------
# The colour
#
# **One brightness for every hue, which is what lets one file serve both a
# light page and a dark one.** HSL lightness does not control brightness: at
# the reference's 0.5, yellow carries several times the light of blue, so any
# single value is illegible at one end of the wheel or the other. 34 of 72
# sampled hues fell below 3:1 against white, and 10 fell below it against
# GitHub's dark canvas. Two files were needed to cover that, and the two
# differed in colour, so a project did not look like itself across themes.
#
# Oklab lightness does control brightness, so holding it fixed holds contrast
# fixed. Every hue then sits at 3.6:1 or better against white and 4.0:1 or
# better against near-black, from one file.
#
# The chroma is capped rather than flattened. Flattening -- every hue held to
# what the narrowest can manage -- costs about half the colour on the wheel to
# buy a uniformity nobody asked for. A cap lets the hues that can be vivid be
# vivid, and only bites where sRGB has room to spare.
#
# The hue draw is unchanged: the same 28 bits from the same digest. It is read
# as an angle in Oklab rather than in HSL, which also removes the crowding the
# old mapping had -- a fifth of all projects used to land in a band of green
# worth about six perceptual degrees, while teal through blue ran at half its
# share.
# ---------------------------------------------------------------------------

MARK_LIGHTNESS = 0.60
MARK_CHROMA = 0.26

# The bisection that finds how much chroma a hue can take. Fixed bounds and a
# fixed iteration count, because "search until it converges" is not a
# specification -- two implementations would stop in different places. The
# result is rounded to four decimals so that a port whose cube roots differ in
# the last bits still lands on the same number.
GAMUT_STEPS = 30
GAMUT_CEILING = 0.4


def _hsl_to_rgb(hue, saturation, lightness):
    """The reference's own HSL conversion, transliterated.

    Kept for keys stamped at mapping version 0 or 1, which must keep drawing
    what they always drew. See `identicon_colour`.

    Not `colorsys.hls_to_rgb`. The reference mutates `s` and `b` while building
    the sector table, and indexes it with `h|16` and `h|8` -- an integer trick
    for the six-sector rotation. Standard library conversion agrees on most
    inputs but this is a conformance target, so the arithmetic is reproduced
    rather than approximated. Verified against the library's own output for
    every key in vectors.json.
    """
    hue *= 6.0
    fraction = hue % 1

    spread = saturation * (lightness if lightness < 0.5 else 1 - lightness)
    high = lightness + spread
    doubled = spread * 2
    low = high - doubled

    sectors = [
        high,
        high - fraction * spread * 2,
        low,
        low,
        low + fraction * doubled,
        low + doubled,
    ]

    sector = int(hue)
    return (sectors[sector % 6],
            sectors[(sector | 16) % 6],
            sectors[(sector | 8) % 6])

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


# The mapping version selects the colour rule, and old versions never retire.
#
# Putting the version in the key was meant to guarantee that a repository's
# mark cannot change unless that line changes. A version stamp that only
# records what the mark *was* stamped at, while the current code redraws it
# anyway, would not be that guarantee -- it would be a comment. So the rule is
# chosen by the version in the key, and a version 0 or 1 repository keeps the
# colour it has had since the day it was seeded, whatever this file goes on to
# do.
#
# The cost is that every rule ever shipped stays here, and a port has to
# implement all of them to reproduce every vector. That is the price of the
# promise, and it is the right way round: the burden sits with the
# implementation rather than with somebody's repository.
COLOUR_RULES = (0, 1, 2)


def identicon_colour(key, chroma=MARK_CHROMA, lightness=MARK_LIGHTNESS):
    """Return the foreground colour as an (r, g, b) triple of 0-255 ints.

    Version 0 and 1: the reference's HSL, 70% saturation and half lightness.
    Version 2 onward: a hue angle in Oklab at one lightness, with the chroma
    capped. `chroma` and `lightness` are ignored for the older rules, which
    have no such parameters to vary.
    """
    version, _ = parse_key(key)
    if version < 2:
        red, green, blue = _hsl_to_rgb(identicon_hue(key), 0.7, 0.5)
        return (_quantise(red), _quantise(green), _quantise(blue))

    degrees = identicon_hue(key) * 360.0
    return tuple(_encode(channel) for channel in
                 _oklch_to_linear(lightness, gamut_chroma(degrees, lightness,
                                                          chroma), degrees))


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


def profile_name(key):
    """Display name of the generated profile, and what setProfile matches on."""
    return f"{project_name(key)} [{short_hash(key, 6)}]"


def profile_filename(key):
    return f"{ICON_PREFIX}-{short_hash(key)}.profile"


def profile_body(key, parent="FALLBACK/"):
    """The .profile file contents.

    Icon lives under [General], per Profile.cpp: {Icon, "Icon", GENERAL_GROUP}.
    Nothing else is set, so the profile inherits everything from its parent and
    the switch changes the icon alone.
    """
    return (
        "[General]\n"
        f"Name={profile_name(key)}\n"
        f"Parent={parent}\n"
        f"Icon={icon_name(key)}\n"
    )


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


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
    whatever that divides into, and for a terminal handed a pixel budget. Both
    are canvases we do not choose. Everything we do choose is specified as a
    block.
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
    cell = block
    if edge is None:
        edge, margin = canvas_edge(block, border), border
    else:
        margin = (edge - cell * GRID) // 2
    size = edge

    if background is None:
        back = bytes((0, 0, 0, 0))
    else:
        back = bytes(tuple(background) + (255,))
    fore = bytes((red, green, blue, 255))

    rows = []
    for y in range(size):
        row = bytearray()
        grid_y = (y - margin) // cell if cell else -1
        inside_y = margin <= y < margin + cell * GRID
        for x in range(size):
            grid_x = (x - margin) // cell if cell else -1
            inside_x = margin <= x < margin + cell * GRID
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
    cell, margin = block, border
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
                x = margin + column * cell
                y = margin + row * cell
                parts.append(
                    f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" fill="{colour}"/>'
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


# --- Terminal colour --------------------------------------------------------

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


def _bg(rgb, depth):
    if depth == NONE:
        return ""
    if depth == TRUECOLOR:
        return "\033[48;2;{};{};{}m".format(*rgb)
    return f"\033[48;5;{_xterm256(rgb)}m"


RESET = "\033[0m"

CHIP = "█"

# The text rendering lives in text-identicon.py, which takes a grid and a colour
# and nothing else. Loaded by path because the file name carries a hyphen.
#
# **These two files are a pair and must be deployed together.** This one was
# self-contained until the half-block grid was removed; the octant table and the
# emoji palette live next door, and duplicating either to keep one file would
# guarantee they diverge. `doctor` reports whether the sibling is present,
# because the alternative is a hook that prints nothing and exits 0.
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
    """The identicon as two lines: the octant grid, then the emoji triple.

    **The half-block grid this replaced is gone.** It packed two grid rows into
    one text row with an upper half block, three rows of five characters, and
    coloured them with escape sequences -- which made it five columns wide and
    three tall for a five-by-five grid, and unusable at that size. The octants
    carry four cells per character instead: the same twenty-five cells in two
    lines of three, with the colour in the squares rather than in an escape
    sequence, because one glyph covering four cells cannot be coloured per cell.
    """
    grid = identicon_grid(key)
    colour = identicon_colour(key, chroma, lightness)
    return _text_module().text(grid, colour).split("\n")


def render_banner(key, source=None, depth=TRUECOLOR, **kwargs):
    """The identicon with the project name beside it."""
    rows = render_text(key, kwargs.get("chroma", MARK_CHROMA),
                       kwargs.get("lightness", MARK_LIGHTNESS))
    colour = identicon_colour(key, kwargs.get("chroma", MARK_CHROMA),
                              kwargs.get("lightness", MARK_LIGHTNESS))
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
    colour = identicon_colour(key, kwargs.get("chroma", MARK_CHROMA),
                              kwargs.get("lightness", MARK_LIGHTNESS))
    mark = (f"{_fg(colour, depth)}{CHIP}{RESET}" if depth != NONE
            else _text_module().emoji_triple(colour))
    return [f"{mark} {project_name(key)}"]


# --- Inline images ----------------------------------------------------------
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


_TEXT_STYLES = {
    TEXT: lambda key, source=None, depth=TRUECOLOR, **kw: render_text(
        key, kw.get("chroma", MARK_CHROMA), kw.get("lightness", MARK_LIGHTNESS)),
    "full": lambda key, source=None, depth=TRUECOLOR, **kw: render_ansi(key).splitlines(),
    "banner": render_banner,
    "line": lambda key, source=None, depth=TRUECOLOR, **kw: render_line(key, depth, **kw),
}

STYLES = ("icon", "image", TEXT, "full", "banner", "line")


# ---------------------------------------------------------------------------
# Icon theme installation
# ---------------------------------------------------------------------------


def icon_theme_root():
    data_home = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return pathlib.Path(data_home) / "icons" / "hicolor"


def konsole_profile_dir():
    data_home = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return pathlib.Path(data_home) / "konsole"


# ---------------------------------------------------------------------------
# Installing the identicon into a repository
#
# This is what the project is for. Everything above derives a mark; this puts
# it in the repository it belongs to, in forms a consumer that knows nothing
# about this tool can use without parsing anything.
#
# The mark is a constant for a repository -- derived from the remote, not
# stored anywhere -- so these files are a cache, not a source. They exist
# because a README, a shell prompt or a forge cannot run a derivation.
# ---------------------------------------------------------------------------

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

    One of each. The mark holds its brightness across the hue wheel, so the
    same file sits on a white page and a near-black one, and a project looks
    like itself in both.
    """
    yield "png", f"{ARTIFACT_STEM}.png"
    yield "png4x", f"{ARTIFACT_STEM}@{ARTIFACT_SCALE}x.png"
    for canvas in LARGE_CANVASES:
        yield f"png{canvas}", f"{ARTIFACT_STEM}-{canvas}.png"
    yield "svg", f"{ARTIFACT_STEM}.svg"
    yield "colour", f"{ARTIFACT_STEM}.colour"


def artifact_paths(root):
    directory = pathlib.Path(root) / IDENTICON_DIR
    return {name: directory / filename for name, filename in artifact_names()}


# **The key is recorded, and changing it is a positive act.**
#
# The key was re-derived from the remote on every run, which made a rename
# silently change a repository's identity -- the one thing an identity is for
# is not doing that. It also conflated two unrelated reasons to re-run:
# wanting newer artifacts, and wanting a different mark. Those are now
# separate. `apply` refreshes the artifacts from the recorded key, so an
# improved renderer or a different size reaches every repository without
# touching anybody's identity; `--reseed` and `--remap` are the only things
# that change what the mark is derived from.
#
# The file holds the whole key, mapping version included, and it is hashed
# verbatim. So this file is not merely a record of what the mark was built
# from -- it *is* what the mark is built from, and no change anywhere else can
# move it. `.repository-identicon` is hand-written and holds a seed, not a key:
# it outranks the git remote when a seed has to be derived, and is outranked by
# this file once one has been.
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
    """The recorded key, verbatim, or None if this repository is not seeded.

    Verbatim matters: the first payload line is hashed exactly as it reads,
    version stamp and all. An unstamped line is a version 0 key and still
    derives the mark it always did.
    """
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

    Three files rather than one. A combined file would be readable by every
    tool that knows the format, which is one tool; a README cannot address a
    fragment inside a blob, and `$(cat …/*.colour)` is a whole parser.
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
    colour = identicon_colour(key,
                              render_kwargs.get("chroma", MARK_CHROMA),
                              render_kwargs.get("lightness", MARK_LIGHTNESS))
    wanted["colour"] = (hex_colour(colour) + "\n").encode("utf-8")
    return wanted


# The artifacts are inert until something points at them, and the one thing
# every repository already has is a README. So the line goes in by default and
# --no-readme is the way out, rather than the other way round: an identicon
# nobody put on the page is an identicon nobody sees.
README_MARK = f"![]({IDENTICON_DIR}/{ARTIFACT_STEM}.svg)"

# **What counts as the mark already being there, twice corrected by
# dogfooding.** Matching the bare path anywhere was wrong: a README that
# *documents* these paths reads as one that displays them, so exactly the
# projects integrating with this would never get a mark. Requiring an image
# reference was still wrong, because this repository's own README shows the
# markdown in a fenced block as an example. So: strip fenced code first, then
# look for an image. A mark inside a code fence is a mark being talked about.
# No trailing dot on the path: a mark somebody pointed at one of the sized
# rasters, or at a variant from an older version of this tool, is still a mark
# and must not be duplicated.
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
    opens with what the project is called. Recognised on the way back in by
    the artifact path, which never changes -- so a line an author has moved,
    resized with an <img> tag, or pointed at the PNG instead is left exactly
    where they put it. This writes once and then keeps out of the way.
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

    **Two things you might want from a re-run, and they are separate.**
    Refreshing the artifacts -- a better renderer, a different size, a new
    file in the set -- must reach every repository without disturbing any
    identity. Changing what the mark is derived from must not happen by
    accident. So the key is recorded on the first run and reused verbatim on
    every run after it; `reseed` and `remap` are the only things that replace
    it.

    Once seeded, the mark is stable against anything: renaming the repository,
    moving it between forges, cloning it to a path that would resolve
    differently, or a new mapping version shipping in this file. Those change
    what the key *would* be, which is reported as `seed_drift` and
    `mapping_drift`, and nothing more. Acting on it is somebody's decision.

    `reseed` adopts today's seed at today's mapping version. `remap` keeps the
    recorded seed and moves it to today's mapping version -- the same identity,
    drawn by the new mapping.

    For a fixed key this writes identical bytes on every run and reports
    nothing changed.

    `check` reports what *would* change and writes nothing, which is what a
    dependent tool or a CI job should call.

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
        # The file wins. Hashed exactly as it reads, prefix and all.
        key, source = recorded, "key"

    mapping_version, resolved_seed = parse_key(key)

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

    colour = identicon_colour(key,
                              render_kwargs.get("chroma", MARK_CHROMA),
                              render_kwargs.get("lightness", MARK_LIGHTNESS))
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


def install_icon(key, root=None, sizes=INSTALL_SIZES, **render_kwargs):
    """Write one PNG per size into the user's hicolor tree. Returns the paths.

    hicolor under XDG_DATA_HOME merges with the system theme, so no index.theme
    of our own is needed for QIcon::fromTheme to find these.
    """
    root = pathlib.Path(root) if root else icon_theme_root()
    name = icon_name(key)
    written = []
    for size in sizes:
        directory = root / f"{size}x{size}" / "apps"
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / f"{name}.png"
        target.write_bytes(render_png(key, fit_block(size), edge=size,
                                      **render_kwargs))
        written.append(target)

    scalable = root / "scalable" / "apps"
    scalable.mkdir(parents=True, exist_ok=True)
    target = scalable / f"{name}.svg"
    target.write_text(render_svg(key, ARTIFACT_BLOCK, **render_kwargs))
    written.append(target)
    return written


def installed_icons(root=None):
    """Every identicon this tool has installed, as {icon name: [paths]}."""
    root = pathlib.Path(root) if root else icon_theme_root()
    found = {}
    if not root.is_dir():
        return found
    for path in sorted(root.glob(f"*/apps/{ICON_PREFIX}-*")):
        found.setdefault(path.stem, []).append(path)
    return found


def remove_icon(name, root=None):
    root = pathlib.Path(root) if root else icon_theme_root()
    removed = []
    for path in sorted(root.glob(f"*/apps/{name}.*")):
        path.unlink()
        removed.append(path)
    return removed


def install_profile(key, directory=None, parent="FALLBACK/"):
    directory = pathlib.Path(directory) if directory else konsole_profile_dir()
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / profile_filename(key)
    target.write_text(profile_body(key, parent))
    return target


def installed_profiles(directory=None):
    directory = pathlib.Path(directory) if directory else konsole_profile_dir()
    if not directory.is_dir():
        return []
    return sorted(directory.glob(f"{ICON_PREFIX}-*.profile"))


# ---------------------------------------------------------------------------
# D-Bus
# ---------------------------------------------------------------------------

SESSION_IFACE = "org.kde.konsole.Session"
QDBUS_CANDIDATES = ("qdbus6", "qdbus-qt6", "qdbus")


class DBusError(RuntimeError):
    pass


def find_qdbus():
    for candidate in QDBUS_CANDIDATES:
        found = shutil.which(candidate)
        if found:
            return found
    return None


def find_gdbus():
    return shutil.which("gdbus")


def _run(argv):
    completed = subprocess.run(argv, capture_output=True, text=True)
    if completed.returncode != 0:
        raise DBusError((completed.stderr or completed.stdout).strip() or f"{argv[0]} failed")
    return completed.stdout


def dbus_call(service, path, method, args=(), qdbus=None):
    """Call a method on a Konsole session. Argument list, never a shell string."""
    qdbus = qdbus or find_qdbus()
    if qdbus:
        return _run([qdbus, service, path, f"{SESSION_IFACE}.{method}",
                     *[str(a) for a in args]])
    gdbus = find_gdbus()
    if not gdbus:
        raise DBusError("neither qdbus nor gdbus is on PATH")
    argv = [gdbus, "call", "--session", "--dest", service, "--object-path", path,
            "--method", f"{SESSION_IFACE}.{method}"]
    argv += [str(a) for a in args]
    return _run(argv)


def dbus_members(service, path):
    """Method names exposed on the object, for capability probing."""
    qdbus = find_qdbus()
    if qdbus:
        listing = _run([qdbus, service, path])
        names = set()
        for line in listing.splitlines():
            line = line.strip()
            if not line:
                continue
            head = line.split("(")[0].split()[-1]
            names.add(head.rsplit(".", 1)[-1])
        return names
    gdbus = find_gdbus()
    if not gdbus:
        raise DBusError("neither qdbus nor gdbus is on PATH")
    xml = _run([gdbus, "introspect", "--session", "--dest", service,
                "--object-path", path, "--xml"])
    names = set()
    for line in xml.splitlines():
        line = line.strip()
        if line.startswith("<method "):
            names.add(line.split('name="', 1)[1].split('"', 1)[0])
    return names


def list_konsole_services():
    qdbus = find_qdbus()
    if qdbus:
        return sorted(n for n in _run([qdbus]).split() if n.startswith("org.kde.konsole"))
    gdbus = find_gdbus()
    if not gdbus:
        return []
    out = _run([gdbus, "call", "--session", "--dest", "org.freedesktop.DBus",
                "--object-path", "/org/freedesktop/DBus",
                "--method", "org.freedesktop.DBus.ListNames"])
    return sorted({tok.strip("'\", []()") for tok in out.split(",")
                   if "org.kde.konsole" in tok})


def list_sessions(service):
    qdbus = find_qdbus()
    if not qdbus:
        return []
    return sorted(line.strip() for line in _run([qdbus, service]).splitlines()
                  if line.strip().startswith("/Sessions/"))


def resolve_session(spec=None):
    """Return (service, path) for the session to act on.

    With no spec, use the KONSOLE_DBUS_SERVICE and KONSOLE_DBUS_SESSION that
    Konsole exports into every session's environment, so running this inside
    the tab you want marked just works.
    """
    if spec:
        if ":" not in spec:
            raise DBusError(f"session spec must be service:/Sessions/N, got {spec!r}")
        service, path = spec.split(":", 1)
        return service, path

    service = os.environ.get("KONSOLE_DBUS_SERVICE")
    path = os.environ.get("KONSOLE_DBUS_SESSION")
    if service and path:
        return service, path

    services = list_konsole_services()
    if len(services) == 1:
        sessions = list_sessions(services[0])
        if len(sessions) == 1:
            return services[0], sessions[0]
    raise DBusError(
        "not running inside Konsole and could not pick a session unambiguously; "
        "pass --session service:/Sessions/N (see the `sessions` command)"
    )


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


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
    "key": f"the recorded key, which outranks all of the below",
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
    print(f"profile   {profile_name(key)}")
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


def cmd_install(args):
    key = _key_from_args(args)
    written = install_icon(key, **_render_kwargs(args))
    print(f"icon {icon_name(key)}")
    for path in written:
        print(f"  {path}")
    print()
    print("Konsole reads profile icons through QIcon::fromTheme, which caches. A")
    print("running Konsole may not show a brand new icon until it restarts.")
    return 0


def cmd_list(args):
    icons = installed_icons()
    profiles = installed_profiles()
    if not icons and not profiles:
        print("nothing installed")
        return 0
    for name, paths in icons.items():
        print(f"{name}  ({len(paths)} files)")
    for path in profiles:
        print(f"{path.name}  ->  {path}")
    return 0


def cmd_uninstall(args):
    if args.all:
        names = list(installed_icons())
        profiles = installed_profiles()
    else:
        key = _key_from_args(args)
        names = [icon_name(key)]
        candidate = konsole_profile_dir() / profile_filename(key)
        profiles = [candidate] if candidate.exists() else []

    removed = 0
    for name in names:
        for path in remove_icon(name):
            print(f"removed {path}")
            removed += 1
    for path in profiles:
        path.unlink()
        print(f"removed {path}")
        removed += 1
    if not removed:
        print("nothing to remove")
    return 0


def cmd_sessions(args):
    services = list_konsole_services()
    if not services:
        print("no Konsole instance is on the session bus")
        return 1
    for service in services:
        print(service)
        for path in list_sessions(service):
            print(f"  {service}:{path}")
    return 0


BADGE_METHODS = (
    "setBadgeEnabled",
    "setBadgeText",
    "setBadgeColor",
    "setBadgeTextOnly",
    "setBadgeTransparency",
    "setBadgeFontFamily",
    "setBadgeFontSize",
)


def cmd_probe(args):
    """Report which of the two routes this Konsole build actually offers.

    setBadgeColor takes a QColor, which is not a basic D-Bus type. Konsole
    registers no metatype for it, so it may be absent from introspection even
    though the header marks it Q_SCRIPTABLE. That is exactly what this checks.
    """
    service, path = resolve_session(args.session)
    print(f"session   {service}:{path}")
    members = dbus_members(service, path)
    print(f"members   {len(members)}")
    print()
    print("badge route")
    for method in BADGE_METHODS:
        print(f"  {'yes' if method in members else 'NO '}  {method}")
    print()
    print("profile route")
    for method in ("setProfile", "profile"):
        print(f"  {'yes' if method in members else 'NO '}  {method}")
    print()
    print("not scriptable, hence no direct tab-icon route")
    print("  NO   setIconName")
    return 0


def cmd_badge(args):
    key = _key_from_args(args)
    service, path = resolve_session(args.session)
    members = dbus_members(service, path)

    if args.clear:
        dbus_call(service, path, "setBadgeEnabled", ["false"])
        print(f"badge cleared on {service}:{path}")
        return 0

    label = args.label or badge_label(key)
    dbus_call(service, path, "setBadgeText", [label])
    dbus_call(service, path, "setBadgeEnabled", ["true"])
    print(f"badge text  {label}")

    colour = hex_colour(identicon_colour(key, args.chroma, args.lightness))
    if "setBadgeColor" in members:
        dbus_call(service, path, "setBadgeColor", [colour])
        print(f"badge colour {colour}")
    else:
        print(f"badge colour {colour} NOT APPLIED - setBadgeColor absent from introspection")
        print("             QColor has no D-Bus metatype registered in Konsole")
    return 0


def cmd_profile(args):
    key = _key_from_args(args)
    install_icon(key, **_render_kwargs(args))
    target = install_profile(key, parent=args.parent)
    name = profile_name(key)
    print(f"icon     {icon_name(key)}")
    print(f"profile  {name}")
    print(f"         {target}")

    if not args.apply:
        print()
        print("re-run with --apply to switch the current tab to it")
        return 0

    service, path = resolve_session(args.session)
    dbus_call(service, path, "setProfile", [name])
    active = dbus_call(service, path, "profile").strip()
    print(f"applied  {service}:{path}")
    print(f"now on   {active or '(empty)'}")
    if active != name:
        print()
        print("setProfile matches against already-loaded profiles and no-ops on a")
        print("miss. A profile written after Konsole started is not loaded yet;")
        print("open Settings, Manage Profiles, or restart Konsole, then retry.")
        return 1
    return 0


def cmd_demo(args):
    key = _key_from_args(args)
    print(f"=== {key} ===")
    print(render_ansi(key))
    print()
    for step, handler in (("probe", cmd_probe), ("badge", cmd_badge),
                          ("profile", cmd_profile)):
        print(f"--- {step} ---")
        try:
            handler(args)
        except DBusError as error:
            print(f"skipped: {error}")
        print()
    return 0


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


# --- Conformance validator --------------------------------------------------
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

    # The vectors span mapping versions, because the keys do: version 0 keys
    # are still out there and must still draw what they always drew. What is
    # not allowed is seeding at a version nothing pins, so bumping the constant
    # without generating the vectors for it fails here rather than in the wild.
    covered = sorted({parse_key(vector["key"])[0] for vector in vectors})
    if MAPPING_VERSION not in covered:
        raise ValueError(
            f"{path} pins mapping versions {covered} and this implementation "
            f"seeds at version {MAPPING_VERSION}; a bump has to bring its "
            f"vectors with it")
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
    sibling = text_module_path()
    found = (str(sibling) if sibling.is_file()
             else "NOT FOUND - text styles will print nothing")
    print(f"{TEXT_MODULE:16} {found}")
    print(f"qdbus            {find_qdbus() or 'NOT FOUND'}")
    print(f"gdbus            {find_gdbus() or 'NOT FOUND'}")
    print(f"icon theme root  {icon_theme_root()}")
    print(f"profile dir      {konsole_profile_dir()}")
    print(f"in Konsole       {'yes' if os.environ.get('KONSOLE_DBUS_SESSION') else 'no'}")
    for variable in ("KONSOLE_DBUS_SERVICE", "KONSOLE_DBUS_SESSION", "KONSOLE_VERSION"):
        print(f"  {variable}={os.environ.get(variable, '')}")
    print(f"icons installed  {len(installed_icons())}")
    print(f"profiles written {len(installed_profiles())}")
    try:
        services = list_konsole_services()
        print(f"konsole services {', '.join(services) if services else 'none'}")
    except DBusError as error:
        print(f"konsole services unavailable: {error}")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        prog="repository-identicon",
        description="Per-project identicons for Konsole tabs, over the session "
                    "D-Bus interface.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(target, *, path=True, render=False, session=False):
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
        if session:
            target.add_argument("--session",
                                help="service:/Sessions/N; default from the "
                                     "environment")
        else:
            target.set_defaults(session=None)

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

    install = sub.add_parser("install", help="install the identicon into the user icon theme")
    add_common(install, render=True)
    install.set_defaults(func=cmd_install)

    listing = sub.add_parser("list", help="list installed identicons and profiles")
    add_common(listing, path=False)
    listing.set_defaults(func=cmd_list)

    uninstall = sub.add_parser("uninstall", help="remove installed identicons and profiles")
    add_common(uninstall)
    uninstall.add_argument("--all", action="store_true")
    uninstall.set_defaults(func=cmd_uninstall)

    sessions = sub.add_parser("sessions", help="list Konsole sessions on the bus")
    add_common(sessions, path=False)
    sessions.set_defaults(func=cmd_sessions)

    probe = sub.add_parser("probe", help="report which D-Bus methods this Konsole exposes")
    add_common(probe, path=False, session=True)
    probe.set_defaults(func=cmd_probe)

    badge = sub.add_parser("badge", help="route one: set the session badge")
    add_common(badge, render=True, session=True)
    badge.add_argument("--label", help="override the derived one or two character label")
    badge.add_argument("--clear", action="store_true", help="disable the badge instead")
    badge.set_defaults(func=cmd_badge)

    profile = sub.add_parser(
        "profile", help="route two: generate a profile carrying the icon")
    add_common(profile, render=True, session=True)
    profile.add_argument("--parent", default="FALLBACK/", help="profile to inherit from")
    profile.add_argument("--apply", action="store_true", help="switch the session to it")
    profile.set_defaults(func=cmd_profile)

    demo = sub.add_parser("demo", help="probe, then exercise both routes on one session")
    add_common(demo, render=True, session=True)
    demo.add_argument("--label", default=None)
    demo.add_argument("--parent", default="FALLBACK/")
    demo.set_defaults(func=cmd_demo, clear=False, apply=True)

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
    add_common(doctor, path=False)
    doctor.set_defaults(func=cmd_doctor)

    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except DBusError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except BrokenPipeError:
        # Piping into head closes the pipe early. Retarget stdout at devnull so
        # the interpreter's own flush at exit does not report it a second time.
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        return 0


if __name__ == "__main__":
    sys.exit(main())

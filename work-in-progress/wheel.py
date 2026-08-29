#!/usr/bin/env python3
"""The wheel: the gamut as a ring, and the vocabulary available to name it.

    python3 wheel.py --painted                render the next free wheelN.svg
    python3 wheel.py --painted --ring-only    the ring alone, tiers not drawn
    python3 wheel.py --painted --out FILE     render to a name of your own
    python3 wheel.py --reference              regenerate in-use.tsv

`--painted` judges in the colours the vendors paint, and everything is authored
against it; the Unicode palette is a different arrangement and solving anything
against it will not transfer.

**`wheel.tsv` is the wheel, and this file only draws it.** All 165 triples have
a line each, 63 on the ring with an angle, the rest in a tier or one of three
sunk bands; a tile's number is the line it sits on, clockwise from the top.
`--reference` writes `in-use.tsv`, the mapping alone, from that same file.

A block carries the multiset only -- no arrangement, no square-versus-circle.
Those are identity, and identity is a separate question from whether the mark
names the colour.
"""

import importlib.util
import math
import pathlib
import sys

REPO = str(pathlib.Path(__file__).resolve().parent.parent) + "/"
HERE = pathlib.Path(__file__).parent


def load(path, module):
    spec = importlib.util.spec_from_file_location(module, path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


text = load(REPO + "text-identicon.py", "t")
identicon = load(REPO + "repository-identicon.py", "i")


# ---------------------------------------------------------------------------
# Palette, painted and nominal
# ---------------------------------------------------------------------------

NOMINAL = {name: "#{:02x}{:02x}{:02x}".format(*rgb)
           for _e, name, _cp, rgb in text.PALETTE}
ORDER = {name: k for k, (_e, name, _cp, _rgb) in enumerate(text.PALETTE)}

# What the squares are actually painted, averaged across the vendor sets by the
# share of developers likely to be reading through each -- from
# `../emoji-square-colours.md`, which samples seven sets and states its own
# weighting. The palette proper stays anchored on the Unicode names, because
# there is no single truth to anchor on: seven vendors disagree by up to twenty
# degrees of hue on one square, so any vendor's values would be wrong for
# everybody else's reader. These are for asking a different question -- what a
# triple looks like where it is actually read -- and `--painted` asks it.
#
# Independently corroborated where it could be: sampling Emojipedia's renderings
# of the Fluent 3D and Twemoji squares reproduces that document's values exactly,
# and its Noto values match the COLRv1 font installed on this machine.
PAINTED = {
    "red": (0xE4, 0x3B, 0x3F), "orange": (0xFD, 0x85, 0x26),
    "yellow": (0xFD, 0xC1, 0x39), "green": (0x53, 0xBC, 0x53),
    "blue": (0x27, 0x7E, 0xE2), "purple": (0xA6, 0x55, 0xD7),
    "brown": (0x98, 0x5D, 0x4A), "black": (0x29, 0x28, 0x2A),
    "white": (0xE0, 0xDB, 0xE4),
}
AS_PAINTED = False       # --painted


def square_rgb(name):
    """The colour to treat this square as, under whichever palette is in force."""
    return PAINTED[name] if AS_PAINTED else text.PALETTE[ORDER[name]][3]


def square_hex(name):
    """Hex for a square under whichever palette is in force."""
    return text.hex_colour(square_rgb(name))


def multiset(names):
    """Order-free form, for asking whether two triples use the same squares."""
    return tuple(sorted(names, key=lambda n: ORDER[n]))


# ---------------------------------------------------------------------------
# Geometry
#
# The ring is thick enough to read as a colour rather than a line. Reading
# outward: the tiers, tier 0's numbers, the gamut, and tier 0's trefoils on
# neutral ground.
# ---------------------------------------------------------------------------

SIZE = 720
CENTRE = SIZE / 2
TIER_FLOOR = 62                # nearest the middle a tier may reach
# The pitch is capped rather than derived from this, so moving the ring out
# costs the stack depth, not every block its height.
TIER_OUT = 258                 # the outermost tier
# Tier 0 alone is held off the stack below it. The gap between the ring and the
# first tier is doing a different job from the gap between any other pair --
# it separates the arrangement from the alternatives to it, not one alternative
# from the next -- so it is set on its own rather than by widening every tier's
# label gap, which would have thinned every block to pay for it.
RING_SEP = 5

# **A view, not a smaller wheel.** `--ring-only` draws the ring and leaves the
# tiers and the roster off the page. Everything is still read, still packed,
# still assigned a tier and still reported by the checklist -- the run says the
# same things it always did and the numbering is untouched. What changes is one
# picture, for looking at the arrangement without the alternatives to it
# crowding round; `wheel.tsv` remains the record of all 165.
RING_ONLY = False
RING_DEEP = 1.5                # the ring's depth, with nothing beneath it
# **The offsets and tier 0's numbers have changed places.** The ticks were out
# in the corridor between the ring and the gamut, and the numbers were in the
# clear gap inside the ring with every other tier's. That put the one mark that
# measures a tile against the gamut on the far side of the tile from the gamut,
# so reading a tick against the hue it points at meant crossing the block, and
# it put tier 0's numbers deepest of the two things competing for the corridor's
# attention. Reversed: the ticks drop into the gap inside the ring, where the
# leader now runs outward to the tile's inner edge, and the numbers take the
# corridor, where a number sits between the ring it names and the gamut it is
# being judged against.
#
# The tick radius is not a constant any more -- the gap it sits in is set by
# `pitch`, which is set by how deep the stack turned out, so it is computed
# where that is known and passed in.
# Every block carries its number, and no number is laid over a colour. A tier
# is therefore two bands: the block itself, and a clear gap immediately inside
# it holding that tier's numbers.
TIER_BAND = 13                 # the coloured block
TIER_LABEL = 11                # the clear gap inside it, for its numbers
RING_IN, RING_OUT = 264, 306   # the gamut itself
# Centred in the corridor rather than set from either edge: the number belongs
# to neither the ring nor the gamut. It is the thing that lets you name one
# while looking at the other, so it sits the same distance from both.
RING_NUMBER_R = (TIER_OUT + RING_IN) / 2
NUMBER_SIZE = 4.5              # small enough to clear the corridor
# The neutral band and the trefoils that sit on it. Deep enough for the cluster
# (about 2.9 disc radii) with a little air at each edge.
TREF_IN, TREF_OUT = 306, 336   # inner edge against the gamut, no seam
TREF_BG = "#e2e2e2"
COL_W = 120                    # one roster column, beside the wheel
ROSTER_ROWS = 96               # rows a column holds at this canvas height
RING_STEP = 0.25                # degrees per ring segment


def polar(radius, degrees):
    """Hue zero at the top, increasing clockwise, matching the spikes."""
    a = math.radians(degrees)
    return CENTRE + radius * math.sin(a), CENTRE - radius * math.cos(a)


def sector(r0, r1, a0, a1):
    """An annular sector as a path.

    Real arcs, not the rotated rectangles the ring gets away with: these span
    from one degree up to the trefoil band's half-circles, and at these radii a
    rectangle's corners visibly overshoot.
    """
    large = 1 if (a1 - a0) % 360 > 180 else 0
    x0, y0 = polar(r1, a0)
    x1, y1 = polar(r1, a1)
    x2, y2 = polar(r0, a1)
    x3, y3 = polar(r0, a0)
    return (f'M{x0:.2f},{y0:.2f} A{r1},{r1} 0 {large} 1 {x1:.2f},{y1:.2f} '
            f'L{x2:.2f},{y2:.2f} A{r0},{r0} 0 {large} 0 {x3:.2f},{y3:.2f} Z')


# A wedge is as wide as the identity its triple affords. Three distinct
# squares give six arrangements and eight shape combinations -- forty-eight
# marks -- against a pair's three-by-eight and three-of-a-kind's one-by-eight.
# Eight degrees, four and one price that, near enough, and make the picture
# say what each entry is worth rather than merely that it exists.
#
# **The eight is optimistic and the wheel does not currently show it.** Black
# and white are never circled, so a triple containing one has four shape
# combinations and one containing both has two. A three-distinct block with a
# black in it is worth twelve marks, not forty-eight, and is drawn as wide as
# one worth forty-eight. See the README: it is a real fault in the pricing, not
# a rounding.
WEDGE = {3: 8.0, 2: 4.0, 1: 1.0}
# --scale multiplies every class alike, so the 8/4/1 ratio -- and with it the
# reading that width is the identity a triple affords -- survives untouched.
WIDTH_SCALE = 1.0
# Wedges may touch. They are meant to: an eight-degree run of eight-degree
# wedges tiles exactly, and demanding clear air between them pushed a
# perfectly packed row inward one wedge at a time for no reason. Only a real
# overlap sends an entry to the next lane.
WEDGE_TOL = 1e-6


# ---------------------------------------------------------------------------
# The catalogue, and what the harness says
# ---------------------------------------------------------------------------

# Below this Oklab chroma a blend is a grey and its hue angle is noise. Seven
# qualify under the Unicode names, at chroma zero, with the next candidate two
# orders of magnitude clear. Under --painted it is six and the margin is thin:
# the highest neutral is 0.018 and the next candidate 0.022, so this is a knife
# edge, not a comfortable cut. Do not nudge it.
NEUTRAL_CHROMA = 0.02


_PERC = None


def harness():
    """The perceptual rules, loaded once. Advisory here, not a gate."""
    global _PERC
    if _PERC is None:
        _PERC = load(str(HERE / "perceptual.py"), "perc")
    return _PERC


# `W` and `K`, for a single white or black on an extreme target, were dropped
# with the rule behind them -- see the tint note in perceptual.py.
FLAGS = [("opponent", "opp"), ("gap", "gap"), ("two whites", "WW"),
         ("two blacks", "KK"), ("forbidden", "no")]


def flag_of(broken):
    """The shortest honest label for what the harness says about a triple."""
    for prefix, code in FLAGS:
        if any(b.startswith(prefix) for b in broken):
            return code
    return ""


def catalogue():
    """**Every** triple, at the hue its blend reads as, with what the harness
    thinks of it -- and nothing kept off the page for what the harness thinks.

    All 165 multisets. The rules are still run and what they say is drawn on
    the block as a broken edge and named in the roster, but they no longer
    decide what is admitted. `DARK` and `LIGHT` are absolute luminances and the
    version 2 ring runs 0.20 to 0.49, never reaching `LIGHT` at 0.58, so the
    two-white rule fires at every hue and is measuring nothing -- and is right
    every time anyway, since all seven two-white triples were sunk by eye.
    Moving the cut into the gap in the distribution would make it pass four of
    them. See the note in `perceptual.py`.

    A few multisets average to a neutral and have no hue at all: six under
    `--painted`, seven under the Unicode names. `atan2` of nothing is zero, so
    `nearest_gamut` hands them a position they have no claim to -- three blacks
    read 0.0 degrees, at dE 0.411 painted and 0.646 named. They are returned
    separately, listed in the roster and given no place on the ring, since a
    wheel is an argument about hue and they are not in it.

    Returned best-first, by how faithfully the blend renders the colour at the
    hue it reads as.
    """
    perceptual = harness()
    palette = [name for _e, name, _cp, _rgb in text.PALETTE]
    rows, hueless, seen = [], [], set()
    for a in palette:
        for b in palette:
            for c in palette:
                key = multiset((a, b, c))
                if key in seen:
                    continue
                seen.add(key)
                mixed = mix_rgb(key)
                _L, ok_a, ok_b = oklab(mixed)
                reads, colour, delta = nearest_gamut(mixed)
                flag = flag_of(perceptual.violations(
                    colour, tuple(ORDER[n] for n in key)))
                if math.hypot(ok_a, ok_b) < NEUTRAL_CHROMA:
                    hueless.append((delta, None, key, mixed, "--"))
                else:
                    rows.append((delta, reads, key, mixed, flag))
    return sorted(rows), sorted(hueless)


def flag_at(names, hue):
    """What the harness says about this triple at the hue it is drawn on."""
    return flag_of(harness().violations(gamut_at(hue),
                                        tuple(ORDER[n] for n in names)))


def circular_overlap(a0, a1, b0, b1):
    """Do two arcs meet, allowing for either having been written across zero?"""
    for shift in (-360.0, 0.0, 360.0):
        if a0 + shift < b1 - WEDGE_TOL and b0 < a1 + shift - WEDGE_TOL:
            return True
    return False


# **The seating constants have gone with the seating**: `MAX_NUDGE`,
# `NUDGE_STEP`, `MAX_PUSH`, `AUTO_FILL` and `FLUSH_TOL`, none of them reachable
# now that every seat is written down and the ring is closed. `FLUSH_TOL` was
# set from Justin's eye: the gap between two adjacent tiles, in degrees of ring.
# A gap of 0.106 he could not see, one of 0.380 he asked to close -- about half
# a pixel and about two, at this radius. HANDOVER.md:169 holds the fuller
# version.


# ---------------------------------------------------------------------------
# Verdicts: bias, sink, and the sunk bands
# ---------------------------------------------------------------------------

# How a tile is nudged between tiers. `out` is packed before its neighbours so
# it takes the outermost tier with room; `in` starts its search a tier deeper.
# Neither can put a tile on the ring -- that is what `ring` is for -- and
# neither moves it in angle, which stays fixed at the hue its blend reads.
BIAS = {"out": -1, "in": 1}


def bias_of(names):
    """How many tiers out or in, from the verdict and its optional count.

    `out 2` is dropped before `out`, which is dropped before everything else,
    so it gets first refusal on the outer tiers. `in 2` starts its search two
    tiers further in. Neither moves a tile in angle.
    """
    verdict, where = placements().get(names, ("", None))
    step = BIAS.get(verdict, 0)
    if step and where and where[0] == "count":
        return step * int(where[1])
    return step


# Where the two cuts fall, in the same 0-100 luminance the blocks are drawn in.
# Widened from 45 and 74 on Justin's eye: `red green black` at 48.6 reads dark
# and `red green white` at 64.9 reads light, and both were in the middle band.
#
# **Set past the block that moved them, not at it.** 48.7 would have taken #29
# and left `orange blue black` at 48.8 behind, which is a tenth of a point and
# nothing anybody can see. Each cut sits in the nearest real hole in the
# distribution instead -- 50.5 falls between 49.9 and 53.2, 63.0 between 61.6
# and 64.8 -- so no pair a hair apart ends up in different rings.
#
# Frozen rather than taken from the ring's own range, which is what they were
# first set against: a threshold that moves when the ring moves would quietly
# reband a tile between one render and the next.
SUNK_DARK, SUNK_MID, SUNK_LIGHT = 0, 1, 2
SUNK_DARK_MAX = 50.5
SUNK_LIGHT_MIN = 63.0


def luminance(rgb):
    """Perceived lightness of a blend, 0 to 100, gamma-aware.

    Straight-average grey put `yellow white white` and `blue black black` far
    closer together than any eye does, and the bands drawn off it did not look
    like bands.
    """
    r, g, b = ((c / 255) ** 2.2 for c in rgb)
    return 100 * (0.2126 * r + 0.7152 * g + 0.0722 * b) ** (1 / 2.2)


def sunk_band(rgb):
    """Which of the three sunk rings a rejected blend belongs in."""
    lit = luminance(rgb)
    if lit <= SUNK_DARK_MAX:
        return SUNK_DARK
    return SUNK_LIGHT if lit >= SUNK_LIGHT_MIN else SUNK_MID


def is_sunk(names):
    """Whether a tile has been sent to the inner-inner band.

    `sink` is for the ones judged noise: they are read as a block, if at all,
    and never against the tile beside them. So they come out from among the
    alternatives, where their only effect was to push the tiers that are still
    being judged inward and away from the ring.
    """
    return placements().get(names, ("", None))[0] == "sink"


def sunk_at(names):
    """The angle a `sink` line gives, if it gives one.

    **The one verdict that moves a tile in angle without seating it.** For
    anything still under judgement that would be a lie -- the whole point of a
    tier is that a tile sits at the hue its blend reads, so it can be compared
    with the ring above it. A sunk tile is not being compared with anything, so
    a few degrees costs nothing, and spending them is what lets the set close
    up into two rows instead of splaying across nine.
    """
    verdict, where = placements().get(names, ("", None))
    if verdict != "sink":
        return None
    return where[1] if where and where[0] == "at" else None


# ---------------------------------------------------------------------------
# wheel.tsv: the wheel
# ---------------------------------------------------------------------------

# The wheel's version, which is now also the key's mapping version -- `0.3` in
# both places, one number for one thing. The colour rule and the arrangement of
# tricolours standing over the gamut it produces were solved together, so a tile
# moving and the rule moving are the same event and are numbered once.
WHEEL_VERSION = "0.3"

WHEEL_TSV = HERE / "wheel.tsv"

_LINES = None


def tsv_lines():
    """Every line of `wheel.tsv`, in order: `(verb, where, triple)`.

    **The line number is the tile's number, and the line says which tile.**
    Both, deliberately: position alone would put the whole file one out,
    silently, if a line were ever dropped, and the triple alone was what the
    old file avoided carrying, because transcribing one by hand put half a
    batch on the wrong tiles once. The number column is never read as an
    identity, only compared with where it sits.
    """
    global _LINES
    if _LINES is not None:
        return _LINES
    _LINES = []
    if not WHEEL_TSV.exists():
        return _LINES
    for line in WHEEL_TSV.read_text().splitlines():
        # A trailing comment, so a placement can carry what it cost beside it.
        line = line.split("#", 1)[0]
        if not line.strip():
            continue
        parts = line.split()
        n, verb, where, triple = parts[0], parts[1], parts[2], parts[3:]
        if len(triple) != 3:
            print(f"  not three squares: {line.strip()}")
            continue
        if not n.isdigit() or int(n) != len(_LINES) + 1:
            print(f"  #{n} sits on line {len(_LINES) + 1}: {line.strip()}")
        _LINES.append((verb, where, multiset(tuple(triple))))
    seen = {t for _v, _w, t in _LINES}
    if len(seen) != len(_LINES):
        print(f"  {len(_LINES) - len(seen)} triples named twice "
              f"in {WHEEL_TSV.name}")
    return _LINES


def placements():
    """Where each tile goes, keyed by triple, read off `wheel.tsv`.

    Every tile has a line, including the ones the packer would place by falling
    through to its default. `tier` is that default written down: off the ring,
    wherever the packing puts it.
    """
    out = {}
    for verb, where, names in tsv_lines():
        if verb == "ring":
            out[names] = ("ring", ("at", float(where)))
        elif verb == "sink":
            out[names] = ("sink", ("at", float(where)))
        elif verb in ("tier", "eject", "hueless"):
            out[names] = ("inner", None)
        elif verb in ("in", "out"):
            out[names] = (verb, ("count", int(where)))
        else:
            print(f"  no such verdict: {verb} on {' '.join(names)}")
    return out


# ---------------------------------------------------------------------------
# Placing the ring
# ---------------------------------------------------------------------------

# Ranking candidates by dE alone was wrong at least once: `red yellow purple`
# won 14 degrees on Justin's eye over two orange-based triples that dE
# preferred. That judgement is in `wheel.tsv` now, tile by tile.


def propose(rows):
    """The ring: every tile `wheel.tsv` seats, at the angle it gives them.

    A lookup, not a search: every seat is written down. The one piece of work
    left is the collision guard, and it stays even though nothing currently
    trips it, because a silently overlapping ring is the failure the whole
    flattening was done to avoid.

    **The harness does not vote here.** What the rules say is carried on the
    block as a broken edge and in the roster as a code, for you to overrule or
    agree with by looking.
    """
    decided = placements()
    chosen = []

    # Angle, not hue: equal angle is equal share of projects, and a tile is as
    # wide as the share it takes. Compression belongs to the ring alone -- a
    # tile squeezed along with it gives back exactly what the compression was
    # for.

    def verdict(names):
        got = decided[names][0] if names in decided else None
        return "inner" if got in ("out", "in") else got

    for delta, reads, names, mixed, _flag in rows:
        if verdict(names) != "ring":
            continue
        where = decided[names][1]
        if where is None or where[0] != "at":
            print(f"  {' '.join(names)} (#{canon(names)}) is on the ring "
                  f"with no angle; left off")
            continue
        chosen.append((delta, where[1] % 360, names, mixed, reads))

    keep, contested = [], []
    for row in sorted(chosen, key=lambda r: r[1]):
        half = WEDGE[len(set(row[2]))] * WIDTH_SCALE / 2
        if any(circular_overlap(row[1] - half, row[1] + half,
                                k[1] - WEDGE[len(set(k[2]))] * WIDTH_SCALE / 2,
                                k[1] + WEDGE[len(set(k[2]))] * WIDTH_SCALE / 2)
               for k in keep):
            contested.append(row)
        else:
            keep.append(row)
    return keep, contested


def gaps(chosen):
    """The arcs tier 0 leaves unnamed, longest first, in angle.

    Angle rather than hue, so a gap reads as the share of projects that would
    get no triple: one degree here is one degree of the draw wherever it sits.
    """
    arcs = sorted(((r[1] - WEDGE[len(set(r[2]))] * WIDTH_SCALE / 2) % 360,
                   WEDGE[len(set(r[2]))] * WIDTH_SCALE) for r in chosen)
    out = []
    for k, (lo, wide) in enumerate(arcs):
        nxt = arcs[(k + 1) % len(arcs)][0] + (360 if k + 1 == len(arcs) else 0)
        if nxt - (lo + wide) > WEDGE_TOL:
            out.append(((lo + wide) % 360, nxt - (lo + wide)))
    return sorted(out, key=lambda g: -g[1])


def gamut_at(hue):
    """The colour mapping version 2 produces at this hue.

    One Oklab lightness right around the wheel, with the chroma capped or held
    to what sRGB carries, whichever is smaller. The ring is the thing a block
    is judged against, so it has to be the ring the project actually draws --
    it was identicon.js's fixed-saturation HSL until version 2 replaced it.
    """
    degrees = hue % 360
    return tuple(identicon._encode(v) for v in identicon._oklch_to_linear(
        identicon.MARK_LIGHTNESS, identicon.gamut_chroma(degrees), degrees))


# ---------------------------------------------------------------------------
# Compressing the ring
#
# The hue draw is uniform, so every degree of ring gets the same share of
# projects -- including the degrees no triple can name. A warp changes where
# those bits land: hue still runs 0 to 360 and every colour still exists, but
# an arc can be given less of the draw than its width suggests.
#
# The speed function is a raised cosine, so its derivative is zero at both
# ends and the ramp has no corner: `speed(t) = 1 + (peak-1) * bump(t)`, with
# the bump one full cosine period centred on `centre` and half-width `half`.
# Its integral is elementary, which matters more than it looks: a port has to
# reproduce this exactly, and a closed form with one sine in it is a paragraph
# of specification where a spline would be a page.
#
# WARP is (centre, half, peak) in degrees, or None for the uniform draw.
# `peak` is how much faster the hue advances at the centre, so the share of
# projects landing there falls by roughly that factor.
# ---------------------------------------------------------------------------

WARP = (215.0, 50.0, 4.0)


def warp_theta(angle):
    """Angle around the drawing to hue on the ring. Identity when unwarped."""
    if WARP is None:
        return angle % 360
    centre, half, peak = WARP
    total = 360 + (peak - 1) * half
    return 360 * (angle + (peak - 1) * _bump_integral(angle % 360)) / total


def _bump_integral(t):
    """The raised-cosine bump, integrated from the ramp's start to angle t."""
    centre, half, _peak = WARP
    u = t - centre
    if u <= -half:
        return 0.0
    if u >= half:
        return half
    return 0.5 * (u + half) + (half / (2 * math.pi)) * math.sin(math.pi * u / half)


def warp_angle(hue):
    """Hue on the ring back to angle around the drawing, by bisection.

    Numeric because only the renderer needs it: the mapping itself only ever
    goes the other way, from the digest's bits to a colour.
    """
    if WARP is None:
        return hue
    turns, hue = divmod(hue, 360)
    lo, hi = 0.0, 360.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if warp_theta(mid) < hue:
            lo = mid
        else:
            hi = mid
    return turns * 360 + (lo + hi) / 2


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def ring(out):
    """The gamut itself, one thin segment at a time.

    Drawn as rotated rectangles rather than annular sectors: at this radius a
    quarter-degree of arc is under a pixel, so the difference is invisible and
    the arithmetic is one line instead of four.
    """
    inner, outer = RING_IN, RING_OUT
    width = 2 * math.pi * outer * RING_STEP / 360 + 0.4
    steps = int(round(360 / RING_STEP))
    for k in range(steps):
        angle = k * RING_STEP
        colour = text.hex_colour(gamut_at(warp_theta(angle)))
        out.append(
            f'<rect x="{CENTRE - width / 2:.3f}" y="{CENTRE - outer:.1f}" '
            f'width="{width:.3f}" height="{outer - inner}" fill="{colour}" '
            f'transform="rotate({angle:.4f} {CENTRE} {CENTRE})"/>')


# White pulls less weight than the physics says it should. A rendered white
# square is not #ffffff -- it carries a border and the glyph is not a flat
# field -- and next to two saturated squares the eye discounts it further,
# reading it as a lightener rather than as a third of the colour. Halving it
# is Justin's calibration against what he can see, not a claim about optics,
# and it is the one place in this file where the model is deliberately not
# physical. Black is untouched: nothing suggests it needs the same.
WHITE_WEIGHT = 0.5


def mix_rgb(names):
    """The three squares averaged in linear light, back as sRGB.

    Linear light because that is what optical mixing does; averaging the sRGB
    numbers directly comes out too dark. White is weighted down -- see
    `WHITE_WEIGHT`.
    """
    weights = [WHITE_WEIGHT if n == "white" else 1.0 for n in names]
    total = sum(weights)
    linear = [tuple(text._linear(v) for v in square_rgb(n)) for n in names]
    return tuple(text._encode(sum(w * c[k] for w, c in zip(weights, linear)) / total)
                 for k in range(3))


def oklab(rgb):
    """sRGB to Oklab."""
    return text._oklab(tuple(text._linear(v) for v in rgb))


_GAMUT = [(h * RING_STEP, gamut_at(h * RING_STEP))
          for h in range(int(360 / RING_STEP))]


def hue_angle(rgb):
    """The blend's hue in Oklab, in degrees. Not an HSL hue."""
    _L, a, b = oklab(rgb)
    return math.degrees(math.atan2(b, a)) % 360


_GAMUT_HUE = [(h, colour, hue_angle(colour)) for h, colour in _GAMUT]


def nearest_gamut(rgb):
    """Which gamut hue this blend reads as, by hue and not by proximity.

    **Not by Oklab distance.** A blend of three squares is always lighter and
    duller than the gamut, so the nearest colour outright gets chosen mostly on
    lightness, pale blends matching the cyans and dark ones the oranges
    regardless of hue: `blue blue white` came out at 198 degrees when its hue
    is 282.

    A blend's hue is its hue. It is read off the Oklab hue angle and matched
    against the gamut's, and the distance is then reported against the colour
    at *that* hue, which is a measure of how faithfully the blend renders it
    rather than a search for something else it resembles.
    """
    want = hue_angle(rgb)
    hue, colour, _a = min(
        _GAMUT_HUE, key=lambda hca: abs((hca[2] - want + 180) % 360 - 180))
    return hue, colour, math.dist(oklab(colour), oklab(rgb))


DISC_R = 6.0           # a constituent disc; what a 4 degree block can carry


def tiers(out, proposal, rest, tiers_map=None):
    """The vocabulary, stacked inward from the gamut, the suggestion outermost.

    **Nothing may be hidden.** Bucketing by four degrees and stacking three
    deep buried anything sharing a bucket and still overlapped across bucket
    edges. A block you cannot see is a block you cannot judge.

    Tiers are packed greedily instead: walk the entries in angle order and drop
    each into the first tier whose last block has cleared, opening a new tier
    only when every existing one is still occupied. That guarantees no overlap
    at any angle and uses depth only where the crowding is. Tier 0 is filled
    first and alone, so the suggestion reads as one band against the gamut and
    everything else stacks behind it.

    **Every block carries its number**, in the clear gap inside its own tier.
    Numbering tier 0 alone was a false economy: three green-blue triples read
    within a degree of each other, so they stack radially and read as one mark,
    and nothing on the drawing could say what the two behind it were.

    The trefoils stay with the outermost tier; one per tile would be a thicket.
    """
    ends = []                       # the arcs already taken in each tier
    assigned = []

    def drop(row, floor):
        """Into the outermost tier with actual room at this angle.

        **Each tier holds a list of arcs, not a running end angle.** The end
        angle was enough only while every tile arrived in angle order; the
        moment a tier bias let one jump the queue, it set the tier's end past
        everything behind it and locked the rest of the ring out -- five tiles
        in tiers 2 to 6 with tier 1 empty beneath them.
        """
        wide = width_of(row) / 2
        for k in range(floor, len(ends)):
            if not any(circular_overlap(row[1] - wide, row[1] + wide, a, b)
                       for a, b in ends[k]):
                ends[k].append((row[1] - wide, row[1] + wide))
                assigned.append((k, row))
                return
        # Nothing had room: open a new tier. Appending to the last one instead
        # drew every tile that did not fit on top of what was already there --
        # a shallow-looking stack that was an overlapping one, and the check
        # that passed it only ever looked at the ring.
        while len(ends) < floor:
            ends.append([])
        ends.append([(row[1] - wide, row[1] + wide)])
        assigned.append((len(ends) - 1, row))

    for row in sorted(proposal, key=lambda r: r[1]):
        drop(row, 0)
    behind = len(ends)
    for row in sorted((r for r in rest if not is_sunk(r[2])),
                      key=lambda r: (bias_of(r[2]), r[1])):
        drop(row, behind + max(0, bias_of(row[2])))

    # **The sunk ones start below everything, not merely deeper.** Given a
    # bias they still competed for tiers with the alternatives, and one that
    # happened to find room surfaced among them -- which is the one thing the
    # verdict is for preventing. Their floor is whatever depth the rest ended
    # at, so the band is theirs alone and cannot be entered from above.
    #
    # **And banded by luminance.** Split by how dark the blend comes out, the
    # two ends read as what they are -- too dark to carry a hue, too light to
    # carry one -- with the middle band holding the ones rejected for some
    # other reason entirely. Each band's floor is the depth the band above
    # ended at, so no tile can surface out of its own band however much room
    # happens to be going in the one above it. Outermost first, so: neither,
    # then too light, then too dark hard against the middle of the wheel. The
    # two ends are done being looked at and the middle band is not, so the band
    # that still has questions in it sits nearest the tiers still being judged.
    for band in (SUNK_MID, SUNK_LIGHT, SUNK_DARK):
        floor = len(ends)
        for row in sorted((r for r in rest
                           if is_sunk(r[2]) and sunk_band(r[3]) == band),
                          key=lambda r: r[1]):
            drop(row, floor)

    # **Nothing is reordered after packing.** Ranking the tiers by chroma broke
    # the one property the packing exists to give: a tile sits in the outermost
    # tier that had room for it, so the stack is dense from tier 1 inward and
    # depth reads as crowding. Reordering left holes against the ring and put
    # sparse tiers outside full ones.

    depth = max(len(ends), 1)
    # `RING_SEP` comes off the top before the stack is divided up, so holding
    # tier 0 clear costs the tiers below it depth rather than costing every
    # block its height.
    pitch = min(TIER_BAND + TIER_LABEL,
                (TIER_OUT - RING_SEP - TIER_FLOOR) / depth)
    height = pitch * TIER_BAND / (TIER_BAND + TIER_LABEL)
    # Half again as deep, and only with the tiers hidden. At full depth the ring
    # would eat the gap below it and sit on the tier behind it, so the deeper
    # block and the hidden stack are one look rather than two settings.
    ring_height = height * (RING_DEEP if RING_ONLY else 1.0)

    ticks = []
    tiers_map = {} if tiers_map is None else tiers_map
    for tier, row in assigned:
        _delta, at, names, mixed, n, proposed, _reads, flag = row
        wide = width_of(row) / 2
        lo, hi = at - wide, at + wide
        outer = TIER_OUT - tier * pitch - (RING_SEP if tier else 0)
        # Tier 0 is drawn with a heavier edge -- lightened to 0.65, but not
        # down to the 0.5 the other tiers get. Being outermost is not enough to
        # find it by: it is filled first and only where a block fits, so a
        # stretch of hue it has nothing for shows tier 1 as the outermost thing
        # present, and the suggestion and the alternatives read alike.
        #
        # A block the harness objects to is drawn with a broken edge, not a
        # colour and not a fade: the fill is the entire claim the block makes,
        # so anything done to it argues with the thing being judged.
        colour, weight = ('#333', 0.65) if proposed else ('#888', 0.5)
        dash = ' stroke-dasharray="2 1.6"' if flag else ''
        # **Recorded before anything is drawn.** Under `--ring-only` the tiers
        # are not drawn, and every one of them is still packed, still assigned a
        # depth and still reported by the checklist. Nothing is dropped from the
        # run; one band of it is left off the picture.
        tiers_map[names] = tier
        band = ring_height if tier == 0 else height
        if RING_ONLY and tier:
            continue
        out.append(
            f'<path d="{sector(outer - band, outer, lo, hi)}" '
            f'fill="{text.hex_colour(mixed)}" stroke="{colour}" '
            f'stroke-width="{weight}"{dash}/>')
        # Up against the block rather than centred in the gap below it. Centred
        # sat a number as near the tier beneath as the one it names, and on a
        # wheel nine deep that is a real question every time you read one.
        # Tier 0 alone is numbered outward, in the corridor between the ring and
        # the gamut; every other tier keeps its number in the gap inside itself,
        # which is the only place it could go without covering something.
        number(out, at, n, RING_NUMBER_R if tier == 0
               else outer - height - (pitch - height) * 0.3)
        constituents(out, names, at, outer - band / 2, hi - lo)
        if proposed:
            ticks.append((at, warp_angle(_reads), mixed))
        if proposed and width_of(row) >= 4.0:
            venn(out, names, tref_top(), at, DISC_R)
    # Inside the ring now: the ticks take the clear gap tier 0's numbers left,
    # hung a fixed distance below the block, and the leader runs outward from
    # that vertex to the tile's inner edge.
    drift(out, ticks, TIER_OUT - ring_height,
          TIER_OUT - ring_height - TICK_GAP)
    return depth


DRIFT_W = 0.55            # the tick stroke, in pixels
DRIFT_LEAD_W = 0.25       # the leader running from the tick to the block

# **The tick is anchored at its far end, not at its middle.** It used to be
# drawn either side of a centre radius, so shortening it walked the leader's
# attachment point outward and moved the whole fan. The vertex -- where the
# leader leaves the tick -- is now the fixed thing, set as a gap below the
# block, and the tick grows outward from it. Shortening it therefore opens air
# between the tick and the block it belongs to and disturbs nothing else.
TICK_GAP = 6.5            # vertex to the block's inner edge
TICK_LEN = 5.0 / 3        # a third of what it was


def drift(out, ticks, band, vertex):
    """A tick where each tile would sit if nobody had moved it, and a leader.

    A placed tile and one left where it fell look identical, so each tile gets
    a tick at its unmoved hue and a leader back to it. The tick is painted in
    the tile's own colour, which is what says whose it is.
    """
    for at, home, mixed in ticks:
        colour = text.hex_colour(mixed)
        x0, y0 = polar(vertex, home)
        x1, y1 = polar(vertex + TICK_LEN, home)
        out.append(f'<line x1="{x0:.2f}" y1="{y0:.2f}" x2="{x1:.2f}" '
                   f'y2="{y1:.2f}" stroke="{colour}" stroke-width="{DRIFT_W}"/>')
        if abs(((at - home + 180) % 360) - 180) < 0.01:
            continue
        bx, by = polar(band, at)
        out.append(f'<line x1="{x0:.2f}" y1="{y0:.2f}" x2="{bx:.2f}" '
                   f'y2="{by:.2f}" stroke="{colour}" '
                   f'stroke-width="{DRIFT_LEAD_W}" stroke-opacity="0.85"/>')


DOT_R = 1.7               # a constituent dot inside its own tile
DOT_MIN = 0.5             # below this a dot is a smudge, and nothing is drawn


def constituents(out, names, at, radius, span):
    """The three squares themselves, in order, inside the tile they make.

    The tile is the mixture; these are what it is a mixture of, in the order
    they would be shown. Drawn where the tile is rather than out on the
    trefoil band, so the two are read together without moving the eye.

    **Shrunk to fit, not dropped.** A tile too narrow for three dots at full
    size used to get none at all, and the rule bit far harder than its width
    suggested: the dots are a fixed size in pixels while a tile's width is an
    angle, so the same four-degree block loses them purely by sitting in a
    deeper tier, where the radius is smaller and four degrees is fewer pixels.
    That put the makeup out of reach of exactly the blocks whose colour is
    hardest to guess, and the only way to see one was to promote it. The dots
    now take whatever size the tile can hold, down to `DOT_MIN`, below which
    they would be three smudges rather than three colours.
    """
    step = math.degrees(2.6 * DOT_R / radius)
    rad = DOT_R
    if span < 3 * step:
        step = span / 3
        rad = math.radians(step) * radius / 2.6
        if rad < DOT_MIN:
            return
    for k, name in enumerate(names):
        x, y = polar(radius, at + (k - 1) * step)
        # The separating stroke shrinks with the dot. Held at 0.35 it was
        # thicker than the small dots were wide, so three colours read as one
        # white pill.
        out.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{rad:.2f}" '
                   f'fill="{square_hex(name)}" stroke="#ffffff" '
                   f'stroke-width="{min(0.35, rad * 0.2):.2f}"/>')


def number(out, hue, n, radius):
    """The block's number, in the clear gap immediately inside its own tier.

    **On the band it was type laid over the colour it was meant to let you
    read**, and taking it off entirely left the wheel unnameable -- the roster
    could say what a block was but you could not point at one. A gap per tier
    does both jobs: nothing is covered, and every number sits directly under
    the block it names, so which tier it belongs to needs no explaining.

    Set tangentially, and flipped through the lower half so none of them stand
    on their heads. Rotating with the wheel rather than staying upright is what
    keeps a three-digit number inside the four degrees most blocks get; upright
    text would need the width of its diagonal at every angle.
    """
    lower = 90 < hue < 270
    turn = hue - 180 if lower else hue
    y = CENTRE + radius if lower else CENTRE - radius
    # The baseline nudge is a share of the size rather than a fixed 2.2, so the
    # number stays centred on its radius when the size changes. At 2.2 against a
    # smaller face it sat low in the corridor instead of in the middle of it.
    out.append(
        f'<text x="{CENTRE}" y="{y + NUMBER_SIZE * 0.4:.2f}" '
        f'text-anchor="middle" font-family="monospace" '
        f'font-size="{NUMBER_SIZE}" fill="#666" '
        f'transform="rotate({turn:.3f} {CENTRE} {CENTRE})">{n}</text>')


def width_of(row):
    """How wide this block is drawn: its class price, and nothing else.

    Nothing is hand-stretched any more; every block is at 1x.
    """
    return WEDGE[len(set(row[2]))] * WIDTH_SCALE


# ---------------------------------------------------------------------------
# The trefoils
# ---------------------------------------------------------------------------

# The trefoil is a Venn diagram, not three separate discs. Separate discs said
# only which squares go in; overlapping them puts the two-way mixes and the
# three-way mix on the page as well, which is where the question "what does
# this actually average to" is being asked. Inner borders are dropped: a stroke
# on each lens would out-draw the fills at this size.
#
# DISC_SEP is the centre-to-centre separation as a multiple of the disc radius:
# below sqrt(3) there is a middle region at all, and 1.0 is the tightest
# arrangement here. **Do not widen it to make the lenses readable** -- they
# were missing because the clip-paths did not resolve, not because they were
# thin, and the regions are explicit polygons now.
DISC_SEP = 1.0


def tref_top():
    """The radius the outermost point of a trefoil sits at, centring it.

    **Measured, not nudged.** The cluster's depth is two disc radii plus the
    drop to the tucked-under third, so the padding that centres it is worked
    out rather than guessed, and it stays centred if the discs or the band
    change size.
    """
    depth = 2 * DISC_R + 1.5 * DISC_SEP * DISC_R / math.sqrt(3)
    return TREF_OUT - (TREF_OUT - TREF_IN - depth) / 2


def venn(out, names, top, hue, radius=None):
    """Three overlapping discs, with every intersection filled by its mix.

    Drawn without any subtraction: the three discs go down whole, the three
    lenses are each a disc clipped to its partner, and the middle is a disc
    clipped to both of the others. Later paint covers earlier, so exclusive
    regions survive as the bare disc underneath.
    """
    rad = DISC_R if radius is None else radius
    cee = DISC_SEP * rad / math.sqrt(3)
    # Two abreast, one tucked beneath, matching the old cluster's footprint.
    # y runs inward; the outermost point of the cluster sits at `top`.
    local = [(-0.8660 * cee, -0.5 * cee),
             (0.8660 * cee, -0.5 * cee),
             (0.0, cee)]
    centres = []
    for x, y in local:
        r = top - rad - (y + 0.5 * cee)
        centres.append(polar(r, hue + math.degrees(x / r)))

    def disc(k, extra=""):
        cx, cy = centres[k]
        return f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{rad:.2f}"{extra}/>'

    # Strokes go down first and the fills paint over them, so every arc that
    # runs through the inside of another disc is covered and only the union's
    # outer boundary survives: an outline round the cluster, no inner borders.
    for k in range(3):
        out.append(disc(k, ' fill="none" stroke="#777" stroke-width="0.9"'))
    for k in range(3):
        out.append(disc(k, f' fill="{square_hex(names[k])}"'))
    for a, b in ((0, 1), (1, 2), (0, 2)):
        out.append(overlap([centres[a], centres[b]],
                           mix_rgb((names[a], names[b])), rad))
    out.append(overlap(centres, mix_rgb(names), rad))


def overlap(centres, mixed, rad):
    """The region common to these discs, as one explicit polygon.

    **No clip-paths.** A lens drawn as a disc carrying `clip-path="url(#...)"`
    is honoured by every browser and by at least one SVG renderer not at all --
    an unresolved reference clips the shape away entirely, so the three plain
    discs survive and every overlap silently vanishes, with nothing in the file
    looking wrong. The region is computed and written out as coordinates
    instead, so what the file says is what any renderer draws.

    The intersection of discs is convex, hence star-shaped about any interior
    point, so casting a ray from the centroid and taking the nearest exit of
    the several circles traces the boundary exactly. Sixty-four steps is well
    past the resolution of a disc this size.
    """
    cx = sum(p[0] for p in centres) / len(centres)
    cy = sum(p[1] for p in centres) / len(centres)
    points = []
    for i in range(64):
        th = 2 * math.pi * i / 64
        ux, uy = math.cos(th), math.sin(th)
        best = None
        for px, py in centres:
            dx, dy = px - cx, py - cy
            along = ux * dx + uy * dy
            root = rad * rad - (dx * dx + dy * dy) + along * along
            if root <= 0:            # the ray misses: no common region at all
                return ""
            t = along + math.sqrt(root)
            best = t if best is None else min(best, t)
        if best <= 0:
            return ""
        points.append(f"{cx + ux * best:.2f},{cy + uy * best:.2f}")
    return (f'<polygon points="{" ".join(points)}" '
            f'fill="{text.hex_colour(mixed)}"/>')


# ---------------------------------------------------------------------------
# Numbering, the roster and the checklist
# ---------------------------------------------------------------------------

def table(out, rows, columns):
    """Every block on the wheel, beside the wheel, in as many columns as it takes.

    The wheel says where each block sits and what it looks like; it cannot say
    what it is made of without covering itself in type. This is the other half:
    mixture, constituents, the hue the mixture reads as, and dE, the Oklab
    distance between the blend and the gamut colour it stands in for.

    **All of them, not the suggestion alone.** Tier 0 used to be the roster and
    the rest lived in corner lists behind a flag, which meant a block could be
    drawn on the wheel, numbered on the wheel, and named nowhere. Tier 0 comes
    first, in ring order; the rest follow from 101 in the order of the hue they
    read as, which is the order their numbers were issued in, so a number found
    on the wheel is looked up by counting down.
    """
    SW, GAP, ROW = 6, 1, 7.0
    top = 22
    # Tier 0 gets a column to itself even where it does not fill one. Splitting
    # on the row count alone ran the 101s up the bottom of the first column
    # under a heading that said they were on the ring, which is exactly the
    # sort of quiet mislabelling this roster exists to prevent.
    first = [r for r in rows if r[5]]
    others = sorted((r for r in rows if not r[5]), key=lambda r: r[4])
    chunks = [first] + [others[k:k + ROSTER_ROWS]
                        for k in range(0, len(others), ROSTER_ROWS)]
    out.append('<g font-family="monospace" font-size="5.5" fill="#444">')
    for c, chunk in enumerate(chunks[:columns]):
        if not chunk:
            continue
        x0 = SIZE + 14 + c * COL_W
        head = (f"on the ring: {len(chunk)}" if c == 0 else
                f"#{chunk[0][4]}-{chunk[-1][4]}")
        out.append(f'<text x="{x0}" y="{top - 9}" font-size="6.5" '
                   f'fill="#222">{head}</text>')
        out.append(f'<text x="{x0 + 78}" y="{top - 2}" text-anchor="end" '
                   f'fill="#888">reads</text>')
        out.append(f'<text x="{x0 + 100}" y="{top - 2}" text-anchor="end" '
                   f'fill="#888">dE</text>')
        out.append(f'<text x="{x0 + 104}" y="{top - 2}" fill="#888">rule</text>')
        for i, row in enumerate(chunk):
            delta, _hue, names, mixed, n, proposed, reads, flag = row
            y = top + i * ROW
            drop = y + SW - 2
            out.append(f'<text x="{x0 + 12}" y="{drop}" text-anchor="end" '
                       f'fill="{"#333" if proposed else "#999"}">{n}</text>')
            out.append(f'<rect x="{x0 + 15}" y="{y}" width="{SW}" '
                       f'height="{SW}" fill="{text.hex_colour(mixed)}" '
                       f'stroke="#666" stroke-width="0.7"/>')
            for s, name in enumerate(names):
                out.append(f'<rect x="{x0 + 26 + s * (SW + GAP)}" y="{y}" '
                           f'width="{SW}" height="{SW}" fill="{square_hex(name)}" '
                           f'stroke="#aaa" stroke-width="0.5"/>')
            where = "  --  " if reads is None else f"{reads:.1f}&#176;"
            out.append(f'<text x="{x0 + 78}" y="{drop}" text-anchor="end">'
                       f'{where}</text>')
            # Red past dE 0.15: far enough from the gamut colour it stands in
            # for to be worth a second look.
            out.append(f'<text x="{x0 + 100}" y="{drop}" text-anchor="end" '
                       f'fill="{"#b00" if delta >= 0.15 else "#444"}">'
                       f'{delta:.3f}</text>')
            if flag:
                out.append(f'<text x="{x0 + 104}" y="{drop}" fill="#999">'
                           f'{flag}</text>')
    out.append('</g>')


# **A number is a position, and the position is written down.** It is the line
# a tile sits on in `wheel.tsv`, which is ordered clockwise from the top -- so
# the file is the numbering, and sorting the file is how the wheel is
# renumbered. Nothing in this module decides it, so nothing here can disagree
# with the drawing about what a number means.
CANON = {}


def canon(names):
    """The tile's number: the line it sits on in `wheel.tsv`."""
    if not CANON:
        for k, (_verb, _where, triple) in enumerate(tsv_lines(), 1):
            CANON[triple] = k
    return CANON[names]


# Three row shapes travel through this file, aligned on delta, names and mixed
# so a helper can take more than one of them. Field 1 is not shared: it is the
# hue the blend reads as in the first, and the angle the tile is drawn at in
# the other two.
#   catalogue: (delta, reads, names, mixed, flag)
#   propose:   (delta, angle, names, mixed, reads)
#   numbered:  (delta, angle, names, mixed, number, on_ring, reads, flag)
def numbered(picks, others):
    """Rows for the renderer, each carrying the number `wheel.tsv` gives it."""
    rows = []
    for i, (delta, at, names, mixed, reads) in enumerate(sorted(picks,
                                                                key=lambda r: r[1])):
        rows.append((delta, at, names, mixed, canon(names), True, reads,
                     flag_at(names, warp_theta(at))))
    for i, (delta, reads, names, mixed, flag) in enumerate(
            sorted(others, key=lambda r: r[1])):
        moved = sunk_at(names)
        rows.append((delta, warp_angle(reads) if moved is None else moved,
                     names, mixed, canon(names), False, reads, flag))
    return rows


def checklist(picks, tiers_of):
    """Every line of `wheel.tsv`, and what actually became of it.

    Reported by the run rather than by me: a tile that could not be seated used
    to print one line among many and was missed, and an instruction applied to
    the wrong tile showed up nowhere at all.
    """
    seats = {r[2]: r[1] for r in picks}
    print("     #  verdict         triple                  outcome")
    trouble = 0
    for n, (verb, where, names) in enumerate(tsv_lines(), 1):
        if names in seats:
            got = f"ring {seats[names]:.1f}"
        elif names in tiers_of:
            got = f"tier-{tiers_of[names]}"
        elif verb == "hueless":
            got = "no hue"
        else:
            got = "NOWHERE"
        # A tile asked for the ring and not on it, or one that landed nowhere
        # at all. Everything else is the file and the drawing agreeing.
        bad = (verb == "ring" and names not in seats) or got == "NOWHERE"
        trouble += bad
        print(f"  {'! ' if bad else '  '}{n:>3}  {verb + ' ' + where:<14} "
              f"{' '.join(names):<22}  {got}")
    if trouble:
        print(f"  {trouble} line(s) did not land")
    return trouble


# ---------------------------------------------------------------------------
# Assembling the page
# ---------------------------------------------------------------------------

def render():
    """The wheel: the gamut, and every triple admissible against it.

    The canvas takes as many roster columns as the vocabulary needs, so adding
    a triple widens the page rather than dropping a row off the bottom of it.
    """
    all_rows, hueless = catalogue()
    picks, ejected = propose(all_rows)
    for row in ejected:
        print(f"  no room on the ring for {' '.join(row[2])} "
              f"(#{canon(row[2])}); it stays in the tiers")
    taken = {r[2] for r in picks}
    rest = [r for r in all_rows if r[2] not in taken]
    rows = numbered(picks, rest)
    # The ones that average to a neutral keep their place in the roster and
    # take none on the ring: no hue, so nowhere to stand.
    rows += [(d, None, names, mixed, canon(names), False, None, flag)
             for d, _r, names, mixed, flag in hueless]
    # One column for tier 0, then as many as the rest need. With the roster off
    # the canvas is the wheel and nothing else.
    columns = 1 + max(1, -(-(len(rows) - len(picks)) // ROSTER_ROWS))
    wide = SIZE if RING_ONLY else SIZE + 14 + columns * COL_W + 24
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{wide}" '
           f'height="{SIZE}" viewBox="0 0 {wide} {SIZE}">',
           f'<rect width="{wide}" height="{SIZE}" fill="#ffffff"/>']
    ring(out)
    # Neutral, not a second gamut. Putting the gamut back there sounded right
    # -- read each trio against the colour it stands in for -- but it gave
    # every trefoil a different ground, so no two clusters could be compared
    # with each other, only each with the hue behind it. A flat mid grey is
    # the same everywhere and biases nothing.
    out.append(f'<path d="{sector(TREF_IN, TREF_OUT, 0, 180)}" fill="{TREF_BG}"/>')
    out.append(f'<path d="{sector(TREF_IN, TREF_OUT, 180, 360)}" fill="{TREF_BG}"/>')
    tiers_of = {}
    depth = tiers(out, [r for r in rows if r[5]],
                  [r for r in rows if not r[5] and r[1] is not None], tiers_of)
    if not RING_ONLY:
        table(out, rows, columns)
    out.append('</svg>')
    return "\n".join(out), rows, picks, depth, tiers_of


# ---------------------------------------------------------------------------
# The in-use artifact, and the CLI
# ---------------------------------------------------------------------------

IN_USE = HERE / "in-use.tsv"

EMOJI = {name: emoji for emoji, name, _cp, _rgb in text.PALETTE}


def reference():
    """The in-use set alone, as arcs of hue, for an implementation to consume.

    `wheel.tsv` is a working document: it carries what was rejected, what sits
    in a tier unused, and which band each of those is in. None of that is
    wanted by something deciding which three squares a project gets. This is
    the other artifact -- the mapping and nothing else, derived from the same
    file so the two cannot disagree.

    Rows tile [0, 360) with no gap and no overlap, so a lookup is `from <= hue
    < to` and always hits exactly once. The block that straddles zero is split
    into two rows sharing its number rather than left to wrap, because a
    consumer that has to special-case one row will eventually not.
    """
    rows = sorted(((n, names, float(where))
                   for n, (verb, where, names) in enumerate(tsv_lines(), 1)
                   if verb == "ring"), key=lambda r: r[2])
    arcs = []
    for n, names, at in rows:
        # Class price, no multiplier.
        half = WEDGE[len(set(names))] / 2
        lo, hi = at - half, at + half
        if lo < 0:
            arcs.append((0.0, hi, n, names))
            arcs.append((lo + 360, 360.0, n, names))
        elif hi > 360:
            arcs.append((lo, 360.0, n, names))
            arcs.append((0.0, hi - 360, n, names))
        else:
            arcs.append((lo, hi, n, names))
    arcs.sort()

    edge = 0.0
    for lo, hi, n, _names in arcs:
        assert abs(lo - edge) < 1e-6, f"gap or overlap at {lo} (#{n})"
        edge = hi
    assert abs(edge - 360) < 1e-6, f"ends at {edge}, not 360"

    out = [
        f"# Colour mapping wheel {WHEEL_VERSION}.",
        "#",
        "# The mapping, and nothing else: which three squares stand for a hue.",
        "#",
        "# Generated by `wheel.py --reference` from wheel.tsv. Do not edit by",
        "# hand -- edit wheel.tsv and regenerate, or the wheel and the table",
        "# will disagree and only one of them is being looked at.",
        "#",
        "# **Indexed by the draw, not by the hue.** The number to look up is the",
        "# raw 28 bits from the digest as degrees -- `hexval(h[-7:]) / 0xfffffff",
        "# * 360` -- before any mapping version's colour rule touches it. Under",
        "# version 3 the hue is that value warped, so the two are different",
        "# numbers and indexing by the wrong one silently shifts every triple",
        "# around the blue-greens. The ring these rows come from is placed in the",
        "# same coordinate, which is why they agree.",
        "#",
        "# Rows tile 0 to 360 with no gap and no overlap: the row to use is the",
        "# one where `from <= draw < to`, and there is always exactly one.",
        "#",
        "# The squares are given inner to outer, already in the order they are",
        "# to be shown. Arrangement and square-versus-circle are a separate",
        f"# channel and are not in this file. {len(rows)} blocks.",
        "#",
        "# from\tto\tn\tone\ttwo\tthree\tmark   (from/to are draw, not hue)",
    ]
    for lo, hi, n, names in arcs:
        out.append("\t".join([f"{lo:.1f}", f"{hi:.1f}", str(n), *names,
                              "".join(EMOJI[x] for x in names)]))
    IN_USE.write_text("\n".join(out) + "\n")
    return len(arcs), len(rows)


def next_path():
    """One past the highest wheelN.svg. The wheel is a series, like the sheets.

    **Highest plus one, not first free.** The series is full of holes, and a
    render into a hole overwrites nothing on disk and everything in the record:
    the numbers are how these pictures are referred to across sessions, so
    wheel1 meaning two different pictures is worse than a gap. Observed, not
    theorised -- a plain render landed on the committed wheel1.svg.
    """
    used = [int(p.stem[5:])
            for p in HERE.glob("wheel*.svg") if p.stem[5:].isdigit()]
    return HERE / f"wheel{max(used, default=0) + 1}.svg"


def main(argv):
    """Parse the flags, then either regenerate in-use.tsv or render and report
    what landed where.
    """
    global AS_PAINTED, WARP, WIDTH_SCALE, RING_ONLY
    AS_PAINTED = "--painted" in argv
    RING_ONLY = "--ring-only" in argv
    if "--scale" in argv:
        WIDTH_SCALE = float(argv[argv.index("--scale") + 1])
    if "--warp" in argv:
        centre, half, peak = (float(v) for v in
                              argv[argv.index("--warp") + 1].split(","))
        WARP = (centre, half, peak)

    if "--reference" in argv:
        arcs, blocks = reference()
        print(f"{IN_USE} {arcs} arcs from {blocks} blocks, tiling 0-360")
        return 0

    if "--out" in argv:
        path = pathlib.Path(argv[argv.index("--out") + 1])
        if not path.is_absolute():
            path = HERE / path
    else:
        path = next_path()
    svg, rows, picks, depth, tiers_of = render()
    path.write_text(svg)
    checklist(picks, tiers_of)
    covered = sum(WEDGE[len(set(r[2]))] for r in picks)
    flagged = sum(1 for r in rows if r[7])
    print(f"{path} {len(svg)} bytes")
    # Which palette: the two make pictures easily mistaken for each other.
    print(f"  {'squares as the vendors paint them, weighted' if AS_PAINTED else 'squares as Unicode names them'}"
          f"{f', tiles at {WIDTH_SCALE:g}x' if WIDTH_SCALE != 1 else ''}"
          f"{', ring only -- the tiers are packed and reported, not drawn' if RING_ONLY else ''}")
    print(f"  catalogue {len(rows)} triples, {depth} tiers deep, "
          f"{flagged} flagged by the harness, "
          f"{sum(1 for r in rows if r[1] is None)} with no hue")
    print(f"  tier 1: {len(picks)} blocks, {covered:.0f} of 360 degrees "
          f"({covered / 3.6:.0f}%), "
          f"{sum(1 for r in rows if r[5] and r[7])} of them flagged")
    for at, wide in gaps(picks)[:6]:
        print(f"    gap {wide:5.1f} deg from {at:5.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

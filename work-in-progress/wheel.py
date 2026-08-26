#!/usr/bin/env python3
"""The wheel: the gamut as a ring, and the vocabulary available to name it.

    python3 wheel.py --painted         render the next free wheelN.svg
    python3 wheel.py --painted --ring-only    the ring alone, tiers not drawn
    python3 wheel.py --reference       regenerate in-use.tsv from wheel.tsv

`--painted` judges in the colours the vendors paint, and everything is authored
against it; the Unicode palette is a different arrangement and solving anything
against it will not transfer.

**`wheel.tsv` is the wheel, and this file only draws it.** All 165 triples have
a line each: sixty-three on the ring with the angle they are drawn at, the rest
in a tier or in one of the three sunk bands. A tile's number is the line it sits
on, and the lines run clockwise from the top.

This used to be a program that decided the arrangement -- it searched for the
best triple per stretch of hue, nudged blocked candidates to sit flush, pushed
neighbours aside, filled leftover arcs, and applied swaps, rolls, presses and
inserts on top. The ring is closed now at 360 of 360 with nothing spare, so all
of that has gone. What is left reads the file, draws it, and says when the two
disagree.

`in-use.tsv` is the other artifact: the mapping and nothing else, for an
implementation to consume, generated from the same file so the two cannot
disagree.

**One concern per artifact.** A block carries the multiset only: three squares,
no arrangement, no square-versus-circle. Those two are identity, and identity is
a separate question from whether the mark names the colour. Mixing them is what
made the contact sheets hard to read, because a change of arrangement and a
change of mapping look identical at a glance and only one is a colour judgement.

Nothing here reads a font or a screen. The ring is the gamut identicon.js
actually produces, at its own fixed saturation and lightness, so a block sits
directly against the colour it is meant to name.
"""

import importlib.util
import math
import pathlib
import sys

D = str(pathlib.Path(__file__).resolve().parent.parent) + "/"
S = pathlib.Path(__file__).parent


def load(path, module):
    spec = importlib.util.spec_from_file_location(module, path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


text = load(D + "text-identicon.py", "t")
identicon = load(D + "repository-identicon.py", "i")

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
    return text.hex_colour(square_rgb(name))

# ---------------------------------------------------------------------------
# Geometry. The ring is thick enough to read as a colour rather than a line,
# and the spike starts close enough to it that the comparison is immediate.
# ---------------------------------------------------------------------------

# Reading outward: the tiers, tier 1's numbers, the gamut, and tier 1's
# trefoils on neutral ground.
#
# **The gamut has moved out to where the block ring was.** Tier 0 held the
# fifty placed blocks in a wide band outside the gamut, and removing it left
# that band empty with nothing entitled to fill it -- nothing is placed. The
# ring takes the radius instead, which buys the tiers the whole interior: the
# vocabulary is 113 triples where the old ring was 50, and it has to stack.
SIZE = 720
CENTRE = SIZE / 2
TIER_FLOOR = 62                # nearest the middle a tier may reach
# Out by six, which is the corridor between tier 0 and the gamut narrowing to
# ten. Moving the ring out rather than the gamut in leaves the gamut, the
# neutral band and the trefoils exactly where they were, and the tier stack
# simply follows it out -- the pitch is capped, not derived from this, so
# nothing behind tier 0 changes shape.
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
# same things it always did and the index is untouched. What changes is one
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
# it holding that tier's numbers. Type over the band was tried on the version 1
# wheel and taken off again -- it covered the one thing the block is there to
# let you read -- and 112 numbers would have made that worse, not better.
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

    The base band uses real arcs rather than the rotated rectangles the ring
    gets away with: a division is five degrees wide, and at this radius a
    rectangle's corners would visibly overshoot the arc.
    """
    large = 1 if (a1 - a0) % 360 > 180 else 0
    x0, y0 = polar(r1, a0)
    x1, y1 = polar(r1, a1)
    x2, y2 = polar(r0, a1)
    x3, y3 = polar(r0, a0)
    return (f'M{x0:.2f},{y0:.2f} A{r1},{r1} 0 {large} 1 {x1:.2f},{y1:.2f} '
            f'L{x2:.2f},{y2:.2f} A{r0},{r0} 0 {large} 0 {x3:.2f},{y3:.2f} Z')


# ---------------------------------------------------------------------------
# **The bench is gone.** `bench.tsv` was the version 1 roster and the tool that
# fed it: `read_bench` parsed it, `pool` offered every unused triple the harness
# allowed, and `--refill` appended them for judging. That was the apparatus of
# choosing a vocabulary, and the vocabulary is chosen -- `wheel.tsv` carries all
# 165 with a verdict each, so there is nothing left to offer. The file described
# a ring sixteen of whose fifty blocks are no longer on this one, and it was the
# last thing `--reference` still read.
# ---------------------------------------------------------------------------

# Below this Oklab chroma a blend is a grey and its hue angle is noise. The
# seven that qualify are exactly the neutrals; the next candidate up is more
# than an order of magnitude clear of it.
NEUTRAL_CHROMA = 0.02


_PERC = None


def harness():
    """The perceptual rules, loaded once. Advisory here, not a gate."""
    global _PERC
    if _PERC is None:
        _PERC = load(str(S / "perceptual.py"), "perc")
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

    All 165 multisets. The rules are still run, and what they say is drawn on
    the block as a broken edge and named in the roster, but they no longer
    decide what is admitted. `DARK` and `LIGHT` are absolute luminances
    calibrated against the version 1 ring, which ran 0.20 at blue to 0.80 at
    yellow; the version 2 ring runs 0.20 to 0.49 and never reaches 0.58, so the
    two-white rule fires at every hue on the wheel and is measuring nothing.

    **It is nonetheless right every time**, which is the thing to know before
    touching it. All seven two-white triples were sunk by eye, so the rule that
    cannot discriminate and the person who can reach the same verdict on every
    one of them. Moving the cut into the gap in the distribution would make it
    pass four of them. See the note in `perceptual.py`.

    Seven multisets average to a neutral and have no hue at all: three blacks,
    three whites, black with two whites, and the opponent pairs that cancel.
    `atan2` of nothing is zero, so `nearest_gamut` hands them a position they
    have no claim to -- three blacks read 0.0 degrees at dE 0.646. They are
    returned separately, listed in the roster and given no place on the ring,
    since a wheel is an argument about hue and they are not in it.

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


# **The seating constants have gone with the seating.** `MAX_NUDGE` and
# `NUDGE_STEP` bounded how far a blocked block could slide to sit flush;
# `MAX_PUSH` bounded how far a fixed tile could shove its neighbour before the
# shuffle was called a relocation; `AUTO_FILL` said whether a leftover arc could
# be colonised by the best triple that fitted. None of them can be reached now
# that every seat is written down and the ring is closed.
#
# `FLUSH_TOL` went with them, and it is the one worth naming: it was set from
# Justin's eye rather than from a calculation, bracketed by a seam at 0.106 he
# could not see and one at 0.380 he asked to close. It governed only which tiles
# a `press` counted as coupled, and there is no `press`. The reading survives
# here in case a later question needs it; the constant does not, because a
# threshold nothing consults is a claim nothing tests.


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
    verdict, where = hand().get(names, ("", None))
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
    return hand().get(names, ("", None))[0] == "sink"


def sunk_at(names):
    """The angle a `sink` line gives, if it gives one.

    **The one verdict that moves a tile in angle without seating it.** For
    anything still under judgement that would be a lie -- the whole point of a
    tier is that a tile sits at the hue its blend reads, so it can be compared
    with the ring above it. A sunk tile is not being compared with anything, so
    a few degrees costs nothing, and spending them is what lets the set close
    up into two rows instead of splaying across nine.
    """
    verdict, where = hand().get(names, ("", None))
    if verdict != "sink":
        return None
    return where[1] if where and where[0] == "at" else None


HAND = S / "wheel.tsv"

_INDEX = None


def index():
    """Every line of `wheel.tsv`, in order: `(verb, where, triple)`.

    **The line number is the tile's number, and the line says which tile.**
    Both, deliberately. Position alone would put the whole file one out if a
    line were ever dropped, and silently. The triple alone was what the old
    file avoided carrying, because transcribing one by hand put half a batch on
    the wrong tiles once. Carrying both means the file can be checked against
    itself, which is what the number column is for -- it is never read as an
    identity, only compared with where it sits.
    """
    global _INDEX
    if _INDEX is not None:
        return _INDEX
    _INDEX = []
    if not HAND.exists():
        return _INDEX
    for line in HAND.read_text().splitlines():
        # A trailing comment, so a placement can carry what it cost beside it.
        line = line.split("#", 1)[0]
        if not line.strip():
            continue
        parts = line.split()
        n, verb, where, triple = parts[0], parts[1], parts[2], parts[3:]
        if len(triple) != 3:
            print(f"  not three squares: {line.strip()}")
            continue
        if not n.isdigit() or int(n) != len(_INDEX) + 1:
            print(f"  #{n} sits on line {len(_INDEX) + 1}: {line.strip()}")
        _INDEX.append((verb, where, multiset(tuple(triple))))
    seen = {t for _v, _w, t in _INDEX}
    if len(seen) != len(_INDEX):
        print(f"  {len(_INDEX) - len(seen)} triples named twice in {HAND.name}")
    return _INDEX


def hand():
    """Where each tile goes, read off the index.

    Every tile has a line, including the ones the packer used to place by
    falling through to its default. `tier` is that default written down: off
    the ring, wherever the packing puts it. It says the same thing the absence
    of a line used to say, and it says it where it can be read.
    """
    out = {}
    for verb, where, names in index():
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


# `score`, `base_square` and `BASE_FAVOUR` are gone with the automatic pass that
# was their only caller. They ranked candidates for a seat -- a triple carrying
# the single square nearest the colour it stood for was treated as better than
# its dE said, because `red yellow purple` beat two orange-based triples at 14
# degrees on Justin's eye and dE alone had it losing. That judgement is now in
# the ring itself, which is where it was always heading: the file records where
# each tile sits, so nothing has to be re-derived to decide it.


def propose(rows):
    """The ring: every tile the index seats, at the angle the index gives it.

    **This used to be an algorithm and is now a lookup.** It searched for the
    best triple per stretch of hue, seated it at or near its own hue, slid
    blocked candidates up to `MAX_NUDGE` to sit flush, pushed neighbours along
    when a fixed tile grew into their slot, filled leftover arcs with the best
    unplaced triple, and then applied a sequence of swaps, rolls, slides,
    presses and inserts on top. All of it was the machinery of arriving at an
    arrangement, and the arrangement has arrived: the ring is closed at 360 of
    360 and every tile on it carries a hand-written angle. Nothing was ever
    nudged, pushed, auto-filled or operated on in the final render -- traced,
    not assumed -- so all of it has gone, along with `MAX_PUSH`, `FLUSH_TOL`
    and `AUTO_FILL`.

    What is left is the one thing that still does work: place what the file
    says, then refuse to draw two tiles on top of each other. That check stays
    even though nothing currently trips it, because it is the guard that says
    so when an edit to the file overlaps two tiles -- and a silently
    overlapping ring is the failure the whole flattening was done to avoid.

    **The harness does not vote here.** What the rules say is carried on the
    block as a broken edge and in the roster as a code, for you to overrule or
    agree with by looking.
    """
    decided = hand()
    chosen = []

    # **Everything here is in angle, not in hue.** The angle around the wheel is
    # the draw: equal angle is equal share of projects, by construction, and a
    # tile's width is the share it takes. Compression belongs to the ring alone
    # -- it decides which hue sits under a given angle, and so how much hue a
    # tile spans, which is what compressing an under-served stretch means. A
    # tile squeezed along with the ring would have given back exactly what the
    # compression was for.

    def verdict(names):
        got = decided[names][0] if names in decided else None
        return "inner" if got in ("out", "in") else got

    # Every seat is written down, so this is a read rather than a search.
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
    """The arcs tier 1 leaves unnamed, longest first, in angle.

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
    centre, half, peak = WARP
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


# `share` and `hue_of` are gone. `share` reported what fraction of projects fell
# in an arc under the warp, and its only caller was the banner. `hue_of` was a
# plain HSL hue, superseded by `hue_angle`, which measures in Oklab -- the space
# every other judgement on this wheel is made in.


def multiset(names):
    """Order-free form, for asking whether two triples use the same squares."""
    return tuple(sorted(names, key=lambda n: ORDER[n]))


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def ring(out, inner=None, outer=None):
    """The gamut itself, one thin segment at a time.

    Drawn as rotated rectangles rather than annular sectors: at this radius a
    quarter-degree of arc is under a pixel, so the difference is invisible and
    the arithmetic is one line instead of four.

    Drawn twice now. The inner copy is what the block ring is judged against.
    The outer copy is the ground the trefoils sit on, so each cluster of
    constituent squares is read against the gamut colour at its own position
    rather than against white -- which is the comparison actually being made
    when a triple is placed, and the one thing white paper cannot show.
    """
    inner = RING_IN if inner is None else inner
    outer = RING_OUT if outer is None else outer
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

    **This was wrong, and wrong in a way that pointed the same direction every
    time.** It used to take the gamut colour at the smallest Oklab distance --
    but a blend of three squares is always lighter and duller than the gamut,
    which is fixed at saturation 0.7, so the nearest colour outright was chosen
    mostly on lightness. Pale blends were matched to the cyans and darker ones
    to the oranges, regardless of hue: `blue blue white` came out as 198
    degrees when its hue is 282, and `green purple brown` came out as 38
    degrees when it is a green at 129.

    A blend's hue is its hue. It is read off the Oklab hue angle and matched
    against the gamut's, and the distance is then reported against the colour
    at *that* hue, which is a measure of how faithfully the blend renders it
    rather than a search for something else it resembles.
    """
    want = hue_angle(rgb)
    hue, colour, _a = min(
        _GAMUT_HUE, key=lambda hca: abs((hca[2] - want + 180) % 360 - 180))
    return hue, colour, math.dist(oklab(colour), oklab(rgb))


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
DISC_R = 6.0           # a constituent disc; what a 4 degree block can carry


def tiers(out, proposal, rest, tiers_map=None):
    """The vocabulary, stacked inward from the gamut, the suggestion outermost.

    **Nothing may be hidden.** An earlier version bucketed by four degrees and
    stacked three deep, which buried anything sharing a bucket and still
    overlapped across bucket edges -- two entries a degree apart landed in
    different buckets and drew straight over each other. A block you cannot see
    is a block you cannot judge.

    Tiers are packed greedily instead: walk the entries in angle order and drop
    each into the first tier whose last block has cleared, opening a new tier
    only when every existing one is still occupied. That guarantees no overlap
    at any angle and uses depth only where the crowding is. Tier 1 is filled
    first and alone, so the suggestion reads as one band against the gamut and
    everything else stacks behind it.

    **Every block carries its number**, in the clear gap inside its own tier.
    Numbering tier 1 alone was a false economy: three green-blue triples read
    within a degree of each other, so they stack radially and read as one mark,
    and with only the outermost named there was no way to ask what the two
    behind it were except by asking me. A wheel that cannot answer that is not
    a working document.

    The trefoils stay with tier 1. They are for judging one candidate closely
    and 112 of them would be a thicket.
    """
    ends = []                       # the arcs already taken in each tier
    assigned = []

    def drop(row, floor):
        """Into the outermost tier with actual room at this angle.

        **Each tier holds a list of arcs, not a running end angle.** The end
        angle was enough only while every tile arrived in angle order; the
        moment one jumped the queue -- which is exactly what a tier bias does
        -- it set the tier's end past everything behind it and locked the rest
        of the ring out. Five tiles sat in tiers 2 to 6 with tier 1 empty
        beneath them, and a tile asked to move one tier in went to tier 8.
        """
        wide = width_of(row) / 2
        for k in range(floor, len(ends)):
            if not any(circular_overlap(row[1] - wide, row[1] + wide, a, b)
                       for a, b in ends[k]):
                ends[k].append((row[1] - wide, row[1] + wide))
                assigned.append((k, row))
                return
        # Nothing had room: open a new tier. Appending to the last one
        # instead put every tile that did not fit on top of whatever was
        # already there, which read as a shallow stack and was an overlapping
        # one -- and the check that passed it only ever looked at the ring.
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
    # **And banded by luminance, darkest band first.** Sunk together they were
    # 41 blocks in two rows packed by angle, which is a hedge and not a
    # judgement: nothing could be said about them as a group. Split by how dark
    # the blend actually comes out and the two ends read as what they are --
    # too dark to carry a hue, too light to carry one -- with the middle band
    # holding the ones rejected for some other reason entirely. Each band's
    # floor is the depth the band above ended at, so no tile can surface out of
    # its own band however much room happens to be going in the one above it.
    # Outermost first, so: neither, then too light, then too dark hard against
    # the middle of the wheel. The two ends are done being looked at and the
    # middle band is not, so the band that still has questions in it sits
    # nearest the tiers that are still being judged.
    for band in (SUNK_MID, SUNK_LIGHT, SUNK_DARK):
        floor = len(ends)
        for row in sorted((r for r in rest
                           if is_sunk(r[2]) and sunk_band(r[3]) == band),
                          key=lambda r: r[1]):
            drop(row, floor)

    # **Nothing is reordered after packing.** Ranking the tiers by chroma was
    # tried, to sink the near-neutral pastilles toward the middle, and it broke
    # the one property the packing exists to give: a tile sits in the outermost
    # tier that had room for it, so the stack is dense from tier 2 inward and
    # you can read depth as crowding. Reordering left holes against the ring
    # and put sparse tiers outside full ones.

    depth = max(len(ends), 1)
    # `RING_SEP` comes off the top before the stack is divided up, so holding
    # tier 0 clear costs the tiers below it depth rather than costing every
    # block its height.
    pitch = min(TIER_BAND + TIER_LABEL,
                (TIER_OUT - RING_SEP - TIER_FLOOR) / depth)
    height = pitch * TIER_BAND / (TIER_BAND + TIER_LABEL)
    # Half again as deep, and only with the tiers hidden. At full depth the ring
    # would eat the gap below it and sit on tier 1, so the deeper block and the
    # hidden stack are one look rather than two settings.
    ring_height = height * (RING_DEEP if RING_ONLY else 1.0)

    ticks = []
    tiers_map = {} if tiers_map is None else tiers_map
    for idx, (tier, row) in enumerate(assigned):
        _delta, at, names, mixed, n, proposed, _reads, flag = row
        wide = width_of(row) / 2
        # Placed, sized and drawn in angle. The tile's width is its share of the
        # draw and does not vary with where it sits; how much *hue* it spans is
        # what the compression changes, and that is the compression's whole job.
        lo, hi = at - wide, at + wide
        outer = TIER_OUT - tier * pitch - (RING_SEP if tier else 0)
        # Tier 1 is drawn with a heavier edge. Being outermost is not enough to
        # find it by: it is filled first and only where a block fits, so a
        # stretch of hue it has nothing for shows tier 2 as the outermost
        # thing present, and the suggestion and the alternatives read alike.
        #
        # A block the harness objects to is drawn with a broken edge. The
        # objection has to be carried by geometry rather than by colour or by
        # fading, because the fill is the entire claim the block makes and
        # anything done to it argues with the thing being judged.
        # Lighter, but not down to the 0.5 the other tiers get: the heavier
        # edge is how tier 0 is found when a stretch of hue leaves it empty and
        # tier 1 becomes the outermost thing present, so it has to stay
        # distinguishable from one.
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
            venn(out, idx, names, tref_top(), at, DISC_R)
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

    **Back, because there are offsets again.** They came off when the ring was
    a pure measurement and every tile sat on the hue its blend reads as, so
    every tick would have been under its own tile and every leader a point.
    Hand placement and anchoring put that back: 23 of the 58 have been moved,
    one of them by thirty degrees, and a tile gives no sign of it on its own --
    a placed tile and one left where it fell look identical.

    The tick is painted in the tile's own colour rather than in grey, because
    that is what says which tile it belongs to; the leader closes the loop by
    running from the tick to the tile's inner edge. Each leans by exactly how
    far its tile was moved, so they fan rather than stack and the far ones read
    as slope without needing a number.
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


# `chroma_of` is gone. It measured how much colour was left in a blend, for the
# abandoned experiment of ranking the tiers by chroma to sink the near-neutral
# pastilles toward the middle -- see the note in `tiers` about why nothing is
# reordered after packing. `NEUTRAL_CHROMA` still does the one chroma test that
# survived, inline, on the catalogue.


def width_of(row):
    """How wide this block is drawn: its class price, and nothing else.

    **The hand stretch is gone with the placements it belonged to.** A block
    was widened past its price where a stretch of the old ring had to carry
    more decision than the price allowed, and the rules under it declared by
    how much. Nothing is placed now, so nothing is stretched: every block is at
    1x and the rules would all be drawings of zero.
    """
    return WEDGE[len(set(row[2]))] * WIDTH_SCALE


# The offset markers are gone with the placements they measured. A tick at the
# hue a block would sit at if nobody had moved it, and a leader running to
# where it was actually put, is the one marker on the wheel that recorded a
# judgement rather than a measurement -- and there are no judgements on this
# wheel. Every block is centred on the hue its blend reads as, so every tick
# would sit under its own block and every leader would be a point.
#
# The trefoil is a Venn diagram, not three separate discs. Separate discs said
# only which squares go in; overlapping them puts the two-way mixes and the
# three-way mix on the page as well, in the one place where the question "what
# does this actually average to" is being asked. Inner borders are dropped: a
# stroke on each lens would out-draw the fills at this size, and the whole
# point is to read the colours.
#
# The discs stay DISC_R across; pulling their centres together is what makes
# the cluster smaller. How far together is the whole balance of the mark. At a
# centre-to-centre separation of DISC_R the middle swallowed almost everything
# and the two-way lenses came out as slivers too thin to carry a colour -- the
# mixes were being drawn and could not be seen. DISC_SEP is that separation as
# a multiple of the radius: below sqrt(3) there is a middle region at all, and
# 1.45 leaves all seven regions wide enough to read.
#
# Back to 1.0 -- centres one radius apart, the tightest arrangement here. The
# wider setting was a fix for the wrong fault: the mixes were missing because
# the clip-paths did not resolve, not because the lenses were thin. With the
# regions drawn as explicit polygons they show at any separation, so the
# cluster can be as compact as it was to begin with.
DISC_SEP = 1.0


def tref_top():
    """The radius the outermost point of a trefoil sits at, centring it.

    **Measured, not nudged.** The cluster used to hang three pixels below the
    outer edge of the band, which was a number chosen when the band was 24 deep
    and stopped meaning anything the moment it grew. Its depth is two disc radii
    plus the drop to the tucked-under third, so the padding that centres it can
    be worked out instead of guessed, and it stays centred if the discs or the
    band change size.
    """
    depth = 2 * DISC_R + 1.5 * DISC_SEP * DISC_R / math.sqrt(3)
    return TREF_OUT - (TREF_OUT - TREF_IN - depth) / 2


def venn(out, idx, names, top, hue, radius=None):
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

    **This used to be done with clip-paths, and that is why the mixes were
    missing.** The lens was a disc carrying `clip-path="url(#...)"`, which
    every browser honours and at least one SVG renderer does not -- an
    unresolved reference clips the shape away entirely, so the three plain
    discs survived and every overlap silently vanished. Nothing in the file
    looked wrong, which is the worst kind of wrong. There are no references
    here now: the region is computed and written out as coordinates, so what
    the file says is what any renderer draws.

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


def table(out, rows, columns):
    """Every block on the wheel, beside the wheel, in as many columns as it takes.

    The wheel says where each block sits and what it looks like; it cannot say
    what it is made of without covering itself in type. This is the other half:
    mixture, constituents, the hue the mixture reads as, and how faithfully it
    renders the gamut colour there.

    **All of them, not the suggestion alone.** Tier 1 used to be the roster and
    the other sixty-eight lived in corner lists behind a flag, which meant a
    block could be drawn on the wheel, numbered on the wheel, and named
    nowhere. Tier 1 comes first, in ring order; the rest follow from 101 in the
    order of the hue they read as, which is the order their numbers were issued
    in, so a number found on the wheel is looked up by counting down.

    **The offset column has gone where the offsets did.** It reported how far a
    block had been moved from the hue its blend reads as, and every block here
    is centred on that hue, so the column would be a run of zeros. Fidelity
    takes the space: dE is the Oklab distance between the blend and the gamut
    colour it is standing in for, and it is what decides tier 1.
    """
    SW, GAP, ROW = 6, 1, 7.0
    top = 22
    # Tier 1 gets a column to itself even where it does not fill one. Splitting
    # on the row count alone ran the 101s up the bottom of the first column
    # under a heading that said tier 1, which is exactly the sort of quiet
    # mislabelling this roster exists to prevent.
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
            out.append(f'<text x="{x0 + 100}" y="{drop}" text-anchor="end" '
                       f'fill="{"#b00" if delta >= 0.15 else "#444"}">'
                       f'{delta:.3f}</text>')
            if flag:
                out.append(f'<text x="{x0 + 104}" y="{drop}" fill="#999">'
                           f'{flag}</text>')
    out.append('</g>')


# **A number is a position again, and the position is written down.** It was
# the triple's index in the palette enumeration, which no render could move --
# right while the ring was being settled, when every reissue made a note saying
# "promote #143" mean something else by the time the next picture came back.
# The ring is closed now and nothing is spare, so that churn cannot happen, and
# the number goes back to the more useful job of saying where to look.
#
# It is not computed here. It is the line a tile sits on in `wheel.tsv`, which
# is ordered clockwise from the top -- so the file is the numbering, and sorting
# the file is how the wheel is renumbered. Nothing in this module can disagree
# with the drawing about what a number means, because nothing in this module
# decides it.
CANON = {}


def canon(names):
    if not CANON:
        for k, (_verb, _where, triple) in enumerate(index(), 1):
            CANON[triple] = k
    return CANON[names]


def numbered(picks, others):
    """Rows for the renderer, each carrying the number the index gives it.

    Nothing is worked out here. The number is the line the tile sits on in
    `wheel.tsv`, so a number on the drawing and a number in the file cannot
    come apart -- and renumbering is something done to that file rather than
    something this function has an opinion about.
    """
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


def checklist(rows, picks, tiers_of):
    """Every instruction in the table, and what actually became of it.

    Reported by the run rather than by me: a tile that could not be seated used
    to print one line among many and was missed, and an instruction applied to
    the wrong tile showed up nowhere at all.
    """
    seats = {r[2]: r[1] for r in picks}
    print("     #  verdict         triple                  outcome")
    trouble = 0
    for n, (verb, where, names) in enumerate(index(), 1):
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
    # The seven that average to a neutral keep their place in the roster and
    # take none on the ring: no hue, so nowhere to stand.
    rows += [(d, None, names, mixed, canon(names), False, None, flag)
             for d, _r, names, mixed, flag in hueless]
    # One column for tier 1, then as many as the rest need. With the roster off
    # the canvas is the wheel and nothing else.
    columns = 1 + max(1, -(-(len(rows) - len(picks)) // ROSTER_ROWS))
    wide = SIZE if RING_ONLY else SIZE + 14 + columns * COL_W + 24
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{wide}" '
           f'height="{SIZE}" viewBox="0 0 {wide} {SIZE}">',
           f'<rect width="{wide}" height="{SIZE}" fill="#ffffff"/>']
    # **The banner is gone.** It said which palette produced the picture, on
    # the grounds that the two renders are similar enough to be mistaken for
    # each other. Everything is authored against `--painted` now, so it named a
    # choice nobody is making, and it was the one piece of type on the drawing
    # that was not attached to something on it. The run still prints the
    # palette to the terminal, which is where the question gets asked.
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
# Scoring a candidate against the target
# ---------------------------------------------------------------------------

IN_USE = S / "in-use.tsv"

EMOJI = {name: emoji for emoji, name, _cp, _rgb in text.PALETTE}


def reference():
    """The in-use set alone, as arcs of hue, for an implementation to consume.

    `wheel.tsv` is a working document: it carries what was rejected, what sits
    in a tier unused, and which band each of those is in. None of that is
    wanted by something deciding which three squares a project gets. This is
    the other artifact -- the mapping and nothing else, derived from the same
    file so the two cannot disagree.

    **It used to be derived from `bench.tsv`, and had gone stale there.** That
    file described the version 1 ring: of the fifty blocks it placed, sixteen
    are no longer on the wheel and twenty-nine of the current sixty-three it
    never saw. So the one file aimed at a consumer was not merely unused, it
    was wrong, and something reading it would have got the old wheel. It comes
    off the ring lines now, which are the ring.

    Rows tile [0, 360) with no gap and no overlap, so a lookup is `from <= hue
    < to` and always hits exactly once. The block that straddles zero is split
    into two rows sharing its number rather than left to wrap, because a
    consumer that has to special-case one row will eventually not.
    """
    rows = sorted(((n, names, float(where))
                   for n, (verb, where, names) in enumerate(index(), 1)
                   if verb == "ring"), key=lambda r: r[2])
    arcs = []
    for n, names, at in rows:
        # Every block is at its class price. The hand stretch went with the
        # placements it belonged to, so there is no multiplier to carry.
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
        "# The mapping, and nothing else: which three squares stand for a hue.",
        "#",
        "# Generated by `wheel.py --reference` from wheel.tsv. Do not edit by",
        "# hand -- edit wheel.tsv and regenerate, or the wheel and the table",
        "# will disagree and only one of them is being looked at.",
        "#",
        "# Hue is the HSL hue identicon.js derives from the digest, in degrees,",
        "# at its fixed saturation 0.7 and lightness 0.5. Rows tile 0 to 360",
        "# with no gap and no overlap: the row to use is the one where",
        "# `from <= hue < to`, and there is always exactly one.",
        "#",
        "# The squares are given inner to outer, already in the order they are",
        "# to be shown. Arrangement and square-versus-circle are a separate",
        f"# channel and are not in this file. {len(rows)} blocks.",
        "#",
        "# from\tto\tn\tone\ttwo\tthree\tmark",
    ]
    for lo, hi, n, names in arcs:
        out.append("\t".join([f"{lo:.1f}", f"{hi:.1f}", str(n), *names,
                              "".join(EMOJI[x] for x in names)]))
    IN_USE.write_text("\n".join(out) + "\n")
    return len(arcs), len(rows)


def next_path():
    """One past the highest wheelN.svg. The wheel is a series, like the sheets.

    **Highest plus one, not first free.** This walked upward from 1 and took
    the first name nothing was using, which is the same thing only while the
    series has no holes -- and the series is full of them, because sixty-one
    renders were deleted and one was regenerated under its old name. A render
    into a hole overwrites nothing on disk and everything in the record: the
    numbers are how these are referred to across sessions, so wheel1 meaning
    two different pictures is worse than a gap. Observed, not theorised: a
    plain render landed on the committed wheel1.svg and replaced it.
    """
    used = [int(p.stem[5:]) for p in S.glob("wheel*.svg") if p.stem[5:].isdigit()]
    return S / f"wheel{max(used, default=0) + 1}.svg"


def main(argv):
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
            path = S / path
    else:
        path = next_path()
    svg, rows, picks, depth, tiers_of = render()
    path.write_text(svg)
    checklist(rows, picks, tiers_of)
    covered = sum(WEDGE[len(set(r[2]))] for r in picks)
    flagged = sum(1 for r in rows if r[7])
    print(f"{path} {len(svg)} bytes")
    # What used to be the banner. The two palettes make pictures similar enough
    # to be mistaken for each other, so the run still says which this is -- to
    # the terminal, where it is read once, rather than on the drawing, where it
    # sat permanently and named a choice nobody is making any more.
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

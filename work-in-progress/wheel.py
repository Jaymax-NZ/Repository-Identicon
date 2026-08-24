#!/usr/bin/env python3
"""The wheel: the gamut as a ring, and the vocabulary available to name it.

    python3 wheel.py                   render the next free wheelN.svg
    python3 wheel.py --reference       regenerate in-use.tsv from bench.tsv
    python3 wheel.py --refill          add newly admissible triples to bench.tsv
    python3 wheel.py --painted         judge in the colours the vendors paint

**Nothing is placed here any more.** Mapping version 2 reparametrised the ring,
and the fifty blocks settled by hand against the old one do not survive it: all
fifty remain admissible, none keeps its position, and hue angles up to 53
degrees out are a reparametrisation rather than drift. So tier 0 -- the placed
ring -- is gone, and what the wheel draws is the vocabulary itself: every triple
the harness allows, at the hue its blend reads as, tiered so that none is
hidden.

Tier 1 is a suggestion and says so by sitting in a tier rather than on a ring.
It is the best-fidelity selection that does not overlap itself, with nothing
moved off the hue it reads as -- moving a block is the placement pass, and the
placement pass is by hand.

The roster in `bench.tsv` and the mapping in `in-use.tsv` both still describe
version 1 and are not read here; `--reference` regenerates the second from the
first and is untouched by any of this.

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
TIER_OUT = 248                 # the outermost tier
DRIFT_R = 259                  # the offset ticks, between tier 1 and the gamut
# Every block carries its number, and no number is laid over a colour. A tier
# is therefore two bands: the block itself, and a clear gap immediately inside
# it holding that tier's numbers. Type over the band was tried on the version 1
# wheel and taken off again -- it covered the one thing the block is there to
# let you read -- and 112 numbers would have made that worse, not better.
TIER_BAND = 13                 # the coloured block
TIER_LABEL = 8                 # the clear gap inside it, for its numbers
RING_IN, RING_OUT = 264, 306   # the gamut itself
# The neutral band and the trefoils that sit on it. Deep enough for the cluster
# (about 2.9 disc radii) with a little air at each edge.
TREF_IN, TREF_OUT = 312, 336
TREF_BG = "#ececec"
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
# The bench: the version 1 roster. Nothing on this wheel comes from it; it is
# still what `--reference` regenerates `in-use.tsv` from.
# ---------------------------------------------------------------------------

BENCH = S / "bench.tsv"


def read_bench():
    """The roster, verbatim. Numbers are the file's, never recomputed."""
    out = []
    for line in BENCH.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        f = line.split("\t")
        at = float(f[5]) if len(f) > 5 and f[5].strip() else None
        mult = float(f[6]) if len(f) > 6 and f[6].strip() else 1.0
        out.append((int(f[0]), multiset(f[1:4]), f[4].strip(), at, mult))
    return out


def pool(roster):
    """Every unused triple the harness allows, best first, minus the rejected."""
    perceptual = harness()
    # **One class.** Whether a triple is currently on the wheel is not a
    # property of the triple, and the spread-and-stretch route assigns them by
    # hand anyway -- so being in use no longer disqualifies anything. The
    # roster is the vocabulary, not a list of leftovers. Only what is already
    # numbered, and what has been rejected outright, is excluded.
    known = {multiset(names) for _n, names, _s, _at, _m in roster}
    palette = [name for _e, name, _cp, _rgb in text.PALETTE]

    rows, seen = [], set()
    for a in palette:
        for b in palette:
            for c in palette:
                key = multiset((a, b, c))
                if key in seen or key in known:
                    continue
                seen.add(key)
                mixed = mix_rgb(key)
                hue, colour, delta = nearest_gamut(mixed)
                if perceptual.violations(colour, tuple(ORDER[n] for n in key)):
                    continue
                rows.append((delta, hue, key, mixed))
    return sorted(rows)


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


FLAGS = [("opponent", "opp"), ("gap", "gap"), ("two whites", "WW"),
         ("two blacks", "KK"), ("white on", "W"), ("black on", "K"),
         ("forbidden", "no")]


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
    decide what is admitted, because they are not currently in a position to:
    `DARK`, `LIGHT` and the two tints are absolute luminances calibrated
    against the version 1 ring, which ran 0.20 at blue to 0.80 at yellow. The
    version 2 ring runs 0.23 to 0.49 and never reaches 0.58, so the two-white
    rule rejects two whites at every hue on the wheel -- `blue white white`
    and `green white white` among them, both of which are on `REQUIRED` as
    triples that must exist. A filter that cannot pass what it is required to
    pass is a filter to look at, not to look through.

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


# How far tier 1 will slide a block to seat it against its neighbour. Four
# degrees is half the widest block and well inside what the hand pass moves
# things by; a block that cannot be seated within it is left out rather than
# dragged to a hue it does not name.
MAX_NUDGE = 4.0
NUDGE_STEP = 0.25
MAX_PUSH = 15.0        # past this a push is a relocation, and is refused

# When two tiles count as touching, for the purpose of finding a run to move.
#
# **A gap you cannot see is not a gap.** This was 0.01 degrees, which is a
# hairline in arithmetic and nothing at all on the drawing: at the tier radius
# a degree is about four and a half pixels, so a tenth of a degree is half a
# pixel. A run that reads as one solid arc was being cut in two there, and
# `press` moved three tiles out of the ten the eye says are coupled.
#
# Set from Justin's eye rather than from a calculation, and bracketed by two
# actual readings: the seam between #152 and #36 is invisible at 0.106, and the
# one in front of #15 is a gap he asked to close at 0.380. So the threshold
# sits between them. It governs only which tiles a `press` counts as coupled --
# how far a press then travels is the gap it is closing, however small.
FLUSH_TOL = 0.2

# Whether an unplaced triple may seat itself in a leftover arc.
#
# **Off: the ring is what the table names, and nothing else.** This filled any
# gap with the best triple that fitted, which is right for a wheel proposing an
# arrangement and wrong for one recording a settled arrangement. Once the table
# became pure placement, every gap left deliberately was colonised the moment
# it opened -- eject a tile and the next-best candidate took its slot, eject
# that and the one after it arrived. A gap is a decision, and it has to be
# possible to leave one.
AUTO_FILL = False


def names_of(row):
    return row[2]


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


HAND = S / "hand.tsv"


def hand():
    """The instructions, resolved from canonical numbers by the engine.

    **Keyed by number, and deliberately.** The file held triples while numbers
    were positional and would rot; they have been canonical since the numbering
    was fixed, so the number is the identity and holding it removes the one
    step where a triple could be transcribed wrongly. Half a batch once landed
    on the wrong tiles that way.
    """
    canon(multiset(("red", "red", "red")))
    by_number = {v: k for k, v in CANON.items()}
    out = {}
    if not HAND.exists():
        return out
    for line in HAND.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = line.split()
        verb, args = parts[0], parts[1:]
        if verb == "swap":
            if any(int(x) not in by_number for x in args[:2]):
                print(f"  no such tile in: {line.strip()} (numbers run 1-165)")
                continue
            a, b = (by_number[int(x)] for x in args[:2])

            def held(k):
                """The angle the table already gave this tile, if any.

                **A swap must exchange seats, not hues.** Overriding the tile's
                `ring n <deg>` line dropped that angle, so the arrangement the
                swap resolved against put both tiles back at the hue their
                blends read -- and for two tiles three degrees apart that is
                indistinguishable from doing nothing at all.
                """
                w = out.get(k, (None, None))[1]
                return w[1] if w and w[0] == "at" else None

            out.setdefault("__ops__", []).append(("swap",) + (a, b))
            for k in (a, b):
                out.setdefault(k, ("ring", None))
            continue
        if int(args[0]) not in by_number:
            print(f"  no such tile: #{args[0]} (numbers run 1-165)")
            continue
        names = by_number[int(args[0])]
        if verb == "ring":
            out[names] = ("ring", ("at", float(args[1])) if len(args) > 1 else None)
        elif verb == "eject":
            out[names] = ("inner", None)
        elif verb in ("in", "out"):
            out[names] = (verb, ("count", int(args[1]) if len(args) > 1 else 1))
        elif verb == "ccw":
            out[names] = ("ring", ("ccw", None))
        elif verb == "slide":
            out.setdefault("__ops__", []).append(
                ("slide", names, by_number[int(args[1])], by_number[int(args[2])]))
        elif verb == "insert":
            # `insert <n> <b> [ccw]`: clockwise of b by default, anticlockwise
            # of it with `ccw`, pushing whichever way it faces.
            out.setdefault("__ops__", []).append(
                ("insert", names, len(args) > 2 and args[2] == "ccw",
                 by_number[int(args[1])]))
            # Off the ring for the automatic pass. `insert` seats it at a named
            # place afterwards, and a tile seated twice collides with itself.
            # Assigned rather than defaulted: an earlier line about this tile is
            # precisely what the insert supersedes.
            out[names] = ("inner", None)
        elif verb == "press":
            out.setdefault("__ops__", []).append(("press",) + 
                (names, by_number[int(args[1])]))
        elif verb == "roll":
            out.setdefault("__ops__", []).append(("roll",) + 
                (names, by_number[int(args[1])]))
    return out


# How much a triple is favoured for carrying the base -- the single square
# nearest the colour it is standing for. A triple that contains it is treated
# as this much better than its dE says, which is a thumb on the scale rather
# than a rule: `red yellow purple` beats two orange-based triples at 14 degrees
# on Justin's eye because the red is there, and dE alone had it losing.
BASE_FAVOUR = 0.8


def base_square(hue):
    """The single square nearest the ring at this hue, in the palette in force."""
    target = oklab(gamut_at(hue))
    return min((name for _e, name, _c, _r in text.PALETTE),
               key=lambda n: math.dist(oklab(square_rgb(n)), target))


def score(delta, reads, names):
    return delta * (BASE_FAVOUR if base_square(reads) in names else 1.0)


def propose(rows, swaps=True):
    """Tier 1: the best triple for each stretch of hue, at or near its own hue.

    Best first, taken if the arc its class earns is free. So the triple that
    renders a colour most faithfully gets the position it names, and a crowded
    stretch keeps the best of what wants to sit there rather than whatever the
    sweep reached first.

    **Seated, not placed.** A candidate blocked by a degree of overlap used to
    be dropped outright, which left the ring at 48% with gaps of a degree and a
    half between eight-degree blocks -- gaps nobody would keep and everybody
    would close by hand at once. A block may now slide up to `MAX_NUDGE` to sit
    flush against its neighbour. Anything that cannot be seated inside that is
    left to the tiers behind.

    **The harness does not vote here either.** It used to veto a nudged block
    whose new position broke a rule, which quietly gave version 1's luminance
    thresholds a say in a version 2 suggestion. What the rules say is carried
    on the block as a broken edge and in the roster as a code, for you to
    overrule or agree with by looking.
    """
    offsets = [0.0]
    k = NUDGE_STEP
    while k <= MAX_NUDGE + 1e-9:
        offsets += [-k, k]
        k += NUDGE_STEP

    decided = hand()
    ops = decided.pop("__ops__", [])
    if not swaps:
        # The baseline arrangement: what the ring looks like with every swap
        # suspended, so a swap can be given the slot its target actually
        # occupies. Both halves are suspended together -- the newcomer's place
        # on the ring and the demotion it implies -- or the target would be
        # missing from the very arrangement being measured.
        wanted = {w[1] for _v, w in decided.values()
                  if w and w[0] in ("instead", "swap")}
        decided = {n: ("ring" if n in wanted else v,
                       (("at", w[2]) if len(w) > 2 and w[2] is not None else None)
                       if w and w[0] == "swap" else w)
                   for n, (v, w) in decided.items()
                   if not (w and w[0] in ("instead", "implied"))}
        for n in wanted:
            decided.setdefault(n, ("ring", None))
    seats = ({r[2]: r[1] for group in propose(rows, swaps=False)
              for r in group}
             if swaps and any(w and w[0] in ("instead", "swap")
                              for _v, w in decided.values()) else {})
    natural = {names: warp_angle(reads)
               for _d, reads, names, _m, _f in rows}
    taken, chosen = [], []

    # **Everything here is in angle, not in hue.** The angle around the wheel is
    # the draw: equal angle is equal share of projects, by construction, and a
    # tile's width is the share it takes. Compression belongs to the ring alone
    # -- it decides which hue sits under a given angle, and so how much hue a
    # tile spans, which is what compressing an under-served stretch means. A
    # tile squeezed along with the ring would have given back exactly what the
    # compression was for.
    #
    # The hand goes first, at its own position with no sliding: a placement
    # somebody made by eye is the fixed point everything else arranges around.
    seated = {}

    def seat(delta, at, names, mixed, reads, back=False):
        """Seat a hand placement at the angle asked for, or the nearest free one.

        **A hand placement is a request, not a coordinate.** Seating rigidly
        meant two tiles that both wanted the same arc were drawn on top of each
        other, and once that was forbidden, one of them simply vanished from
        the ring -- including pairs asked to swap, whose two seats overlapped
        each other by construction. The shuffle is the same one the automatic
        pass gets: up to `MAX_NUDGE`, nearest first, either way round.
        """
        half = WEDGE[len(set(names))] * WIDTH_SCALE / 2
        for off in offsets:
            if not any(circular_overlap(at + off - half, at + off + half, a, b)
                       for a, b in taken):
                at += off
                break
        else:
            start = at
            while any(circular_overlap(at - half, at + half, a, b)
                      for a, b in taken):
                if back:
                    # Anticlockwise: the mirror of the push below, and the one
                    # `ccw` asks for. Ends and starts are both taken on the
                    # branch nearest the tile, so a span written across zero
                    # cannot send it round the wheel.
                    near = [lo - 360 * round((lo - at) / 360) for lo, hi in taken
                            if circular_overlap(at - half, at + half, lo, hi)]
                    at = min(near) - half
                    if abs(at - start) > MAX_PUSH:
                        print(f"  NO ROOM anticlockwise for {' '.join(names)} "
                              f"(#{canon(names)}); left off the ring")
                        return
                    continue
                if abs(at - start) > MAX_PUSH:
                    # Past this it is not a shuffle, it is a relocation: on a
                    # ring this full the walk carries on until it finds a gap,
                    # and one tile travelled 209 degrees out of the violets
                    # into the greens rather than admitting it had nowhere to
                    # go. Better to say so.
                    print(f"  NO ROOM for {' '.join(names)} (#{canon(names)}) "
                          f"at {start:.2f}; left off the ring")
                    return
                # Each end is taken on the branch nearest the tile being
                # pushed. Comparing raw values mixed a span written across
                # zero with one written below it, and the maximum came back
                # from the far side of the wheel -- one tile was pushed 151
                # degrees, out of the violets and into the greens.
                near = [hi - 360 * round((hi - at) / 360) for lo, hi in taken
                        if circular_overlap(at - half, at + half, lo, hi)]
                at = max(near) + half
            print(f"  {' '.join(names)} (#{canon(names)}) pushed "
                  f"{at - start:+.2f} deg: its slot was taken")
        taken.append((at - half, at + half))
        seated[names] = (at - half, at + half)
        chosen.append((delta, at, names, mixed, reads))


    def verdict(names):
        got = decided[names][0] if names in decided else None
        return "inner" if got in ("out", "in") else got

    for delta, reads, names, mixed, _flag in rows:
        if verdict(names) != "ring" or decided[names][1] is not None:
            continue
        seat(delta, warp_angle(reads), names, mixed, reads)

    # Then the anchored ones, which may name a triple seated just above.
    def anchor_order(row):
        """Positions first, then slots, then neighbours -- and within the
        positions, round the ring rather than best-first, so each tile meets
        only its actual neighbours instead of whatever happened to be seated."""
        where = decided.get(row[2], (None, None))[1]
        kind = where[0] if where else ""
        rank = {"ccw": 0, "at": 1, "instead": 2, "swap": 2}.get(kind, 3)
        return (rank, where[1] if kind == "at" else 0.0)

    # **A tile at a fixed angle is never dropped; its neighbour gives way.**
    # Seating round the ring in order, each tile takes the angle the table
    # gives it or the first free angle clockwise of it -- so a tile that has
    # grown into its neighbour's slot pushes that neighbour along rather than
    # deleting it, and the offset marker shows how far the push travelled.
    for delta, reads, names, mixed, _flag in sorted(
            (r for r in rows if verdict(r[2]) == "ring"
             and decided[r[2]][1] is not None), key=anchor_order):
        kind, target = decided[names][1][:2]
        half = WEDGE[len(set(names))] * WIDTH_SCALE / 2
        if kind == "ccw":
            seat(delta, warp_angle(reads), names, mixed, reads, back=True)
            continue
        if kind == "at":
            at = target
        elif kind == "instead":
            # **The slot, not the target's own hue.** A tile on the ring is
            # very often not at the hue its blend reads -- 23 of 58 were not --
            # so handing a replacement the target's home angle moves it
            # somewhere the target had never been.
            at = seats.get(target, natural.get(target, warp_angle(reads)))
        else:
            # An anchor may name any tile, not only a hand-placed one. Where
            # the target has not been seated yet -- because the automatic pass
            # has not run -- its own hue is where it will land, and that is
            # what somebody reading the wheel is pointing at anyway.
            span = seated.get(target)
            if span is None:
                home = seats.get(target, natural.get(target))
                if home is not None:
                    edge = WEDGE[len(set(target))] * WIDTH_SCALE / 2
                    span = (home - edge, home + edge)
            if span is None:
                at = warp_angle(reads)
            else:
                at = span[1] + half if kind == "after" else span[0] - half
        seat(delta, at % 360, names, mixed, reads)

    ordered = ([] if not AUTO_FILL else
               sorted((r for r in rows if verdict(names_of(r)) != "ring"),
                      key=lambda r: score(r[0], r[1], r[2])))
    for delta, reads, names, mixed, _flag in ordered:
        if verdict(names) == "inner":
            continue
        half = WEDGE[len(set(names))] * WIDTH_SCALE / 2
        home = warp_angle(reads)
        for off in offsets:
            at = home + off
            if any(circular_overlap(at - half, at + half, a, b)
                   for a, b in taken):
                continue
            taken.append((at - half, at + half))
            chosen.append((delta, at, names, mixed, reads))
            break
    # **Every sequence operation, in the order the file gives them.** The ring
    # is a sequence: a roll compacts a run, a press slides one rigidly until it
    # meets another tile, a swap exchanges two places and re-lays the span
    # between. All three preserve membership and widths, which is what the
    # angle-and-patch versions could not do -- they resolved collisions by
    # dropping tiles, so an instruction that must keep every tile lost one.
    half = lambda k: WEDGE[len(set(k))] * WIDTH_SCALE / 2

    def run_from(seats, head):
        """The contiguous flush run starting at `head`, going clockwise."""
        out_run, edge = [head], seats[head] + half(head)
        for off, k in sorted(((seats[k] - seats[head]) % 360, k) for k in seats):
            if off == 0:
                continue
            if abs((seats[k] - half(k)) - edge) > FLUSH_TOL:
                break
            out_run.append(k)
            edge = seats[k] + half(k)
        return out_run

    for op in ops:
        kind, a, b = op[0], op[1], op[-1]
        seats = {r[2]: r[1] for r in chosen}
        # `insert` is the one op whose subject is meant to be off the ring --
        # that is what it is for -- so only its anchor has to be found.
        missing = [canon(k) for k in ((b,) if kind == "insert" else (a, b))
                   if k not in seats]
        if missing:
            print(f"  {kind} {canon(a)} {canon(b)}: #{missing[0]} is not on the ring")
            continue
        moved = {}
        if kind == "swap":
            order = [k for _x, k in sorted((seats[k], k) for k in seats)]
            i, j = sorted((order.index(a), order.index(b)))
            order[i], order[j] = order[j], order[i]
            place = min(seats[a], seats[b]) - half(order[i])
            for k in order[i:j + 1]:
                moved[k] = place + half(k)
                place = moved[k] + half(k)
            note = f"re-laid {j - i + 1} tiles"
        elif kind == "roll":
            run = [k for k in run_from(seats, a)]
            span = sorted(((seats[k] - seats[a]) % 360, k) for k in seats
                          if (seats[k] - seats[a]) % 360 <= (seats[b] - seats[a]) % 360)
            place = seats[a] - half(a)
            for _off, k in span:
                moved[k] = place + half(k)
                place = moved[k] + half(k)
            note = f"compacted {len(span)} tiles"
        elif kind == "slide":
            # A named range, slid rigidly anticlockwise until its head touches
            # the tile it is closing against. Nothing outside the range moves,
            # so the skew it can introduce is bounded by the gap being closed.
            first, last = op[1], op[2]
            span = [k for _o, k in sorted(((seats[k] - seats[first]) % 360, k)
                                          for k in seats)
                    if (seats[k] - seats[first]) % 360
                    <= (seats[last] - seats[first]) % 360]
            delta = ((seats[b] + half(b) + half(first)) - seats[first] + 180) % 360 - 180
            for k in span:
                moved[k] = seats[k] + delta
            note = f"slid {len(span)} tiles {delta:+.2f} deg"
        elif kind == "insert":
            # **Each solid run slides just clear of the one before it, and no
            # further.** Two faults were in the previous version, and they
            # compounded. It shoved every neighbour by the newcomer's whole
            # width, ignoring the gap already sitting in front of it -- so a
            # tile dropped into a half-empty slot moved its neighbour twice as
            # far as it had to. And it stopped only at a gap wide enough to
            # swallow the tile entire, so the shove travelled straight past
            # several gaps that between them would have absorbed it. That is
            # what ballooned the offsets.
            #
            # Here the push dies out the moment a run has room, and what it
            # gives up on the way is the air between runs. Runs move rigidly:
            # a seam under `FLUSH_TOL` is not a gap, so it is not somewhere to
            # absorb a push either, and the tiles either side of it stay
            # together rather than being prised apart by a fraction of a degree.
            #
            # `step` is the direction of travel, so one piece of arithmetic
            # serves both: every span is read as the face pointing back toward
            # the newcomer and the face pointing away from it.
            back = op[2]
            step = -1 if back else 1
            at = seats[b] + step * (half(b) + half(a))
            order = [k for _x, k in sorted((((seats[k] - at) * step) % 360, k)
                                           for k in seats if k != a)]

            def seam(cur, nxt):
                """The air between two tiles, in the direction of travel."""
                raw = ((seats[nxt] - step * half(nxt))
                       - (seats[cur] + step * half(cur))) * step
                return (raw + 180) % 360 - 180

            edge, shifted, k = at + step * half(a), [], 0
            while k < len(order):
                run = [order[k]]
                while k + 1 < len(order) and seam(order[k], order[k + 1]) < FLUSH_TOL:
                    k += 1
                    run.append(order[k])
                k += 1
                lead = run[0]
                # Taken on the branch nearest the newcomer, like every other
                # span on this wheel. `edge` accumulates and runs past 360 for
                # anything seated near the top, and comparing it raw against a
                # wrapped seat made a tile with five degrees of clear air in
                # front of it look three hundred and fifty overlapped.
                over = ((edge - (seats[lead] - step * half(lead))) * step
                        + 180) % 360 - 180
                if over <= 1e-9:           # this run has room; the push dies here
                    break
                for j in run:
                    moved[j] = seats[j] + step * over
                    shifted.append(j)
                edge = moved[run[-1]] + step * half(run[-1])
            fresh = [r for r in rows if r[2] == a][0]
            chosen = [r for r in chosen if r[2] != a]
            chosen.append((fresh[0], at % 360, a, fresh[3], fresh[1]))
            note = (f"seated at {at % 360:.1f}, "
                    f"{'anticlockwise' if back else 'clockwise'} of #{canon(b)}, "
                    f"pushing {len(shifted)} tiles "
                    f"({', '.join('#' + str(canon(j)) for j in shifted)})")
        else:                                   # press
            run = run_from(seats, a)
            delta = ((seats[b] + half(b) + half(a)) - seats[a] + 180) % 360 - 180
            for k in run:
                moved[k] = seats[k] + delta
            note = f"slid {len(run)} tiles {delta:+.2f} deg"
        chosen = [(d, moved.get(k, x), k, m, r) for d, x, k, m, r in chosen]
        print(f"  {kind} #{canon(a)} #{canon(b)}: {note}")

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


def refill():
    """Append every triple the harness allows to the roster.

    No slot count, no sector quota and no quality bar. The roster is meant to
    hold every admissible triple, and the wedge widths already price each one
    by the identity it affords -- so a weak triple shows as a thin sliver
    rather than being kept off the list. Rationing existed when there were
    twenty-four places to give out; there are none now.
    """
    roster = read_bench()
    # No quality bar any more. The wedge widths now price each entry by the
    # identity it affords -- eight degrees for three distinct squares, four
    # for a pair, one for three of a kind -- so a weak triple shows as a
    # thin sliver rather than being left out of the picture entirely.
    chosen = list(pool(roster))
    if not chosen:
        print("nothing new under the good line")
        return 0

    nxt = max((n for n, _k, _s, _at, _m in roster), default=0) + 1
    lines = BENCH.read_text().rstrip("\n").split("\n")
    for delta, hue, names, _mixed in sorted(chosen, key=lambda r: r[1]):
        lines.append("\t".join([str(nxt), *names, "offered"]))
        print(f"  #{nxt:<4} {hue:>5.0f}  {' '.join(names):26} dE {delta:.3f}")
        nxt += 1
    BENCH.write_text("\n".join(lines) + "\n")
    return len(chosen)


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


def share(lo, hi):
    """What fraction of projects land in this arc of hue, under the warp."""
    return ((warp_angle(hi) - warp_angle(lo)) % 360) / 360


def hue_of(rgb):
    """Plain HSL hue in degrees. Zero for an achromatic."""
    r, g, b = rgb
    mx, mn = max(rgb), min(rgb)
    if mx == mn:
        return 0.0
    d = mx - mn
    h = ((g - b) / d) % 6 if mx == r else \
        ((b - r) / d + 2 if mx == g else (r - g) / d + 4)
    return (h * 60) % 360


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
    for row in sorted(rest, key=lambda r: (bias_of(r[2]), r[1])):
        drop(row, behind + max(0, bias_of(row[2])))

    # **Nothing is reordered after packing.** Ranking the tiers by chroma was
    # tried, to sink the near-neutral pastilles toward the middle, and it broke
    # the one property the packing exists to give: a tile sits in the outermost
    # tier that had room for it, so the stack is dense from tier 2 inward and
    # you can read depth as crowding. Reordering left holes against the ring
    # and put sparse tiers outside full ones.

    depth = max(len(ends), 1)
    pitch = min(TIER_BAND + TIER_LABEL, (TIER_OUT - TIER_FLOOR) / depth)
    height = pitch * TIER_BAND / (TIER_BAND + TIER_LABEL)

    ticks = []
    tiers_map = {} if tiers_map is None else tiers_map
    for idx, (tier, row) in enumerate(assigned):
        _delta, at, names, mixed, n, proposed, _reads, flag = row
        wide = width_of(row) / 2
        # Placed, sized and drawn in angle. The tile's width is its share of the
        # draw and does not vary with where it sits; how much *hue* it spans is
        # what the compression changes, and that is the compression's whole job.
        lo, hi = at - wide, at + wide
        outer = TIER_OUT - tier * pitch
        # Tier 1 is drawn with a heavier edge. Being outermost is not enough to
        # find it by: it is filled first and only where a block fits, so a
        # stretch of hue it has nothing for shows tier 2 as the outermost
        # thing present, and the suggestion and the alternatives read alike.
        #
        # A block the harness objects to is drawn with a broken edge. The
        # objection has to be carried by geometry rather than by colour or by
        # fading, because the fill is the entire claim the block makes and
        # anything done to it argues with the thing being judged.
        colour, weight = ('#333', 0.9) if proposed else ('#888', 0.5)
        dash = ' stroke-dasharray="2 1.6"' if flag else ''
        out.append(
            f'<path d="{sector(outer - height, outer, lo, hi)}" '
            f'fill="{text.hex_colour(mixed)}" stroke="{colour}" '
            f'stroke-width="{weight}"{dash}/>')
        tiers_map[names] = tier
        number(out, at, n, outer - height - (pitch - height) / 2)
        constituents(out, names, at, outer - height / 2, hi - lo)
        if proposed:
            ticks.append((at, warp_angle(_reads), mixed))
        if proposed and width_of(row) >= 4.0:
            venn(out, idx, names, TREF_OUT - 3.0, at, DISC_R)
    drift(out, ticks, TIER_OUT)
    return depth


DRIFT_W = 1.1             # the tick stroke, in pixels


def drift(out, ticks, band):
    """A tick where each tile would sit if nobody had moved it, and a leader.

    **Back, because there are offsets again.** They came off when the ring was
    a pure measurement and every tile sat on the hue its blend reads as, so
    every tick would have been under its own tile and every leader a point.
    Hand placement and anchoring put that back: 23 of the 58 have been moved,
    one of them by thirty degrees, and a tile gives no sign of it on its own --
    a placed tile and one left where it fell look identical.

    The tick is painted in the tile's own colour rather than in grey, because
    that is what says which tile it belongs to; the leader closes the loop by
    running from the tick to the tile's outer edge. Each leans by exactly how
    far its tile was moved, so they fan rather than stack and the far ones read
    as slope without needing a number.
    """
    for at, home, mixed in ticks:
        colour = text.hex_colour(mixed)
        x0, y0 = polar(DRIFT_R - 2.5, home)
        x1, y1 = polar(DRIFT_R + 2.5, home)
        out.append(f'<line x1="{x0:.2f}" y1="{y0:.2f}" x2="{x1:.2f}" '
                   f'y2="{y1:.2f}" stroke="{colour}" stroke-width="{DRIFT_W}"/>')
        if abs(((at - home + 180) % 360) - 180) < 0.01:
            continue
        bx, by = polar(band, at)
        out.append(f'<line x1="{x0:.2f}" y1="{y0:.2f}" x2="{bx:.2f}" '
                   f'y2="{by:.2f}" stroke="{colour}" stroke-width="0.5" '
                   f'stroke-opacity="0.85"/>')


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
    out.append(
        f'<text x="{CENTRE}" y="{y + 2.2:.1f}" text-anchor="middle" '
        f'font-family="monospace" font-size="5.5" fill="#666" '
        f'transform="rotate({turn:.3f} {CENTRE} {CENTRE})">{n}</text>')


def chroma_of(rgb):
    """How much colour is left in a blend, as Oklab chroma."""
    _L, a, b = oklab(rgb)
    return math.hypot(a, b)


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


# **A number names a triple, for good.** It used to be positional -- 1 upward
# round the ring, 101 upward for everything else -- on the grounds that a number
# should tell you where a thing sits. That is defensible for a settled ring
# being written about afterwards, and wrong for a ring being settled: every
# render reissued them, so a note saying "promote #143" meant something
# different by the time the next picture came back, and the person reading the
# wheel had no way to know. The number is now the triple's index in the
# enumeration of all 165 multisets in palette order, which no render can move.
CANON = {}


def canon(names):
    if not CANON:
        palette = [n for _e, n, _c, _r in text.PALETTE]
        k = 0
        for a in range(len(palette)):
            for b in range(a, len(palette)):
                for c in range(b, len(palette)):
                    k += 1
                    CANON[multiset((palette[a], palette[b], palette[c]))] = k
    return CANON[names]


def numbered(picks, others):
    """Rows for the renderer, numbered by the convention the roster used.

    Positional, and positional both times: tier 1 is numbered clockwise from
    the top in the order its blocks sit, and everything else takes 101 upward
    ordered by the hue its blend reads as. A number is a position, so it moves
    when the thing it names moves -- which is the cost of the number meaning
    something, and it is why nothing here is carried over from `bench.tsv`,
    where numbers were permanent and named a version 1 ring.
    """
    rows = []
    for i, (delta, at, names, mixed, reads) in enumerate(sorted(picks,
                                                                key=lambda r: r[1])):
        rows.append((delta, at, names, mixed, canon(names), True, reads,
                     flag_at(names, warp_theta(at))))
    for i, (delta, reads, names, mixed, flag) in enumerate(
            sorted(others, key=lambda r: r[1])):
        rows.append((delta, warp_angle(reads), names, mixed, canon(names),
                     False, reads, flag))
    return rows


def checklist(rows, picks, tiers_of):
    """Every instruction in the table, and what actually became of it.

    Reported by the run rather than by me: a tile that could not be seated used
    to print one line among many and was missed, and an instruction applied to
    the wrong tile showed up nowhere at all.
    """
    canon(multiset(("red", "red", "red")))
    by_number = {v: k for k, v in CANON.items()}
    seats = {r[2]: r[1] for r in picks}
    # Only the last word on a tile counts. An earlier `swap` superseded by a
    # later `in` is not a failed instruction, it is a changed mind, and
    # reporting it as a failure buries the ones that matter.
    last = {}
    for line in HAND.read_text().splitlines():
        parts = line.split()
        if not parts or parts[0].startswith("#"):
            continue
        take = 2 if parts[0] in ("swap", "roll") else 1
        for x in parts[1:1 + take]:
            if x.isdigit():
                last[int(x)] = line

    print("  instruction        triple                  outcome")
    trouble = 0
    for line in HAND.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = line.split()
        # One number for most verbs, two for swap and roll. Scanning the whole
        # line for anything numeric read the count in `in 82 3` as tile #3 and
        # reported on the wrong tile -- the same class of mistake this file was
        # keyed by number to prevent.
        take = 2 if parts[0] in ("swap", "roll") else 1
        for n in [int(x) for x in parts[1:1 + take]
                  if x.isdigit() and int(x) in by_number
                  and last.get(int(x)) == line]:
            names = by_number[n]
            if names in seats:
                got = f"ring {seats[names]:.1f}"
            elif names in tiers_of:
                got = f"tier-{tiers_of[names]}"
            else:
                got = "NOWHERE"
            want_ring = parts[0] in ("ring", "swap", "ccw")
            bad = (want_ring and names not in seats) or got == "NOWHERE"
            trouble += bad
            print(f"  {'! ' if bad else '  '}{' '.join(parts):<16} "
                  f"{' '.join(names):<22}  {got}")
    if trouble:
        print(f"  {trouble} instruction(s) did not land")
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
    # One column for tier 1, then as many as the rest need.
    columns = 1 + max(1, -(-(len(rows) - len(picks)) // ROSTER_ROWS))
    wide = SIZE + 14 + columns * COL_W + 24   # 24 so the last rule column fits
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{wide}" '
           f'height="{SIZE}" viewBox="0 0 {wide} {SIZE}">',
           f'<rect width="{wide}" height="{SIZE}" fill="#ffffff"/>']
    # Which palette produced this picture. The two renders are similar enough
    # to be mistaken for each other and different enough to matter, so the
    # drawing says which it is rather than relying on the file name.
    palette = (f"tiles at {WIDTH_SCALE:g}x   |   " if WIDTH_SCALE != 1 else "")
    palette += ("squares as the vendors paint them, weighted" if AS_PAINTED
               else "squares as Unicode names them")
    if WARP:
        c, h, p = WARP
        palette += (f"   |   {p:g}x at {c:g}&#177;{h:g}&#176;, "
                    f"{share(c - h, c + h) * 100:.0f}% of projects in it "
                    f"({2 * h / 3.6:.0f}% unwarped)")
    out.append(f'<text x="20" y="26" font-family="monospace" font-size="12" '
               f'fill="#444">{palette}</text>')
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

    `bench.tsv` is a working document: it carries what was rejected, what is
    on the bench unused, how far each block was stretched and by whose hand.
    None of that is wanted by something deciding which three squares a project
    gets. This is the other artifact -- the mapping and nothing else, derived
    from the same file so the two cannot disagree.

    Rows tile [0, 360) with no gap and no overlap, so a lookup is `from <= hue
    < to` and always hits exactly once. The block that straddles zero is split
    into two rows sharing its number rather than left to wrap, because a
    consumer that has to special-case one row will eventually not.
    """
    rows = sorted((r for r in read_bench() if r[3] is not None),
                  key=lambda r: r[3])
    arcs = []
    for n, names, _status, at, mult in rows:
        half = WEDGE[len(set(names))] * mult / 2
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
        "# Generated by `wheel.py --reference` from bench.tsv. Do not edit by",
        "# hand -- edit bench.tsv and regenerate, or the wheel and the table",
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
    global AS_PAINTED, WARP, WIDTH_SCALE
    AS_PAINTED = "--painted" in argv
    if "--scale" in argv:
        WIDTH_SCALE = float(argv[argv.index("--scale") + 1])
    if "--warp" in argv:
        centre, half, peak = (float(v) for v in
                              argv[argv.index("--warp") + 1].split(","))
        WARP = (centre, half, peak)

    if "--refill" in argv:
        added = refill()
        print(f"{added} added to {BENCH.name}")
        return 0

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

#!/usr/bin/env python3
"""The target wheel: the gamut as a ring, the intended triple as a spike.

    python3 wheel.py --emit            seed target.tsv from the current mapping
    python3 wheel.py                   render target.tsv to wheel.svg
    python3 wheel.py --score           how closely a mapping reproduces the target
    python3 wheel.py --spikes 144      finer divisions, when the target needs them

**This inverts what the sheets do.** A sheet renders whatever the algorithm
currently says and asks whether it looks right. The wheel is the other way
round: `target.tsv` says what the answer *should* be at each division, judged by
eye and edited by hand, and the algorithm is then hunted for until it reproduces
it -- or comes close enough. The artifact is the specification; the anchors,
the reading table and the interpolation are one candidate implementation of it.

**One concern per artifact.** The spike carries the multiset only -- three
squares in palette order, no arrangement, no square-versus-circle. Those two are
identity, and identity is a separate question from whether the mark names the
colour. Mixing them is what made the contact sheets hard to read: a change of
arrangement and a change of mapping look identical at a glance, and only one of
them is a colour judgement.

**It is meant to grow.** `--spikes` sets the divisions. Start coarse enough to
tune by hand, then double when a band turns out to need finer resolution than
the current step can express. Re-emitting preserves nothing, so a target that
has been edited should be widened by editing, not by `--emit`.

Nothing here reads a font or a screen. The ring is the gamut identicon.js
actually produces, at its own fixed saturation and lightness, so a spike sits
directly against the colour it is meant to name.
"""

import importlib.util
import math
import pathlib
import sys

D = "/home/justin/Code/Projects/Repository-Identicon/"
S = pathlib.Path(__file__).parent
TARGET = S / "target.tsv"


def load(path, module):
    spec = importlib.util.spec_from_file_location(module, path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


text = load(D + "text-identicon.py", "t")
anchored = load(str(S / "anchored2.py"), "a2")
current = load(str(S / "anchored3.py"), "a3")

NOMINAL = {name: "#{:02x}{:02x}{:02x}".format(*rgb)
           for _e, name, _cp, rgb in text.PALETTE}
ORDER = {name: k for k, (_e, name, _cp, _rgb) in enumerate(text.PALETTE)}

# ---------------------------------------------------------------------------
# Geometry. The ring is thick enough to read as a colour rather than a line,
# and the spike starts close enough to it that the comparison is immediate.
# ---------------------------------------------------------------------------

SIZE = 1400
CENTRE = SIZE / 2
BASE_IN, BASE_OUT = 112, 163   # the base-colour band, off by default
RING_IN, RING_OUT = 170, 212   # the gamut itself
BLEND_IN, BLEND_OUT = 216, 238  # in use: what each division mixes to
OFFER_OUT = 164                 # on offer: the unused candidates from the corners
OFFER_LANES, LANE_H, LANE_GAP = 3, 14, 2.5
OFFER_IN = OFFER_OUT - OFFER_LANES * (LANE_H + LANE_GAP)
SPIKE_START = 246
SWATCH_W, SWATCH_H, SWATCH_GAP = 15, 22, 4
LABEL_GAP = 10
RING_STEP = 0.25          # degrees per ring segment


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


def spike_end():
    return SPIKE_START + 3 * SWATCH_H + 2 * SWATCH_GAP


# ---------------------------------------------------------------------------
# The bench: triples that are not on the wheel but might deserve to be.
# ---------------------------------------------------------------------------

BENCH_PER_CORNER = 27
CHROMATIC = ("red", "orange", "yellow", "green", "blue", "purple", "brown")


BENCH = S / "bench.tsv"

# Where the line falls between a triple that names a colour and one that
# only gestures at it. Everything under it goes on the roster, in use or
# not, and everything on the roster is drawn inside the ring.
GOOD = 0.10


def read_bench():
    """The roster, verbatim. Numbers are the file's, never recomputed."""
    out = []
    for line in BENCH.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        f = line.split("\t")
        at = float(f[5]) if len(f) > 5 and f[5].strip() else None
        out.append((int(f[0]), multiset(f[1:4]), f[4].strip(), at))
    return out


def pool(target, roster):
    """Every unused triple the harness allows, best first, minus the rejected."""
    perceptual = load(str(S / "perceptual.py"), "perc")
    # **One class.** Whether a triple is currently on the wheel is not a
    # property of the triple, and the spread-and-stretch route assigns them by
    # hand anyway -- so being in use no longer disqualifies anything. The
    # roster is the vocabulary, not a list of leftovers. Only what is already
    # numbered, and what has been rejected outright, is excluded.
    known = {multiset(names) for _n, names, _s, _at in roster}
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


def candidates(target, limit):
    """What the bench currently offers, with its own numbers.

    **The numbers used to be positional and moved under the reader.** Placing
    six triples and freeing three renumbered everything, so `red red blue` went
    from 22 to 21 without shifting a degree. The roster now lives in
    `bench.tsv`, an entry keeps its number for good, and a number is never
    reissued -- the same discipline `target.tsv` already gets, for the same
    reason: it is referred to by hand, across renders.

    A plain render only reads. `--refill` is what appends new candidates,
    picking sector by sector so the cool half is not crowded out, and giving
    each the next free number.
    """
    # Where a triple is drawn inside the ring is its own datum, in the `at`
    # column, and nothing else decides it. It was briefly derived from the
    # divisions a triple occupied in target.tsv, which quietly imposed that
    # file's five-degree sampling grid on a ring that has no grid -- eight
    # degrees became unrepresentable for no reason at all. A triple with no
    # `at` falls back to the hue its blend reads as, which is a measurement
    # rather than a placement, and is only a starting point.
    rows = []
    for n, names, status, at in read_bench():
        if status != "offered":
            continue
        mixed = mix_rgb(names)
        reads, _colour, delta = nearest_gamut(mixed)
        rows.append((delta, reads if at is None else at, names, mixed, n, at is not None))
    rows.sort(key=lambda r: r[1])
    return rows[:limit]


def refill(target, limit):
    """Append every triple good enough to belong in the vocabulary.

    No slot count and no sector quota any more. The roster is meant to hold all
    of them, so the only question is whether a triple blends within `GOOD` of
    the hue it claims. Sector balancing existed to ration twenty-four places;
    with no rationing it would only distort the picture.
    """
    roster = read_bench()
    # No quality bar any more. The wedge widths now price each entry by the
    # identity it affords -- eight degrees for three distinct squares, four
    # for a pair, one for three of a kind -- so a weak triple shows as a
    # thin sliver rather than being left out of the picture entirely.
    chosen = list(pool(target, roster))
    if not chosen:
        print("nothing new under the good line")
        return 0

    nxt = max((n for n, _m, _s, _at in roster), default=0) + 1
    lines = BENCH.read_text().rstrip("\n").split("\n")
    for delta, hue, names, _mixed in sorted(chosen, key=lambda r: r[1]):
        lines.append("\t".join([str(nxt), *names, "offered"]))
        print(f"  #{nxt:<4} {hue:>5.0f}  {' '.join(names):26} dE {delta:.3f}")
        nxt += 1
    BENCH.write_text("\n".join(lines) + "\n")
    return len(chosen)


def bench(out, rows):
    """The candidates, parked in the four corners the wheel does not reach."""
    SW, GAP, ROW = 11, 2, 15
    margin = 14
    reach = spike_end() + LABEL_GAP
    box = CENTRE - reach / math.sqrt(2)          # how far in the circle stays
    # Right-hand columns are right-aligned to the margin rather than mirrored
    # from the circle, so they use the full width instead of hugging the wheel.
    entry_w = 3 * (SW + GAP) + 8 + SW + 6 + 52
    right = SIZE - margin - entry_w
    bottom = SIZE - margin - BENCH_PER_CORNER * ROW - 4

    gutter = 16
    corners = [(margin + gutter, margin), (right, margin),
               (margin + gutter, bottom), (right, bottom)]

    out.append('<g font-family="monospace" font-size="9" fill="#666">')
    for c, (ox, oy) in enumerate(corners):
        chunk = rows[c * BENCH_PER_CORNER:(c + 1) * BENCH_PER_CORNER]
        if not chunk:
            continue
        if c == 0:
            out.append(f'<text x="{ox}" y="{oy + 8}" fill="#444">not on the wheel</text>')
        top = oy + (20 if c == 0 else 8)
        for r, row in enumerate(chunk):
            delta, hue, names, mixed = row[0], row[1], row[2], row[3]
            y = top + r * ROW
            n = row[4]
            out.append(f'<text x="{ox - 4}" y="{y + SW - 3}" text-anchor="end" '
                       f'fill="#999">{n}</text>')
            for s, name in enumerate(names):
                out.append(f'<rect x="{ox + s * (SW + GAP)}" y="{y}" width="{SW}" '
                           f'height="{SW}" fill="{NOMINAL[name]}" stroke="#aaa" '
                           f'stroke-width="0.5"/>')
            mx = ox + 3 * (SW + GAP) + 8
            out.append(f'<rect x="{mx}" y="{y}" width="{SW}" height="{SW}" '
                       f'fill="{text.hex_colour(mixed)}" stroke="#666" '
                       f'stroke-width="0.7"/>')
            out.append(f'<text x="{mx + SW + 6}" y="{y + SW - 3}">'
                       f'{hue:.0f}&#176; {delta:.3f}</text>')
    out.append('</g>')


def gamut_at(hue):
    """The colour identicon.js produces at this hue."""
    return anchored.gamut_at(hue)


def divisions(spikes):
    return [i * 360.0 / spikes for i in range(spikes)]


ACHROMATIC = {"black", "white"}
NOMINAL_HUE = {name: (None if max(rgb) == min(rgb) else anchored.hue_of(rgb))
               for _e, name, _cp, rgb in text.PALETTE}


def canonical(names, hue):
    """A first guess at the order, used only when seeding a fresh target.

    **This is not the authority.** `target.tsv` records the order as written,
    inner to outer, and the first square is the division's declared base. That
    is a judgement, not an arithmetic property, so nothing recomputes it -- hue
    165 is a green with two blues on it because it sits in the green block, even
    though blue holds two of the three slots. A majority rule got that backwards
    and would quietly get it backwards again on every read.

    What remains here is the heuristic that produced the initial ordering:
    majority first, then nearest the target hue, achromatics last, palette order
    to settle the rest. It runs once, at seed time, and never again.
    """
    counts = {n: list(names).count(n) for n in names}

    def distance(name):
        own = NOMINAL_HUE[name]
        if own is None:
            return 1e6
        d = abs(own - hue) % 360
        return min(d, 360 - d)

    return tuple(sorted(names, key=lambda n: (-counts[n], distance(n), ORDER[n])))


def multiset(names):
    """Order-free form, for comparing a target against a candidate."""
    return tuple(sorted(names, key=lambda n: ORDER[n]))


def _catalogue():
    """Every triple the palette can make, numbered once and for all.

    **The bench used to number by position**, so a candidate's number changed
    whenever the pool did -- place six triples and free three, and everything
    renumbers even though nothing moved. `red red blue` went from 22 to 21
    without shifting a degree, which makes referring to a candidate across two
    renders impossible.

    These are catalogue numbers instead: the index of the multiset in the fixed
    enumeration of all 165, in palette order. Number 22 is the same three
    squares today, after any edit, and in any future wheel. They are sparse on
    the bench and out of order, which is the price of meaning something.
    """
    palette = [name for _e, name, _cp, _rgb in text.PALETTE]
    out, n = {}, 0
    for i in range(len(palette)):
        for j in range(i, len(palette)):
            for k in range(j, len(palette)):
                n += 1
                out[(palette[i], palette[j], palette[k])] = n
    return out


CATALOGUE = _catalogue()


# ---------------------------------------------------------------------------
# The target file
# ---------------------------------------------------------------------------

HEADER = [
    "# The intended triple at each division. No arrangement, no square-versus-",
    "# circle. This file is the specification. It is tracked per spike and",
    "# maintained by hand -- an algorithm is fitted to it, never the other way",
    "# round, so --emit refuses to overwrite it without --force.",
    "#",
    "# ORDER IS INNER TO OUTER, as the wheel draws it, and the first square is",
    "# the division's base. That is a judgement and is never recomputed: hue 165",
    "# is green-blue-blue because it sits in the green block, even though blue",
    "# holds two of its three slots.",
    "#",
    "# origin: 'eye' means Justin has judged it and it is settled.",
    "#         'seed' means it still carries whatever the mapping said and",
    "#         has not been looked at yet.",
    "#",
    "# hue\tone\ttwo\tthree\torigin",
]


def emit(spikes, mapping, force):
    if TARGET.exists() and not force:
        judged = sum(1 for _h, _n, o in read_target() if o == "eye")
        raise SystemExit(
            f"{TARGET.name} already exists, with {judged} division(s) judged by eye.\n"
            "Reseeding would discard them. This file is now the specification, not\n"
            "an output -- widen or correct it by editing. Use --force to overrule.")
    lines = list(HEADER)
    for hue in divisions(spikes):
        rgb = gamut_at(hue)
        names = canonical([text.PALETTE[k][1] for k in mapping.triple_indices(rgb)], hue)
        lines.append(f"{hue:.4f}\t" + "\t".join(names) + "\tseed")
    TARGET.write_text("\n".join(lines) + "\n")
    return len(lines) - len(HEADER)


def read_target():
    if not TARGET.exists():
        raise SystemExit(f"no {TARGET.name}; run --emit first")
    out = []
    for line in TARGET.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        f = line.split("\t")
        hue = float(f[0])
        origin = f[4].strip() if len(f) > 4 and f[4].strip() else "seed"
        # Verbatim, inner to outer. The first square is the declared base and
        # nothing here may second-guess it.
        out.append((hue, tuple(n.strip() for n in f[1:4]), origin))
    return out


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def ring(out):
    """The gamut itself, one thin segment at a time.

    Drawn as rotated rectangles rather than annular sectors: at this radius a
    quarter-degree of arc is under a pixel, so the difference is invisible and
    the arithmetic is one line instead of four.
    """
    width = 2 * math.pi * RING_OUT * RING_STEP / 360 + 0.4
    steps = int(round(360 / RING_STEP))
    for k in range(steps):
        hue = k * RING_STEP
        colour = text.hex_colour(gamut_at(hue))
        out.append(
            f'<rect x="{CENTRE - width / 2:.3f}" y="{CENTRE - RING_OUT:.1f}" '
            f'width="{width:.3f}" height="{RING_OUT - RING_IN}" fill="{colour}" '
            f'transform="rotate({hue:.4f} {CENTRE} {CENTRE})"/>')


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
    linear = [tuple(text._linear(v) for v in text.PALETTE[ORDER[n]][3])
              for n in names]
    return tuple(text._encode(sum(w * c[k] for w, c in zip(weights, linear)) / total)
                 for k in range(3))


def oklab(rgb):
    return text._oklab(tuple(text._linear(v) for v in rgb))


_GAMUT = [(h * RING_STEP, gamut_at(h * RING_STEP))
          for h in range(int(360 / RING_STEP))]


def chroma_of(rgb):
    _L, a, b = oklab(rgb)
    return math.hypot(a, b)


def hue_angle(rgb):
    """The blend's hue in Oklab, in degrees. Not an HSL hue."""
    _L, a, b = oklab(rgb)
    return math.degrees(math.atan2(b, a)) % 360


# Below this, a blend is near enough neutral that its hue angle is noise and
# should not be reported as if it meant something.
FAINT = 0.055

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


def blend_band(out, target):
    """What each division's triple mixes to, sitting against the gamut.

    Outside the ring and inside the spikes, at the division's own hue, so the
    three squares of a spike and the colour they average to are radially in
    line, with the gamut they are meant to name immediately inside. Where the
    blend departs from the ring beside it, that division is claiming something
    it does not deliver.
    """
    step = 360.0 / len(target)
    for hue, names, _origin in target:
        out.append(
            f'<path d="{sector(BLEND_IN, BLEND_OUT, hue - step / 2, hue + step / 2)}" '
            f'fill="{text.hex_colour(mix_rgb(names))}"/>')


# A wedge is as wide as the identity its triple affords. Three distinct
# squares give six arrangements and eight shape combinations -- forty-eight
# marks -- against a pair's three-by-eight and three-of-a-kind's one-by-eight.
# Eight degrees, four and one price that, near enough, and make the picture
# say what each entry is worth rather than merely that it exists.
WEDGE = {3: 8.0, 2: 4.0, 1: 1.0}
# Wedges may touch. They are meant to: an eight-degree run of eight-degree
# wedges tiles exactly, and demanding clear air between them pushed a
# perfectly packed row inward one wedge at a time for no reason. Only a real
# overlap sends an entry to the next lane.
WEDGE_TOL = 1e-6
OFFER_SEP = 0.5        # clear air between two blocks sharing a lane
OFFER_FLOOR = 62       # nearest the middle a lane may reach
DISC_R = 2.6           # a constituent disc under a placed block
DISC_GAP = 2.5         # clear air between the block and its discs
DISC_BAND = 12         # room reserved for the trefoils, before lane 1


def offer_band(out, rows):
    """The vocabulary, inside the ring, at the hue each entry sits at.

    **Nothing may be hidden.** The previous version bucketed by four degrees
    and stacked three deep, which buried anything that shared a bucket and,
    worse, still overlapped across bucket edges -- #67 at 345.5 and #24 at
    346.5 landed in different buckets and drew straight over each other. A
    block you cannot see is a block you cannot judge.

    Lanes are now packed greedily instead: walk the entries in angle order and
    drop each into the first lane whose last block has cleared, opening a new
    lane only when every existing one is still occupied. That guarantees no
    overlap at any angle, and uses depth only where the crowding actually is --
    one lane through the empty stretches, five or six through the oranges.
    Lane height then divides whatever room the deepest cluster needs.
    """
    # Two passes, and the order matters. Entries with an explicit position are
    # a deliberate arrangement, so they take the lanes against the gamut and
    # read as one clean ring. Everything still sitting at the hue its blend
    # happens to make is a measurement, not a decision, and goes behind them.
    lanes = []                      # end angle of the last block in each lane
    assigned = []

    def half(row):
        return WEDGE[len(set(row[2]))] / 2

    def drop(row, floor):
        start = row[1] - half(row)
        for k in range(floor, len(lanes)):
            if start >= lanes[k] - WEDGE_TOL:
                lanes[k] = row[1] + half(row)
                assigned.append((k, row))
                return
        lanes.append(row[1] + half(row))
        assigned.append((len(lanes) - 1, row))

    for row in sorted((r for r in rows if r[5]), key=lambda r: r[1]):
        drop(row, 0)
    behind = len(lanes)
    for row in sorted((r for r in rows if not r[5]), key=lambda r: r[1]):
        drop(row, behind)

    depth = max(len(lanes), 1)
    height = min(LANE_H,
                 (OFFER_OUT - OFFER_FLOOR - DISC_BAND) / depth - LANE_GAP)

    for lane, (delta, hue, names, mixed, n, _p) in assigned:
        # Lane 0 is the placed ring and keeps DISC_BAND to itself for the
        # trefoils; everything behind starts below that reserved strip.
        outer = OFFER_OUT - lane * (height + LANE_GAP)
        if lane:
            outer -= DISC_BAND
        wide = WEDGE[len(set(names))] / 2
        out.append(
            f'<path d="{sector(outer - height, outer, hue - wide, hue + wide)}" '
            f'fill="{text.hex_colour(mixed)}" stroke="#888" stroke-width="0.5"/>')
        if WEDGE[len(set(names))] >= 4.0:
            x, y = polar(outer - height / 2, hue)
            out.append(
                f'<text x="{x:.1f}" y="{y + 3:.1f}" text-anchor="middle" '
                f'font-family="monospace" font-size="8" '
                f'fill="{contrast(mixed)}">{n}</text>')

        # The three squares being averaged, as touching discs just inside the
        # block. A placed entry has been moved away from the hue its blend
        # makes, so the blend alone no longer says what it is made of, and the
        # corner list is a long way from the block. This puts the composition
        # where the decision is being taken.
        if not _p or WEDGE[len(set(names))] < 8.0:
            continue
        # A trefoil, not a row: two abreast with the third tucked beneath, so
        # the cluster is two discs wide instead of three and reads as one mark
        # rather than a miniature of the spike.
        top = outer - height - DISC_GAP - DISC_R
        half = math.degrees(DISC_R / top)
        places = [(top, hue - half), (top, hue + half),
                  (top - DISC_R * math.sqrt(3), hue)]
        for name, (r, a) in zip(names, places):
            dx, dy = polar(r, a)
            out.append(
                f'<circle cx="{dx:.1f}" cy="{dy:.1f}" r="{DISC_R}" '
                f'fill="{NOMINAL[name]}" stroke="#777" stroke-width="0.4"/>')


def contrast(rgb):
    """Black or white, whichever will be readable on this fill."""
    return "#000" if pc_luminance(rgb) > 0.5 else "#fff"


def pc_luminance(rgb):
    r, g, b = (v / 255 for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def base_band(out, target):
    """The primary of each triple, as a contiguous band inside the gamut.

    Every division owns the arc centred on it, and neighbours meet with no gap,
    so a run of divisions sharing a primary reads as one solid block. That is
    the point of it: the spikes show what each division does, and this shows
    where the mapping's territories actually begin and end -- which is the thing
    that was impossible to see on the contact sheets.
    """
    step = 360.0 / len(target)
    for hue, names, _origin in target:
        a0, a1 = hue - step / 2, hue + step / 2
        out.append(f'<path d="{sector(BASE_IN, BASE_OUT, a0, a1)}" '
                   f'fill="{NOMINAL[names[0]]}"/>')
    # A hairline where the primary changes, so a boundary between two similar
    # colours is still findable.
    for k, (hue, names, _origin) in enumerate(target):
        previous = target[k - 1][1][0]
        if previous == names[0]:
            continue
        x0, y0 = polar(BASE_IN, hue - step / 2)
        x1, y1 = polar(BASE_OUT, hue - step / 2)
        out.append(f'<line x1="{x0:.2f}" y1="{y0:.2f}" x2="{x1:.2f}" '
                   f'y2="{y1:.2f}" stroke="#fff" stroke-width="1"/>')


def spike(out, hue, names):
    """Three swatches marching outward, nearest the ring first."""
    out.append(f'<g transform="rotate({hue:.4f} {CENTRE} {CENTRE})">')
    out.append(f'<line x1="{CENTRE}" y1="{CENTRE - RING_OUT}" x2="{CENTRE}" '
               f'y2="{CENTRE - SPIKE_START}" stroke="#bbb" stroke-width="0.6"/>')
    for k, name in enumerate(names):
        top = CENTRE - SPIKE_START - (k + 1) * SWATCH_H - k * SWATCH_GAP
        out.append(
            f'<rect x="{CENTRE - SWATCH_W / 2:.1f}" y="{top:.1f}" '
            f'width="{SWATCH_W}" height="{SWATCH_H}" fill="{NOMINAL[name]}" '
            f'stroke="#999" stroke-width="0.5"/>')
    out.append('</g>')


def label(out, hue, origin):
    """The division's hue, upright on both halves of the wheel.

    A judged division gets a filled dot under its number. The wheel is the
    tracking surface as well as the specification, so what has been looked at
    has to be visible without opening the file.
    """
    r = spike_end() + LABEL_GAP
    flip = 90 < hue < 270
    turn = hue + 180 if flip else hue
    y = CENTRE + r if flip else CENTRE - r
    fill = "#222" if origin == "eye" else "#888"
    out.append(
        f'<text x="{CENTRE}" y="{y:.1f}" text-anchor="middle" '
        f'transform="rotate({turn:.4f} {CENTRE} {CENTRE})" '
        f'font-family="monospace" font-size="9" fill="{fill}">{hue:.0f}</text>')
    if origin == "eye":
        dy = 7 if flip else -7
        out.append(f'<circle cx="{CENTRE}" cy="{y + dy:.1f}" r="1.8" fill="#222" '
                   f'transform="rotate({turn:.4f} {CENTRE} {CENTRE})"/>')


def render(target, show_base_band=False):
    """The wheel.

    The base band is off by default. It did its job -- it turned twenty-three
    ragged runs into eight clean blocks by making the boundaries visible -- and
    once the blocks are settled it competes with the spikes for attention.
    `--base-band` brings it back when a territory needs looking at again.
    """
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{SIZE}" '
           f'height="{SIZE}" viewBox="0 0 {SIZE} {SIZE}">',
           f'<rect width="{SIZE}" height="{SIZE}" fill="#ffffff"/>']
    if show_base_band:
        base_band(out, target)
    ring(out)
    offers = candidates(target, 4 * BENCH_PER_CORNER)
    blend_band(out, target)
    offer_band(out, offers)
    bench(out, offers)
    for hue, names, _o in target:
        spike(out, hue, names)
    for hue, _n, origin in target:
        label(out, hue, origin)

    judged = sum(1 for _h, _n, o in target if o == "eye")
    out.append(f'<text x="{CENTRE}" y="{CENTRE - 6}" text-anchor="middle" '
               f'font-family="monospace" font-size="13" fill="#444">'
               f'{len(target)} divisions</text>')
    out.append(f'<text x="{CENTRE}" y="{CENTRE + 12}" text-anchor="middle" '
               f'font-family="monospace" font-size="10" fill="#888">'
               f'{judged} judged, {len(target) - judged} seeded</text>')
    out.append('</svg>')
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Scoring a candidate against the target
# ---------------------------------------------------------------------------

def next_path():
    """The next unused wheelN.svg. The wheel is a series, like the sheets."""
    n = 1
    while (S / f"wheel{n}.svg").exists():
        n += 1
    return S / f"wheel{n}.svg"


def score(target, mapping, name):
    hits, misses = 0, []
    for hue, want, _origin in target:
        rgb = gamut_at(hue)
        got = multiset([text.PALETTE[k][1] for k in mapping.triple_indices(rgb)])
        if got == multiset(want):
            hits += 1
        else:
            misses.append((hue, multiset(want), got))
    print(f"{name}: {hits}/{len(target)} divisions "
          f"({hits / len(target) * 100:.1f}%)")
    for hue, want, got in misses:
        print(f"   {hue:6.1f}  want {' '.join(want):26} got {' '.join(got)}")
    return hits


def main(argv):
    spikes = 72
    if "--spikes" in argv:
        i = argv.index("--spikes")
        spikes = int(argv[i + 1])
        argv = argv[:i] + argv[i + 2:]

    if "--emit" in argv:
        n = emit(spikes, current, "--force" in argv)
        print(f"{TARGET} seeded with {n} divisions from anchored3")
        return 0

    if "--refill" in argv:
        added = refill(read_target(), 4 * BENCH_PER_CORNER)
        print(f"{added} added to {BENCH.name}")
        return 0

    if "--score" in argv:
        target = read_target()
        score(target, current, "anchored3")
        score(target, anchored, "anchored2")
        return 0

    target = read_target()
    if "--out" in argv:
        path = pathlib.Path(argv[argv.index("--out") + 1])
        if not path.is_absolute():
            path = S / path
    else:
        path = next_path()
    svg = render(target, "--base-band" in argv)
    path.write_text(svg)
    judged = sum(1 for _h, _n, o in target if o == "eye")
    print(f"{path} {len(svg)} bytes, {len(target)} divisions, "
          f"{judged} judged by eye")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

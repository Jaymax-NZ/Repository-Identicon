#!/usr/bin/env python3
"""The wheel: the gamut as a ring, and the blocks placed by hand against it.

    python3 wheel.py                   render the next free wheelN.svg
    python3 wheel.py --reference       regenerate in-use.tsv from bench.tsv
    python3 wheel.py --refill          add newly admissible triples to bench.tsv
    python3 wheel.py --tables          also draw the corner lists and the unused

**No algorithm is being scored here any more.** The wheel was built to hold an
algorithm to a target file, and that route ended: `bench.tsv` is now the answer
itself, fifty blocks placed by eye, and `in-use.tsv` is generated from it. What
survives from that era is the measurement -- every block still reports the hue
its blend reads as, and how far it was moved from it.

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

D = "/home/justin/Code/Projects/Repository-Identicon/"
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

# ---------------------------------------------------------------------------
# Geometry. The ring is thick enough to read as a colour rather than a line,
# and the spike starts close enough to it that the comparison is immediate.
# ---------------------------------------------------------------------------

# 1400 was sized for the spikes, which reached far outside the gamut ring.
# With them off the drawing stops at RING_OUT, and the canvas was mostly the
# white space they used to occupy. The corner lists set the floor now, not the
# wheel: 27 rows at 15px, twice over, plus margins.
SIZE = 720
CENTRE = SIZE / 2
TECH_IN, TECH_OUT = 152, 160   # the workings: stretch rules and drift ticks
NUM_R = 165                    # the numbers, in the gap before the gamut
RING_IN, RING_OUT = 170, 212   # the gamut itself
OUTER_IN, OUTER_OUT = 218, 268  # the ring to look at: the blocks, wide
# The second gamut ring, and the trefoils that sit on it. Deep enough for the
# cluster (about 2.9 disc radii) with a little air at each edge.
TREF_IN, TREF_OUT = 272, 296
TREF_BG = "#ececec"
TABLE_W = 232                  # the roster, beside the wheel
LANE_H, LANE_GAP = 14, 2.5      # the lane stack, with --tables
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
# The bench: triples that are not on the wheel but might deserve to be.
# ---------------------------------------------------------------------------

BENCH_PER_CORNER = 27
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
    perceptual = load(str(S / "perceptual.py"), "perc")
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


def candidates(limit, placed_only=True):
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
    for n, names, status, at, mult in read_bench():
        if status != "offered":
            continue
        # The ring is full and hand-placed, so an entry with no position is no
        # longer a candidate waiting its turn -- it is a colour that did not
        # make it. Drawing those behind the ring, and listing them in the
        # corners, was the apparatus of choosing. `--tables` brings both back
        # when there is choosing to do again.
        if placed_only and at is None:
            continue
        mixed = mix_rgb(names)
        reads, _colour, delta = nearest_gamut(mixed)
        rows.append((delta, reads if at is None else at, names, mixed, n,
                     at is not None, reads, mult))
    rows.sort(key=lambda r: r[1])
    return rows[:limit]


def refill(limit):
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


def bench(out, rows):
    """The candidates, parked in the four corners the wheel does not reach."""
    SW, GAP, ROW = 11, 2, 15
    margin = 14
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
    """The colour identicon.js produces at this hue, at its fixed s and l."""
    return tuple(identicon._quantise(v)
                 for v in identicon._hsl_to_rgb((hue % 360) / 360,
                                                identicon.SATURATION,
                                                identicon.LIGHTNESS))


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
        hue = k * RING_STEP
        colour = text.hex_colour(gamut_at(hue))
        out.append(
            f'<rect x="{CENTRE - width / 2:.3f}" y="{CENTRE - outer:.1f}" '
            f'width="{width:.3f}" height="{outer - inner}" fill="{colour}" '
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
# Wedges may touch. They are meant to: an eight-degree run of eight-degree
# wedges tiles exactly, and demanding clear air between them pushed a
# perfectly packed row inward one wedge at a time for no reason. Only a real
# overlap sends an entry to the next lane.
WEDGE_TOL = 1e-6
OFFER_FLOOR = 62       # nearest the middle a lane may reach
DISC_R = 6.0           # a constituent disc; what a 4 degree block can carry


def offer_band(out, rows, tables=False):
    """The vocabulary, at the hue each entry sits at.

    **Two rings, with different jobs.** The blocks are drawn twice. Outside the
    gamut, wide, is the ring to look at: the mixture each triple makes, at the
    hue it has been placed, with its trefoil beyond it. Inside the gamut is a
    narrow technical band carrying the machinery -- the entry number, the
    stretch rules, and the drift ticks and their leaders. Reading a colour and
    auditing a placement are different acts and were fighting for the same
    forty pixels; separating them lets the outer ring be as large as the
    comparison needs while the workings stay legible and out of the way.

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
        return width_of(row) / 2

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
                 (TECH_OUT - OFFER_FLOOR) / depth - LANE_GAP) if tables \
        else TECH_OUT - TECH_IN

    ticks = []
    for idx, (lane, row) in enumerate(assigned):
        delta, hue, names, mixed, n, _p, reads, _mult = row
        colour = text.hex_colour(mixed)
        wide = width_of(row) / 2
        outer = TECH_OUT - lane * (height + LANE_GAP)

        # The technical band: thin, inside the gamut, carrying the workings.
        out.append(
            f'<path d="{sector(outer - height, outer, hue - wide, hue + wide)}" '
            f'fill="{colour}" stroke="#888" stroke-width="0.5"/>')
        if width_of(row) >= 4.0 and not lane:
            number(out, hue, n)
        if lane:
            continue
        ticks.append((reads, hue, mixed))
        stretch(out, row, outer - height)

        # The ring to look at: same block, outside the gamut, wide enough to
        # judge the colour against the gamut it sits beside.
        out.append(
            f'<path d="{sector(OUTER_IN, OUTER_OUT, hue - wide, hue + wide)}" '
            f'fill="{colour}" stroke="#888" stroke-width="0.5"/>')
        if width_of(row) >= 4.0:
            venn(out, idx, names, TREF_OUT - 3.0, hue, trefoil_r(row))

    drift(out, ticks)


def number(out, hue, n):
    """The block's number, in the white gap between the workings and the gamut.

    **On the band it was type laid over the colour it was meant to let you
    read**, and taking it off entirely left the wheel unnameable -- the roster
    could say what a block was but you could not point at one. The gap does
    both jobs: nothing is covered, and the number sits on the same radius as
    its block.

    Set tangentially, and flipped through the lower half so none of them stand
    on their heads. Rotating with the wheel rather than staying upright is what
    keeps a two-digit number inside the four degrees the narrowest block gets;
    upright text would need the width of its diagonal at every angle.
    """
    lower = 90 < hue < 270
    turn = hue - 180 if lower else hue
    y = CENTRE + NUM_R if lower else CENTRE - NUM_R
    out.append(
        f'<text x="{CENTRE}" y="{y + 3:.1f}" text-anchor="middle" '
        f'font-family="monospace" font-size="6.5" fill="#666" '
        f'transform="rotate({turn:.3f} {CENTRE} {CENTRE})">{n}</text>')


def trefoil_r(_row):
    """One size for every trefoil.

    **Sizing each cluster to its own block was wrong.** It looked efficient --
    a wide block has more arc, so it can carry a bigger mark -- but disc area
    then reads as a quantity, and it is not one: a trefoil says what three
    squares average to, and that claim is identical whether the block beneath
    it is four degrees or sixteen. Varying the size made narrow blocks look
    like lesser statements of the same fact. The size is set by the narrowest
    block that gets a trefoil at all, which is four degrees.
    """
    return DISC_R


def width_of(row):
    """How wide this block is drawn: its class price, times any hand stretch."""
    return WEDGE[len(set(row[2]))] * row[7]


STRETCH_IN = 1.6       # how far inward of the block the first rule sits
STRETCH_STEP = 1.7     # spacing between stacked rules
STRETCH_W = 1.0
STRETCH_CAP = 1.4      # length of the radial cap at each end


def stretch(out, row, inner):
    """Rules under a widened block, as long as the block ought to have been.

    The 8/4/1 degrees price a block by the identity it affords, and that is the
    one thing a stretched block stops saying: at 2x a pair is as wide as an
    unstretched three-distinct and reads as worth the same. This puts the class
    price back on the page. Each rule spans the natural width, centred, with a
    cap at each end, so the block overhangs it by exactly what was added.

    **How far it was stretched is a count, not a length.** One rule alone said
    only that a block had been widened -- telling 1.5x from 2x meant eyeing the
    overhang against a width that is itself variable, which is no way to read a
    chart. There is now one rule per half-step of stretch: one for 1.5x, two
    for 2x. Counting two marks is immediate in a way that judging a proportion
    never is.
    """
    steps = int(round((row[7] - 1) / 0.5))
    if steps < 1:
        return
    natural = WEDGE[len(set(row[2]))] / 2
    for k in range(steps):
        r = inner - STRETCH_IN - k * STRETCH_STEP
        sx, sy = polar(r, row[1] - natural)
        ex, ey = polar(r, row[1] + natural)
        out.append(
            f'<path d="M {sx:.2f} {sy:.2f} A {r:.1f} {r:.1f} 0 0 1 {ex:.2f} '
            f'{ey:.2f}" fill="none" stroke="#555" stroke-width="{STRETCH_W}"/>')
    deep = inner - STRETCH_IN - (steps - 1) * STRETCH_STEP
    for side in (-natural, natural):
        cx, cy = polar(inner - STRETCH_IN + STRETCH_CAP / 2, row[1] + side)
        dx, dy = polar(deep - STRETCH_CAP / 2, row[1] + side)
        out.append(
            f'<line x1="{cx:.2f}" y1="{cy:.2f}" x2="{dx:.2f}" y2="{dy:.2f}" '
            f'stroke="#555" stroke-width="{STRETCH_W}"/>')


# Where a block sits is a decision, and the block itself cannot show that a
# decision was taken -- a placed entry and one left at the hue its blend reads
# looks identical. This is the only marker on the wheel that records a
# judgement rather than a measurement, so it is drawn as faintly as it can be
# and still be found when looked for: a hairline arc from the block's nominal
# hue to where it was actually put, with a tick at nominal. Lanes behind the
# first are all at nominal by definition and get nothing.
# Inside the technical band, not between it and the gamut. The ticks used to
# sit in the six pixels separating the two, where the leaders had to cross the
# band's own edge to reach their blocks and the whole apparatus pressed up
# against the gamut it was not about. Below the band there is open space, the
# leaders run inward and unobstructed, and the ring reads outward from the
# gamut without this crossing it.
DRIFT_R = 143
# **Every lane 0 block gets a tick, including the ones that never moved.**
# Ticks were suppressed below a quarter of a degree on the grounds that such a
# move is rounding rather than a decision, which is true and beside the point:
# a block sitting exactly on nominal is a fact worth showing, and suppressing
# it made the mono-colours -- which are all at nominal, by construction --
# look as though they had been left out. A block at nominal now reads as a
# tick with a leader running straight down it.


DRIFT_W = 1.1          # tick stroke, in pixels
# One tick's worth of arc, so a split pair reads as two marks with a gap the
# same size as the marks themselves.
DRIFT_GAP = math.degrees(2 * DRIFT_W / DRIFT_R)


def drift(out, ticks):
    """Ticks at the hue each lane 0 block would sit at if nobody had moved it.

    **The connecting arc is gone.** Joining tick to block along a circle put
    every one of them on the same line, and at this density the lines ran into
    each other and read as one continuous rule rather than as forty separate
    displacements. The tick alone says where nominal was; the block's own
    colour says which block it belongs to, which is why it is painted in that
    colour rather than in grey.

    **Coincidences are split, not stacked.** Two triples can blend to the same
    hue -- #16 and #95 both read 261.8 -- and drawing one over the other lost
    a tick with nothing to show it had happened, so the marks could never be
    counted. Any run closer together than a tick's width is spread evenly
    about its own mean with exactly that width between neighbours: the pair
    still reads as one event at one hue, and both are there to be counted.
    """
    placed = []
    for angle, hue, mixed in sorted(ticks):
        if placed and angle - placed[-1][-1][0] <= DRIFT_GAP:
            placed[-1].append((angle, hue, mixed))
        else:
            placed.append([(angle, hue, mixed)])
    for group in placed:
        mid = sum(a for a, _h, _m in group) / len(group)
        for i, (_a, hue, mixed) in enumerate(group):
            at = mid + (i - (len(group) - 1) / 2) * DRIFT_GAP
            colour = text.hex_colour(mixed)
            x0, y0 = polar(DRIFT_R - 2.5, at)
            x1, y1 = polar(DRIFT_R + 2.5, at)
            out.append(
                f'<line x1="{x0:.2f}" y1="{y0:.2f}" x2="{x1:.2f}" '
                f'y2="{y1:.2f}" stroke="{colour}" '
                f'stroke-width="{DRIFT_W}"/>')
            # The leader closes the loop the tick alone could not: it runs
            # from the tick's outer end to the middle of the block's outer
            # edge, so every tick names its block unambiguously. Because each
            # one leans by however far its block was moved, they fan rather
            # than stack, and the extreme cases are the ones lying nearly
            # flat against the ring -- visible as slope, without a number.
            bx, by = polar(TECH_IN, hue)
            out.append(
                f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{bx:.2f}" '
                f'y2="{by:.2f}" stroke="{colour}" stroke-width="0.45" '
                f'stroke-opacity="0.85"/>')


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
        out.append(disc(k, f' fill="{NOMINAL[names[k]]}"'))
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


def table(out, rows):
    """What is in use, in hue order, beside the wheel.

    The wheel says where each block sits and what it looks like; it cannot say
    what it is made of and where it ought to have been without covering itself
    in type. This is the other half: mixture, constituents, the hue the mixture
    reads as, and how far the block was moved from it. Sorted by position, so
    reading down the column walks round the ring.

    Offset carries its sign. A block pulled back against the direction of
    increasing hue reads negative, and a column of like signs is a run that was
    dragged bodily rather than seated one at a time -- which is worth being
    able to see at a glance, since it is exactly what the cascades did.
    """
    SW, GAP, ROW = 10, 2, 12.4
    x0 = SIZE + 14
    top = 26
    out.append('<g font-family="monospace" font-size="8.5" fill="#444">')
    out.append(f'<text x="{x0}" y="{top - 12}" font-size="9.5" fill="#222">'
               f'in use, {len(rows)} blocks, by position</text>')
    out.append(f'<text x="{x0 + 150}" y="{top - 2}" text-anchor="end" '
               f'fill="#888">nominal</text>')
    out.append(f'<text x="{x0 + 196}" y="{top - 2}" text-anchor="end" '
               f'fill="#888">offset</text>')
    for i, row in enumerate(sorted(rows, key=lambda r: r[1])):
        _d, hue, names, mixed, n, _p, reads, _m = row
        y = top + i * ROW
        drop = y + SW - 2
        out.append(f'<text x="{x0 + 18}" y="{drop}" text-anchor="end" '
                   f'fill="#999">{n}</text>')
        out.append(f'<rect x="{x0 + 24}" y="{y}" width="{SW}" height="{SW}" '
                   f'fill="{text.hex_colour(mixed)}" stroke="#666" '
                   f'stroke-width="0.7"/>')
        for s, name in enumerate(names):
            out.append(f'<rect x="{x0 + 44 + s * (SW + GAP)}" y="{y}" '
                       f'width="{SW}" height="{SW}" fill="{NOMINAL[name]}" '
                       f'stroke="#aaa" stroke-width="0.5"/>')
        off = ((hue - reads + 180) % 360) - 180
        out.append(f'<text x="{x0 + 150}" y="{drop}" text-anchor="end">'
                   f'{reads:.1f}&#176;</text>')
        out.append(f'<text x="{x0 + 196}" y="{drop}" text-anchor="end" '
                   f'fill="{"#b00" if abs(off) >= 10 else "#444"}">'
                   f'{off:+.1f}&#176;</text>')
    out.append('</g>')


def render(show_tables=False):
    """The wheel: the gamut, the blocks placed against it, and the workings.

    `--tables` restores the corner lists and the unused colours -- the
    apparatus of choosing, which travels together and is off while there is
    nothing left to choose.
    """
    wide = SIZE + TABLE_W
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
    offers = candidates(4 * BENCH_PER_CORNER, not show_tables)
    offer_band(out, offers, show_tables)
    table(out, [r for r in offers if r[5]])
    if show_tables:
        bench(out, offers)
    out.append('</svg>')
    return "\n".join(out)


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
    """The next unused wheelN.svg. The wheel is a series, like the sheets."""
    n = 1
    while (S / f"wheel{n}.svg").exists():
        n += 1
    return S / f"wheel{n}.svg"


def main(argv):
    if "--refill" in argv:
        added = refill(4 * BENCH_PER_CORNER)
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
    svg = render("--tables" in argv)
    path.write_text(svg)
    placed = sum(1 for r in read_bench() if r[3] is not None)
    print(f"{path} {len(svg)} bytes, {placed} blocks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

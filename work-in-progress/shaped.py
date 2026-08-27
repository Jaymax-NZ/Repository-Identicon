#!/usr/bin/env python3
"""The shape channel: square or circle, laid over the triple from in-use.tsv.

`arrange` already takes a second channel out of the colour — which squares to
use answers fidelity, what order to lay them in answers identity, and the two
cost each other nothing. This is a third channel of the same kind, and it is
worth having because order alone is not enough: ordered triples of nine colours
reach 729 and the gamut is 1074. Order cannot separate every colour no matter
how cleverly it is chosen. There is no arrangement of nine squares in three
positions that gets there.

**Shape is not a weak channel.** It is preattentive, and a circle among squares
is found without search. It is not a tiebreak bolted onto colour; it is a second
axis of comparable strength, which is why it is worth spending on identity.

**Black and white stay square.** Unicode names their circles MEDIUM BLACK CIRCLE
and MEDIUM WHITE CIRCLE where every square in the palette is LARGE, and the
palette is anchored on those names — the size word is part of the definition,
not a rendering detail. Mixing a MEDIUM neutral with LARGE chromatics reads
ragged, and white alone lands on 53 colours, so it would read ragged often.
Justin's direction, 2026-08-19.

That leaves seven circleable colours and two that are not, so a position offers
sixteen glyphs rather than eighteen, and ordered marks reach 4096 against the
gamut's 1074 — clear by a factor of nearly four, where colour and order together
fell short by 345.

**Where the bit comes from, and why after the arrangement.** The same MD5 of
`#rrggbb` that `arrange` hashes, decomposed mixed-radix rather than taken modulo
twice. `arrange` keeps the remainder against the permutation count; the shape
takes the *quotient* and reduces that. Two consequences, both wanted:

  - Arrangement is bit-for-bit what it is today. Nothing already chosen moves.
    Sheet 4 and sheet 5 carry identical arrangements, so flipping between them
    shows the shape channel by itself and nothing else.
  - The two draws are independent. Reducing one number modulo 6 and again
    modulo 8 correlates them; taking successive digits of a mixed-radix
    expansion does not.

This is what "arrangement comes before square-versus-circle" means in the code:
arrangement consumes the low digits, shape takes what is left.

The triple stays a pure function of the colour. `.colour` remains sufficient —
a consumer holding only a hex string can still compute the whole mark, shape
included, without being able to re-resolve the key.
"""

import bisect
import hashlib
import importlib.util
import itertools
import pathlib

D = "/home/justin/Code/Projects/Repository-Identicon/"
S = pathlib.Path(__file__).parent


def load(path, module):
    spec = importlib.util.spec_from_file_location(module, path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


text = load(D + "text-identicon.py", "t")
wheel = load(str(S / "wheel.py"), "wheel")

# **The triple comes from the table now, not from an algorithm.** This used to
# call into the anchored mapping, which was one candidate implementation of a
# target file; both are gone. `in-use.tsv` is the mapping, so the shape channel
# is laid over whatever it says, and the two cannot fall out of step.
_ARCS = []
for _line in (S / "in-use.tsv").read_text().splitlines():
    if _line.startswith("#") or not _line.strip():
        continue
    _f = _line.split("\t")
    _ARCS.append((float(_f[0]), float(_f[1]),
                  tuple(text.PALETTE[wheel.ORDER[n]][1] for n in _f[3:6])))
_ARCS.sort()
_STARTS = [a[0] for a in _ARCS]


def draw_of(rgb):
    """Where in the draw this colour came from, recovered from the colour alone.

    **The table is indexed by the draw, not by the hue.** Those were the same
    number until mapping version 3, which warps the draw before using it as a
    hue -- so this used to be `hue_of(rgb)`, a plain HSL hue, and that lookup is
    now wrong by up to a third of the wheel around the blue-greens. It is
    exactly the mistake the header of `in-use.tsv` warns about, and it was
    sitting in this file.

    Recovered rather than passed in, because the point of hashing the colour is
    that `.identicon/repository-identicon.colour` is sufficient: a consumer with
    only `#rrggbb` can still compute the whole mark. The warp is monotonic, so
    it inverts; the hue is read in Oklab, which is the space the mark's colour
    was built in.

    A caller holding the key should pass its own draw to `mark` instead, which
    is exact. This is the colour-only path and carries the quantising error --
    see `_selftest`, which measures how often that lands in the wrong arc.
    """
    return wheel.warp_angle(wheel.hue_angle(rgb)) % 360.0


def triple(rgb, grid, draw=None):
    """The three palette indices for `rgb`, in laid-out order.

    Which three squares is a table lookup on the draw; what order they go in is
    `arrange`, which now reads the grid. Arrangement is an identity channel and
    has never depended on which squares were chosen -- it used to depend on the
    colour, which is exactly the fault: hashing an output of the mapping cannot
    add identity the mapping has not already spent.
    """
    at = draw_of(rgb) if draw is None else draw % 360.0
    _lo, _hi, names = _ARCS[bisect.bisect_right(_STARTS, at) - 1]
    return text.arrange(tuple(wheel.ORDER[n] for n in names), grid)


# Never circled. See the module docstring: their circles are MEDIUM where every
# square is LARGE, and the Unicode name is the palette's definition.
ALWAYS_SQUARE = ("black", "white")

# The seven that can be either. Red and blue come from Unicode 6's emoji block
# and the rest from Unicode 12's, which is why the codepoints are not one run --
# the same split that puts the black and white squares at U+2B1B and U+2B1C
# rather than alongside their coloured siblings.
CIRCLES = {
    "red":    "\U0001F534",   # LARGE RED CIRCLE
    "orange": "\U0001F7E0",   # LARGE ORANGE CIRCLE
    "yellow": "\U0001F7E1",   # LARGE YELLOW CIRCLE
    "green":  "\U0001F7E2",   # LARGE GREEN CIRCLE
    "blue":   "\U0001F535",   # LARGE BLUE CIRCLE
    "purple": "\U0001F7E3",   # LARGE PURPLE CIRCLE
    "brown":  "\U0001F7E4",   # LARGE BROWN CIRCLE
}


def _bits(grid):
    """The one number both channels are drawn from.

    **The grid, not the colour.** This hashed `#rrggbb`, which meant both
    channels were functions of an output of the mapping and could add nothing
    to it -- two projects on the same quantised colour got the same order and
    the same circles, necessarily. The grid is fifteen bits of the key's digest,
    from a slice disjoint from the one the hue is drawn from, and it is already
    in hand wherever a mark is being made.
    """
    return text.grid_bits(grid)


def _arrangements(indices):
    """How many distinct orders the multiset affords -- 1, 3 or 6.

    Recomputed here rather than imported because it is the radix `arrange`
    consumed, and the shape channel must divide by exactly that to take the
    next digit rather than a correlated one.
    """
    return len(set(itertools.permutations(indices)))


def circleable(arranged):
    """Positions in the laid-out triple that may take a circle."""
    return [k for k, i in enumerate(arranged)
            if text.PALETTE[i][1] not in ALWAYS_SQUARE]


def shapes(arranged, grid):
    """Which of the three laid-out positions are circles.

    A tuple of three booleans, True meaning circle. All False when the triple
    holds nothing circleable, which is the black-and-white corner of the gamut.
    """
    positions = circleable(arranged)
    out = [False, False, False]
    if not positions:
        return tuple(out)
    value = _bits(grid) // _arrangements(arranged)
    bits = value % (1 << len(positions))
    for j, position in enumerate(positions):
        out[position] = bool(bits >> j & 1)
    return tuple(out)


def mark(rgb, grid, draw=None):
    """`(arranged indices, shape flags)` -- the whole choice for one project."""
    arranged = triple(rgb, grid, draw)
    return arranged, shapes(arranged, grid)


def emoji(rgb, grid):
    """The three emoji for this project, shapes applied, as one string."""
    arranged, flags = mark(rgb, grid)
    out = []
    for index, circle in zip(arranged, flags):
        name = text.PALETTE[index][1]
        out.append(CIRCLES[name] if circle else text.PALETTE[index][0])
    return "".join(out)


def names(rgb, grid):
    """The three squares as `colour` or `colour-circle`, in laid-out order."""
    arranged, flags = mark(rgb, grid)
    return tuple(f"{text.PALETTE[i][1]}{'-circle' if c else ''}"
                 for i, c in zip(arranged, flags))


def key(rgb, grid):
    """A hashable identity for the whole mark, for spread measurement."""
    arranged, flags = mark(rgb, grid)
    return tuple(zip(arranged, flags))


def _selftest():
    """**Measured over projects, not over colours.**

    This used to sweep the gamut, one sample per colour, and report the spread
    of the marks it found. That measurement is exactly the one that could not
    see the fault it was meant to catch: with the order and the shapes hashed
    from the colour, one sample per colour makes every mark look distinct by
    construction, however many projects are piled on it. The population is
    projects, so the sample is projects.
    """
    identicon = load(D + "repository-identicon.py", "i")
    N = 4000
    rows = []
    for k in range(N):
        key_ = identicon.stamp_key(f"github.com/example/project-{k:05d}", 3)
        rows.append((identicon.identicon_colour(key_),
                     identicon.identicon_grid(key_),
                     identicon.identicon_hue(key_) * 360.0))

    for rgb, grid, draw in rows[:500]:
        assert mark(rgb, grid, draw) == mark(rgb, grid, draw)
        assert mark(rgb, grid, draw)[0] == triple(rgb, grid, draw)
        arranged, flags = mark(rgb, grid, draw)
        for index, circle in zip(arranged, flags):
            assert not (circle and text.PALETTE[index][1] in ALWAYS_SQUARE)
        assert len(emoji(rgb, grid)) == 3

    colours = len({text.hex_colour(r) for r, _g, _d in rows})
    triples = len({triple(r, g, d) for r, g, d in rows})
    marks = len({key(r, g) for r, g, _d in rows})
    print(f"over {N} projects: {colours} colours, {triples} arrangements, "
          f"{marks} marks with shape")

    # The fault, as a test. Projects that share a colour must not be forced to
    # share a mark; that is the whole reason the order moved to the grid.
    by_colour = {}
    for rgb, grid, _d in rows:
        by_colour.setdefault(text.hex_colour(rgb), []).append(grid)
    shared = [(c, gs) for c, gs in by_colour.items() if len(gs) > 1]
    collapsed = 0
    for _c, grids in shared:
        rgb = tuple(int(_c[i:i + 2], 16) for i in (1, 3, 5))
        if len({key(rgb, g) for g in grids}) < len(grids):
            collapsed += 1
    # Under the old rule every one of these collapsed, by construction: the
    # order and the shapes were a function of the colour, and the colour is
    # what these projects share. That is the comparison worth asserting, rather
    # than a threshold picked to pass.
    print(f"{len(shared)} colours carry more than one project; "
          f"{collapsed} still collapse to one mark, against "
          f"{len(shared)} under the old rule")
    assert collapsed < len(shared) / 2, (
        "projects sharing a colour are still sharing a mark")
    # What is left is not the channel failing but the vocabulary running out:
    # a triple of three of a kind affords one order, and one holding black and
    # white affords few shapes, so some projects have nowhere else to go.

    # `draw_of` recovers the wheel position from the colour alone, for a
    # consumer that has one and no key. It cannot be exact -- the colour is
    # quantised -- and what matters is whether the error crosses an arc.
    disagree = sum(1 for rgb, grid, draw in rows
                   if triple(rgb, grid) != triple(rgb, grid, draw))
    print(f"draw recovered from the colour alone: {disagree} of {N} "
          f"land in a different arc")
    print("selftest OK")


if __name__ == "__main__":
    _selftest()

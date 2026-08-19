#!/usr/bin/env python3
"""The shape channel: square or circle, laid over the anchored triple.

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
anchored = load(str(S / "anchored2.py"), "a2")

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


def _digest(rgb):
    """The one number both channels are drawn from."""
    return int(hashlib.md5(text.hex_colour(rgb).encode("utf-8")).hexdigest(), 16)


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


def shapes(arranged, rgb):
    """Which of the three laid-out positions are circles.

    A tuple of three booleans, True meaning circle. All False when the triple
    holds nothing circleable, which is the black-and-white corner of the gamut.
    """
    positions = circleable(arranged)
    out = [False, False, False]
    if not positions:
        return tuple(out)
    value = _digest(rgb) // _arrangements(arranged)
    bits = value % (1 << len(positions))
    for j, position in enumerate(positions):
        out[position] = bool(bits >> j & 1)
    return tuple(out)


def mark(rgb):
    """`(arranged indices, shape flags)` -- the whole choice for a colour."""
    arranged = anchored.triple(rgb)
    return arranged, shapes(arranged, rgb)


def emoji(rgb):
    """The three emoji for `rgb`, shapes applied, as one string."""
    arranged, flags = mark(rgb)
    out = []
    for index, circle in zip(arranged, flags):
        name = text.PALETTE[index][1]
        out.append(CIRCLES[name] if circle else text.PALETTE[index][0])
    return "".join(out)


def names(rgb):
    """The three squares as `colour` or `colour-circle`, in laid-out order."""
    arranged, flags = mark(rgb)
    return tuple(f"{text.PALETTE[i][1]}{'-circle' if c else ''}"
                 for i, c in zip(arranged, flags))


def key(rgb):
    """A hashable identity for the whole mark, for spread measurement."""
    arranged, flags = mark(rgb)
    return tuple(zip(arranged, flags))


def _selftest():
    perceptual = load(str(S / "perceptual.py"), "perc")
    colours = perceptual.gamut()

    # Every colour has exactly the shapes its own digest asks for, and asking
    # twice gives the same answer.
    for rgb in colours:
        assert mark(rgb) == mark(rgb)

    # Arrangement is untouched by the shape channel.
    for rgb in colours:
        assert mark(rgb)[0] == anchored.triple(rgb)

    # Black and white are never circles.
    for rgb in colours:
        arranged, flags = mark(rgb)
        for index, circle in zip(arranged, flags):
            assert not (circle and text.PALETTE[index][1] in ALWAYS_SQUARE)

    # Every emoji is one codepoint, so the mark stays three characters.
    for rgb in colours:
        assert len(emoji(rgb)) == 3, (text.hex_colour(rgb), emoji(rgb))

    before = len({anchored.triple(rgb) for rgb in colours})
    after = len({key(rgb) for rgb in colours})
    print(f"gamut {len(colours)}   arrangements {before}   with shape {after}")

    counts = {}
    for rgb in colours:
        k = key(rgb)
        counts[k] = counts.get(k, 0) + 1
    total = sum(counts.values())
    effective = 1 / sum((c / total) ** 2 for c in counts.values())
    print(f"spread: {len(counts)} distinct, {effective:.1f} effective")

    shaped_positions = sum(sum(mark(rgb)[1]) for rgb in colours)
    print(f"circles drawn: {shaped_positions} of {3 * len(colours)} positions")
    print("selftest OK")


if __name__ == "__main__":
    _selftest()

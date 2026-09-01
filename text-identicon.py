#!/usr/bin/env python3
"""The identicon as text: two lines, for clients that render neither an image
nor ANSI colour. A terminal chat client shows an assistant message as plain
markdown -- an inline PNG arrives as literal base64 and ANSI escapes are
stripped -- but Unicode block glyphs and colour emoji survive.

    <cell><cell><cell>
    <cell><cell><cell> <emoji><emoji><emoji>

The two parts have names, and they are the names of the artifacts each one is
written to. The pattern is drawn on a **lattice** -- `sextant` on the 2x3 set,
`octant` on the 2x4 -- three characters by two lines either way, carrying the
whole 5x5 matrix. The **tricolour** is the colour: three colours drawn from a
palette of nine, one emoji each. The tricolour terminates the mark rather than
opening it, because an emoji is a full character cell tall and so sits flush
beside the line that is full of matrix.

**A palette entry is a colour, not a square.** It is drawn as a square here
because that is the only shape this file emits, but which shape carries a
colour is a separate decision from which colours are chosen -- square and
circle are peers, settled after the colours are -- so nothing below calls a
palette entry a square.

Both lattices are written. They differ in how tall the mark stands and in how
likely a font is to have the glyphs, not in what they can carry, so which one
suits is the host's question rather than this file's. `text` draws sextants
unless told otherwise.

No seed, no digest and no palette of its own: `text` takes a matrix and a colour,
so this file can be vendored alone into a tool with no identicon machinery.

    python3 text-identicon.py '#2692d9' '.#.#.,.#.#.,#...#,#.#.#,.#.#.'

Standard library only.
"""

import itertools
import math

# ---------------------------------------------------------------------------
# The two lattices
#
# Both put the 5x5 matrix in three characters by two lines, and both are
# lossless: every one of the ten pinned vectors reconstructs its matrix exactly
# from either. `work-in-progress/lattice-comparison.md` is the two side by side
# on real seeds.
#
# Neither is a fallback for the other and both are written, because what
# separates them is the host, not the mark:
#
#   octants   2x4. Unicode 16.0, 2024. Squarer -- a terminal cell is roughly
#             twice as tall as it is wide, so a 2x4 subcell is about square,
#             and five rows span 1.25 cell-heights.
#   sextants  2x3. Unicode 13.0, 2020, so a font is four years likelier to have
#             them, and a host without the glyphs draws the whole mark as tofu.
#             Five rows span 1.67 cell-heights, a third taller for the same
#             width.
#
# Bit i of a pattern is subcell (row i // 2, col i % 2), rows top to bottom, in
# both tables. Unicode numbers the octants 1..8 and the sextants 1..6 in that
# same order, so BLOCK OCTANT-247 is the pattern with bits 1, 3 and 6 set and
# BLOCK SEXTANT-235 the one with bits 1, 2 and 4. Index a table by the pattern.
#
# Both tables are literal because the obvious construction is wrong in both
# cases: some patterns were already encoded elsewhere, under descriptive names,
# and were not re-encoded when the set was specified. Octants: 230 characters
# at U+1CD00-U+1CDE5 for 256 patterns, 26 inherited. Sextants: 60 at
# U+1FB00-U+1FB3B for 64 patterns, 4 inherited -- SPACE, LEFT HALF BLOCK, RIGHT
# HALF BLOCK and FULL BLOCK. Offset arithmetic with the wrong exclusion set
# produces plausible, wrong glyphs, and past U+1CDE5 it walks into pictograms:
# an early draft rendered U+1CDED BOTTOM HALF LEFT-FACING RUNNER FRAME-1 into
# the middle of a mark.
#
# The inherited characters come from a far older design pass, and fonts
# commonly do not harmonise them with the ones drawn later -- differing weight
# and coverage show as visible seams within a single rendered mark. Do not
# substitute lookalikes: for most of these patterns there is no alternative
# encoding at all.
# ---------------------------------------------------------------------------

OCTANTS = (
    " 𜺨𜺫🮂𜴀▘𜴁𜴂𜴃𜴄▝𜴅𜴆𜴇𜴈▀𜴉𜴊𜴋𜴌🯦𜴍𜴎𜴏𜴐𜴑𜴒𜴓𜴔𜴕𜴖𜴗"   #   0- 31
    "𜴘𜴙𜴚𜴛𜴜𜴝𜴞𜴟🯧𜴠𜴡𜴢𜴣𜴤𜴥𜴦𜴧𜴨𜴩𜴪𜴫𜴬𜴭𜴮𜴯𜴰𜴱𜴲𜴳𜴴𜴵🮅"   #  32- 63
    "𜺣𜴶𜴷𜴸𜴹𜴺𜴻𜴼𜴽𜴾𜴿𜵀𜵁𜵂𜵃𜵄▖𜵅𜵆𜵇𜵈▌𜵉𜵊𜵋𜵌▞𜵍𜵎𜵏𜵐▛"   #  64- 95
    "𜵑𜵒𜵓𜵔𜵕𜵖𜵗𜵘𜵙𜵚𜵛𜵜𜵝𜵞𜵟𜵠𜵡𜵢𜵣𜵤𜵥𜵦𜵧𜵨𜵩𜵪𜵫𜵬𜵭𜵮𜵯𜵰"   #  96-127
    "𜺠𜵱𜵲𜵳𜵴𜵵𜵶𜵷𜵸𜵹𜵺𜵻𜵼𜵽𜵾𜵿𜶀𜶁𜶂𜶃𜶄𜶅𜶆𜶇𜶈𜶉𜶊𜶋𜶌𜶍𜶎𜶏"   # 128-159
    "▗𜶐𜶑𜶒𜶓▚𜶔𜶕𜶖𜶗▐𜶘𜶙𜶚𜶛▜𜶜𜶝𜶞𜶟𜶠𜶡𜶢𜶣𜶤𜶥𜶦𜶧𜶨𜶩𜶪𜶫"   # 160-191
    "▂𜶬𜶭𜶮𜶯𜶰𜶱𜶲𜶳𜶴𜶵𜶶𜶷𜶸𜶹𜶺𜶻𜶼𜶽𜶾𜶿𜷀𜷁𜷂𜷃𜷄𜷅𜷆𜷇𜷈𜷉𜷊"   # 192-223
    "𜷋𜷌𜷍𜷎𜷏𜷐𜷑𜷒𜷓𜷔𜷕𜷖𜷗𜷘𜷙𜷚▄𜷛𜷜𜷝𜷞▙𜷟𜷠𜷡𜷢▟𜷣▆𜷤𜷥█"   # 224-255
)

SEXTANTS = (
    " 🬀🬁🬂🬃🬄🬅🬆🬇🬈🬉🬊🬋🬌🬍🬎🬏🬐🬑🬒🬓▌🬔🬕🬖🬗🬘🬙🬚🬛🬜🬝"   #   0- 31
    "🬞🬟🬠🬡🬢🬣🬤🬥🬦🬧▐🬨🬩🬪🬫🬬🬭🬮🬯🬰🬱🬲🬳🬴🬵🬶🬷🬸🬹🬺🬻█"   #  32- 63
)

MATRIX_SIZE = 5

# Each lattice as (table, sub-rows per character, what a blank cell emits,
# sub-rows of blank above the matrix).
#
# **The blank differs because the widths do.** Entry 0 of either table is
# U+0020, which is genuinely the character for the empty pattern, but it is
# single-width. Sextants render one column, so one space keeps the column
# count; every octant but that one renders two, so a blank mid-line needs two
# spaces or the line falls a column short and the mark skews against the line
# below. The tables stay canonical; the compensation lives here, at emission.
#
# **The padding goes above in both.** Two lines of octants are eight sub-rows
# against the matrix's five and two lines of sextants are six, so there are three
# spare and one. All of them go above, which fills the lower line completely
# with matrix and is what lets the tricolour sit flush against it. For octants
# the upper line then holds only the matrix's top row, and is entirely blank
# whenever that row is, roughly one repository in eight -- keep both lines
# intact anyway, because anything that strips trailing whitespace collapses the
# mark's height. Centring instead puts a partly-empty line under the tricolour.
OCTANT_LATTICE = (OCTANTS, 4, "  ", 3)
SEXTANT_LATTICE = (SEXTANTS, 3, " ", 1)


def parse_matrix(text):
    """A 5x5 matrix from 25 characters, or from five rows separated by commas.

    Filled cells are `#`, `1`, `X` or `x`; anything else is empty.
    """
    rows = text.split(",") if "," in text else [
        text[i:i + MATRIX_SIZE] for i in range(0, len(text), MATRIX_SIZE)]
    if len(rows) != MATRIX_SIZE or any(len(r) != MATRIX_SIZE for r in rows):
        raise ValueError(f"not a {MATRIX_SIZE}x{MATRIX_SIZE} matrix: {text!r}")
    return [[c in "#1Xx" for c in row] for row in rows]


def lattice_lines(matrix, lattice):
    """The matrix drawn on one lattice: three characters per line, two lines.

    One routine for both, because the bit order, the cell width and the
    placement of the padding are the same rule in each -- only the numbers
    differ, and those come in on `lattice`.
    """
    table, sub_rows, blank, top_pad = lattice
    cells_per_line = (MATRIX_SIZE + 1) // 2
    line_count = (MATRIX_SIZE + top_pad + sub_rows - 1) // sub_rows

    def filled(row, col):
        # The lower bound is not redundant -- top_pad makes `row` negative in
        # the padding, and a negative index would wrap to the matrix's bottom.
        return (0 <= row < MATRIX_SIZE and 0 <= col < MATRIX_SIZE
                and bool(matrix[row][col]))

    lines = []
    for line_index in range(line_count):
        chars = []
        for cell in range(cells_per_line):
            pattern = 0
            for bit in range(sub_rows * 2):
                if filled(line_index * sub_rows + bit // 2 - top_pad,
                          cell * 2 + bit % 2):
                    pattern |= 1 << bit
            chars.append(blank if pattern == 0 else table[pattern])
        lines.append("".join(chars))
    return lines


def octant(matrix):
    """The matrix on the 2x4 lattice, two lines.

    The contents of `.identicon/repository-identicon.octant`, one line each.
    """
    return lattice_lines(matrix, OCTANT_LATTICE)


def sextant(matrix):
    """The matrix on the 2x3 lattice, two lines.

    The contents of `.identicon/repository-identicon.sextant`, one line each.
    """
    return lattice_lines(matrix, SEXTANT_LATTICE)


# ---------------------------------------------------------------------------
# The palette
#
# Each colour is anchored on the colour word in the name of the character that
# carries it, and that word is the definition. Red, green and blue take the RGB
# primaries. Orange, purple and brown have no primary reading and take their CSS
# named-colour values.
#
# The name is the anchor, never the installed font: LARGE BLUE SQUARE is
# `#0000FF` whatever a font paints it (the Noto here paints Material Blue 700
# `#1976D2`, and Apple, Twemoji and Windows differ again). A repository must
# produce the same triple for everyone who works on it, so do not sample fonts
# here, and be suspicious of any change that makes the output depend on the
# environment.
#
# Mixtures are averaged in linear light, which is what optical mixing does, and
# compared in Oklab; fixed-lightness HSL, which the identicon's colour comes
# from, clusters badly in the greens.
# ---------------------------------------------------------------------------

# **Every colour exists as a square and as a circle**, which is what lets the
# shape be a channel of its own. Black and white were excluded once, on the
# grounds that their circles are named MEDIUM where every square is LARGE; that
# was overruled after testing, so all nine circle and the shape channel is a
# flat three bits rather than a count of which positions happen to qualify.
PALETTE = (
    ("\U0001F7E5", "\U0001F534", "red",    (0xFF, 0x00, 0x00)),
    ("\U0001F7E7", "\U0001F7E0", "orange", (0xFF, 0xA5, 0x00)),
    ("\U0001F7E8", "\U0001F7E1", "yellow", (0xFF, 0xFF, 0x00)),
    ("\U0001F7E9", "\U0001F7E2", "green",  (0x00, 0xFF, 0x00)),
    ("\U0001F7E6", "\U0001F535", "blue",   (0x00, 0x00, 0xFF)),
    ("\U0001F7EA", "\U0001F7E3", "purple", (0x80, 0x00, 0x80)),
    ("\U0001F7EB", "\U0001F7E4", "brown",  (0xA5, 0x2A, 0x2A)),
    ("⬛",     "⚫",     "black",  (0x00, 0x00, 0x00)),
    ("⬜",     "⚪",     "white",  (0xFF, 0xFF, 0xFF)),
)

SQUARE = "square"
CIRCLE = "circle"

# name -> (square, circle), for the one lookup the renderer does.
GLYPHS = {name: (square, circle) for square, circle, name, _rgb in PALETTE}


def parse_hex(value):
    """`#rrggbb` or `rrggbb` to an (r, g, b) triple of 0-255 ints."""
    text = value.strip().lstrip("#")
    if len(text) != 6:
        raise ValueError(f"not a six-digit hex colour: {value!r}")
    return tuple(int(text[i:i + 2], 16) for i in (0, 2, 4))


def hex_colour(rgb):
    """`#rrggbb`. Public surface -- the vendoring consumers and
    `work-in-progress/` call it."""
    return "#{:02x}{:02x}{:02x}".format(*rgb)


# ---------------------------------------------------------------------------
# The tricolour
#
# **This module renders a tricolour; it does not choose one.** Which three
# colours, in what order, and which of them are circles are all decided in
# `repository-identicon.py` from the seed's digest and the colour map. What
# arrives here is the answer: three (colour name, shape) pairs.
#
# It was the other way round -- a fidelity search over PALETTE picked the
# colours from the drawn `#rrggbb`. That search measured full Oklab distance
# against the nominal primaries, so it compared a mark drawn at lightness 0.60
# against a pure green at 0.87 and called it orange. The colour map replaces
# it, and the search is gone rather than fixed.
# ---------------------------------------------------------------------------

def tricolour(pairs):
    """The three emoji for `pairs`, as one string of three characters.

    Each pair is `(colour name, "square" | "circle")`.
    """
    return "".join(GLYPHS[name][shape == CIRCLE] for name, shape in pairs)


def tricolour_names(pairs):
    """The three colours as `colour` or `colour-circle`, in laid-out order."""
    return tuple(f"{name}{'-circle' if shape == CIRCLE else ''}"
                 for name, shape in pairs)


def selftest():
    """Invariants that hold for any palette and any Unicode host."""
    import unicodedata
    host = tuple(int(p) for p in unicodedata.unidata_version.split(".")[:1])

    for table, size, prefix, drawn, since in (
            (OCTANTS, 256, "BLOCK OCTANT-", 230, (16,)),
            (SEXTANTS, 64, "BLOCK SEXTANT-", 60, (13,))):
        assert len(table) == size, (prefix, len(table))
        assert len(set(table)) == size, f"{prefix} table has duplicates"
        # Re-derive the table from the Unicode database where the host has it,
        # so the literal above is verified rather than trusted.
        if host < since:
            continue
        named = 0
        for pattern, char in enumerate(table):
            try:
                name = unicodedata.name(char)
            except ValueError:
                continue
            if not name.startswith(prefix):
                continue
            named += 1
            bits = 0
            for digit in name[len(prefix):]:
                bits |= 1 << (int(digit) - 1)
            assert bits == pattern, (name, pattern, bits)
        assert named == drawn, f"expected {drawn} {prefix} characters, saw {named}"

    # The sextant patterns encoded elsewhere, by name rather than by codepoint.
    if host >= (13,):
        for pattern, name in ((0, "SPACE"), (0b010101, "LEFT HALF BLOCK"),
                              (0b101010, "RIGHT HALF BLOCK"),
                              (0b111111, "FULL BLOCK")):
            assert unicodedata.name(SEXTANTS[pattern]) == name, pattern

    # The tricolour is rendered, not chosen. Every pair renders to the glyph
    # its shape names, and every colour has both -- the shape channel is a flat
    # three bits because there is no colour that cannot be a circle.
    for square, circle, name, _rgb in PALETTE:
        assert tricolour([(name, SQUARE)] * 3) == square * 3, name
        assert tricolour([(name, CIRCLE)] * 3) == circle * 3, name
        assert square != circle, name
    assert len({g for pair in GLYPHS.values() for g in pair}) == 18, (
        "eighteen glyphs: nine colours, two shapes")

    # Shape and order are both carried, so two marks over the same three
    # colours can still differ.
    assert (tricolour([("blue", SQUARE), ("green", SQUARE), ("blue", SQUARE)])
            != tricolour([("blue", CIRCLE), ("green", SQUARE), ("blue", SQUARE)]))
    assert (tricolour([("blue", SQUARE), ("green", SQUARE), ("blue", SQUARE)])
            != tricolour([("green", SQUARE), ("blue", SQUARE), ("blue", SQUARE)]))

    assert tricolour_names([("blue", CIRCLE), ("green", SQUARE),
                            ("blue", SQUARE)]) == (
        "blue-circle", "green", "blue")

    # Both lattices are lossless, which is the whole reason there is a choice
    # to make: neither loses a cell the other keeps.
    for shape in ("#" * 25, "." * 25, ".#.#.,#...#,.....,#...#,.#.#.",
                  "#...#,.###.,#.#.#,.....,##.##"):
        source = parse_matrix(shape)
        for lattice in (OCTANT_LATTICE, SEXTANT_LATTICE):
            assert _recover(lattice_lines(source, lattice), lattice) == source, (
                shape, lattice[1])

    # A lattice carries no palette glyphs. Composing a lattice with a
    # tricolour is a caller's concern now -- `.txt` and the function that
    # built it are gone -- so what is checked here is that the two vocabularies
    # do not overlap and a caller can tell them apart.
    for shape in ("#" * 25, ".#.#.,#...#,.....,#...#,.#.#."):
        for line in lattice_lines(parse_matrix(shape), SEXTANT_LATTICE):
            assert not any(g in line for pair in GLYPHS.values()
                           for g in pair), line

    # Whatever the padding or the pattern, either lattice is two lines of three
    # cells, and every line is the same number of columns wide -- which is the
    # property the blank exists to preserve. Blanks are one character wide for
    # sextants and two for octants, so a cell count needs the blank width.
    for shape in ("#" * 25, "." * 25, ".#.#.,#...#,.....,#...#,.#.#."):
        for lattice in (OCTANT_LATTICE, SEXTANT_LATTICE):
            blank = lattice[2]
            rendered = lattice_lines(parse_matrix(shape), lattice)
            assert len(rendered) == 2, rendered
            for line in rendered:
                assert line.count(" ") % len(blank) == 0, repr(line)
                cells = (sum(1 for c in line if c != " ")
                         + line.count(" ") // len(blank))
                assert cells == 3, (repr(line), cells)
    return True


def _recover(lines, lattice):
    """The matrix read back out of its rendered lines. For `selftest` only."""
    table, sub_rows, blank, top_pad = lattice
    index = {char: pattern for pattern, char in enumerate(table)}
    matrix = [[False] * MATRIX_SIZE for _ in range(MATRIX_SIZE)]
    for line_index, line in enumerate(lines):
        cells = []
        while line:
            if line.startswith(blank):
                cells.append(0)
                line = line[len(blank):]
            else:
                cells.append(index[line[0]])
                line = line[1:]
        for cell, pattern in enumerate(cells):
            for bit in range(sub_rows * 2):
                if not pattern & (1 << bit):
                    continue
                row = line_index * sub_rows + bit // 2 - top_pad
                col = cell * 2 + bit % 2
                assert 0 <= row < MATRIX_SIZE and 0 <= col < MATRIX_SIZE, (row, col)
                matrix[row][col] = True
    return matrix


def _main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__.strip().splitlines()[0])
        print("\nusage: text-identicon.py --selftest")
        print("       text-identicon.py [--octant] <#rrggbb> <matrix>")
        print("\n  <matrix>     25 characters, or five rows separated by commas;")
        print("             `#`, `1`, `X` or `x` is a filled cell.")
        print("  --octant   draw on the 2x4 lattice; the default is 2x3.")
        return 0
    lattice = SEXTANT_LATTICE
    if argv and argv[0] == "--octant":
        lattice, argv = OCTANT_LATTICE, argv[1:]
    if argv and argv[0] == "--selftest":
        selftest()
        print("selftest: ok")
        return 0
    if len(argv) != 2:
        print("need a colour and a matrix; --help for the spelling")
        return 2
    print(text(parse_matrix(argv[1]), parse_hex(argv[0]), lattice))
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(_main(sys.argv[1:]))

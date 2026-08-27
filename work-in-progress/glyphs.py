#!/usr/bin/env python3
"""The emoji squares and circles as Noto paints them, as plain SVG paths.

**A flat rectangle is not what the reader sees.** The sheets drew one colour per
square, taken from the palette, and on a dark ground the black square vanished
and on a light one the white square did. That is not what happens in a terminal
or a chat window, because Noto Color Emoji does not paint a flat square: every
glyph is three layers, a darker rim, the body, and a lighter highlight. `⬛` is
not black at all -- it is `#575757` over `#424242` under `#787878` -- and `⬜`
carries a `#bdbdbd` rim, which is exactly why both survive either ground.

So the sheets were lying about the one thing they exist to show. This reads the
real outlines out of the font and emits them as ordinary SVG paths: no font
embedding, no dependence on what the viewer has installed, and the same shapes
the emoji font would have drawn.

The alternative was embedding a subset of the font, which is smaller to write
and worse to rely on -- COLRv1 support varies by renderer, and a sheet that
looks right here and wrong in a browser is the failure this is meant to end.
"""

import pathlib

from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.misc.transform import Transform

FONT = pathlib.Path("/usr/share/fonts/google-noto-color-emoji-fonts/"
                    "Noto-COLRv1.ttf")

# The nine squares and the seven circles, by name, matching the palette.
SQUARES = {"red": 0x1F7E5, "orange": 0x1F7E7, "yellow": 0x1F7E8,
           "green": 0x1F7E9, "blue": 0x1F7E6, "purple": 0x1F7EA,
           "brown": 0x1F7EB, "black": 0x2B1B, "white": 0x2B1C}
CIRCLES = {"red": 0x1F534, "orange": 0x1F7E0, "yellow": 0x1F7E1,
           "green": 0x1F7E2, "blue": 0x1F535, "purple": 0x1F7E3,
           "brown": 0x1F7E4}

_FONT = None
_CACHE = {}


def _font():
    global _FONT
    if _FONT is None:
        _FONT = TTFont(FONT)
    return _FONT


def _layers(codepoint):
    """`[(glyph name, transform, #rrggbb)]` for one emoji, outermost first.

    The layers are returned as glyph references rather than as finished paths
    because two callers need them drawn through different pens -- one to get
    the outline, one to get the bounding box. The base glyph itself has no
    outline at all; everything is in the layers, which is what made a bounds
    check on the base glyph come back empty.

    Walks the COLRv1 paint tree. Only the formats this font actually uses for
    these sixteen glyphs are handled -- layers, solid fills, glyph references
    and affine transforms -- and anything else raises rather than being drawn
    wrongly and quietly.
    """
    font = _font()
    palette = font["CPAL"].palettes[0]
    colr = font["COLR"].table
    records = {r.BaseGlyph: r
               for r in colr.BaseGlyphList.BaseGlyphPaintRecord}
    glyphs = font.getGlyphSet()
    name = font.getBestCmap()[codepoint]
    out = []

    def solid(paint):
        if paint.Format != 2:
            raise ValueError(f"expected a solid fill, got format {paint.Format}")
        c = palette[paint.PaletteIndex]
        return f"#{c.red:02x}{c.green:02x}{c.blue:02x}"

    def walk(paint, transform):
        fmt = paint.Format
        if fmt == 1:                                  # a list of layers
            for i in range(paint.FirstLayerIndex,
                           paint.FirstLayerIndex + paint.NumLayers):
                walk(colr.LayerList.Paint[i], transform)
        elif fmt == 10:                               # a glyph, with a fill
            out.append((paint.Glyph, transform, solid(paint.Paint)))
        elif fmt == 12:                               # an affine transform
            t = paint.Transform
            walk(paint.Paint, transform.transform(
                (t.xx, t.yx, t.xy, t.yy, t.dx, t.dy)))
        else:
            raise ValueError(f"unhandled paint format {fmt} in {name}")

    walk(records[name].Paint, Transform())
    return out


def _cached(codepoint):
    if codepoint not in _CACHE:
        _CACHE[codepoint] = _layers(codepoint)
    return _CACHE[codepoint]


def _bounds():
    """One box for every glyph, so a square and a circle come out the same size.

    Taken over all sixteen together rather than per glyph. Normalising each to
    its own box would make the circles as wide as the squares, and they are
    drawn slightly smaller on purpose.
    """
    from fontTools.pens.boundsPen import BoundsPen
    if "bounds" not in _CACHE:
        glyphs = _font().getGlyphSet()
        lo = [1e9, 1e9]
        hi = [-1e9, -1e9]
        for cp in list(SQUARES.values()) + list(CIRCLES.values()):
            for glyph, transform, _colour in _cached(cp):
                pen = BoundsPen(glyphs)
                glyphs[glyph].draw(TransformPen(pen, transform))
                if pen.bounds is None:
                    continue
                x0, y0, x1, y1 = pen.bounds
                lo[0], lo[1] = min(lo[0], x0), min(lo[1], y0)
                hi[0], hi[1] = max(hi[0], x1), max(hi[1], y1)
        _CACHE["bounds"] = (lo[0], lo[1], hi[0], hi[1])
    return _CACHE["bounds"]


def ident(name, circle):
    """The id a glyph is defined under, for `defs` and `use`."""
    return f"g-{name}-{'c' if circle and name in CIRCLES else 's'}"


def defs(palette=None):
    """Every glyph once, normalised into a unit box, for a `<defs>` block.

    A sheet draws twelve hundred of these and there are sixteen distinct ones,
    so writing the outlines out each time made the file 1.8MB of repetition.
    Defined once and referenced, it is a fiftieth of that and identical on the
    page.

    With `palette` -- a mapping of square name to `#rrggbb` -- only the
    silhouette is drawn, filled with the colour given. That is the honest way
    to render the developer-weighted average from `emoji-square-colours.md`:
    those values are one body colour per square, sampled from the middle of
    each glyph across seven vendor sets. There is no averaged rim and no
    averaged highlight, because the vendors do not agree on having them -- Noto
    paints three layers, Twemoji paints a flat fill. Inventing a rim from
    Noto's ratios would be drawing a seventh of the data as though it were all
    of it.
    """
    glyphset = _font().getGlyphSet()
    x0, y0, x1, y1 = _bounds()
    scale = 1.0 / max(x1 - x0, y1 - y0)
    parts = []
    for circle in (False, True):
        table = CIRCLES if circle else SQUARES
        for name in table:
            shift = (f"translate({-x0 * scale:.6f} {y1 * scale:.6f}) "
                     f"scale({scale:.8f} {-scale:.8f})")
            parts.append(f'<g id="{ident(name, circle)}" '
                         f'transform="{shift}">')
            layers = _cached(table[name])
            if palette is not None:
                layers = [(layers[0][0], layers[0][1], palette[name])]
            for glyph, transform, colour in layers:
                pen = SVGPathPen(glyphset)
                glyphset[glyph].draw(TransformPen(pen, transform))
                parts.append(f'<path d="{pen.getCommands()}" fill="{colour}"/>')
            parts.append("</g>")
    return "<defs>" + "".join(parts) + "</defs>"


def use(name, circle, x, y, size):
    """A reference to a glyph from `defs`, in a `size` box at x, y."""
    return (f'<use href="#{ident(name, circle)}" '
            f'transform="translate({x:.2f} {y:.2f}) scale({size:.4f})"/>')


def svg(name, circle, x, y, size):
    """The glyph as SVG, drawn into a `size` box with its top-left at x, y.

    Self-contained, for a caller drawing one. Use `defs` and `use` for a sheet.
    """
    table = CIRCLES if circle and name in CIRCLES else SQUARES
    layers = _cached(table[name])
    glyphs = _font().getGlyphSet()
    x0, y0, x1, y1 = _bounds()
    scale = size / max(x1 - x0, y1 - y0)
    # Font y runs up and SVG y runs down, so the vertical axis is flipped and
    # the origin moved to the box's top-left.
    shift = (f"translate({x - x0 * scale:.3f} {y + y1 * scale:.3f}) "
             f"scale({scale:.6f} {-scale:.6f})")
    parts = [f'<g transform="{shift}">']
    for glyph, transform, colour in layers:
        pen = SVGPathPen(glyphs)
        glyphs[glyph].draw(TransformPen(pen, transform))
        parts.append(f'<path d="{pen.getCommands()}" fill="{colour}"/>')
    parts.append("</g>")
    return "".join(parts)


def _selftest():
    for name in SQUARES:
        layers = _cached(SQUARES[name])
        assert layers, name
        print(f"  {name:<7} square  {len(layers)} layers  "
              f"{' '.join(c for _g, _t, c in layers)}")
    for name in CIRCLES:
        layers = _cached(CIRCLES[name])
        print(f"  {name:<7} circle  {len(layers)} layers  "
              f"{' '.join(c for _g, _t, c in layers)}")
    print(f"common box {tuple(round(v) for v in _bounds())}")
    body = svg("white", False, 0.0, 0.0, 10.0)
    assert body.count("<path") == 3, body[:200]
    assert "#bdbdbd" in body, "the white square lost its rim"
    assert "#424242" in svg("black", False, 0, 0, 10), "black lost its body"
    print(f"white square at 10px: {len(body)} chars of SVG")


if __name__ == "__main__":
    _selftest()

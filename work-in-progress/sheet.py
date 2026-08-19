#!/usr/bin/env python3
"""The hue-sorted contact sheet: 400 marks, twenty by twenty, labelled A-T / 1-20.

    python3 sheet.py sheet6.svg            the current mapping, shapes included
    python3 sheet.py --squares out.svg     squares only, as sheets 1 to 4 were
    python3 sheet.py --sheet5 out.svg      the mapping sheet 5 was rendered with
    python3 sheet.py --verify              reproduce sheet4.svg and compare

Sheets 1 to 4 were rendered by code that lived in a session scratchpad on tmpfs
and did not survive it. This is that code, recovered from `sheet4.svg` itself
and committed -- `--verify` reproduces that file byte for byte, which is what
makes the recovery a claim rather than an assertion.

The layout is deliberately unchanged from sheet 4, down to the pixel, because
the sheets are only useful as a series: what a change did is legible by flipping
between two of them and in essentially no other way. Every tile is the same
sample in the same place, so anything that moves is the mapping.
"""

import importlib.util
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
anchored = load(str(S / "anchored2.py"), "a2")     # what sheets 4 and 5 used
current = load(str(S / "anchored3.py"), "a3")      # the corrected purple band
shaped = load(str(S / "shaped.py"), "shaped")

# ---------------------------------------------------------------------------
# Geometry, recovered from sheet4.svg. Every constant here is measured off that
# file rather than chosen, so the series stays comparable.
# ---------------------------------------------------------------------------

COLS, ROWS = 20, 20
WIDTH, HEIGHT = 866, 998

CELL = 5                     # one grid cell
GRID_X0, GRID_Y0 = 27, 18    # top-left cell of tile A1
PITCH_X, PITCH_Y = 42, 49    # tile to tile

SWATCH = 8                   # one square of the triple
SWATCH_PITCH = 10            # so a two-pixel gap between them
SWATCH_X0, SWATCH_Y0 = 26, 47

LABEL_COL_X0, LABEL_COL_Y = 40, 12
LABEL_ROW_X, LABEL_ROW_Y0 = 18, 36

STROKE = 'stroke="#ddd" stroke-width="0.5"'


def label_row_y(row):
    """Baseline of a row's number.

    The alternating 50/48 step is reproduced from sheet4.svg, not derived. The
    marks themselves sit on an exact 49 pitch; only the labels wobble, and they
    are kept wrong rather than corrected so the series diffs cleanly.
    """
    return LABEL_ROW_Y0 + PITCH_Y * row + (row % 2)


def samples():
    """The 400 pinned samples, hue-sorted -- the order the sheet is laid out in."""
    out = []
    for line in (S / "sample.tsv").read_text().splitlines():
        f = line.split("\t")
        rgb = (int(f[3]), int(f[4]), int(f[5]))
        out.append({
            "key": f[0],
            "grid": [[c == "1" for c in row] for row in f[2].split(",")],
            "rgb": rgb,
            "hue": anchored.hue_of(rgb),
        })
    out.sort(key=lambda d: d["hue"])
    return out


def tile(out, item, col, row, with_shapes, mapping):
    """One identicon and the triple beneath it."""
    gx0 = GRID_X0 + PITCH_X * col
    gy0 = GRID_Y0 + PITCH_Y * row
    fill = text.hex_colour(item["rgb"])
    for gy in range(5):
        for gx in range(5):
            if not item["grid"][gy][gx]:
                continue
            out.append(f'<rect x="{gx0 + gx * CELL}" y="{gy0 + gy * CELL}" '
                       f'width="{CELL}" height="{CELL}" fill="{fill}"/>')

    arranged = mapping.triple(item["rgb"])
    flags = shaped.shapes(arranged, item["rgb"]) if with_shapes else (False,) * 3
    sx0 = SWATCH_X0 + PITCH_X * col
    sy = SWATCH_Y0 + PITCH_Y * row
    for k, (index, circle) in enumerate(zip(arranged, flags)):
        colour = "#{:02x}{:02x}{:02x}".format(*text.PALETTE[index][3])
        x = sx0 + k * SWATCH_PITCH
        if circle:
            r = SWATCH / 2
            out.append(f'<circle cx="{x + r:g}" cy="{sy + r:g}" r="{r:g}" '
                       f'fill="{colour}" {STROKE}/>')
        else:
            out.append(f'<rect x="{x}" y="{sy}" width="{SWATCH}" '
                       f'height="{SWATCH}" fill="{colour}" {STROKE}/>')


def render(with_shapes=True, mapping=None):
    mapping = current if mapping is None else mapping
    items = samples()
    assert len(items) == COLS * ROWS, len(items)

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" '
           f'height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">',
           f'<rect width="{WIDTH}" height="{HEIGHT}" fill="#ffffff"/>',
           '<g font-family="monospace" font-size="10" fill="#666">']
    for col in range(COLS):
        out.append(f'<text x="{LABEL_COL_X0 + PITCH_X * col}" y="{LABEL_COL_Y}" '
                   f'text-anchor="middle">{chr(ord("A") + col)}</text>')
    for row in range(ROWS):
        out.append(f'<text x="{LABEL_ROW_X}" y="{label_row_y(row)}" '
                   f'text-anchor="end">{row + 1}</text>')
    out.append('</g>')

    for index, item in enumerate(items):
        tile(out, item, index % COLS, index // COLS, with_shapes, mapping)

    out.append('</svg>')
    # No trailing newline: sheet4.svg has none, and --verify is byte-exact.
    return "\n".join(out)


def verify():
    """Reproduce sheet4.svg from scratch and compare it with the committed file."""
    want = (S / "sheet4.svg").read_text()
    got = render(with_shapes=False, mapping=anchored)
    if got == want:
        print(f"sheet4.svg reproduced exactly: {len(got)} bytes")
        return 0
    print(f"MISMATCH: {len(got)} bytes rendered against {len(want)} committed")
    a, b = want.splitlines(), got.splitlines()
    for n, (x, y) in enumerate(zip(a, b), 1):
        if x != y:
            print(f"  first difference, line {n}\n    committed {x}\n    rendered  {y}")
            break
    if len(a) != len(b):
        print(f"  line counts differ: {len(a)} committed, {len(b)} rendered")
    return 1


def main(argv):
    if argv[:1] == ["--verify"]:
        return verify()
    with_shapes, mapping, name = True, current, "anchored3"
    while argv and argv[0].startswith("--"):
        if argv[0] == "--squares":
            with_shapes = False
        elif argv[0] == "--sheet5":
            mapping, name = anchored, "anchored2"
        else:
            print(f"unknown option {argv[0]}", file=sys.stderr)
            return 2
        argv = argv[1:]
    if not argv:
        print(__doc__.strip().splitlines()[2], file=sys.stderr)
        return 2
    path = pathlib.Path(argv[0])
    if not path.is_absolute():
        path = S / path
    svg = render(with_shapes, mapping)
    path.write_text(svg)
    print(f"{path} {len(svg)} bytes, {name}, shapes {'on' if with_shapes else 'off'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

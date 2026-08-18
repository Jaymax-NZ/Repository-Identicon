#!/usr/bin/env python3
"""One row of the hue-sorted contact sheet, enlarged, plus its numbers.

    python3 row.py <row 1-20>

Renders the row at 3x the sheet's scale so the arrangement is readable, and
prints the assignment behind each tile: hue, hex, the multiset the fidelity
search chose, the order `arrange` put them in, and the resulting error.
"""

import importlib.util
import pathlib
import struct
import sys
import zlib

D = "/home/justin/Code/Projects/Repository-Identicon/"
S = pathlib.Path(__file__).parent


def load(name, module):
    spec = importlib.util.spec_from_file_location(module, D + name)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


t = load("text-identicon.py", "t")


def hue(rgb):
    r, g, b = rgb
    mx, mn = max(rgb), min(rgb)
    if mx == mn:
        return 0.0
    d = mx - mn
    h = ((g - b) / d) % 6 if mx == r else ((b - r) / d + 2 if mx == g else (r - g) / d + 4)
    return h * 60


def items():
    rows = [l.split("\t") for l in (S / "sample.tsv").read_text().splitlines()]
    out = []
    for r in rows:
        fg = (int(r[3]), int(r[4]), int(r[5]))
        out.append({
            "key": r[0],
            "grid": [[c == "1" for c in row] for row in r[2].split(",")],
            "rgb": fg,
            "hue": hue(fg),
        })
    out.sort(key=lambda d: d["hue"])
    return out


def render(row, path):
    CELL, BORDER = 12, 3
    ICON = 5 * CELL + 2 * BORDER
    SW, SH, SGAP = 20, 20, 3
    TILE_W = max(ICON, 3 * SW + 2 * SGAP)
    TILE_H = ICON + 8 + SH
    PAD = 12
    W = len(row) * TILE_W + (len(row) + 1) * PAD
    H = TILE_H + 2 * PAD
    buf = [[(255, 255, 255)] * W for _ in range(H)]

    for idx, d in enumerate(row):
        ox = PAD + idx * (TILE_W + PAD)
        oy = PAD
        gx0 = ox + (TILE_W - ICON) // 2
        for gy in range(5):
            for gx in range(5):
                if not d["grid"][gy][gx]:
                    continue
                for dy in range(CELL):
                    for dx in range(CELL):
                        buf[oy + BORDER + gy * CELL + dy][gx0 + BORDER + gx * CELL + dx] = d["rgb"]
        swatches = [t.PALETTE[k][3] for k in t.triple(d["rgb"])]
        sx0 = ox + (TILE_W - (3 * SW + 2 * SGAP)) // 2
        sy = oy + ICON + 8
        for k, colour in enumerate(swatches):
            for dy in range(SH):
                for dx in range(SW):
                    buf[sy + dy][sx0 + k * (SW + SGAP) + dx] = colour

    raw = b"".join(b"\x00" + b"".join(bytes(p) for p in line) for line in buf)

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 9))
           + chunk(b"IEND", b""))
    path.write_bytes(png)
    return W, H


def main(argv):
    n = int(argv[0])
    row = items()[(n - 1) * 20:n * 20]
    path = S / f"row-{n:02d}.png"
    w, h = render(row, path)
    print(f"row {n}: hues {row[0]['hue']:.1f} to {row[-1]['hue']:.1f} degrees   {path} {w}x{h}")
    print()
    print(f"{'#':>3} {'hue':>6} {'hex':>8}  {'chosen (multiset)':<24} {'as laid out':<24} {'dE':>6}")
    for i, d in enumerate(row):
        detail = t.triple_detail(d["rgb"])
        chosen = " ".join(t.PALETTE[k][1] for k in detail["indices"])
        laid = " ".join(t.PALETTE[k][1] for k in detail["arranged"])
        print(f"{(n - 1) * 20 + i + 1:>3} {d['hue']:>6.1f} {t.hex_colour(d['rgb']):>8}  "
              f"{chosen:<24} {laid:<24} {detail['delta_e']:>6.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

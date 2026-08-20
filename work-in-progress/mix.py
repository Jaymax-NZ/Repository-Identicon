#!/usr/bin/env python3
"""What does a triple actually mix to, and what colour would it be naming?

    python3 mix.py "yellow green orange"        one candidate
    python3 mix.py "yellow green orange" "brown orange yellow"
    python3 mix.py --hue 165                    what the target says there
    python3 mix.py --all                        every division in target.tsv

Writes `mixes.svg` and prints the same thing as a table.

**How accurate is accurate(ish).** The mix is the mean of the three squares in
**linear light**, which is what optical mixing does when three patches are small
enough or far enough away to fuse -- averaging the sRGB numbers directly would
be wrong and would come out too dark. The comparison is then made in Oklab,
which is near enough perceptually uniform that a distance means something.

Two honest caveats. The squares are their **Unicode names**, so yellow is
`#ffff00` -- no font paints that, and the installed Noto renders these
noticeably differently. And the gamut is identicon.js's own, fixed at
saturation 0.7, which no nominal palette colour ever reaches. So the mix is a
faithful answer to "what do these three average to", not a prediction of what
your screen will show.

The useful column is the last one. `names` is the gamut hue whose colour the
mix lands closest to -- what the triple would be claiming if you saw it cold.
With `--hue` or `--all` it also reports the distance to the colour the division
is actually supposed to name, which is the number that says whether a candidate
triple is honest.
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
wheel = load(str(S / "wheel.py"), "wheel")

INDEX = {name: k for k, (_e, name, _cp, _rgb) in enumerate(text.PALETTE)}
NOMINAL = {name: "#{:02x}{:02x}{:02x}".format(*rgb)
           for _e, name, _cp, rgb in text.PALETTE}


# Deferred to wheel.py so the two never disagree -- it also carries the
# white-weighting calibration.
mix_rgb = wheel.mix_rgb


def oklab(rgb):
    return text._oklab(tuple(text._linear(v) for v in rgb))


def distance(a, b):
    return math.dist(oklab(a), oklab(b))


# Deferred to wheel.py, which owns the definition. Matching by smallest Oklab
# distance was wrong -- a blend is always lighter and duller than the gamut, so
# proximity picked on lightness and put blues in the cyans. It matches on hue.
nearest_gamut = wheel.nearest_gamut


def analyse(names, hue=None, number=None):
    mixed = mix_rgb(names)
    near_hue, near_rgb, near_d = nearest_gamut(mixed)
    row = {
        "names": tuple(names),
        "mix": mixed,
        "mix_hex": text.hex_colour(mixed),
        "reads_as_hue": near_hue,
        "reads_as": near_rgb,
        "reads_d": near_d,
        "hue": hue,
        "n": number,
    }
    if hue is not None:
        want = wheel.gamut_at(hue)
        row["want"] = want
        row["want_hex"] = text.hex_colour(want)
        row["want_d"] = distance(mixed, want)
    return row


# ---------------------------------------------------------------------------

SW, GAP, PAD = 34, 6, 16
ROW = SW + 14
LABEL_W = 250


def render(rows):
    width = LABEL_W + 3 * (SW + GAP) + 30 + SW + 30 + SW + 150
    height = PAD * 2 + len(rows) * ROW + 26
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
           f'height="{height}" viewBox="0 0 {width} {height}">',
           f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
           f'<g font-family="monospace" font-size="10" fill="#555">']

    x_sw = LABEL_W
    x_mix = x_sw + 3 * (SW + GAP) + 24
    x_want = x_mix + SW + 30
    out.append(f'<text x="{x_sw}" y="{PAD}">the three squares</text>')
    out.append(f'<text x="{x_mix}" y="{PAD}">mixes to</text>')
    out.append(f'<text x="{x_want}" y="{PAD}">reads as / wanted</text>')

    for i, r in enumerate(rows):
        y = PAD + 8 + i * ROW
        label = " ".join(r["names"])
        if r["hue"] is not None:
            label = f'{r["hue"]:.0f}  {label}'
        if r.get("n") is not None:
            label = f'#{r["n"]}  {label}'
        out.append(f'<text x="{PAD}" y="{y + SW * 0.65:.0f}">{label}</text>')
        for k, n in enumerate(r["names"]):
            out.append(f'<rect x="{x_sw + k * (SW + GAP)}" y="{y}" width="{SW}" '
                       f'height="{SW}" fill="{NOMINAL[n]}" stroke="#999" '
                       f'stroke-width="0.5"/>')
        out.append(f'<text x="{x_sw + 3 * (SW + GAP) + 4}" y="{y + SW * 0.65:.0f}">=</text>')
        out.append(f'<rect x="{x_mix}" y="{y}" width="{SW}" height="{SW}" '
                   f'fill="{r["mix_hex"]}" stroke="#999" stroke-width="0.5"/>')
        out.append(f'<rect x="{x_want}" y="{y}" width="{SW}" height="{SW}" '
                   f'fill="{text.hex_colour(r["reads_as"])}" stroke="#999" '
                   f'stroke-width="0.5"/>')
        note = (f'{r["mix_hex"]}  reads as hue {r["reads_as_hue"]:.0f} '
                f'(dE {r["reads_d"]:.3f})')
        if r["hue"] is not None:
            note += f'   want dE {r["want_d"]:.3f}'
            out.append(f'<rect x="{x_want + SW + 6}" y="{y}" width="{SW}" '
                       f'height="{SW}" fill="{r["want_hex"]}" stroke="#999" '
                       f'stroke-width="0.5"/>')
        out.append(f'<text x="{x_want + 2 * SW + 16}" y="{y + SW * 0.65:.0f}">{note}</text>')

    out.append('</g></svg>')
    return "\n".join(out)


def report(rows):
    head = f'{"triple":34} {"mixes to":9} {"reads as":>9} {"dE":>7}'
    if any(r["hue"] is not None for r in rows):
        head += f' {"want":>9} {"dE":>7}'
    print(head)
    for r in rows:
        label = " ".join(r["names"])
        if r["hue"] is not None:
            label = f'{r["hue"]:>5.0f}  {label}'
        line = (f'{label:34} {r["mix_hex"]:9} '
                f'{r["reads_as_hue"]:>8.0f}° {r["reads_d"]:>7.3f}')
        if r["hue"] is not None:
            line += f' {r["want_hex"]:>9} {r["want_d"]:>7.3f}'
        print(line)


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 0

    rows = []
    if "--unplaced-three" in argv:
        used = {wheel.multiset(n) for _h, n, _o in wheel.read_target()}
        picks = []
        for n, names, status in wheel.read_bench():
            if status != "offered" or len(set(names)) < 3:
                continue
            if wheel.multiset(names) in used:
                continue
            picks.append((wheel.nearest_gamut(mix_rgb(names))[0], n, names))
        for _h, n, names in sorted(picks):
            rows.append(analyse(names, number=n))
    elif "--all" in argv:
        for hue, names, _origin in wheel.read_target():
            rows.append(analyse(names, hue))
    elif "--hue" in argv:
        want = float(argv[argv.index("--hue") + 1])
        for hue, names, _origin in wheel.read_target():
            if abs(hue - want) < 1e-6:
                rows.append(analyse(names, hue))
        if not rows:
            raise SystemExit(f"no division at hue {want}")
    else:
        for spec in argv:
            names = spec.replace(",", " ").split()
            if len(names) != 3:
                raise SystemExit(f"need three colour names, got {spec!r}")
            for n in names:
                if n not in INDEX:
                    raise SystemExit(f"not a palette colour: {n!r}  "
                                     f"({', '.join(INDEX)})")
            rows.append(analyse(names))

    report(rows)
    path = S / "mixes.svg"
    path.write_text(render(rows))
    print(f"\n{path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

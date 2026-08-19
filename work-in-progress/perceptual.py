#!/usr/bin/env python3
"""Perceptual constraints on a triple, so iterating needs no human eyes.

Justin judged three rows by looking and rejected them for reasons that turn out
to be one rule and a half:

  row 5   "you cant really mix green and red. red and purple somewhat works"
  row 12  "blue and orange are famous for being the best example of an
           impossible colour ... outside any gamut accessible to humans"
  row 11  "the light blues would be blue-white-white ... black here is beyond
           strange"

The first two are the opponent-process axes: red-green and blue-yellow are
antagonistic channels in human vision, so no colour is reddish-green or
bluish-yellow, and a triple pairing them shows two stops rather than one colour.
Orange is a red-yellow blend, so orange-blue is the same violation. Red and
purple sit 60 degrees apart and read as one family, which is exactly what he
said.

So a single SPAN rule reproduces all three chromatic judgements: no two
chromatic squares in a triple may sit more than MAX_SPAN degrees apart.

The third is a lightness rule, not a hue one. Black and white are not colours
here, they are modifiers, and they are only honest when the target is actually
dark or actually light. `yellow yellow black` for #d9d926 -- one of the
brightest colours in the gamut -- is the case he called beyond strange.

Nothing here needs a font, a screen, or an opinion. Run it against any candidate
mapping and it will say which of these it breaks and how often.
"""

import colorsys
import importlib.util

D = "/home/justin/Code/Projects/Repository-Identicon/"


def load(name, module):
    spec = importlib.util.spec_from_file_location(module, D + name)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


identicon = load("repository-identicon.py", "i")
text = load("text-identicon.py", "t")

# **Not a span rule.** Span was tried and is wrong: red-green is 120 degrees and
# Justin rejected it, blue-green is also 120 degrees and he wants it. Same
# angle, opposite verdict, so the geometry is not what decides.
#
# What decides is opponency. Red-green and blue-yellow are antagonistic channels
# in human vision, so no colour is reddish-green or yellowish-blue and a triple
# containing one shows two stops rather than one colour. Teal is not in that
# class -- it is an ordinary colour -- and neither is red-purple.
#
# Orange is red plus yellow, so it inherits yellow's quarrel with blue, which is
# the pair Justin called the clearest example.
#
# Listed rather than derived, because this is biology and the list is short.
OPPONENTS = {
    frozenset(("red", "green")),
    frozenset(("yellow", "blue")),
    frozenset(("orange", "blue")),
}

# A run is allowed to be wide if something sits between: red-purple-blue spans
# 120 degrees but reads as a gradient, because purple bridges it. So the check
# is on the largest gap between *adjacent* members, not on the total extent.
MAX_GAP = 125.0

# Relative luminance, ITU-R BT.709. How strong a claim an achromatic square
# makes depends on how many of them there are, so the threshold does too.
#
# **Two of them assert.** Two blacks say the target is at the dark end of the
# gamut and two whites say it is at the light end, so they answer to DARK and
# LIGHT. `purple white white` on luminance 0.29 is the case that fails here.
#
# **One of them tints.** A single achromatic among two chromatics shades the
# mix rather than claiming anything about where the colour sits, and reads
# honestly almost anywhere -- `blue purple white` on 0.28 is a violet with a
# lift, not a claim that violet is light. It answers only to the far end of the
# gamut, five hundredths inside each extreme, which is TINT_DARK and TINT_LIGHT.
#
# This replaces a per-hue exception. A rule naming one colour is a rule that has
# stopped explaining anything, and the count is what was actually doing the work.
DARK = 0.33
LIGHT = 0.58
TINT_DARK = 0.75
TINT_LIGHT = 0.25

ACHROMATIC = {"black", "white"}

# Multisets rejected outright, by eye, for reasons no threshold captures. Keyed
# by the sorted names so order and arrangement cannot smuggle one past.
FORBIDDEN = {
    ("black", "black", "purple"):
        "two blacks take purple past dark and into black; blue darkens it "
        "without obliterating it",
}
# `purple white white` needs no entry here: two whites on luminance 0.29 fails
# the LIGHT rule already. `purple purple white` is fine and stays -- Justin's
# correction, 2026-08-19, against an earlier guess of mine that forbade it.


def luminance(rgb):
    r, g, b = (v / 255 for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def hue_of(rgb):
    return colorsys.rgb_to_hls(*[v / 255 for v in rgb])[0] * 360


def separation(a, b):
    d = abs(a - b) % 360
    return min(d, 360 - d)


def chromatic(name, rgb):
    """Is this square carrying a hue at all? Black and white never do."""
    if name in ACHROMATIC:
        return False
    return colorsys.rgb_to_hls(*[v / 255 for v in rgb])[2] > 0.05


def violations(rgb, indices):
    """Every rule the triple breaks for this target colour."""
    out = []
    squares = [(text.PALETTE[k][1], text.PALETTE[k][3]) for k in indices]
    names = [n for n, _ in squares]

    for a in set(names):
        for b in set(names):
            if a != b and frozenset((a, b)) in OPPONENTS:
                out.append(f"opponent {a} with {b}")

    # Largest gap between adjacent chromatic members, going round the circle.
    hues = sorted({hue_of(c) for n, c in squares if chromatic(n, c)})
    if len(hues) > 1:
        gaps = [hues[k + 1] - hues[k] for k in range(len(hues) - 1)]
        gaps.append(360 - hues[-1] + hues[0])
        gaps.sort()
        # The largest gap is the arc the run does *not* cover; the run's own
        # widest internal step is the next one down.
        widest = gaps[-2]
        if widest > MAX_GAP:
            out.append(f"gap {widest:.0f} deg inside the run")

    lum = luminance(rgb)
    names = [n for n, _ in squares]

    forbidden = tuple(sorted(names))
    if forbidden in FORBIDDEN:
        out.append(f"forbidden {' '.join(forbidden)}: {FORBIDDEN[forbidden]}")

    blacks, whites = names.count("black"), names.count("white")
    if blacks >= 2 and lum > DARK:
        out.append(f"two blacks on a target of luminance {lum:.2f}")
    elif blacks == 1 and lum > TINT_DARK:
        out.append(f"black on a target of luminance {lum:.2f}")
    if whites >= 2 and lum < LIGHT:
        out.append(f"two whites on a target of luminance {lum:.2f}")
    elif whites == 1 and lum < TINT_LIGHT:
        out.append(f"white on a target of luminance {lum:.2f}")
    return out


def gamut():
    """Every colour identicon.js can produce, once each."""
    MAX = 0xFFFFFFF
    seen, out = set(), []
    for k in range(0, MAX, MAX // 20000):
        rgb = tuple(identicon._quantise(v)
                    for v in identicon._hsl_to_rgb(k / MAX,
                                                   identicon.SATURATION,
                                                   identicon.LIGHTNESS))
        if rgb not in seen:
            seen.add(rgb)
            out.append(rgb)
    return out


# Triples Justin has said should exist, by eye, with where he saw them. A
# checker that only rejects can never notice an absence: green-blue went missing
# for three iterations because nothing ever emitted it, so nothing ever failed.
# These are the other half -- what must be reachable somewhere in the gamut.
REQUIRED = [
    (("orange", "orange", "yellow"), "3K-4B"),
    (("yellow", "yellow", "green"), "from 4Q"),
    (("green", "green", "blue"), "the blue-greens"),
    (("green", "blue", "blue"), "the blue-greens"),
    (("white", "white", "green"), "works: green is neutral enough"),
    (("red", "black", "black"), "narrow, at the darkest reds"),
    (("blue", "black", "purple"), "the dark blue-purples"),
    (("brown", "orange", "yellow"), "a whole possibility class"),
    (("red", "red", "black"), "darkest reds"),
    (("blue", "blue", "black"), "darkest blues"),
    (("blue", "white", "white"), "the light blues"),
    (("blue", "purple", "white"), "scope around Q16 on sheet 5"),
]


def coverage(chooser):
    """Which required triples the mapping never produces."""
    produced = set()
    for rgb in gamut():
        produced.add(tuple(sorted(text.PALETTE[k][1] for k in chooser(rgb))))
    missing = [(want, why) for want, why in REQUIRED
               if tuple(sorted(want)) not in produced]
    return produced, missing


def audit(chooser, label):
    """Report how a candidate mapping fares. Returns the failure count."""
    colours = gamut()
    failed, kinds, examples = 0, {}, {}
    for rgb in colours:
        broken = violations(rgb, chooser(rgb))
        if broken:
            failed += 1
            for b in broken:
                kind = b.split(" ")[0]
                kinds[kind] = kinds.get(kind, 0) + 1
                examples.setdefault(kind, (rgb, b, chooser(rgb)))

    print(f"=== {label} ===")
    print(f"gamut colours: {len(colours)}   violating: {failed}"
          f"  ({failed / len(colours) * 100:.1f}%)")
    for kind, count in sorted(kinds.items(), key=lambda kv: -kv[1]):
        rgb, detail, idx = examples[kind]
        names = " ".join(text.PALETTE[k][1] for k in idx)
        print(f"   {kind:8} {count:>5}   e.g. {text.hex_colour(rgb)} -> "
              f"{names:<26} {detail}")

    counts = {}
    for rgb in colours:
        key = tuple(chooser(rgb))
        counts[key] = counts.get(key, 0) + 1
    total = sum(counts.values())
    effective = 1 / sum((c / total) ** 2 for c in counts.values())
    print(f"   spread: {len(counts)} distinct, {effective:.1f} effective")

    produced, missing = coverage(chooser)
    if missing:
        print(f"   MISSING {len(missing)} of {len(REQUIRED)} required triples:")
        for want, why in missing:
            print(f"      {' '.join(want):<28} ({why})")
    else:
        print(f"   coverage: all {len(REQUIRED)} required triples present")
    return failed, missing


if __name__ == "__main__":
    audit(lambda rgb: text.triple(rgb), "current algorithm")

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
import pathlib

D = str(pathlib.Path(__file__).resolve().parent.parent) + "/"


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
# **One of them tints, and is not objected to at all.** A single achromatic
# among two chromatics shades the mix rather than claiming anything about where
# the colour sits -- `blue purple white` on 0.28 is a violet with a lift, not a
# claim that violet is light.
#
# There used to be a pair of thresholds here, TINT_DARK 0.75 and TINT_LIGHT
# 0.25, catching a single achromatic at the far ends of the gamut. Both were
# written against a gamut that no longer exists. **The version 2 gamut runs
# 0.2012 to 0.4911**, so 0.75 was unreachable -- the black-on rule had not
# fired once in the whole 165 -- and 0.25 was not five hundredths inside the
# light end but a fifth of the way up the entire range, which is why it took
# eight triples, `red red white` and `red brown white` among them. Justin reads
# both of those as fine on the ring. A threshold that can only fire at one end,
# and fires there on things that look right, is not measuring anything.
#
# This replaces a per-hue exception. A rule naming one colour is a rule that has
# stopped explaining anything, and the count is what was actually doing the work.
# **Both are stated against the dead gamut, and `LIGHT` is above its maximum.**
# So the two-white rule fires at every hue and is not discriminating at all.
#
# Do not "fix" that by moving the cut into the gap in the distribution. The
# verdicts were checked against the ring, and on the fourteen triples these
# rules speak to, refusing outright is what the eye did:
#
#   two whites   all seven sunk. The rule flags all seven. Unanimous.
#   two blacks   the rule flags six; the seventh, `red black black`, it passes
#                and the eye sank anyway.
#
# So a cut at 0.38 -- the middle of the hole between `purple` and `blue` -- would
# pass `blue`, `green`, `yellow` and `orange` with two whites, every one of which
# was rejected by eye. The threshold is degenerate and the answer it gives is
# right, which is an uncomfortable pair but not a licence to move it.
#
# What the evidence actually suggests is that on a gamut this narrow and this
# uniformly mid-lightness, two achromatics always overclaim, and the honest rule
# is the count with no luminance test at all. That is a rule change and wants
# Justin's eye on it, not a constant nudged in the dark.
DARK = 0.33
LIGHT = 0.58

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
    """Shortest angle between two hues, in degrees.

    Kept although nothing here calls it. The first rule tried was a limit on
    this -- how far apart two squares may sit on the hue circle -- and it is
    wrong: red-green is 120 degrees and must be refused, blue-green is also 120
    and must be allowed. `OPPONENTS` replaced it. This stays as the measurement
    that argument is made in, and because the next person to reach for a span
    rule should find it already written and already explained.
    """
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
    if whites >= 2 and lum < LIGHT:
        out.append(f"two whites on a target of luminance {lum:.2f}")
    return out


def gamut():
    """Every colour the current mapping can produce, once each."""
    MAX = 0xFFFFFFF
    seen, out = set(), []
    for k in range(0, MAX, MAX // 20000):
        degrees = k / MAX * 360.0
        rgb = tuple(identicon._encode(v) for v in identicon._oklch_to_linear(
            identicon.MARK_LIGHTNESS, identicon.gamut_chroma(degrees), degrees))
        if rgb not in seen:
            seen.add(rgb)
            out.append(rgb)
    return out


# **`REQUIRED` and `coverage` are gone.** Twelve triples were listed here as
# having to be reachable somewhere in the gamut, because a checker that only
# rejects cannot notice an absence -- green-blue went missing for three
# iterations and nothing ever failed, since nothing emitted it and there was
# nothing to reject.
#
# That was a real hole, and the list was the patch for it: candidates fed back
# in by hand against an automatic chooser that kept losing them. The chooser is
# what has gone. The ring is placed by eye, tile by tile, and every one of the
# 165 has a line in `wheel.tsv` saying where it is -- so an absence is not
# something that has to be detected any more, it is something written down. A
# triple missing from the ring is missing because somebody put it in a tier.
#
# It had also stopped agreeing with the eye that wrote it. Three of the twelve
# were later sunk as rejected, `blue white white` among them -- required as "the
# light blues" and refused as too light to carry a hue. A list that records what
# was wanted at one moment cannot arbitrate against a later look at the same
# tile, and it was being read as though it could.


def audit(chooser, label):
    """Report how a candidate mapping fares. Returns the failure count.

    Rejections only. What a mapping fails to produce used to be reported here
    too, against a hand-written list of triples that had to be reachable; that
    went with the automatic chooser it was compensating for.
    """
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

    return failed


if __name__ == "__main__":
    # `triple_indices`, not `triple`: the harness judges which squares were
    # chosen, and that is a question about the colour alone. The order they are
    # laid out in comes from the grid now and cannot break a rule -- the same
    # three squares in a different order are the same colours.
    audit(lambda rgb: text.triple_indices(rgb), "current algorithm")

#!/usr/bin/env python3
"""Anchored mapping, third pass: the purple band, corrected by eye.

Same machinery as `anchored2`, which is left frozen because sheets 4 and 5 were
rendered with it and `sheet.py --verify` checks against that. Only the anchor
list moves.

Three corrections, all Justin's, 2026-08-19, from sheet 5:

**`black black purple` does not work.** It came from the anchor at 255 whose
secondary was black: both intervals touching that anchor double the secondary
in one of their six readings, so purple-with-two-blacks appeared on either side
of it. Fifteen colours, hue 250 to 260. Purple is already near the floor of this
gamut's luminance -- the whole purple band runs 0.23 to 0.35 -- so two blacks
take it past dark purple and into black, and the mark stops naming a colour.

**`blue black purple` does work**, and is the replacement: blue darkens purple
where black obliterates it. Changing the 255 anchor's secondary from black to
blue removes every doubled-black reading in the region while keeping this one,
which comes from the interval below as `[lp, ls, hp]`.

**There is scope around Q16 for `blue purple white`.** Q16 is `#8926d9`, hue
273.2. A new anchor at 276 makes the 270-to-276 interval six degrees wide, and
`[lp, hp, hs]` -- the fourth of its six readings -- lands on 273.0 to 274.0,
which is Q16 and its immediate neighbours.

**The rule this breaks, stated plainly.** Q16's luminance is 0.282 and
`perceptual.LIGHT` is 0.58, so the harness calls white on it dishonest. That is
not a near miss to be tuned away: no purple in this gamut reaches 0.35, and
nothing at or above LIGHT sits outside hues 34 to 194. White can never be honest
on any purple while the rule is a single luminance threshold.

The eye outranks the constant, so `perceptual` now carries a narrow, named
exception rather than a moved threshold -- see `WHITENABLE` there. It is
deliberately one hue: white on purple reads as lilac, a colour family with its
own name, where white on a dark blue or a dark green reads only as a mistake.
"""

import importlib.util
import pathlib

S = pathlib.Path(__file__).parent


def load(path, module):
    spec = importlib.util.spec_from_file_location(module, path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


anchored = load(str(S / "anchored2.py"), "a2")

# Differences from anchored2, and nothing else:
#   255  secondary black -> blue     kills black-black-purple, keeps blue-black-purple
#   276  new                         puts blue-purple-white on Q16
#   282  new, blue over purple       closes the white window without flattening the
#                                    band -- a monochrome anchor here was tried and
#                                    cost 10 effective identifiers, because it
#                                    collapsed blue-purple-purple's twenty degrees
ANCHORS = [
    (0,   "red",    "black"),
    (15,  "red",    "brown"),
    (24,  "brown",  "brown"),
    (33,  "brown",  "orange"),
    (45,  "orange", "yellow"),
    (60,  "yellow", "yellow"),
    (78,  "yellow", "green"),
    (120, "green",  "green"),
    (138, "green",  "white"),
    (155, "green",  "blue"),
    (190, "blue",   "white"),
    (220, "blue",   "blue"),
    (240, "blue",   "black"),
    (255, "purple", "blue"),
    (270, "blue",   "purple"),
    (276, "purple", "white"),
    (282, "blue",   "purple"),
    (300, "purple", "purple"),
    (330, "purple", "red"),
    (350, "red",    "red"),
]

hue_of = anchored.hue_of
luminance = anchored.luminance
INDEX = anchored.INDEX
CENTRED = anchored.CENTRED

perceptual = load(str(S / "perceptual.py"), "perc")
text = anchored.text


def _readings(low, high):
    """The interval's distinct readings, with the territory each has earned.

    **Two bugs lived in the old six-slot list, and they compounded.**

    It never deduplicated. A monochrome anchor makes three of the six slots the
    same multiset -- with `high` at `(purple, purple)`, `[lp, ls, ls]`,
    `[lp, ls, hp]` and `[lp, hp, hs]` are all blue-purple-purple -- and each
    was paid separately, so one reading took 64% of the interval. That is where
    the flood of blue-purple-purple came from, and green-green-yellow at 95
    colours is the same fault at the other end of the wheel.

    And the weight never matched its own stated intent. Territory is meant to
    go in proportion to the arrangements a reading affords, but every mixed
    reading scored 3 -- true for a pair, wrong for three distinct squares,
    which afford 6. The readings carrying the most identity were the ones being
    short-changed.

    Both are fixed by asking the multiset directly: dedupe, then weight by how
    many distinct orders it actually has.

    **A third fault: the table never mixed the two secondaries.** Six slots walk
    the low anchor's pair into the high anchor's pair, but none of them holds
    `ls` and `hs` together -- so between `(green, white)` and `(green, blue)` the
    only readings available were green-with-white and green-with-blue, and the
    band stepped from green-white-white straight to green-green-blue with
    nothing in between. `[lp, ls, hs]` is that missing step, and it is the one
    reading in the interval with three distinct squares, so it earns the widest
    territory of the six.

    Across the whole wheel it introduces exactly two multisets that were
    unreachable before: green-blue-white through the greens, which is the
    natural transition and was previously a single narrow bucket eighteen
    colours wide; and red-black-brown at the darkest reds, which is new and
    unjudged. Everywhere else it duplicates a slot already there and dedupes
    away.
    """
    lp, ls = low[1], low[2]
    hp, hs = high[1], high[2]
    slots = [[lp, lp, ls], [lp, ls, ls], [lp, ls, hp], [lp, ls, hs],
             [lp, hp, hs], [hp, hs, hs], [hp, hp, hs]]
    out, seen = [], set()
    for slot in slots:
        key = tuple(sorted(slot))
        if key in seen:
            continue
        seen.add(key)
        arrangements = 6 if len(set(slot)) == 3 else (1 if len(set(slot)) == 1 else 3)
        out.append((slot, arrangements))
    return out


def _pick(readings, where, rgb):
    """The reading whose territory contains `where`, skipping any that breaks a rule.

    **The rules prune, rather than only reporting.** A reading that violates for
    this particular colour is passed over and the next one down takes it, in
    order of territory. Anchors then declare intent and the harness enforces it,
    instead of the two disagreeing and the disagreement being logged.

    This is what lets white into a band at all. Any anchor carrying white as a
    secondary necessarily emits `X white white` and `X X white` from two of its
    six slots -- the table doubles secondaries, and there is no way to ask for
    one without the others. Pruning drops those where the target is too dark to
    carry two whites, and the colour falls through to the single-white reading
    that was wanted in the first place.

    If everything violates, the territorial answer stands: a wrong reading beats
    no reading, and the audit still reports it.
    """
    total = sum(w for _, w in readings)
    edge, ordered = 0.0, []
    for slot, weight in readings:
        edge += weight / total
        ordered.append((edge, slot))

    preferred = ordered[-1][1]
    for edge, slot in ordered:
        if where < edge:
            preferred = slot
            break

    ranked = [preferred] + [slot for _, slot in
                            sorted(ordered, key=lambda e: -e[0]) if slot is not preferred]
    for slot in ranked:
        if not perceptual.violations(rgb, tuple(INDEX[s] for s in slot)):
            return slot
    return preferred


def classify(rgb):
    """(multiset, class name) for a colour, against this module's anchors."""
    hue = hue_of(rgb)
    target = luminance(rgb)
    n = len(ANCHORS)
    for k in range(n):
        low, high = ANCHORS[k], ANCHORS[(k + 1) % n]
        span = (high[0] - low[0]) % 360
        offset = (hue - low[0]) % 360
        if not (offset < span or span == 0):
            continue

        where = offset / span if span else 0.0

        if anchored._unbridgeable(low, high):
            near = low if where < 0.5 else high
            return tuple(sorted(INDEX[s] for s in anchored.take(near, 3))), "snap"

        for at, anchor_index in ((where < CENTRED, k), (where > 1 - CENTRED, (k + 1) % n)):
            if not at:
                continue
            before = ANCHORS[(anchor_index - 1) % n]
            after = ANCHORS[(anchor_index + 1) % n]
            here = ANCHORS[anchor_index]
            names = [before[1], here[1], after[1]]
            if len(set(names)) == 3 and anchored._straddles(target, names) \
                    and not anchored._unbridgeable(before, after):
                return tuple(sorted(INDEX[s] for s in names)), "balanced"

        return tuple(sorted(INDEX[s] for s in
                            _pick(_readings(low, high), where, rgb))), "lean"

    raise AssertionError("anchors do not cover the circle")


def triple_indices(rgb):
    return classify(rgb)[0]


def triple(rgb):
    return text.arrange(triple_indices(rgb), rgb)

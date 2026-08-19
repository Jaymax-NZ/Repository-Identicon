#!/usr/bin/env python3
"""Anchored triple assignment, with the three reading classes.

Anchors declare "at this hue, these squares read as this colour", validated by
eye. A target then takes three slots from the one or two *adjacent* anchors
bracketing it, so opponent pairs are unreachable by construction.

Three classes, each with a testable condition:

  lean       between two anchors: 2:1 or 1:2, the majority naming the nearer
  balanced   sitting on an anchor whose neighbours straddle it in luminance,
             so they offset -- black-red-orange, where black is darker than the
             target and orange lighter
  extreme    sitting on an anchor at a luminance extremum, where nothing can
             offset because every neighbour lies the same side. Yellow is the
             ceiling at 0.80 and blue the floor at 0.20, so those read as a
             lean and not a balance.

Squares in gamut luminance order: black 0.00, blue 0.20, red 0.30, purple 0.35,
brown 0.50, orange 0.62, green 0.65, yellow 0.80, white 1.00. That ordering is
the whole lightness axis, and it is measured from the gamut rather than from the
palette's nominal values -- comparing the two domains is the mistake that put
black on the brightest colour in the first place.
"""

import importlib.util

D = "/home/justin/Code/Projects/Repository-Identicon/"


def load(name, module):
    spec = importlib.util.spec_from_file_location(module, D + name)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


identicon = load("repository-identicon.py", "i")
text = load("text-identicon.py", "t")
INDEX = {name: k for k, (_, name, _, _) in enumerate(text.PALETTE)}


def gamut_at(hue):
    return tuple(identicon._quantise(v)
                 for v in identicon._hsl_to_rgb((hue % 360) / 360,
                                                identicon.SATURATION,
                                                identicon.LIGHTNESS))


def luminance(rgb):
    r, g, b = (v / 255 for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


# What each square stands for, in the gamut's own luminance terms.
STANDS_FOR = {
    "black": 0.0,
    "blue": luminance(gamut_at(240)),
    "red": luminance(gamut_at(0)),
    "purple": luminance(gamut_at(300)),
    "brown": luminance(gamut_at(24)),
    "orange": luminance(gamut_at(39)),
    "green": luminance(gamut_at(120)),
    "yellow": luminance(gamut_at(60)),
    "white": 1.0,
}

# Validated one band at a time. orange+orange and the old yellow+green position
# are gone: a monochrome anchor blocks the balanced class, because flanking it
# spends two slots on the centre and crowds out the square that would offset.
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
    (255, "purple", "black"),
    (270, "blue",   "purple"),
    (300, "purple", "purple"),
    (330, "purple", "red"),
    (350, "red",    "red"),
]

# How close to an anchor still counts as sitting on it.
CENTRED = 0.15

# Beyond this, two anchors' primaries cannot be blended: Unicode has no cyan
# square, so nothing bridges green to blue and the nearer anchor wins outright.
MAX_STEP = 65.0


def hue_of(rgb):
    r, g, b = rgb
    mx, mn = max(rgb), min(rgb)
    if mx == mn:
        return 0.0
    d = mx - mn
    h = ((g - b) / d) % 6 if mx == r else ((b - r) / d + 2 if mx == g else (r - g) / d + 4)
    return (h * 60) % 360


def _separation(a, b):
    d = abs(a - b) % 360
    return min(d, 360 - d)


SQUARE_HUE = {}
for _c, _n, _cp, _rgb in text.PALETTE:
    SQUARE_HUE[_n] = None if max(_rgb) == min(_rgb) else hue_of(_rgb)


def _unbridgeable(low, high):
    """Only true opponents cannot be blended. Span was the wrong test: red-green
    and blue-green are both 120 degrees and only one of them is impossible."""
    a, b = low[1], high[1]
    return frozenset((a, b)) in OPPONENTS


OPPONENTS = {
    frozenset(("red", "green")),
    frozenset(("yellow", "blue")),
    frozenset(("orange", "blue")),
}


def take(anchor, slots):
    _, primary, secondary = anchor
    if slots == 1:
        return [primary]
    if slots == 2:
        return [primary, secondary]
    return [primary, primary, secondary]


def _straddles(target, names):
    return (any(STANDS_FOR[n] < target for n in names)
            and any(STANDS_FOR[n] > target for n in names))


def classify(rgb, anchors=None):
    """(multiset, class name) for a colour.

    `anchors` defaults to this module's own list, so calling it with one
    argument is exactly what sheets 4 and 5 were rendered with. A later
    candidate passes its own rather than editing this one, which keeps
    `sheet.py --verify` a real check rather than a moving target.
    """
    anchors = ANCHORS if anchors is None else anchors
    hue = hue_of(rgb)
    target = luminance(rgb)
    n = len(anchors)
    for k in range(n):
        low, high = anchors[k], anchors[(k + 1) % n]
        span = (high[0] - low[0]) % 360
        offset = (hue - low[0]) % 360
        if not (offset < span or span == 0):
            continue

        where = offset / span if span else 0.0

        if _unbridgeable(low, high):
            near = low if where < 0.5 else high
            return tuple(sorted(INDEX[s] for s in take(near, 3))), "snap"

        # Sitting on an anchor: try the balanced reading, where the two
        # neighbours offset each other around it.
        for at, anchor_index in ((where < CENTRED, k), (where > 1 - CENTRED, (k + 1) % n)):
            if not at:
                continue
            before = anchors[(anchor_index - 1) % n]
            after = anchors[(anchor_index + 1) % n]
            here = anchors[anchor_index]
            names = [before[1], here[1], after[1]]
            if len(set(names)) == 3 and _straddles(target, names) \
                    and not _unbridgeable(before, after):
                return tuple(sorted(INDEX[s] for s in names)), "balanced"

        # Six readings across the interval, but they do not get equal shares of
        # it. A monochrome triple has exactly one arrangement; every mixed one
        # has three, so a mixed triple carries three times the identity for the
        # same visual footprint. Territory is therefore allocated in proportion
        # to how many arrangements each reading affords -- the permutables are
        # pulled wide precisely because they are permutable, and the monochrome
        # readings shrink to the narrow bands around their own anchors.
        lp, ls = low[1], low[2]
        hp, hs = high[1], high[2]
        readings = [[lp, lp, ls], [lp, ls, ls], [lp, ls, hp],
                    [lp, hp, hs], [hp, hs, hs], [hp, hp, hs]]
        weights = [1 if len(set(r)) == 1 else 3 for r in readings]
        total = sum(weights)
        edge = 0.0
        squares = readings[-1]
        for reading, weight in zip(readings, weights):
            edge += weight / total
            if where < edge:
                squares = reading
                break
        return tuple(sorted(INDEX[s] for s in squares)), "lean"

    raise AssertionError("anchors do not cover the circle")


def triple_indices(rgb, anchors=None):
    return classify(rgb, anchors)[0]


def triple(rgb, anchors=None):
    return text.arrange(triple_indices(rgb, anchors), rgb)

# Work in progress: which three of the nine colours stand for a colour

Not adopted. The shipped mapping is still the search in `../text-identicon.py`,
and nothing here is imported by anything. Committed so it survives the machine.

**Keep the stakes straight.** All of this is about a *patch* — the tricolour
exists only where an image cannot be sent and text cannot be styled, so the
colour would otherwise be lost entirely. The core of the specification is the
key, the generator library the derivation conforms to, and the grid; then the
two lattices; then this. The tricolour has been the hardest part to settle and
is the least load-bearing, and those two facts are unrelated.

**It also serves colour-blind readers worst, by construction.** Measured over
the nine colours as the font paints them, seven of thirty-six pairs collapse
under deuteranopia and five under protanopia — see `../SPEC.md`. The grid is
what carries identity for those readers; the triple is a bonus that does not
arrive. No amount of hand-placing fixes that, because the channel is hue.

## The artifact

`in-use.tsv` is the answer: sixty-three blocks tiling 0–360 with no gap and no
overlap, each naming the three colours that stand for that band of hue, inner to
outer. It comes out as sixty-four rows, because the block straddling zero is
split in two.

```
# from	to	n	one	two	three	mark
0.0	2.4	63	orange	purple	brown	🟧🟪🟫
2.4	10.4	1	red	orange	purple	🟥🟧🟪
10.4	14.4	2	orange	orange	purple	🟧🟧🟪
```

A lookup is `from <= hue < to` and always hits exactly once. The block that
straddles zero is split into two rows sharing its number rather than left to
wrap, because a consumer that has to special-case one row eventually will not.
Hue is the HSL hue `identicon.js` derives from the digest, at its fixed
saturation 0.7 and lightness 0.5.

It is **generated**, by `wheel.py --reference` from `wheel.tsv`, so the table
and the wheel cannot disagree. Do not edit it.

## How it was arrived at, and why not by search

The original chooser searched all 165 combinations for whichever mix minimised
error against the target colour. It matched numbers in a domain the eye does not
work in, and produced answers that were numerically close and perceptually
wrong — green used to raise a channel, black on the brightest colour in the
gamut, orange beside blue. 57.2% of the gamut broke at least one rule Justin
could name on sight.

Two attempts at a better algorithm followed. The third answer was to stop
writing algorithms: the ring is placed by hand, block by block, judged by eye
against the gamut it sits beside.

| file | what it is |
|---|---|
| `wheel.tsv` | **the wheel** — all 165 triples, one line each, with where each one is |
| `in-use.tsv` | **the mapping** — generated from it, the only file a consumer would read |
| `wheel.py` | the renderer and the generator |
| `perceptual.py` | the harness — what is forbidden, and what must exist |

Everything else has been deleted, and git has all of it if a question needs
re-opening: the anchored mapping and the target file it was fitted to, the
contact sheets, eighty wheel renders, the shape-channel and blend-inspection
scripts, and `bench.tsv` — the version 1 roster, along with the tool that fed
it and the seating machinery that consumed it. The arrangement is settled, so
the apparatus of arriving at one is not needed to draw it.

## The wheel

```bash
python3 wheel.py --painted              # render the next free wheelN.svg
python3 wheel.py --painted --ring-only  # the ring alone, tiers not drawn
python3 wheel.py --reference            # regenerate in-use.tsv from wheel.tsv
```

Reading outward: the tiers, stacked inward from the ring with the rejected set
innermost; the drift ticks and their leaders in the gap inside the ring; **the
block ring** itself; the block numbers in the corridor between it and the gamut;
the gamut; and the trefoils on neutral ground.

`--ring-only` draws the ring and leaves the tiers and the roster off the page.
It is a view and not a smaller wheel: everything is still read, still packed and
still reported, and `wheel.tsv` is untouched.

### What the widths mean

A block is as wide as the identity it affords. Three distinct colours give six
arrangements and eight shape combinations — 48 marks — against a pair's 3×8 and
three-of-a-kind's 1×8. Eight degrees, four and one price that, and it comes out
to a constant six marks per degree.

Every block is at its class price. Blocks used to be widened past it where a
stretch of the wheel had to carry more decision than the price allowed, declared
by a rule drawn underneath; nothing is stretched now, so there is nothing to
declare.

### Coverage, as it stands

**The 8/4/1 pricing is exact.** It assumes eight shape combinations per block,
and every block has eight: all nine colours exist as a square and as a circle,
so there is no position that cannot take one.

| | |
|---|---|
| marks reachable | 2,168 |
| effective distinct | 2,166 |
| 50% chance any pair collides at | 55 projects |

This section used to record an overcount, on the grounds that black and white
never circle and a block containing one was worth twelve marks while drawn as
wide as one worth forty-eight. That exclusion was overruled after testing, and
with all nine circling the fault does not exist. Nothing needs re-laying out.

### Numbers are positional

A tile's number is the line it sits on in `wheel.tsv`, and the lines run
clockwise from the top: the ring is 1–63 and walks the hue circle, the tiers
follow outward-in, then the three sunk bands, then the six that average to a
neutral and have no place at all. A number is a position, so moving a tile and
re-sorting the file renumbers what follows it. That is the cost of the number
meaning something, and it is paid deliberately — the ring is closed, so it is no
longer paid often.

The triple is on the line as well as the number, and neither is trusted alone:
the engine reads the names, and the number is checked against its own position,
so a dropped line says so instead of silently shifting everything after it.

## The findings worth keeping

**Opponency, not span.** The first rule tried was a limit on how far apart two
colours could sit on the hue circle. It is wrong: red-green is 120 degrees and
must be refused, blue-green is *also* 120 degrees and must be allowed. Teal is
an ordinary colour; reddish-green is not one at all. The check is a short list of
opponent pairs, and it is biology rather than geometry.

**Hashing an output of the mapping adds nothing to it.** The order of the
three colours, and which of them are circles, were taken from a hash of
`#rrggbb` — so that the colour alone would be sufficient, which is a real
property and was argued for on real grounds. But the colour is what the mapping
produces, so a channel derived from it cannot separate two projects the mapping
has already put in the same place: over four thousand projects it yielded fewer
distinct marks than there were distinct colours. The measurement that was
supposed to catch this swept the gamut one sample per colour, which makes every
mark look distinct by construction. **Measure over the population you have, not
over the space it lives in.**

They moved to the matrix next, which is disjoint from the hue but *identical to
the pattern* — better, and still not independent. Each now reads its own
character of the digest, characters 15 and 16, which needs no argument at all.

**Two domains must not be compared.** The palette is anchored on Unicode
*names*, so `yellow` is nominally `#ffff00` — a colour no font paints and the
gamut never reaches, since `identicon.js` fixes saturation at 0.7. Matching a
70%-saturation target against 100%-saturation anchors forces a compensation
third onto every colour. Every comparison here is made in the gamut's own terms.

**A checker that only rejects cannot see an absence.** Blue-green went missing
for three iterations because nothing emitted it, so nothing ever failed. The
patch was `REQUIRED`, a list of triples that had to be reachable, and it caught
four distinct defects the moment it was added. It is gone now, and the finding
is what replaced it rather than the list: absence was only invisible while an
algorithm was choosing. Every one of the 165 has a line saying where it is, so a
triple missing from the ring is missing because somebody put it in a tier.

**Hue angle, not distance.** Matching a blend to the gamut by Oklab *distance*
is dominated by lightness, because a blend of three colours is always lighter
and duller than the gamut. Pale blends were matched to the cyans and dark ones
to the oranges — `blue blue white` reported 198° when its hue is 282°. A
blend's hue is its hue: read the Oklab hue angle and match on that.

**White does not pull its weight.** A rendered white square is not `#ffffff` —
it carries a border and the glyph is not a flat field — and beside two saturated
neighbours the eye discounts it further, reading it as a lightener rather than
as a third of the colour. `WHITE_WEIGHT` halves it. That is a calibration
against what Justin can see, not a claim about optics, and it is the one place
in `wheel.py` where the model is deliberately not physical.

**Clip-paths are not safe in an SVG anyone else will open.** The trefoil mixes
were drawn as discs carrying `clip-path="url(#...)"`, which every browser honours
and at least one SVG renderer does not — an unresolved reference clips the shape
away entirely, so the plain discs survived and every overlap silently vanished.
Nothing in the file looked wrong. The regions are computed and written out as
coordinates now.

## The structural limit

Nothing in the palette lies between green and blue, so every mixture of the two
lands in the same narrow reading: `green blue white`, `green blue black` and
`green blue brown` all report a nominal hue of 180.0–180.2. One nominal, three
blocks, so at least two must sit off it whatever is done. Hue bands 135–160,
162–197 and 199–250 are unreachable for the same reason. This is not a mapping
fault and cannot be fixed by placement.

## What is still open

- **The wedge widths are priced wrong** wherever a block contains black or
  white — see the coverage table above. Re-pricing changes the layout.
- **The two-achromatic thresholds are calibrated against a gamut that no longer
  exists**, and `LIGHT` sits above its maximum, so the two-white rule fires at
  every hue and measures nothing. It is also right every time: all seven
  two-white triples were sunk by eye, and six of the seven two-black ones are
  flagged with the seventh sunk anyway. Refusing outright is what the eye did on
  all fourteen, which argues for dropping the luminance test rather than
  recalibrating it — a rule change, not a constant. See `HANDOVER.md`.
- `SPEC.md` records this table as not yet normative. Adopting it means replacing
  the search in `../text-identicon.py`, pinning vectors for it, and saying so
  there.

## Running it

```bash
python3 wheel.py --painted
```

```bash
python3 perceptual.py
```

The harness runs on its own, auditing the algorithm currently shipped in
`../text-identicon.py`: violations by kind, with an example of each, and which
required triples it never produces. No network, no fonts, no human eyes.

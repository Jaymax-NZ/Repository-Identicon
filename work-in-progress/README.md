# Work in progress: which three emoji squares stand for a colour

Not adopted. The shipped mapping is still the search in `../text-identicon.py`,
and nothing here is imported by anything. Committed so it survives the machine.

## The artifact

`in-use.tsv` is the answer: fifty arcs tiling 0–360 with no gap and no overlap,
each naming the three squares that stand for that band of hue, inner to outer.

```
# from	to	n	one	two	three	mark
0.0	5.0	1	red	brown	black	🟥🟫⬛
5.0	9.0	2	red	red	brown	🟥🟥🟫
9.0	17.0	3	orange	purple	brown	🟧🟪🟫
```

A lookup is `from <= hue < to` and always hits exactly once. The block that
straddles zero is split into two rows sharing its number rather than left to
wrap, because a consumer that has to special-case one row eventually will not.
Hue is the HSL hue `identicon.js` derives from the digest, at its fixed
saturation 0.7 and lightness 0.5.

It is **generated**, by `wheel.py --reference` from `bench.tsv`, so the table
and the wheel cannot disagree. Do not edit it.

## How it was arrived at, and why not by search

The original chooser searched all 165 combinations for whichever mix minimised
error against the target colour. It matched numbers in a domain the eye does not
work in, and produced answers that were numerically close and perceptually
wrong — green used to raise a channel, black on the brightest colour in the
gamut, orange beside blue. 57.2% of the gamut broke at least one rule Justin
could name on sight.

Two attempts at a better algorithm followed, both kept here because the harness
they were written against still governs what is admissible. The third answer was
to stop writing algorithms: the ring is placed by hand, block by block, judged
by eye against the gamut it sits beside.

| file | what it is |
|---|---|
| `in-use.tsv` | **the mapping** — generated, the only file a consumer would read |
| `bench.tsv` | the working document: every triple the vocabulary knows, in use or not, with where each is placed and how far it is stretched |
| `wheel.py` | the renderer and the generator |
| `perceptual.py` | the harness — what is forbidden, and what must exist |
| `mix.py` | what a given triple averages to, and where that reads |
| `anchored2.py`, `anchored3.py` | the second attempt: declared anchors and interpolation. Superseded; `anchored2` is frozen so `sheet.py --verify` stays a real check |
| `shaped.py` | the shape channel — square or circle, laid over the triple |
| `target.tsv` | the earlier specification, per five-degree division. Historical: the ring superseded it |
| `sheet.py`, `row.py` | the contact sheet renderer, and one row of it enlarged |
| `sample.js`, `sample.tsv` | 400 identicons straight from the reference library, and its output so the sheet rebuilds without node |
| `sheet*.svg` | the contact sheets, eight iterations |
| `wheel*.svg` | the wheels, sixty-one iterations |

Both series are kept whole rather than as one current file. Each render differs
from its neighbour in one decision, so a change is legible by flipping between
two of them and in essentially no other way.

## The wheel

```bash
python3 wheel.py                  # render the next free wheelN.svg
python3 wheel.py --reference      # regenerate in-use.tsv from bench.tsv
```

Reading outward: the drift ticks and their leaders, a narrow technical band
carrying the stretch rules, the block numbers, the gamut, **the block ring**,
and the trefoils on neutral ground.

Four bands are off by default, each having finished its job. `--spokes` brings
back what the algorithm produced at every division; `--blend-band` each
division's mixture beside the gamut; `--base-band` the primary of each triple as
a contiguous territory; `--tables` the corner lists and the unused colours. They
are switched off rather than deleted because each answers a question that may be
asked again.

### What the widths mean

A block is as wide as the identity it affords. Three distinct squares give six
arrangements and eight shape combinations — 48 marks — against a pair's 3×8 and
three-of-a-kind's 1×8. Eight degrees, four and one price that, and it comes out
to a constant six marks per degree.

`mult` widens a block past its price where a stretch of the wheel has to carry
more decision than the price allows. That is declared rather than hidden: a rule
under the block as long as it ought to have been, one rule per half-step of
stretch, so the class price stays readable under a block that has outgrown it.

### Coverage, as it stands

- 50 blocks, 1,720 marks reachable
- **1,549 effective distinct marks** — two random projects collide 1 in 1,549
- **46 projects before a 50% chance any pair collides**, which is birthday-bound
  and barely moves with packing. Raising it needs more marks, not better layout.
- unstretched, the same fifty triples would give 1,719 effective: all the
  widening costs 9.9%

### Numbers are positional

1–50 are in use, numbered clockwise from the top in the order they sit; 101+ are
not in use, ordered by the hue their blend reads as. A block's number is its
position, so removing or reordering one renumbers the rest. That is the cost of
the number meaning something, and it is paid deliberately.

## The findings worth keeping

**Opponency, not span.** The first rule tried was a limit on how far apart two
squares could sit on the hue circle. It is wrong: red-green is 120 degrees and
must be refused, blue-green is *also* 120 degrees and must be allowed. Teal is
an ordinary colour; reddish-green is not one at all. The check is a short list of
opponent pairs, and it is biology rather than geometry.

**Two domains must not be compared.** The palette is anchored on Unicode
*names*, so `yellow` is nominally `#ffff00` — a colour no font paints and the
gamut never reaches, since `identicon.js` fixes saturation at 0.7. Matching a
70%-saturation target against 100%-saturation anchors forces a compensation
square onto every colour. Every comparison here is made in the gamut's own terms.

**A checker that only rejects is half a harness.** Blue-green went missing for
three iterations because nothing emitted it, so nothing ever failed. `REQUIRED`
is the other half: triples Justin has said should exist, with where he saw them.
It caught four distinct defects the moment it was added.

**Hue angle, not distance.** Matching a blend to the gamut by Oklab *distance*
is dominated by lightness, because a blend of three squares is always lighter and
duller than the gamut. Pale blends were matched to the cyans and dark ones to the
oranges — `blue blue white` reported 198° when its hue is 282°. A blend's hue is
its hue: read the Oklab hue angle and match on that.

**White does not pull its weight.** A rendered white square is not `#ffffff` —
it carries a border and the glyph is not a flat field — and beside two saturated
squares the eye discounts it further, reading it as a lightener rather than as a
third of the colour. `WHITE_WEIGHT` halves it. That is a calibration against what
Justin can see, not a claim about optics, and it is the one place in `wheel.py`
where the model is deliberately not physical.

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

- `SPEC.md` records this table as not yet normative. Adopting it means replacing
  the search in `../text-identicon.py`, pinning vectors for it, and saying so
  there.
- The shape channel in `shaped.py` predates the ring and has not been re-scored
  against it. The coverage figures above assume it: 48 marks for three distinct
  squares is 6 arrangements × 8 shape combinations.
- `target.tsv` is historical and is still read by `wheel.py --score` and
  `--emit`. Neither is used any more.

## Running it

```bash
python3 wheel.py --reference
python3 -c "import perceptual, anchored2; perceptual.audit(anchored2.triple, 'candidate')"
python3 shaped.py
python3 sheet.py --verify && python3 sheet.py sheet8.svg
```

The audit prints violations by kind, spread, and which required triples are
missing. `shaped.py` checks the shape channel against the whole gamut.
`sheet.py --verify` reproduces `sheet4.svg` byte for byte — the renderer was
lost with its session scratchpad and is a reconstruction, so that check is what
makes it trustworthy. No network, no fonts, no human eyes.

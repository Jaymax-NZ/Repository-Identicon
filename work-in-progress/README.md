# Work in progress: which three emoji squares stand for a colour

Not adopted. The shipped mapping is still the search in `../text-identicon.py`,
and nothing here is imported by anything. Committed so it survives the machine.

**Keep the stakes straight.** All of this is about a *patch* — the triple exists
only where an image cannot be sent and text cannot be styled, so the colour
would otherwise be lost entirely. The core of the specification is the key, the
generator library the derivation conforms to, and the grid; then the octants;
then this. The triple has been the hardest part to settle and is the least
load-bearing, and those two facts are unrelated.

**It also serves colour-blind readers worst, by construction.** Measured over
the nine squares as the font paints them, seven of thirty-six pairs collapse
under deuteranopia and five under protanopia — see `../SPEC.md`. The grid is
what carries identity for those readers; the triple is a bonus that does not
arrive. No amount of hand-placing fixes that, because the channel is hue.

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
| `shaped.py` | the shape channel — square or circle, laid over the triple |
| `perceptual.py` | the harness — what is forbidden, and what must exist |
| `mix.py` | what a given triple averages to, and where that reads |

The anchored mapping, the target file it was fitted to, the contact sheets and
sixty-one wheel renders have been deleted. They were the route, not the answer,
and git has every one of them if a question needs re-opening. `wheel.py` no
longer depends on any of it: `gamut_at` and `hue_of` are inlined, so the wheel
needs only the reference implementation and the palette.

## The wheel

```bash
python3 wheel.py                  # render the next free wheelN.svg
python3 wheel.py --reference      # regenerate in-use.tsv from bench.tsv
```

Reading outward: the drift ticks and their leaders, a narrow technical band
carrying the stretch rules, the block numbers, the gamut, **the block ring**,
and the trefoils on neutral ground.

`--tables` restores the corner lists and the unused colours. They travel
together because both are the apparatus of choosing, and it is off while there
is nothing left to choose.

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

**The 8/4/1 pricing overcounts, and this is a real fault rather than a rounding.**
It assumes eight shape combinations per block, which holds only when all three
squares are circleable. Black and white never are, so a triple containing one
has four and a triple containing both has two. A three-distinct block with a
black in it is worth twelve marks and is drawn as wide as one worth forty-eight.

| | assuming 8 | actually |
|---|---|---|
| marks reachable | 1,720 | **1,420** |
| effective distinct | 1,549 | **1,003** |
| 50% chance any pair collides at | 46 projects | **37 projects** |

Twenty-three of the fifty blocks carry an achromatic. The fix is to price a
block by `arrangements × 2^circleable` rather than by class alone — which would
make several current widths wrong, so it is a re-layout, not an edit.

Measured over the gamut rather than over projects, `shaped.py` reports 214
arrangements, 732 distinct marks with shape, 546 effective.

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

- **The wedge widths are priced wrong** wherever a block contains black or
  white — see the coverage table above. Re-pricing changes the layout.
- **`REQUIRED` now contradicts the ring.** The table violates nothing — zero of
  1074 gamut colours break a rule, which is the first time that has been true —
  but seven of the twelve required triples are not on it, and at least one of
  them, `blue purple white`, was rejected by eye afterwards. The list records
  what was wanted at the time it was written; the ring records what was chosen.
  One of them has to give, and it is probably the list.
- `SPEC.md` records this table as not yet normative. Adopting it means replacing
  the search in `../text-identicon.py`, pinning vectors for it, and saying so
  there.

## Running it

```bash
python3 wheel.py --reference
python3 shaped.py
python3 -c "import shaped, perceptual; perceptual.audit(shaped.triple, 'in-use')"
python3 mix.py "yellow green orange"
```

`shaped.py` checks the shape channel across the whole gamut — determinism,
arrangement untouched, no circled neutral, three characters out — and reports
spread. The audit prints violations by kind and which required triples are
missing. No network, no fonts, no human eyes.

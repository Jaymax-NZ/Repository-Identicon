# Work in progress: the anchored triple mapping

Unfinished. Committed so it survives the machine, not because it is ready — the
shipped mapping is still the one in `../text-identicon.py`. Nothing here is
imported by anything.

## What this is

The emoji triple's original chooser searched all 165 combinations for whichever
mix minimised error against the target colour. It produced perceptually invalid
answers — green used to raise a channel, black on the brightest colour in the
gamut, orange beside blue — because it matched numbers in a domain the eye does
not work in. 57.2% of the gamut broke at least one rule that Justin could name
on sight.

This replaces the search with declared anchors and an interpolation between
them.

| file | what it is |
|---|---|
| `anchored2.py` | the candidate mapping: anchors, the reading classes, allocation |
| `perceptual.py` | the harness — what is forbidden, and what must exist |
| `sample.js` | 400 identicons straight from the reference library, reproducible |
| `sample.tsv` | its output, so the sheet can be rebuilt without node |
| `row.py` | one row of the contact sheet, enlarged, with its numbers |
| `sheet4.svg` | where it stands: 400 marks, hue-sorted, labelled A–T / 1–20 |

## Where it got to

```
                     violations   distinct   effective   required triples
original                  57.2%         67        49.8    4 of 11
anchored, tonight          6.0%         95        59.9   11 of 11
```

Better on every axis at once, which was not obvious in advance: the invalid
combinations had been carrying a lot of the old distinctness.

## The three findings worth keeping

**Opponency, not span.** The first rule tried was a limit on how far apart two
squares could sit on the hue circle. It is wrong: red-green is 120 degrees and
must be refused, blue-green is *also* 120 degrees and must be allowed. Teal is
an ordinary colour; reddish-green is not one at all. The check is a short list
of opponent pairs, and it is biology rather than geometry.

**Two domains must not be compared.** The palette is anchored on Unicode
*names*, so `yellow` is nominally `#ffff00` — a colour no font paints and the
gamut never reaches, since identicon.js fixes saturation at 0.7. Matching a
70%-saturation target against 100%-saturation anchors forces a compensation
square onto every single colour, which is why three-of-a-kind occurred for 13
colours out of 1074 and why brown and black were doing arithmetic. Every
comparison here is made in the gamut's own terms.

**A checker that only rejects is half a harness.** Blue-green went missing for
three iterations because nothing emitted it, so nothing ever failed. `REQUIRED`
is the other half: triples Justin has said should exist, with where he saw them.
It caught four distinct defects the moment it was added.

## What is still open

- `white` appears on 53 colours at luminance 0.58, exactly on the `LIGHT`
  threshold. Either the constant is slightly wrong or the `blue+white` band has
  grown past where white reads.
- `green blue white` is 18 colours wide and Justin wants it wider. It is one
  bucket of one interval, so weighting cannot widen it — it needs its own
  anchor.
- The anchors have been validated band by band up to the blues. The purples and
  the wrap back to red have had less attention.
- None of this is in `SPEC.md`, which still describes the half-block rendering
  that predates the octant-and-emoji work entirely.

## Running it

```bash
python3 -c "import perceptual, anchored2; perceptual.audit(anchored2.triple, 'candidate')"
```

Prints violations by kind, spread, and which required triples are missing. No
network, no fonts, no human eyes.

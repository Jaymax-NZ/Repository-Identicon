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
| `anchored2.py` | the mapping sheets 4 and 5 used — frozen, so `--verify` stays honest |
| `anchored3.py` | the current mapping: `anchored2`'s machinery, purple band corrected |
| `shaped.py` | the shape channel — square or circle, laid over the anchored triple |
| `perceptual.py` | the harness — what is forbidden, and what must exist |
| `sample.js` | 400 identicons straight from the reference library, reproducible |
| `sample.tsv` | its output, so the sheet can be rebuilt without node |
| `wheel.py` | the target wheel: renders `target.tsv`, seeds it, scores a mapping against it |
| `target.tsv` | **the specification** — the intended triple at each division, edited by eye |
| `wheel.svg` | its rendering: the gamut as a ring, the intended triple spiking outward |
| `sheet.py` | the contact sheet renderer |
| `row.py` | one row of the contact sheet, enlarged, with its numbers |
| `sheet.svg` … `sheet8.svg` | the contact sheet, eight iterations: 400 marks, hue-sorted, labelled A–T / 1–20 |

The sheets are kept as a series rather than one current file. Each is the same
400 marks in the same order, differing from its neighbours only in what the
mapping did, so a change is legible by flipping between two of them and in
essentially no other way. `sheet8.svg` is where it stands. Sheets 1 to 3 were
recovered from a session scratchpad under `/tmp`, which is tmpfs here — they
were one reboot from gone, and none of the other artefacts from that session
were kept.

The renderer went the same way, so `sheet.py` is a reconstruction rather than
the original. `python3 sheet.py --verify` re-renders `sheet4.svg` from
`sample.tsv` and compares: it is byte-for-byte identical, which is what makes
the reconstruction checkable and the sheet-4-to-5 diff attributable to the
mapping alone.

## The wheel inverts the loop

The sheets ask "here is what the algorithm did — is it right?" That conflates
two questions, because a change of arrangement and a change of mapping look the
same at a glance and only one of them is a colour judgement.

`target.tsv` asks the other way round. It states what the triple **should** be
at each division, unarranged and with no square-versus-circle, and the algorithm
is then hunted for until it reproduces it. The spec is the artifact; the
anchors, the reading table and the interpolation are one candidate
implementation of it, to be replaced freely as long as the score holds.

```bash
python3 wheel.py             # render the next wheelN.svg
python3 wheel.py --score     # how many divisions a mapping reproduces
python3 wheel.py --emit      # refuses: the target is no longer an output
```

**The seeding is over.** `target.tsv` was seeded once from `anchored3` and is
now the specification, tracked per spike and maintained by hand. `--emit`
refuses to overwrite it and names how many divisions would be lost; `--force`
overrules, and should not be needed again. An algorithm is fitted to this file,
never the other way round.

Each row carries an `origin`: `eye` for a division Justin has judged, `seed` for
one still carrying whatever the mapping said. The wheel prints judged divisions
in black with a dot beneath the number, so what has been looked at is visible
without opening the file. Four of seventy-two so far.

Scoring against a seeded target is circular by construction — `anchored3` began
at 72 of 72 and means nothing until divisions are judged. It now scores 68, and
the four misses are exactly the four judgements.

The wheels are a numbered series like the sheets: `wheel1.svg`, `wheel2.svg`,
each render taking the next free number so nothing is overwritten and any two
can be compared.

`--spikes` sets the divisions, currently 72 at five degrees. Widening means
editing, not re-emitting.

### The base band

`wheel2.svg` adds a band inside the gamut showing each division's **primary**
alone, contiguous, so a run sharing a primary reads as one solid block and a
hairline marks every boundary. The spikes say what each division does; this says
where the territories begin and end, which the contact sheets could never show.

It immediately reports 23 runs around the wheel, **nine of them a single
division wide** — at hues 75, 135, 155, 160, 165, 180, 235, 265 and 335. Those
are the mapping stuttering between two bases rather than committing, and they
are the obvious first thing to judge.

## Where it got to

```
                     violations   distinct   effective   required triples
original                  57.2%         67        49.8    4 of 11
anchored, sheet 4          6.0%         95        59.9   11 of 11
anchored + shape, sheet 5  6.0%        429       286.8   11 of 11
purples corrected, sheet 6 6.0%        423       284.5   12 of 12
rules prune, sheet 7       0.0%        432       288.2   12 of 12
secondaries mix, sheet 8   0.0%        440       293.8   12 of 12
```

Each line is scored by the harness of its own day, so the columns are not a
like-for-like series. Judged by sheet 7's rules, sheet 5 violates 3.7% and is
missing a required triple; sheet 7 violates nothing, because from sheet 7 the
rules select the reading rather than only complaining about it.

Better on every axis at once, which was not obvious in advance: the invalid
combinations had been carrying a lot of the old distinctness.

The shape channel then multiplies spread by 4.8 and touches nothing else — the
violation count, the examples behind it and the coverage are identical line for
line, because shape changes no colour. Eight projects collide 38.6% of the time
on order alone and 9.4% with shape.

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

## The shape channel

Order alone cannot separate the gamut. Ordered triples of nine colours reach
729 and the gamut is 1074, so there is no arrangement of squares that gets
there — the ceiling is arithmetic, not a matter of choosing better.

Shape clears it. Seven of the nine colours have a circle, black and white stay
square, so a position offers sixteen glyphs and an ordered mark 4096 — clear of
the gamut by nearly four times. It is a strong channel, not a tiebreak: a circle
among squares is preattentive, found without search.

**Black and white are never circled.** Unicode names their circles `MEDIUM BLACK
CIRCLE` and `MEDIUM WHITE CIRCLE` where every square in the palette is `LARGE`,
and the palette is anchored on those names — the size word is part of the
definition, not a rendering accident. White alone lands on 53 colours, so a
ragged mark would be a common one.

**The bit is drawn after the arrangement, from the same digest.** `arrange`
keeps the remainder of the MD5 against the permutation count; the shape takes
the quotient and reduces that. It is one mixed-radix decomposition rather than
two moduli of the same number, so the draws are independent — and arrangement
comes out bit-for-bit what it already was, which is why sheets 4 and 5 carry
identical arrangements and the flip between them shows shape alone.

The triple stays a pure function of the colour. `.colour` remains sufficient to
compute the whole mark, shape included.

## The purple band, sheets 6 and 7

Three corrections, Justin's, from sheet 5. `anchored3.py` carries them and
`anchored2.py` is frozen, so `--verify` stays a real check.

`black black purple` is now **forbidden** outright, in `FORBIDDEN`. It came from
the 255 anchor's black secondary, which both neighbouring intervals doubled —
fifteen colours across hues 250 to 260. Purple sits near this gamut's floor
already, so two blacks take it out of colour entirely. The secondary becomes
blue, which removes every doubled-black reading there while keeping
`blue black purple` from the interval below.

Cost, stated: `blue black purple` narrows from 23 colours to 15, hues 245 to
250. It survives, but as a narrower band.

`blue purple white` now exists on 12 colours, hues 272.2 to 279.9, from a new
anchor at 276 — Q16 among them, which is where it was asked for.

**The luminance rule had to give, and the count is what was doing the work.**
Q16's luminance is 0.282 against a `LIGHT` of 0.58, and that is not a near miss:
no purple in this gamut reaches 0.35, so white could never appear on any purple
while the rule was one threshold. The first attempt was a per-hue exception,
which was the wrong shape — a rule naming one colour has stopped explaining
anything.

What actually distinguishes the cases is **how many achromatic squares there
are**. Two whites assert the target is light, and answer to `LIGHT`; one white
tints a mix without claiming anything, and answers only to `TINT_LIGHT` near the
gamut floor. `purple white white` on 0.29 fails, `blue purple white` on 0.28
passes, and nothing had to be named. `TINT_DARK` mirrors it for black.

## Two structural faults, found by asking where the purple came from

Justin asked what was causing so much `blue purple purple`. Two bugs, and they
compounded.

**The reading table never deduplicated.** A monochrome anchor makes three of the
six slots the same multiset — with `high` at `(purple, purple)`, three separate
slots are all blue-purple-purple — and each was paid territory separately, so
one reading took 64% of its interval. That is the flood. It was never a purple
problem: `green green yellow` at 95 colours was the same fault at the other end
of the wheel, and the largest bucket in the gamut.

**The weights never matched their own stated intent.** Territory is meant to go
in proportion to the arrangements a reading affords, but every mixed reading
scored 3 — right for a pair, wrong for three distinct squares, which afford 6.
The readings carrying the most identity were being short-changed.

Deduplicating and weighting by the real arrangement count fixes both. The
largest bucket falls from 95 to 77 and `blue purple purple` from 77 to 59.

## The rules now prune, rather than only report

A reading that violates for a given colour is passed over, and the next takes
it. Anchors declare intent, the harness enforces it, and the two can no longer
disagree in silence — violations go to **zero**, including the 53 white and 11
black ones that had been standing since the anchors were written.

This is also what lets white into a band at all. Any anchor carrying white as a
secondary necessarily emits `X white white` and `X X white` from two of its six
slots: the table doubles secondaries and there is no way to ask for one without
the others. Pruning drops the doubled white where the target is too dark to
carry it, and the colour falls through to the single-white reading that was
wanted.

## The greens, and a fault the sheet shows but the audit cannot

Justin asked whether the lightest greens were at 8:PQR or 9:C–H, or whether
8:ST and 9:AB were genuinely darker than both.

Neither, and no. The **colour** luminance rises monotonically across both rows,
0.654 at 8:A to 0.681 at 9:T, and never falls. What dips is the **mark**: the
triple's own mix runs 0.953 at 8:P–R, 0.889 at 8:S through 9:A, and 0.953 again
at 9:B–F. Four cells of one-white reading sandwiched inside a two-white band,
while the colour underneath climbs the whole way.

The cause is the anchor at 138, `(green, white)`. The interval below it ends on
`green white white`; the interval above it *restarts* at that anchor's own
triple, `green green white`, before returning to `green white white`. The
sequence across the boundary is ggw, gww, ggw, gww — the walk doubles back.

**This is a cross-interval fault and it is not fixed.** Every interval walks
from its own low anchor with no knowledge of where the previous one ended, so
wherever one overshoots past the shared anchor's own triple, the next steps back
onto it. The audit cannot see this: every reading involved is individually
legal, and only the sequence is wrong. The fix is to suppress an interval's
opening reading when the previous interval has already passed it — a change to
how intervals join, not to any one of them.

## What is still open

- The mark-luminance sawtooth at anchor 138, above. It will exist at every
  anchor where consecutive anchors share a primary.
- `black brown red` is newly reachable at hues 5 to 10, 15 colours, and has
  never been judged by eye.
- R16 and S16 land on `purple purple white`, not the `blue purple white` asked
  for. Forbidding `purple purple white` would route them there, but Justin has
  since said that triple is fine, so the two directions disagree and this is
  left as it falls.
- `blue black purple` is 15 colours at hues 245 to 250, down from 23 — narrowed
  by the 255 anchor change, and worth a look on the sheet.
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

```bash
python3 shaped.py
```

Checks the shape channel against the whole gamut — determinism, arrangement
left untouched, no circled neutral, three characters out — and reports spread.

```bash
python3 sheet.py --verify && python3 sheet.py sheet8.svg
```

Reproduces `sheet4.svg` byte for byte, then renders the current mapping.
`--sheet5` renders with `anchored2` instead, for an A/B against the corrections.

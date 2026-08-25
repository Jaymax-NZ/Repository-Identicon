# Where the wheel stands, and what to avoid

State: **`wheel75.svg`**, reproducible from `hand.tsv`. 63 tiles on the ring,
**360 of 360 degrees, no gaps, nothing on the ring flagged.** 8 tiers deep, the
innermost three of them the rejected set.

`python3 wheel.py --painted --out <name>.svg` renders and prints a checklist.
Everything is authored against `--painted`; the Unicode palette is a different
arrangement and solving anything against it will not transfer.

## The ring is closed

It went 350 -> 360 over six rounds, and every one of those ten degrees went into
a tile rather than being spread or pushed: #2, #10, #3, #54, #86, #120, #131,
#5, #6, #1, and a #42 four degrees wider than the #9 it replaced.

**Nothing is spare.** Every further insert now costs a tile its seat. A
replacement of equal width is free; anything else is a decision about what comes
off.

The last two inserts are the push rule doing its own arithmetic, and are the
model for how to do this by hand:

- #131 is one degree wide. The seventeen tiles from #92 to #116 slid
  anticlockwise by exactly one, and the push died in the 1.055 gap at 135.3,
  leaving 0.055.
- #1 (`red red red`) is also one degree, and the two remaining gaps came to
  0.945 and 0.055 -- exactly it, between them. #8 and the three behind it gave
  up the 0.945 anticlockwise; #7 and the sixteen in front gave up the 0.055
  clockwise. It landed at 34.876 against its own hue of 35.06.

## Do the edits by hand. This is still the whole lesson.

`hand.tsv` is pure placement. One line per tile, carrying the angle it is
actually drawn at. To move a tile, change its number. To close a gap, subtract
it from that tile and from every tile meant to travel with it. Work the
arithmetic out directly and write the numbers.

The op code is still in `wheel.py` and nothing calls it. It can go.

## The rule the pushes follow

Each solid run slides just clear of the one in front of it and no further, so
the push dies the moment a run has room, and what it spends on the way is the
air between runs. Runs move rigidly -- a seam under `FLUSH_TOL` is not a gap, so
it is not somewhere to absorb a push either.

Do this arithmetic yourself and write the resulting angles. Do not rebuild it as
an operation.

## `sink`: the rejected set

`sink <n> [deg]` puts a tile in the inner-inner band. It is the only verdict
that moves a tile in angle without seating it, because the rejects are read as a
block and never against the tile beside them.

**The band is read off the colour, not written down.** `sunk_band` cuts on
measured luminance -- `SUNK_DARK_MAX = 50.5`, `SUNK_LIGHT_MIN = 63.0` -- so the
file cannot disagree with the drawing about which ring a tile is in. Both cuts
sit in a real hole in the distribution rather than at the block that moved them:
48.7 would have taken `red green black` at 48.6 and left `orange blue black` at
48.8 behind, which is a tenth of a point and nothing anybody can see.

Drawn outermost first: **neither (15), too light (20), too dark (14)**, the dark
one hard against the middle. The angles in the file are only what keeps each
band to a single row; the budget is 30 degrees and only the `neither` band needs
much of it (#27 at -16.50, #68 at -11.19).

Each band's floor is the depth the band above ended at, so no tile can surface
out of its own band however much room is going in the one above it.

## The harness is calibrated against a gamut that no longer exists

The single-achromatic tint rule was removed this session, and the reason
generalises. **The version 2 gamut runs 0.2012 to 0.4911.**

- `TINT_DARK = 0.75` was unreachable. The black-on rule had never fired, not
  once in 165.
- `TINT_LIGHT = 0.25` was meant to sit five hundredths inside the light end.
  Against this gamut it sat a fifth of the way up the whole range, and took
  eight triples including `red red white` and `red brown white`, both of which
  Justin reads as fine.

**`DARK = 0.33` and `LIGHT = 0.58` are stated against the same dead gamut, and
0.58 is above its maximum.** So `WW` currently fires on every two-white triple
regardless of hue and is not discriminating either. That is the next one to
look at. 48 of 165 are still flagged.

## Traps, all of them paid for

- **A tile coming back onto the ring must have its old tier line deleted.** The
  tier lines sit below the ring block, so they win. This shows as a hole in the
  ring rather than as an error.
- **`AUTO_FILL` is off, and must stay off.** A gap is a decision.
- **Verify from the seats, not from the code.** Dump the ring before and after
  and diff it. Every edit across these sessions was checked that way.
- **`FLUSH_TOL = 0.2` is set from Justin's eye**, bracketed by the seam at 0.106
  he could not see and the one at 0.380 he asked to close.
- **One render per turn**, one SVG per round. Iterate with a seats dump, which
  renders nothing.
- **Solve packing against the palette that gets rendered.** The sunk set was
  first solved against the Unicode palette: seven nudges, and a spare row
  holding one tile, because three of those triples read as no colour at all
  there and were never given an angle to pack.

## What Justin's shorthand means

    ↻ / ↺        clockwise / anticlockwise
    ⇑ / ⇓        onto the ring / off it
    ↑ / ↓        a tier out / in
    "X in for Y" X takes Y's slot; if X is wider, the difference is pushed
    "the train"  everything visually coupled, not everything arithmetically flush

Ask when a tile-list and the arithmetic disagree -- and check a number against
the ring before assuming it. `#16` for `#81` was caught that way, one being on
the ring and every other name in the list being off it.

## Outstanding

Nothing queued. The `WW`/`DARK`/`LIGHT` recalibration above is the one thing
with a reason behind it rather than a preference.

`work-in-progress/` holds this session's wheel66 through wheel75. Only wheel75
is committed, which is the convention -- one render per commit. The rest, and
everything from earlier sessions, is untracked and safe to delete; `next_path`
takes max + 1.

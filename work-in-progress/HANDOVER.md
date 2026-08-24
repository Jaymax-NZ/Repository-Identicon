# Where the wheel stands, and what to avoid

State: **`wheel65.svg`**, reproducible from `hand.tsv`. 57 tiles on the ring,
350 of 360 degrees (97%), 7 tiers deep. `python3 wheel.py --painted` renders and
prints a checklist.

**The ring is closed up.** Six gaps remain, 1.3 to 2.0 degrees, and every other
tile is flush with its neighbour. The seven seams under a degree were closed and
their 1.282 degrees spread evenly over the six that stayed. The ring is also
rotated to the best rigid fit against the hues its blends read as -- mean offset
2.35 degrees, and no rotation improves it. Any offset left is placement.

So the next change is a judgement about *which triple sits where*, not about
tidying. Closing a gap now means taking the degrees from another gap.

## Do the edits by hand. This is the whole lesson.

`hand.tsv` is now **pure placement**: one `ring <n> <deg>` line per tile,
carrying the angle that tile is actually drawn at. To move a tile, change its
number. To close a gap, subtract it from that tile and from every tile meant to
travel with it. Work the arithmetic out directly and write the numbers.

It used to be a *history* -- a hundred-odd `swap`, `roll`, `press` and `insert`
lines, each shoving tiles that earlier lines had placed. Two things were wrong
with that, and both cost whole sessions:

- **An angle did not mean the angle.** Placements are all resolved before any op
  runs, so writing down the angle you can see on the drawing collided with where
  that tile still was at placement time, and it got pushed somewhere else.
- **Every op was a small algorithm**, and a small algorithm with a sign error
  moves forty tiles. One did.

The op code is still in `wheel.py` and nothing calls it. It can go.

## The rule the pushes followed, if you ever need it again

Justin's tile-lists are what established it, and they pin it exactly: each solid
run slides just clear of the one in front of it and no further, so the push dies
the moment a run has room, and what it spends on the way is the air between
runs. Runs move rigidly -- a seam under `FLUSH_TOL` is not a gap, so it is not
somewhere to absorb a push either.

Do this arithmetic yourself and write the resulting angles. Do not rebuild it as
an operation.

## Traps, all of them paid for

- **A tile coming back onto the ring must have its old tier line deleted.** The
  tier lines sit below the ring block, so they win. This bit twice, and it shows
  as a hole in the ring rather than as an error.
- **`AUTO_FILL` is off, and must stay off.** It filled any leftover arc with the
  best unplaced triple. Once the file became pure placement it colonised every
  gap the moment one opened -- eject a tile, the next-best candidate takes the
  slot; eject that, the one after it arrives. A gap is a decision.
- **Verify from the seats, not from the code.** Dump the ring before and after
  and diff it. Every edit this session was checked that way, and it caught a
  sign error, a wrap-around bug and two overridden tiles before any render.
- **`FLUSH_TOL = 0.2` is set from Justin's eye**, bracketed by two readings: the
  seam at 0.106 he could not see, the one at 0.380 he asked to close.
- **One render per turn.** Iterate with a seats dump, which renders nothing.

## What Justin's shorthand means

    ↻ / ↺        clockwise / anticlockwise
    ⇑ / ⇓        onto the ring / off it
    ↑ / ↓        a tier out / in
    "X in for Y" X takes Y's slot; if X is wider, the difference is pushed
    "the train"  everything visually coupled, not everything arithmetically flush

Ask when a tile-list and the arithmetic disagree -- but do not ask about which
side of a gap a sub-degree sliver falls unless it is genuinely visible.

## Outstanding

Nothing queued. Two flagged tiles remain on the ring; 56 of the 165 are flagged
by the harness overall, which is a filter worth looking at rather than through
(see `wheel.py`'s `catalogue` docstring -- version 1 luminance thresholds
against a version 2 ring).

Everything in `work-in-progress/` is uncommitted, including this session's
wheel57 through wheel64. All eight were shown. Junk renders never shown to
anyone, safe to delete: wheel22-24, 26, 28, 30-31, 33-38, 40, 43-47, 55, 56.
`next_path` takes max + 1, so deleting them is safe.

# Page 3, Geometry — the change set

Accumulated, not executed. Rulings land here as numbered rules, facts are
checked against the source before anything is written.

Facts below were read from `repository-identicon.py` on 2026-09-02.


## What page 3 holds today

Two functions and a record of removed code.

```
[GEOMETRY]        note: "nothing here takes a key"
  3.5  canvas_edge( block, border)
  3.7  large_geometry( canvas)
  3.8  gone to Console-Colophon
[WHO USES THEM]   note: about five deleted derived names
  → c_show   → render_rgba   → artifact_bytes   → c_render
```

**Neither function touches page 1 or page 2.** `canvas_edge` is
`MATRIX_SIZE * block + 2 * border`; `large_geometry` is that inverted. Both
take integers and return integers, and neither sees a seed, a digest, a matrix
or a colour. The only tie to the rest of the diagram is `MATRIX_SIZE`, and it
is inside the function bodies rather than on the page.

A reader cannot tell from this page what either function is for.


## Rule 1 — the two size families are separate, and only one is in scope

**`@4x` exists for the 1-5 px-per-block family, and the record says so.** Four
commits:

| | |
|---|---|
| `0e2f2af` | adds a 4x raster at 1024px -- four times the *canvas* |
| `3299aa6` | reverts it: "it answered the wrong question" |
| `11b022a` | re-adds it |
| `9976339` | "Scale the blocks for @4x, not the canvas" |

**`@4x` is for a context whose pixels are not CSS pixels.**

`BLOCKS = (1, 2, 3, 4, 5)` is a range in **CSS pixels**. That is an assumption
the numbers do not carry and nothing can detect, and it is the fact that keeps
being lost. Where a pixel is a device pixel instead, one to five is four times
too small, and `@4x` is the answer.

`9976339` states why it must be the same drawing with every pixel repeated,
rather than a mark redrawn larger:

> 1024 landed on cell 186 margin 47 where four times the 256-pixel render is
> cell 188 margin 40. The two files were different drawings of one mark.

So it is `ARTIFACT_BLOCK * ARTIFACT_SCALE` with `SCALED_BORDER` -- block 20,
border 2, canvas 104 -- and it belongs with the block family, which is moving
to a per-consumer setting rather than a per-repository one.

**It is not an on-request size**, and that is the sharper reason it does not
belong in `imageSizes`. A requested canvas is something a consumer asks for.
`@4x` follows from the block family: a consumer does not want 104 pixels, it
wants the block-5 mark where a pixel is smaller.

It should be named for that rather than for the multiplier -- `@4x` says how
much and not what for, which is why the reason was recoverable from neither
the filename nor the constant. Naming it is Justin's, not recorded here.

**Provenance, since this was got wrong three times in one session:** the
commit history does *not* say what it is for. `0e2f2af` adds it for
resampling-incapable native toolkits and is reverted. `3299aa6` reverts it and
says only which end of the range it serves. `11b022a` re-adds it with "a
native UI wants the pixels", which names a symptom. The CSS-pixel assumption
is in none of them, and reading a rationale off the reverted commit and
attaching it to the accepted one produced a confident, wrong answer.

**It is therefore out of scope here**, and the conflict it raised against a
1:50 floor goes with it. Of the canvases a consumer actually fixes, 128 and
256, the rule below reproduces both exactly.

### Two axes, and a size request cannot express a density asset

| | asks for | gets |
|---|---|---|
| size request | fill this many pixels | whatever drawing fits |
| density asset | this drawing, every pixel repeated N times | whatever size falls out |

Requesting 104px through `imageSizes` gives block 19 with borders 4/5. `@4x`
is block 20 with border 2. **Same canvas, different drawing** -- which is
`9976339`'s defect arriving by a new route, and a native UI swapping between
the 27px mark and a 104px one built this way would see them flip.

So `imageSizes` must not own `@4x`. When the block family moves to a
per-consumer setting the HiDPI need moves with it, expressed as
`(block, scale)`. It cannot be expressed as a canvas: the canvas is a
consequence, and if the block family shifts, the number a consumer would have
to ask for changes while its need does not.

**`README.md` still carries the misreading that caused the revert.** It calls
`@4x` "the mark magnified 4x, 104px". The mark magnified four times would be
108px, and multiplying the canvas by four is the error `3299aa6` was written
to undo. The block is multiplied by four and the border by two -- the comment
at `ARTIFACT_SCALE` gives the reason, that a quadrupled border spends the new
pixels on empty edge. The code was corrected two commits later; the sentence
never was.


## Rule 2 — a requested canvas is an outer dimension, and the geometry is solved for it

```
floor  = ceil(canvas / 50)
block  = (canvas - 2 * floor) // 5
pad    = canvas - 5 * block
borders = pad // 2, pad - pad // 2
```

**The two borders may differ by one pixel, and that is what makes it work.**
Requiring a single border thickness forces `5 * block + 2 * border == canvas`
exactly, which fixes the border modulo 5. That is why `large_geometry` accepts
only multiples of 32. Letting the odd pixel fall on one side removes the
constraint entirely.

Verified over 7px to 2048px:

| | equal borders | odd pixel allowed |
|---|---|---|
| sizes with an exact geometry | 2040 of 2042 | **2042 of 2042** |
| no solution at | 8px, 10px | none |
| border ratio range | 1:12 to 1:50 | close to the floor at every size |

Reproduces `27 -> block 5, borders 1/1`, `128 -> 24, 4/4` and
`256 -> 48, 8/8`.

**It also rescues 48px.** The comment at `LARGE_CANVASES` says 16 and 48 are
"deliberately absent" because parity forces borders of 18.8% and 8.3%. Under
this rule 48 is block 9 with borders 1/2, a ratio of 1:48. The comment becomes
false for 48 and stays true for 16, which is block 2 with borders 3/3.

`geometry_for_canvas( canvas)` replaces `large_geometry`, whose name describes
a property -- "large" -- that was only ever "one of the two sizes we happened
to ship".

Open: the floor is `1:50` as stated. Nothing shipped constrains it now that
`@4x` is out of scope, so it is a free choice rather than a fitted one.


## Rule 3 — the requested sizes are a third section of `settings.json`

```json
"imageSizes": [128, 256]
```

Top level, beside `identicon` and `renders`. Not `identicon.current`, which
holds derived facts and a request is not derived. Not `renders`, which holds
spellings of those facts.

**Sizes, not filenames.** The name follows from the size, and storing both is
two things that can disagree -- the same reason the colour map holds no emoji
and the matrix is stored as booleans.

`request_image_size( repository_root, canvas)` appends one, and refuses a
canvas too small to carry a block of at least one pixel.

`LARGE_CANVASES` stops being a constant and becomes the default contents of
the array.


## Rule 4 — surplus and staleness are both out of scope, and one needs a test

**A PNG whose size is no longer requested: ignore completely for now.**
Reporting it is `doctor`'s job when it comes to that.

**Staleness: ignore altogether for this function.** It writes what is asked
for and does not ask whether what is there is current.

**But the ordering needs testing before it ships.** The question is when a PNG
has to be rebuilt because the mark moved rather than because the size list
changed, and the resolution is probably sequencing rather than a check. Cases
to run:

- request a new size, then reseed
- reseed, then request a new size
- reseed with several sizes already present
- request a size that is already present, after a colour map change

Two mechanisms to compare, neither chosen: **archive the prior set** when the
mark moves, the way `keep_prior` already sets one file aside, or **delete the
set** and let the next `apply` rebuild it. Deleting is simpler and loses the
rollback; archiving keeps it and needs a naming rule for a whole directory
rather than one file.


## Consequence for the page

With a solver, a request list and a producer, geometry is a subsystem rather
than two multiplications, and page 3 stands as a page.

Before this, the recommendation was to fold it into page 4 as a section --
its callers are all there, and two integer functions do not earn a page. That
is withdrawn.

Still to fix on the page whatever happens:

- the section note says `key`, a concept page 1 deleted, and says what the
  functions do not do rather than what they do
- `WHO USES THEM` is a collecting group of four off-page arrows, the same
  defect as `WHAT COMES OUT` on pages 1 and 2
- its note is about five deleted derived names, which is page 7 material
- `→ c_show` says "show prints all four names"; `cmd_show` prints the seed and
  the colour and touches no geometry, so the arrow is wrong, not just its label
- the numbering is 3.5, 3.7, 3.8 -- gaps left by deletions

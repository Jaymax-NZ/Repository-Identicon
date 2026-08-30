# Where the wheel stands, and what to avoid

State: **`wheel81.svg`**, reproducible from `wheel.tsv`, with `wheel80.svg` the
same ring drawn alone. 63 tiles on the ring, **360 of 360 degrees, no gaps,
nothing on the ring flagged.** 8 tiers deep, the innermost three of them the
rejected set.

## What is left, and why

Four files. `wheel.tsv` is the wheel, `in-use.tsv` is the mapping generated from
it for a consumer, `wheel.py` draws both, `perceptual.py` is the harness.

Everything else went this session, after tracing a render to find what could
still execute rather than reading the code and guessing:

- **The op machinery** -- `swap`, `roll`, `slide`, `insert`, `press`, and the
  `run_from`/`seam` helpers. Nothing emits those verbs any more.
- **The automatic pass** -- the search for the best triple per stretch of hue,
  the nudge to sit flush, the push that moved a neighbour aside, and the
  auto-fill of leftover arcs. `propose` is now a lookup with a collision guard.
- **`MAX_NUDGE`, `NUDGE_STEP`, `MAX_PUSH`, `AUTO_FILL`, `FLUSH_TOL`**, and the
  `score`/`base_square`/`BASE_FAVOUR` ranking the auto-fill used.
- **`bench.tsv`** and its tooling (`read_bench`, `pool`, `--refill`). It was the
  version 1 roster: sixteen of the fifty blocks it placed are off this ring and
  twenty-nine of the current sixty-three it never saw.
- **`share`, `hue_of`, `chroma_of`**, referenced from nowhere; `mix.py`,
  `shaped.py`, `mixes.svg`; and eighty wheel renders.

`wheel.py` went from 89KB to 71KB and **the render is byte-for-byte identical**
to the one before the purge. That is the check that matters: `cmp` on the SVG.

**`in-use.tsv` was stale, not merely unused.** It was generated from `bench.tsv`,
so the one file aimed at a consumer described the version 1 ring -- 51 arcs
against the current 63 tiles. `--reference` reads the ring lines now, and the
file has been regenerated: 64 rows for 63 blocks, the zero-straddler split in
two, tiling asserted on the way out.

The collision guard in `propose` stays although nothing trips it. It is what
says so when an edit to the file overlaps two tiles, and a silently overlapping
ring is the failure the whole flattening was done to avoid.

## One mapping version, and a `.grid` artifact

**Versions 0 to 2 are withdrawn.** Not retired -- withdrawn. The rule is that no
rule reaching a *release* ever retires, and `VERSION` is `0.0.build`, so nothing
had earned that protection. `SPEC.md`, `CONTRIBUTING.md`, the code and the tests
all say it that way now; if `VERSION` ever leaves `0.0.*` this stops being
available and every shipped rule has to stay.

A key at any other version raises `UnknownMappingVersion` rather than being
drawn with today's rule -- redrawing it would move a mark nobody asked to move.
The CLI catches it and prints one line naming `remap`.

**This repository is one of the stranded.** Its key reads
`2:github.com/justin-maxwell/repository-identicon`, so `show` and `apply` refuse
it. `apply --remap` keeps the seed and moves it to 3; the colour goes from
`#00948c` to `#9f7a00`. Not done -- it is a deliberate identity change.

**`.grid` joins the artifacts**: five lines of `01010`, the spelling
`vectors.json` uses. With `.colour` beside it that is the whole mark as text,
enough for a consumer with no PNG decoder and no SVG parser -- checked by
feeding both back through `text-identicon.py`. It is not in the key file, and
must not go there: that file is the source of truth and is left byte-for-byte
alone, so a derived value inside it would go stale with nothing entitled to fix
it.

## The refactor pass

6,152 lines to 5,816, all of it prose. Behaviour verified unchanged by loading
each module beside its committed self and comparing outputs across every key,
grid, block size and border -- zero differences -- plus a byte-identical wheel
render. Module docstrings orient rather than argue; history is compressed to the
imperative it implies; measured facts and traps kept.

**`CONTRIBUTING.md` already stated the rule** -- comments explain the decision,
not the mechanism, and "what was tried and failed" is explicitly sanctioned. The
target is terseness, not deletion of rationale.

## Diagrams

`routines.drawio` is the real call graph: uncompressed draw.io XML, so it opens
in the browser or the VS Code extension, and moving a box returns coordinates
that can be read back. `flow-routines.svg` is the same thing rendered.

Two earlier diagrams were deleted for drawing the proposal as though it shipped.
**`in-use.tsv` and the circles are not in the product.** The shipped triple
still comes from `triple_indices`, the fidelity search; `shaped.py` is the
replacement and nothing imports it. Only the order-from-the-grid work landed.

Also worth knowing, because it drives the shape of that graph: **there is no
identicon value anywhere.** Nothing holds `(key, grid, colour)`, so every
renderer re-derives from the key and `_digest` runs again each time. `_colour_for`
is a half-fix for the colour half of it.

## The wheel is in the generator now

**Mapping version 3** carries the blue-green compression into
`repository-identicon.py`. The warp is `(215, 50, 4)` -- the same closed form
the wheel uses, checked against `wheel.warp_theta` over 36,000 samples at zero
disagreement. It is a new colour rule rather than an edit to version 2, because
the key stamps the rule and old rules never retire; ten new vectors came with
it, which `load_vectors` enforces.

**There are two version numbers now, not three.** `VERSION` is the tool, at
`0.0.build`. `MAPPING_VERSION` is the colour rule, in every key, now the dotted
string `0.3` -- which is the number the wheel in `wheel.tsv` already carried.
The rule and the wheel were solved together, so they are one thing numbered
once; the bare integer `3` was withdrawn as a draft and re-issued as `0.3`,
which changed every mark, because the version is inside the string being hashed.
`--version` prints both because a report about a colour means the second.

**`in-use.tsv` is indexed by the draw, not by the hue.** Those were the same
number until version 3 warped one into the other. A consumer indexing by hue is
wrong by up to a third of the wheel around the blue-greens -- the file says so
in its own header.

**The warp strength was re-examined and stands.** A gentler warp gives back some
teal and costs tricolour coverage; `coverage3.svg` is that comparison, and the
aqua-cyan stretch is already the sparsest on the ring. Anything gentler starves
it further. `peak = 4` is not over-tuned.

Two things that were proposed and are dead, so they are not proposed again:
reallocating the draw by how many distinct `#rrggbb` exist -- that counts values
in a domain the eye does not work in, and measured worst of five for tiling --
and moving `DARK`/`LIGHT`, which are degenerate and right on all fourteen
triples they touch.

## The order and the shapes come from the grid

They were hashed from `#rrggbb`, so both channels were functions of an *output*
of the mapping and could not separate two projects it had already put in the
same place. Over four thousand projects that yielded 696 distinct marks against
1,013 distinct colours -- the channel was subtracting. From the grid it yields
1,404.

The grid, not the key's digest: they measure the same, and the grid is already
fifteen bits of that digest sitting at the call site, so `text(grid, rgb)` still
needs no key and stays vendorable alone.

No mapping bump. The vectors pin grid and colour only, and `SPEC.md` records the
triple as not yet normative, so nothing pinned moved.

**The measurement that hid this swept the gamut, one sample per colour.** That
makes every mark look distinct however many projects pile onto one. `shaped.py`
samples projects now. Measure over the population, not the space.

## `glyphs.py`: the squares as they are actually painted

Noto paints every square in three layers -- `⬛` is `#575757` over `#424242`
under a `#787878` corner highlight, and is not black at all. Flat rectangles from
`PAINTED` made it vanish on a dark ground, which is not what any reader sees.
`glyphs.py` reads the real outlines out of the COLRv1 font and emits them as
plain SVG paths, defined once and referenced.

`PAINTED` itself is not at fault and was not changed: it samples the centre of
each glyph across seven vendor sets, which is the right way to ask what hue a
square reads as. It is the wrong way to ask whether one is visible, and every
vendor applies edge treatment that settles that question -- see the note added
to `emoji-square-colours.md` § 6.

## `wheel.tsv` is the wheel

One file, all 165 tiles, one line each. `hand.tsv` is gone -- it held only what
had been argued about, and the other 34 were placed by the packer falling
through to its default. Nothing was lost that way, because the packing is
deterministic, but the file did not *say* where a third of the tiles were.
`purple purple white` sat in a tier with its argument written down in
`perceptual.py` and no line here at all. `tier` is that default written down.

**The number is the line it sits on, and the lines run clockwise from the top.**
The ring is 1 to 63 and walks the hue circle; the tiers follow, outward-in and
clockwise within each; then the three sunk bands as drawn; then the six that
average to a neutral. To renumber after moving a tile, sort the file.

The triple is on the line as well as the number, and neither is trusted alone:
the engine reads the names, and the number is checked against its own position,
so a dropped line says so instead of silently shifting everything after it.

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

`wheel.tsv` is pure placement. One line per tile, carrying the angle it is
actually drawn at. To move a tile, change its angle. To close a gap, subtract
it from that tile and from every tile meant to travel with it. Work the
arithmetic out directly and write the numbers.

Reversing two neighbours is not an exchange of angles unless they are the same
width. #60 and #61 -- `red purple brown` and `red red blue` -- were reversed
this session: one is a three-colour tile at 8 degrees and the other a two at 4,
so the pair keeps the extent it had and both centres move to fit the new order.

The op code is gone. There is no operation to reach for.

## The rule a push used to follow, for when you do it by hand

Each solid run slides just clear of the one in front of it and no further, so
the push dies the moment a run has room, and what it spends on the way is the
air between runs. Runs move rigidly -- a seam too small to see is not a gap, so
it is not somewhere to absorb a push either.

That was `FLUSH_TOL = 0.2`, set from Justin's eye and bracketed by a seam at
0.106 he could not see and one at 0.380 he asked to close. The constant is gone
with the code that consulted it; the reading is kept here because it is a fact
about what he can see, and the next person doing this arithmetic wants it.

Do the arithmetic yourself and write the resulting angles. Do not rebuild it as
an operation.

## `sink`: the rejected set

`sink <deg>` puts a tile in the inner-inner band. It is the only verdict
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
much of it -- `red green purple` and `orange blue purple` carry the widest.

Each band's floor is the depth the band above ended at, so no tile can surface
out of its own band however much room is going in the one above it.

## The harness is calibrated against a gamut that no longer exists

**The version 2 gamut runs 0.2012 to 0.4911.** The single-achromatic tint rule
was removed for that reason: `TINT_DARK = 0.75` was unreachable and had never
fired once in 165, and `TINT_LIGHT = 0.25` was meant to sit five hundredths
inside the light end but sat a fifth of the way up the whole range, taking eight
triples including `red red white` and `red brown white`, both of which Justin
reads as fine.

`DARK` and `LIGHT` are stated against the same dead gamut and 0.58 is above its
maximum, so `WW` fires on every two-white triple regardless of hue. **Read the
Outstanding section before touching them** -- the reasoning does not generalise
the way it did for the tints, and I assumed it did. 48 of 165 are flagged.

## Traps, all of them paid for

- **A tile has exactly one line, so a tile coming back onto the ring is an edit
  to its own line, not a new one.** Under `hand.tsv` a stale tier line below the
  ring block silently won and showed as a hole in the ring; now a triple named
  twice is reported.
- **The offsets and tier 0's numbers changed places this session.** The ticks
  are in the clear gap inside the ring with the leader running outward to the
  tile's inner edge; the numbers are in the corridor between the ring and the
  gamut, where a number sits between the ring it names and the gamut it is being
  judged against.
- **A gap is a decision, and nothing fills one.** `AUTO_FILL` used to guard
  this and is gone; there is now no code that could colonise a gap.
- **Verify from the seats, not from the code.** Dump the ring before and after
  and diff it. Every edit across these sessions was checked that way, and the
  purge was checked by `cmp` on the SVG either side of it.
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

**Numbers from before wheel77 mean different tiles.** Everything written in the
earlier commit messages, and in the notes above about how the ring was closed,
is in the old palette-index numbering. Read those by the triple, not the number.

## Outstanding

**`DARK` and `LIGHT` are degenerate and correct, and I got this wrong once.**
They are absolute luminances against the version 1 gamut, and `LIGHT = 0.58` is
above the version 2 maximum, so the two-white rule fires at every hue and
measures nothing. I proposed moving the cut to 0.38, the middle of the hole in
the distribution, and that was wrong: **all seven two-white triples were sunk by
eye**, so the rule agrees with you seven times out of seven, and a cut at 0.38
would pass `blue`, `green`, `yellow` and `orange` with two whites -- every one of
them rejected. Part of my case for it was `REQUIRED`, which has since gone.

Two blacks: the rule flags six of seven. The one it passes, `red black black`,
was sunk anyway.

So on all fourteen triples these rules speak to, refusing outright is what the
eye did. What that suggests is not a new threshold but no threshold: on a gamut
this narrow and this uniformly mid-lightness, two achromatics always overclaim,
and the honest rule is the count alone. **That is a rule change and wants your
eye on it**, not a constant nudged in the dark.

`REQUIRED` is gone -- twelve triples listed as having to be reachable, which was
a patch for an automatic chooser that kept losing them. There is no chooser now,
and every one of the 165 has a line saying where it is, so an absence is written
down rather than something to be detected. It had also stopped agreeing with the
eye that wrote it: three of the twelve were later sunk, `blue white white` among
them -- required as "the light blues", refused as too light to carry a hue.

`work-in-progress/` holds `wheel81.svg` and `wheel80.svg`, `coverage3.svg` for
the warp-strength decision, `routines.drawio` and `flow-routines.svg` for the
call graph, and `sheet3`/`sheet4` with their dark pairs -- the
400-project sheets in Noto's squares and in the weighted average. `next_path`
takes max + 1, so the next wheel render is wheel82.

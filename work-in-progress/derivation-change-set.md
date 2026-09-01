# Page 2, Derivation — the change set

**Built, 2026-09-01.** Every rule below is in the code, in six commits from
`The 5x5 is a matrix` to `Hold the shipped colour to the wheel it was drawn
from`. What follows is the record of what was decided and why, not a plan.

Four stages, each ending green, so a failure was always bisectable to one
intent:

| stage | what it did | what proved it |
|---|---|---|
| A | renames only | all 44 fixture artifacts byte-identical, and git recorded the fixture files as renames rather than modifications |
| B | `settings.json` restructured, six artifacts became fields | the five surviving fixtures per seed untouched; only deletions under `tests/fixtures/` |
| C | the colour map ships, the tricolour is three slices | 63 blocks keep their colours and numbers across the rotation; 1440 of 1440 ring segments still match |
| D | the wheel validator | 5 tests, 2890 subtests, against the picture rather than the arithmetic |

Ending state: 122 tests, 3470 subtests, and the diagram regenerates with no
warnings across all ten pages.

Two open questions were settled in the build rather than by a ruling, and
either could be reversed cheaply. `vectors.json` keeps the `01010` spelling of
the matrix rather than booleans, because a fixture file is read by a port
author and `01010` diffs a row at a time. The history timestamp is
`_changed_at()`, a function, so a test can replace it -- `settings.json` is
committed and a clock in it would make two runs of one change disagree.

Original preamble: accumulated, not executed. Same process as
`identity-change-set.md`: rulings land here as numbered rules, facts are
checked against the source before anything is written, and the whole set is
built at once.

Facts below were read from `repository-identicon.py` and `text-identicon.py`
on 2026-09-01.

**Every mark this repository has produced is test output.** Ruled 2026-09-01.
Changing what is drawn costs nothing, so `vectors.json` and
`tests/fixtures/` are regenerated whenever a rule below moves a mark.


## What the digest is actually spent on

`_digest( seed)` returns 32 lowercase hex characters. Two slices are read:

| characters | count | read by | as |
|---|---|---|---|
| 0–14 | 15 | `identicon_grid` | one nibble per cell, even is painted |
| 15–24 | 10 | nothing | — |
| 25–31 | 7 | `identicon_hue` | 28 bits over `0xfffffff` |

Ten hex characters, 40 bits, are never read. Rules 6 and 7 spend eight of them.

`identicon_grid`, `identicon_hue` and every renderer call `_digest( seed)`
separately. One `apply` hashes the seed at least four times.


## Rule 1 — sections get numbers, written by hand

`2.1.1`, `2.1.2`, `2.2.1`. Applies wherever a page has sections, so every page.

`$number=` stays hand-written in the `.mr` and `system-diagram.py` keeps
printing it unchanged. Computing numbers from section position was considered
and **ruled out**: a new diagram generator is being built from MarkRight in its
own repository, and this generator only has to last until that lands.


## Rule 2 — `hash_identicon_seed( identicon_seed)`

Rename `_digest`. Public, not underscore-private: `SPEC.md` pins it and a port
implements it.

It returns an object with the slices split out, so no caller indexes a string.
Four fields, one per component: the matrix slice, the colour slice, the
arrangement slice, the shape slice.


## Rule 3 — every routine is handed the part of the seed it uses

`identicon_matrix` and `identicon_hue` take their slice, not the seed. The seed
is hashed once per run, by the one caller that has it.

This is page 1's defect again in a different place: a value derived once is
currently re-derived by everyone who wants it.


## Rule 4 — the colour derivation is its own section

Seven boxes are colour today: `identicon_hue`, `warp_hue`, `gamut_chroma`,
`_oklch_to_linear`, `_encode`, `identicon_colour`, `_colour_for`. Four are
steps and three are leaf maths.

The section boundary is where the colour map starts applying. `identicon_hue`
returns a fraction of a turn and is map-independent. `HUE_WARP` is a constant
**of colour map 0** — the first thing downstream of the raw draw that a second
map would change. That boundary is invisible on the page now.

Consequence: `warp_hue` and everything after it are colour map 0's rules, and
they belong inside the section that carries the colour-map number.


## Rule 5 — 2.9 already fails with an error

Stated as `UnknownMappingVersion`; it was renamed to `UnknownColourMap` in the
page 1 work and is a `ValueError` subclass that is raised, never returned. The
ruling is already satisfied by the code, and `2.9` is its current number.

What is left is whether an exception class earns a box. Deciding it here sets
the rule for `NotSeeded` on page 1 and any later one.


## Rule 6 — the arrangement reads its own slice

`tricolour( rgb, matrix)` takes two arguments and neither is the seed:

- **which three colours** — `chosen_indices( rgb)`, a function of the drawn
  colour alone. Neighbouring colours choose the same three on purpose; that is
  what makes the emoji track the colour. This does not change.
- **what order** — `arrange( indices, matrix)`, which is
  `sorted( set( permutations( indices)))[ matrix_bits( matrix) % len( options)]`.
  `matrix_bits` re-reads columns 0–2 of every row: **the same fifteen bits the
  pattern is drawn from.**

So today there are two draws off the digest, not three, and the arrangement
carries nothing the pattern does not already carry. `arrange`'s docstring says
its slice is "disjoint from the one the hue comes from" — disjoint from the
*hue*, yes; identical to the *matrix*.

The arrangement takes its own hex character from the unread run instead.
`len( options)` is 1, 3 or 6, so four bits is enough. `matrix_bits` is then
called by nothing and goes.

**This supersedes `shaped.py`'s mixed-radix draw, and improves on its argument.**
`shaped.py` takes the arrangement as `matrix_bits % arrangements` and the shape
as `matrix_bits // arrangements`, and its docstring explains that dividing
rather than taking a second modulus is what keeps the two uncorrelated. True,
but both digits still come out of the pattern's fifteen bits. Separate slices
of the digest are independent by construction and need no argument at all.

Measured, from `shaped.py`'s own selftest over 4000 projects: moving these
channels off `#rrggbb` and onto the matrix took distinct marks from 696 to
1404. Moving them again onto their own slices should go further, because 1404
is bounded by how many distinct matrices there are.

The tricolour comes onto page 2. It is derived, it lands in `.identicon`, and
putting it on the rendering page is what hid this.


## Rule 7 — the shape channel is already written: ship `shaped.py`

`work-in-progress/shaped.py`, 262 lines with a selftest, built 2026-08-19.
Nothing imports it. It is not new work; it is unshipped work.

**All nine colours are circleable. `ALWAYS_SQUARE` is dead and must go.**

`shaped.py`'s MEDIUM-versus-LARGE argument records Justin's direction of
2026-08-19, and that direction was overruled: *"we reintroduced black and white
circles after some testing"*, in the wheel-tiers session. The reversal was
checked at the time against every branch of Repository-Identicon,
Claude-State-Panel and Claude-Colophon — **no commit anywhere introduces U+26AB
or U+26AA**, so the ruling stands and the code never followed it.

| | red | orange | yellow | green | blue | purple | brown | black | white |
|---|---|---|---|---|---|---|---|---|---|
| square | 🟥 | 🟧 | 🟨 | 🟩 | 🟦 | 🟪 | 🟫 | ⬛ | ⬜ |
| circle | 🔴 | 🟠 | 🟡 | 🟢 | 🔵 | 🟣 | 🟤 | ⚫ | ⚪ |

So the shape channel is a flat **three bits, eight combinations, on every
block** — not `1 << len( circleable( arranged))`. `circleable()` and
`ALWAYS_SQUARE` both go, and `shapes()` reads three bits unconditionally.

What that was already measured to be worth, in the same session:

| scale | blocks | marks | effective | 50% collision at |
|---|---|---|---|---|
| ×1.00 | 45 | 1464 | 2157 | 55 projects |
| ×1.25 | 41 | 1192 | 1727 | 49 |
| ×1.50 | 33 | 1016 | 1448 | 45 |
| ×2.00 | 29 | 848 | 1012 | 37 |

Against 1001 effective and 37 projects under the seven-circle exclusion.

What `shaped.py` needs to ship:

- `CIRCLES` moves into `text-identicon.py` beside `PALETTE`, which holds one
  glyph per colour today, and gains black and white.
- `glyphs.py` also holds seven circles and must gain the two, or the sheets
  cannot draw what the algorithm now emits.
- `emoji()`, `names()` and `key()` are the rendering surface; `tricolour()` and
  `tricolour_detail()` are what they replace.
- It loads `wheel.py` and `in-use.tsv` from `work-in-progress/`, which do not
  ship. See Rule 7b.

### Also stale in the same direction

`work-in-progress/README.md:100` still argues the 8/4/1 pricing overcounts,
"a real fault rather than a rounding", because "a triple with black in it is
worth twelve marks and is drawn as wide as one worth forty-eight". With all
nine circling, that fault does not exist. The paragraph and its figures come
out.

### Not page 2, recorded so it is not lost

From the same session: **"the tiles ABSOLUTELY do not get compressed. Later, we
will ensure the generator distributes evenly around the gamut wheel."** Page
angle is the draw; tiles keep their 8/4/1 degrees and the warp only decides
which hue sits under each tile. That is wheel and generator work, not
derivation.

This is not the octant/sextant lattice. Both lattices stay, both are still
always written, and which one a host renders is still a fact about its fonts.


## Rule 7b — the wheel's triple selection never shipped, and it is 96% of marks

Half of the third colour wheel is in the repo and half is not, and the split
runs straight through page 2.

**Shipped.** The hue warp. `HUE_WARP = (215.0, 50.0, 4.0)` in
`repository-identicon.py`, checked against `wheel.warp_theta` over 36,000
samples at zero disagreement. It is on page 2 as 2.4 `warp_hue` and in the
glossary as *the warp*. This is the colour work that shows, convolutedly.

**Not shipped.** The triple selection. `in-use.tsv` — the arc table
`wheel.py --reference` generates from `wheel.tsv` — is read by nothing but
`shaped.py`. The shipped `chosen_indices()` is still the fidelity search,
which commit 2bd7139 *"Make the target a specification, and fit the algorithm
to it instead"* was written to replace.

**Measured, 4000 seeds, this tree:**

```
3849 of 4000 seeds get a different triple (96.2%)
  #00967d  shipped 🟩🟫🟫  wheel 🟩🟫⬛
  #ec004e  shipped 🟥🟥🟪  wheel 🟥⬛⬜
  #009a4f  shipped 🟧🟧⬛  wheel 🟨🟩⬛
```

These are not two tunings of one rule. They are two mappings.

**And the fidelity search has a fault the wheel exists to avoid.**
`nearest_colour` measures full Oklab distance, lightness included, against the
nominal sRGB primaries in `PALETTE`. Marks are drawn at `MARK_LIGHTNESS = 0.60`;
pure green sits at L 0.87. So for `#009a4f`, a green:

| | L | distance |
|---|---|---|
| orange (255,165,0) | 0.793 | **0.2877** |
| green (0,255,0) | 0.866 | 0.3012 |

Its base colour is orange, on lightness alone. `#00967d`, a teal, bases on
brown. That is not a rounding.

`wheel.py` carries `PAINTED`, the glyph colours sampled across seven vendor
sets, which would close most of that gap — but it is `--painted` only and off
by default, so it is not the cause and not the fix.

**Ruled: the table ships, and the table is the colour map version.** This is
what the wheel project was for. `chosen_indices` and the fidelity search go.

`shaped.py`'s selftest calls `identicon.stamp_key(...)`, removed in the page 1
work, so it does not run today and must be repaired as part of shipping this.


## Rule 7c — the colour map is a numbered file

`colourMap: 0` names a shipped data file. Page 1 already ruled that colour map
files are filename-versioned with the digit and that a build learns which maps
it has by seeing which files are present; the arc table is what that ruling was
waiting for. `in-use.tsv` ships as `colour-map-0.tsv`, generated from
`wheel.tsv` by `wheel.py --reference`, which stays in `work-in-progress/`
because generating a map is not something a port does.

88 lines, 63 blocks, tiling 0–360 with no gap and no overlap. Self-contained:
reading it needs no `wheel.py`.

**The map is four things, and they are one version. Settled.**

`HUE_WARP`, `MARK_LIGHTNESS` and `MARK_CHROMA` are the transforms that turn the
default gamut circle into *this* ring of colours. The blockmap was then placed
over that ring by hand. So the blocks only mean what they mean against those
three constants: change any of them and the tiles sit over colours they were
not chosen for.

That is the derivation order. **At runtime the two are parallel, not
sequential** — both the colour and the tricolour are read from the same raw
draw, the table indexed by the draw and the colour by the warped draw. The ring
is the design-time link between them, not a step either one takes.

Measured, so the size of each transform is on record:

| transform | what it does to the circle |
|---|---|
| `HUE_WARP (215, 50, 4)` | reparametrises: 45° of draw at 180 becomes 103° of hue |
| `MARK_LIGHTNESS 0.60` | fixes the Oklab slice, so contrast holds at every hue |
| `MARK_CHROMA 0.26` | a cap, gamut-limited at **1280 of 1440** steps; the real chroma falls to 0.102 at 198° |

Chroma is not close to constant — 89% of the ring is below the cap — so the
ring's shape is genuinely all three.

**Therefore the colour map file carries the constants in its header** and
`colourMap: 0` resolves to exactly one file that determines everything drawn.
Numbering the table alone would let the constants move without the number
moving, which is the fault the wheel/mapping renumbering already fixed once.
This closes the open question rather than leaving it as a choice.

### The table is indexed by the raw draw, and this is easy to get wrong

`hexval( digest[-7:]) / 0xfffffff * 360`, **before** the warp. The warped value
is a different number and indexing by it silently shifts every triple around
the blue-greens. The file's own header warns about this; I made the mistake
inside an hour of reading it. Measured both ways over 4000 seeds against the
shipped fidelity search: **95.7%** differ on the correct index, 96.2% on the
wrong one — so the error is not what produced the finding, but the rule is
real and belongs in `SPEC.md`, not only in a data file's comments.

### What this costs `text-identicon.py`

Its design claim is that `text( grid, rgb)` needs no seed and so vendors alone.
A table indexed by the *draw* breaks that: the draw is not recoverable from the
colour exactly, only approximately.

Measured: recovering the draw from the colour alone via `draw_of` puts
**86 of 4000 seeds, 2.15%, in the wrong arc**.

Three ways, and this one needs a ruling too:

1. `text()` takes the draw. Exact, and the module stops being derivable from
   `.colour` alone.
2. `text()` keeps the colour-only path with `draw_of`, documented as 2.15%
   wrong. Cheap, and wrong is wrong.
3. Under Rule 9 the tricolour is stored in `settings.json` like the matrix and
   the colour, so consumers read it and never re-derive. The colour-only path
   then only matters to something vendoring `text-identicon.py` standalone.

3 makes 1 affordable and is consistent with the rest of this page.

### Deletions this authorises

`chosen_indices`, `nearest_colour`, `_mix`, `_PALETTE_LAB`, `_PALETTE_LINEAR`,
`_oklab`, `_linear` and the fidelity-search half of `tricolour_detail` — its
`base`, `mix_hex` and `delta_e` are all search concepts. The green-called-orange
fault above goes with them; it is not fixed, it is deleted.

`PALETTE` keeps the glyph, the name and the codepoint. Whether it keeps the
nominal RGB depends on nothing left reading it.

## Rule 7d — the wheel is the colour map, and it validates the output

`wheel80.svg` is the map: a 1440-segment ring at 0.25° and **63 numbered
blocks**, which is exactly the block count in `in-use.tsv`. `wheel81.svg` is the
same map plus an appendix of all 165 mixtures with their dE — same ring, extra
pages. Both were committed in 37d8a22 on 2026-08-26 and neither has changed
since.

**Verified: the shipped colour reproduces the ring exactly.** Every one of the
1440 segment fills, compared against `_encode( _oklch_to_linear( 0.60,
gamut_chroma( warp_hue( angle)), warp_hue( angle)))`:

```
as draw (warp applied here): 0 of 1440 differ, worst channel delta 0
as hue  (no warp):        1433 of 1440 differ, worst channel delta 145
```

So the ring is drawn in **draw coordinates** — page angle is the draw, the warp
only decides which hue sits under each tile. That is the model Justin ruled for
the tiles, and the map already obeys it. It also confirms the table's indexing
rule from the other direction.

**Verified: the table tiles the circle.** 64 rows, 63 blocks (one is split
across the 0° seam), summing to exactly 360.0 with no gap and no overlap.
Widths are 8° × 29, 4° × 29 and 1° × 4 — the 8/4/1 pricing by class, so an 8°
block serves eight times the projects a 1° block does, by design.

**Verified: the SVG labels sit exactly on the tile centres.** Every label
angle matches `wheel.tsv` to 0.000000°, allowing the 180° flip on labels drawn
upside-down for reading. 49 of the 63 labels matched my extraction pattern; all
49 are exact.


## Rule 7e — rotate the ring by −2.376°, and stop rounding the table

**The 0.4 is not the phase.** `wheel.tsv` places tile centres at `x.376` and
`x.876`; boundaries fall at centre ± half-width, so they are at `x.376` too.
`in-use.tsv` shows `x.4` because `reference()` writes them with `f"{lo:.1f}"`.

The phase is manual: tiles were pushed around by hand to make space and locked
when there was none left. Nothing depends on the value.

**The rounding is a defect on its own.** A port reading the table and a port
reading the wheel disagree by up to 0.024° at every boundary. Across 63
boundaries that is 1.5° of the circle, about **0.42% of projects**, which get a
different triple depending on which artifact the implementer read. Boundaries on
integers make the one-decimal write exact and the disagreement disappears.

**Rotate by −0.376.** Verified: all 63 boundaries land on integer degrees, none
left over. Centres land on `x.0` for the 8° and 4° tiles and `x.5` for the 1°
tiles, which is what centre ± half-width gives.

A larger rotation that also put a boundary on 0° was considered and **ruled
out** as excessive — it would move a 1° tile more than twice its own width to
buy a convenience nobody needs. So the block straddling zero keeps straddling
it, `in-use.tsv` stays 64 rows for 63 blocks, and `reference()` keeps its
`if lo < 0 … elif hi > 360` wrap case.

**No agent needed.** Subtract 2.376 from the 63 `ring` rows in `wheel.tsv`,
regenerate with `wheel.py --reference`, re-render `wheel80.svg` and
`wheel81.svg`. The colours do not move — the ring is a function of the angle,
and every tile moves by the same amount, so the picture is the same picture
rotated. The assertions in `reference()` that check the tiling still hold or it
refuses to write.

### The validator to build once the table ships

Sweep the ring at its own resolution and assert, at every step:

1. exactly one table row covers the draw — already true today
2. the drawn `#rrggbb` equals the ring segment fill at that angle — **already
   true today, 1440 of 1440**
3. the tricolour equals the block under that angle
4. block occupancy over a project population matches block width

Steps 1 and 2 pass now. Step 3 is the one that cannot pass until the table
ships, because the shipped tricolour is still the fidelity search — the 95.7%
above is exactly this check failing.

This belongs beside `cmd_validate`, which already round-trips `vectors.json`.


### `SPEC.md` and `vectors.json`

`SPEC.md` records the triple as not yet normative. A shipped, numbered colour
map makes it normative, so `vectors.json` should pin the tricolour beside the
matrix and the colour — which is also what makes a port's table readable as
correct or not.

### What the diagram shows, and the asymmetry

Page 5's WHICH THREE COLOURS section draws `chosen_indices`, `nearest_colour`
and `_mix` — the mechanism that ships. The wheel, `wheel.tsv` and `in-use.tsv`
appear nowhere in the `.mr`. So:

| | in the code | on the diagram |
|---|---|---|
| the warp | yes | yes, 2.4 |
| the wheel's triple selection | no | no |
| the shape channel | no | no |
| the fidelity search | yes | yes, page 5 |

The diagram is accurate about what ships. What it cannot show is that two of
those rows were superseded by work that was finished and never landed.


## Rule 11 — the colour map is JSON

`colour-map-0.json`, not a TSV. Page 1 already ruled JSON for `settings.json`
after weighing YAML and TOML; a port then parses one format for everything it
reads, and `vectors.json` is already the third file in it.

The deciding reason is Rule 7c: the map now carries the three transforms as
well as the blocks. TSV can only hold those in comments, and comments are
exactly where the indexing rule is hiding today — the one rule this session got
wrong. A named field cannot be skimmed past the way a comment header can.

The rounding defect is also a TSV artifact: `f"{lo:.1f}"` was a column-width
decision. JSON numbers are written as they are.

```json
{
  "colourMap": 0,
  "hueWarp": { "centre": 215.0, "halfWidth": 50.0, "peak": 4.0 },
  "lightness": 0.60,
  "chromaCap": 0.26,
  "blocks": [
    { "n": 1, "from": 2, "width": 8, "colours": ["red", "orange", "purple"] }
  ]
}
```

**`width`, not `to`.** The width *is* the class price — 8° for three distinct
colours, 4° for two, 1° for one — so it states how much identity the block
affords and how many projects it takes. `to` states the same fact as a
coordinate the reader has to subtract to recover. A lookup is
`from <= angle < from + width`, and the tiling assertion in `reference()` is
unchanged in substance.

Both are exact integers after the Rule 7e rotation.

**The emoji column does not survive.** `in-use.tsv` carries a `mark` column of
three glyphs; once the shape channel ships, the glyph for a colour depends on
the shape bits, so a stored glyph is either redundant or wrong. Colour names
only, and `PALETTE` maps a name to its square and its circle.

`n` stays: it is the number printed on `wheel80.svg`, and it is what lets a
reader check a block against the picture.

What is lost is that a TSV greps and diffs cleanly. `wheel.py --reference`
generates the file either way, so nothing is hand-edited and the loss is small.


## Rule 12 — `.txt` is scrapped, and `text()` goes with it

`text( grid, rgb, lattice=SEXTANT_LATTICE)` composed the mark: the matrix on a
lattice with the tricolour appended to the lower line. `.txt` was the only
thing that wanted it, and `.txt` is dropped for now. The function is deleted
rather than renamed.

**This closes the last open question on the page.** Whether that function should
take the `colour_map_angle` exactly or keep recovering it from the colour at
2.15% wrong no longer arises — nothing composes a mark from a colour any more.
Consumers read `renders` from `settings.json`.

The lattice writer is `lattice_lines( grid, lattice)`, with `octant()` and
`sextant()` as the two-line wrappers that pick a lattice. Those names state
their operation, they feed `renders.blockDrawing`, and they stay.

The module name `text-identicon.py` also stays: there the word distinguishes
the text rendering from the raster, which is a real distinction and the only
work it is doing.

`README.md` argues for `cat`-ing `.txt` as the one-command way to see a mark.
That argument goes with the artifact.


## Rule 10 — `colour_map_angle`, not "the draw"

The 28 bits from the digest, as degrees, before the warp. It is what indexes
the colour map, and it is the one value a port most has to get right.

"The draw" is a metaphor from drawing lots, and the domain has a literal term,
so the CLAUDE.md rule applies. `SPEC.md` also spells it three ways already —
"the draw", "the drawn value", "a position in the draw" — which is three
concepts to a reader who has met none of them.

| | name | what it is |
|---|---|---|
| before the warp | `colour_map_angle` | degrees, indexes the colour map |
| after the warp | `hue_angle` | degrees, the Oklab hue the colour is built at |

`colour_map_angle` names both what the value is and what it is for, and ties to
`colourMap` in settings and `colour-map-0.tsv` on disk. It cannot be read as a
hue, which is the documented trap: `in-use.tsv`'s header exists to warn against
indexing with the warped value, and I made that exact mistake this session
within an hour of reading the warning.

**A third representation goes at the same time.** `identicon_hue()` returns a
fraction of a turn, 0 to 1, and every caller multiplies by 360. So the value
exists as a fraction, as degrees, and as warped degrees, under two names. It
returns degrees and becomes `colour_map_angle( colour_slice)`; `warp_hue`
becomes `hue_angle`.

Renames follow in `SPEC.md`, the diagram glossary, `wheel.py`, `in-use.tsv`'s
header and `shaped.py` — where `draw_of( rgb)` becomes
`colour_map_angle_of( rgb)`, the lossy colour-only recovery from Rule 7b.

`SPEC.md`'s "spends the draw unevenly" and "how much of the draw each one gets"
are the same metaphor as prose; they become share of the circle.


## Rule 8 — the matrix, not the grid

`grid` names the whole 5×5 including the blanks, and only the painted cells
carry anything. `matrix` throughout:

| now | becomes |
|---|---|
| `identicon_grid` | `identicon_matrix` |
| `grid_text` | `matrix_text` |
| `grid_bits` | removed by Rule 6 |
| `parse_grid` | `parse_matrix` |
| `GRID` | `MATRIX_SIZE` |
| `"grid"` in `vectors.json` | `"matrix"` |
| `$term=grid` | `$term=matrix` |

`vectors.json` is a portable contract, so this is a breaking rename of a field
name as well as a Python one. Test output only, so it is allowed.


## Rule 9 — derived values are stored, not written as artifacts

**Each process that establishes a setting stores it immediately after deriving
it.** The colour and the matrix stop being `.colour` and `.grid` files and
become fields in `settings.json`, beside `identiconSeed`.

If a consumer needs them as files, the files are generated *from settings*, not
re-derived from the seed.

### The shape of the file

Two proposals were put. Taking the nesting from the second and the
changed-items-only history from the first:

```json
{
  "identicon": {
    "current": {
      "seed": "owner/repo",
      "colourMap": 0,
      "matrix": ["01010", "10101", "00100", "10101", "01010"],
      "colour": "#rrggbb",
      "tricolour": { "colours": [
        { "colour": "red",    "shape": "square" },
        { "colour": "blue",   "shape": "circle" },
        { "colour": "orange", "shape": "square" }
      ] }
    },
    "history": [
      { "at": "2026-09-01T04:22:11Z", "seed": "old-owner/old-repo" }
    ]
  },
  "renders": {
    "tricolour": "🟥🔵🟧",
    "blockDrawing": {
      "sextant": ["🬞🬂🬏", "🬀🬂🬈"],
      "octant":  ["▛▀▜", "▙▄▟"]
    }
  }
}
```

**`identicon` holds facts; `renders` holds spellings of them.** The tricolour
is stored as three `(colour, shape)` pairs, not as emoji, for the same reason
Rule 11 drops the emoji column from the colour map: a glyph is a rendering of a
colour and a shape, and storing it makes the derived pair unrecoverable from
the stored value. `renders.tricolour` is that pair list spelled in emoji.

`renders` is a sibling of `identicon`, not a child, because it is regenerable:
every field under it is a function of `identicon.current` and needs no history.

**This is what replaces the `.sextant`, `.octant` and `.tricolour` artifacts** —
the omission from the first draft of this rule. With `.colour` and `.grid`
already going, the artifact set drops from eleven files to the rasters, the SVG
and nothing else.

### The matrix is booleans, and its spelling is a render

Ruled: `identicon.current.matrix` holds five rows of five booleans. Every
character spelling of it is a render.

```json
"matrix": [[false,false,false,false,false],
           [false,true, true, true, false], ...]
```

`renders.blockDrawing` gains a third entry, `ascii`, beside `sextant` and
`octant`. Its job is to be the one that draws anywhere, so it is ASCII, and it
exists for `echo "$ascii"` — for someone scripting who will not convert the
booleans.

```
"          "
"  [][][]  "
"[][][][][]"
"[][]  [][]"
"    []    "
```

**`[]` on two spaces.** Chosen by looking at all three candidates rendered in a
terminal: `[]` is taller and squarer, so it reads as a block, where `@@` and
`##` sit short and wide and read as horizontal rules. An argument from glyph
density said `@@`, and the drawing said otherwise; the drawing decides.

**Each cell is two characters wide.** A monospace cell is about twice as tall
as it is wide, so a 5×5 of single characters draws the mark at twice its proper
height. Doubling the column squares it.

**The field is named for what it is, not for its glyphs**, so the glyphs can
change without the name lying.

**`echo "$ascii"` must be quoted, and the description must say so.** Verified:
unquoted, word splitting collapses the runs and drops the leading pad —

```
$ echo $ascii
@@@@@@ @@@@@@@@@@
```

That is the price of a space background, and the booleans in
`identicon.current.matrix` are the fallback for anyone who would rather not pay
it.

**Open: what `vectors.json` pins.** It pins `grid` as five `01010` strings
today. Under this rule that is a render, not the fact, so either it pins
booleans and matches settings, or it keeps a compact string because a fixture
file is read by a port author rather than by a program. `01010` is also more
compact than a doubled ASCII render and unambiguous in a diff.

**Why the nesting.** Inside `.identicon/settings.json`, `identiconSeed` stutters
— the `identicon` prefix on every field name is the nesting spelled out
longhand. `identicon.current.seed` reads as one path and each name says one
thing. This reverses page 1's `identiconSeed` ruling; it is the same
self-documenting goal reaching a different answer once there are four fields
instead of one.

**Why one history, not three.** `identiconSeedHistory` beside
`previousIdenticonColour` was two shapes for one idea. A single array, most
recent first, each entry holding only what changed, removes the question. It
also records *together* the things that changed together, which three parallel
arrays cannot.

**`colourMap` sits in `current`**, because it is exactly the kind of thing that
changes and wants a history entry when it does.

**The timestamp is a field, not a key.** `{ "at": …, "seed": … }` is a plain
object a schema can describe. `{ "2026-09-01T…": { … } }` is an object whose
keys are unpredictable, which every reader and every port then has to iterate
rather than address.

**One thing the timestamp costs.** `identiconSeedHistory` holds plain strings
today, so the file is deterministic and `tests/test_bytes.py` can compare it
byte for byte. Timestamps make two people applying the same change produce
different files. Either the fixtures stop covering `settings.json`, or the
timestamp is injectable for tests.

### What breaks, noted not argued

The artifact set loses `.colour` and `.grid`; `SPEC.md`, `README.md` and
`tests/test_conformance.py` move with it, and fixtures go from 11 files per seed
to 9. `$(cat …/repository-identicon.colour)` stops working unless the file is
regenerated from settings. `SPEC.md` gains a line saying which fields a hand may
set and which `apply` writes.


## Items on the page whose text is now wrong

- 2.1 `_digest( key)`, 2.2 `identicon_grid( key)`, 2.3 `identicon_hue( key)`,
  2.8 `identicon_colour( key, …)`, 2.10 `_colour_for( key, kwargs)` — the
  parameter is `seed` in the code. The signatures on the page were never
  updated when the key concept went.
- The off-page arrow into 2.1 is labelled `→ v_key` / `$target=v_key`, a name
  page 1 no longer has.
- 2.8's description, "Refuses a key stamped at a mapping version this build does
  not draw", describes the removed stamp. It refuses a `colourMap` field.

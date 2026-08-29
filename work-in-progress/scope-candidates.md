# Candidates for removal: what this repository could stop doing

**Nothing here is decided, and nothing here has been done.** `scope-split.md`
recorded two removals that happened; this is the pass over what is left. Every
claim was checked against the tree rather than remembered, and the checks are
written down, so a disagreement is about the judgement and not about the facts.

Every data-dictionary entry and every top-level name in both shipped files is
accounted for below — 40 terms, 96 names in `repository-identicon.py`, 30 in
`text-identicon.py`. Names not listed as candidates are listed as kept, so
nothing is silently passed over. The lists are checked against the sources: no
name appears twice, none is invented, and none is missed.

## The test

Two questions, in this order.

**1. Is it derived from the mark?** A repository identicon generator turns a
seed into a key, a key into a digest, a digest into a grid and a colour, and
those into bytes a repository commits. Something that is not on that path is not
this project's, however useful it is.

**2. If two implementations disagreed about it, would anything break?** This is
what a specification is for. Two tools writing different filenames into one
shared icon theme collide, so the short id is fixed. Two tools shortening a
project's name differently collide with nothing, so shortening a name is not
this document's business — and that argument decides most of the list.

`SPEC.md` § Scope is the third test, unchanged, and it catches what the first
two miss:

> **In:** how to derive a key, and how a key reaches each medium. **Out:** where
> any tool chooses to display the result, and what it does with the rest of its
> interface.

---

# The list, in order

Ordered by how little argument there is on the other side. **№1 is the clearest
scope answer; №2 is the one to fix first** if only one thing is done, because it
is the only entry that is a defect rather than a preference.

| № | What | Why | Cost to remove |
|---:|---|---|---|
| 1 | `badge_label`, `project_name` | not derived from the mark at all | 17 lines, 2 SPEC paragraphs, 2 `show` lines |
| 2 | `--chroma`/`--lightness`/`--background`/`--block` **on `apply`** | writes committed artifacts that contradict the key | one argument in `build_parser` |
| 3 | `discriminator` | specified; nothing in the tree produces one | 1 SPEC table row |
| 4 | `render_ansi` | escape sequences, in a file that says it emits none | 11 lines, 1 `show` line |
| 5 | `icon_name`, `ICON_PREFIX`, `short_hash` | nothing here installs an icon | 6 lines, 1 SPEC paragraph |
| 6 | `fit_block`, `render --edge`, the `fitting` term | both callers left with the desktop half | 10 lines, 1 flag |
| 7 | `tricolour_names` | called by nothing, anywhere | 7 lines |
| 8 | `.txt` | byte-for-byte `.sextant` + `" "` + `.tricolour` | 1 artifact, 1 SPEC line |
| 9 | one of `.sextant` / `.octant` | the same 25 bits, twice | 1 artifact, 1 SPEC line |
| 10 | `LEGACY_OVERRIDE_FILENAMES` | undocumented, untested compatibility shim | 1 line |
| 11 | `prior_path`, `keep_prior`, `.prior.*` | `.gitignore` argues against them in its own comment | 18 lines |
| 12 | `port`, `conforming`, `vendoring` | not data, in a data dictionary | 3 glossary rows |
| 13 | `style` | vocabulary for a feature implemented elsewhere | 1 glossary row |
| 14 | `masking` | an advisory about a state the user chose on purpose | ~8 lines |
| 15 | `_key_from_args` | one line, one caller, wrapping the line above it | 2 lines |
| 16 | the README insertion | placement, and the only heuristic in the tool | 63 lines |
| 17 | `_main`, `parse_grid`, `parse_hex`, `tricolour_detail` | a second CLI and a diagnostic, in the file consumers vendor | 57 lines |
| 18 | `cmd_show` | once 1, 4 and 5 go, it prints what `apply --json` already gives | 12 lines |
| 19 | `VERSION`, `--version` | `"0.0.build"`; nothing is released | 2 lines |
| 20 | four rasters | 27, 104, 128, 256 px, plus an SVG that is any of them | 3 artifacts |
| 21 | most of `work-in-progress/` | 94% of the repository by weight | 4.25 MB |

---

# Every data-dictionary entry, judged

40 terms: **25 core**, **12 candidates**, **3 kept with a caveat.**

| # | Term | Verdict | Why |
|---:|---|---|---|
| 1 | key | **core** | the one input everything derives from |
| 2 | seed | **core** | the identity inside the key |
| 3 | mapping version | **core** | stamped into the key, so it changes the mark |
| 4 | source | keep, note | the *resolution order* is core; the *label* is reporting, and there are seven of them |
| 5 | override | **core** | outranks the remote; specified |
| 6 | recorded key | **core** | outranks every derivation |
| 7 | seed drift | **core** | `SPEC.md` SHOULDs it; a real identity question |
| 8 | masking | **candidate 14** | advisory about a state the user chose deliberately |
| 9 | reseed / remap | **core** | the two acts that move a mark |
| 10 | the mark | **core** | grid and colour together |
| 11 | grid | **core** | pinned by `vectors.json` |
| 12 | hue | **core** | the draw |
| 13 | the warp | **core** | version 0.3's rule |
| 14 | lightness / chroma | **core** | the two constants the colour is built at |
| 15 | gamut chroma | **core** | what sRGB will take |
| 16 | block | **core** | the specified geometry |
| 17 | border | **core** | likewise |
| 18 | canvas | **core** | derived from those two |
| 19 | fitting | **candidate 6** | exists only for `fit_block`, whose callers left |
| 20 | short id | **candidate 5** | feeds `icon_name` and nothing else |
| 21 | discriminator | **candidate 3** | specified; nothing produces it |
| 22 | project name | **candidate 1** | not derived from the mark |
| 23 | badge label | **candidate 1** | not derived from the mark |
| 24 | icon theme name | **candidate 5** | nothing here installs an icon |
| 25 | artifact | **core** | the committed set is the specification |
| 26 | the key file | **core** | the only source of truth in the directory |
| 27 | prior | **candidate 11** | git has the history |
| 28 | current | **core** | `--check`'s exit code, which CI branches on |
| 29 | rendering | **core** | key to bytes, which is the job |
| 30 | style | **candidate 13** | the six names left with `Console-Colophon` |
| 31 | lattice | **core** | the table and the numbers that emit it |
| 32 | octant | keep one | see candidate 9 |
| 33 | sextant | keep one | see candidate 9 |
| 34 | the triple | **core** | the colour channel where nothing else survives |
| 35 | arrangement | **core** | the second channel, from the grid |
| 36 | the palette | **core** | the nine colours |
| 37 | vector | **core** | the contract |
| 38 | port | **candidate 12** | an implementation, not a datum |
| 39 | conforming | **candidate 12** | a predicate, not a datum |
| 40 | vendoring | **candidate 12** | a practice, not a datum |

**§ Derived names is four fifths questionable.** Of its five entries — short id,
discriminator, project name, badge label, icon theme name — one is never
produced, two are not derived from the mark, and the other two exist for an icon
theme this repository does not write to. That is not five small doubts; it is
one section that outlived its consumer.

**Three entries are not data.** `port`, `conforming` and `vendoring` carry the
types `an implementation`, `bool` and `a practice`, which is the dictionary
reporting the problem itself. They are project vocabulary, and `CONTRIBUTING.md`
already explains all three. A data dictionary that holds practices holds
anything.

---

# Every function and constant, judged

## `repository-identicon.py` — 96 names

**Core: 73.** Listed so nothing is passed over silently.

- *the digest and the mark* — `GRID`, `_digest`, `identicon_grid`, `grid_text`,
  `identicon_hue`, `_quantise`, `MARK_LIGHTNESS`, `MARK_CHROMA`, `HUE_WARP`,
  `_warp_bump`, `warp_hue`, `GAMUT_STEPS`, `GAMUT_CEILING`, `_oklch_to_linear`,
  `_in_gamut`, `gamut_chroma`, `_encode`, `UnknownMappingVersion`,
  `identicon_colour`, `_colour_for`, `hex_colour`
- *the seed and the key* — `OVERRIDE_FILENAME`, `normalise_seed`,
  `normalise_remote_url`, `_git`, `repo_toplevel`, `repo_remote_url`,
  `override_seed`, `resolve_seed`, `MAPPING_VERSION`, `KEY_STAMP`, `stamp_key`,
  `parse_key`, `KEY_NAME`, `KEY_FILE_TEMPLATE`, `key_path`, `recorded_key`,
  `resolve_key_for`, `_resolve_from_args`
- *the artifacts* — `BORDER`, `ARTIFACT_BLOCK`, `ARTIFACT_SCALE`,
  `SCALED_BORDER`, `LARGE_CANVASES`, `large_geometry`, `canvas_edge`,
  `render_rgba`, `_png_chunk`, `encode_png`, `render_png`, `render_svg`,
  `TEXT_MODULE`, `_TEXT`, `text_module_path`, `_text_module`, `IDENTICON_DIR`,
  `ARTIFACT_STEM`, `artifact_names`, `artifact_paths`, `artifact_bytes`,
  `install_into_repo`, `cmd_apply`
- *conformance* — `VECTORS_NAME`, `vectors_path`, `load_vectors`, `_cell`,
  `_normalise_grid`, `check_output`, `validate_command`, `cmd_validate`
- *the command line* — `build_parser`, `main`, `cmd_doctor`

**Candidates: 23.**

| Name | L | Reached by | Why a candidate |
|---|---:|---|---|
| `project_name` | 3 | `badge_label`, `cmd_show` | not derived from the mark; reads the key, so a seed with no `/` returns the whole key |
| `badge_label` | 14 | `cmd_show` | the project's name shortened; the badge left with the desktop half |
| `ICON_PREFIX` | 1 | `icon_name` | nothing here installs an icon |
| `icon_name` | 3 | `cmd_show` | likewise; its only output is one line of `show` |
| `short_hash` | 2 | `icon_name` | its only consumer is the line above |
| `fit_block` | 10 | `cmd_render` | the icon theme and the terminal both left |
| `render_ansi` | 11 | `cmd_show` | emits `\x1b[48;2;…`, which the module docstring says it does not |
| `LEGACY_OVERRIDE_FILENAMES` | 1 | `override_seed` | `.claude-state-identicon`, honoured on read; no test, no document |
| `SOURCE_NOTES` | 1 | `cmd_show` | seven prose strings so one command can explain itself |
| `_key_from_args` | 2 | `cmd_render` | `_resolve_from_args(args)[0]`, one caller |
| `_render_kwargs` | 12 | `cmd_apply`, `cmd_render` | the plumbing for candidate 2 |
| `BLOCKS` | 1 | `build_parser` | offers blocks 1–4 where the artifact is 5 |
| `prior_path` | 4 | `keep_prior` | rollback copies git already has |
| `keep_prior` | 14 | `install_into_repo` | likewise |
| `README_MARK` | 1 | `readme_state` | the README insertion |
| `README_NEEDLE` | 1 | `readme_state` | likewise |
| `README_FENCE` | 1 | `without_code_fences` | likewise |
| `without_code_fences` | 14 | `readme_state` | likewise |
| `find_readme` | 16 | `readme_state` | likewise |
| `readme_state` | 33 | `install_into_repo` | likewise |
| `VERSION` | 1 | `build_parser` | `"0.0.build"`; nothing is released |
| `cmd_show` | 12 | `build_parser` | once its contents go, `apply --json` covers what is left |
| `cmd_render` | 17 | `build_parser` | see below |

**`cmd_render` is the one I would keep.** It is the only way to get a raster at
a size the artifact set does not hold, which `scope-split.md` records as a real
gap. What is questionable is its *flags*, not the command: `--edge` (candidate
6), `--block`'s range, and the three drawing options.

## `text-identicon.py` — 30 names

**Core: 22.** `OCTANTS`, `SEXTANTS`, `GRID_SIZE`, `OCTANT_LATTICE`,
`SEXTANT_LATTICE`, `lattice_lines`, `octant`, `sextant`, `PALETTE`, `_linear`,
`_encode`, `_oklab`, `_PALETTE_LINEAR`, `_PALETTE_LAB`, `_mix`,
`nearest_colour`, `chosen_indices`, `grid_bits`, `arrange`, `tricolour_indices`,
`tricolour`, `text`.

**Candidates: 8.**

| Name | L | Reached by | Why a candidate |
|---|---:|---|---|
| `tricolour_names` | 7 | **nothing, anywhere** | its docstring says vendoring consumers call it; nothing in this tree does, and the claim cannot be checked from here |
| `tricolour_detail` | 20 | `selftest` | a diagnostic — `delta_e`, `mix_hex`, `base` — shipped in the file consumers copy |
| `hex_colour` | 4 | `tricolour_detail` | character-for-character the same function as the one in the other file |
| `parse_grid` | 10 | `_main`, `selftest` | input parsing for this file's own command line |
| `parse_hex` | 6 | `_main`, `selftest` | likewise |
| `_main` | 21 | — | a second command line in a repository that has one |
| `selftest` | 131 | `_main` | a test, in the module rather than in `tests/` |
| `_recover` | 23 | `selftest` | likewise |

**`selftest` has the best case of anything on this list, and should stay.** It
re-derives both lattice tables from `unicodedata` and reads every rendered mark
back to its grid, and it must run *wherever the module is vendored*, on whatever
Unicode the host has — which `tests/` cannot do. Keep it and the 23 lines of
`_recover` with it. Those five names — `selftest`, `_recover`, `_main`,
`parse_grid`, `parse_hex` — are 191 lines between them, and that defends 154 of
them; the remaining 37 are the command line. If `_main` goes, `parse_grid` and
`parse_hex` are `selftest`'s alone and can become private.

**`hex_colour` existing twice is deliberate, and should stay that way.** The
whole point of `text-identicon.py` is that it vendors alone into a tool with no
identicon machinery. Two copies of two lines is the price, and it is the right
price. Recorded so it is not mistaken for an oversight later.

---

# The detail

## 1. A badge label is not an identicon

Konsole draws a small text overlay on a terminal session and calls it a badge.
This repository used to set it: a `badge` subcommand with `--label` and
`--clear`, driving `setBadgeText` / `setBadgeEnabled` / `setBadgeColor` over
D-Bus. The overlay fits one or two characters, so `badge_label` derived them
from the project name — split on `-`, `_`, `.` and space, initials of the first
two parts or else the first two characters, upper-cased. That is why this
repository's own badge is `RI`.

All of it left in `2694526`, *The desktop half leaves*: the subcommand,
`BADGE_METHODS`, the whole D-Bus route, to `Console-Colophon`. `badge_label`
stayed for one reason — § Derived names had written it down.

**Every citation of it is in a section this repository does not implement.**
Three: the consumer table in § Why it exists, row "Konsole session badge";
§ Terminal, which opens "**This section is specified here and implemented in
`Console-Colophon`**"; and one bullet in § Text about a single-line medium.

**The precedent is in the tree and went the other way.** `scope-split.md` called
`profile_name` a judgement call and moved it out with the profile code, because
"§ Derived names fixes the short id, the icon theme name and the badge label,
but says nothing about how a terminal emulator names a profile". That sentence
is the case for keeping `badge_label` — and the only difference between the two
names is which document mentioned it first.

**It also reads the key where it means the seed**, so a seed with no `/` falls
back to returning the whole key, mapping version included:

| key | project name | badge |
|---|---|---|
| `0.3:github.com/torvalds/linux` | `linux` | `LI` |
| `0.3:a` | `0.3:a` | `03` |
| `0.3:` | `0.3:` | `03` |
| `0.3:my.project` | `0.3:my.project` | `03` |

Two of those are pinned vectors. Every repository in that shape collides on
`03`, shows the mapping version where a name should be, and would change at the
next version bump — the leak the version-in-key design exists to prevent. An
explicit `--seed` is taken verbatim and unnormalised, so `--seed my.project`
reaches it.

**The cost, honestly.** The one-line medium outlives Konsole: a tab title, a
status field, a prompt segment. Remove this and the only answer left is the
tricolour alone, three double-width cells carrying no pattern. What is lost is
two letters of a name the consumer already has.

**What removal touches.** `project_name` and `badge_label`; two lines of
`cmd_show`; § Derived names loses two paragraphs; the § Why it exists table row
becomes "colour"; two single-line-medium mentions lose "or the badge label"; the
diagram loses two items and two glossary rows. No test references either name,
and no mark moves — `vectors.json` pins the grid and the colour, not the names.

## 2. `apply` can write artifacts the specification forbids

The only entry that is a defect. Checked in an empty repository at
`0.3:github.com/a/b`:

```
default                                .colour  #007fee
apply --chroma 0.40 --lightness 0.85   .colour  #acd1ff
the key file, unchanged                         0.3:github.com/a/b
what that key actually draws                    #007fee
```

The committed `.colour` is a colour the committed `.key` does not produce, and
every artifact in the directory moves with it. `apply --background ff0000`
writes `<rect width="27" height="27" fill="#ff0000"/>` into the committed SVG,
which § Where this departs from the reference says an implementation MUST NOT
paint. `apply --block 2` writes a 12×12 `.png` where the artifact is 27×27.

Nothing warns, and the output is indistinguishable from conforming output.

**Why it happened.** `add_common(target, render=True)` gives `apply`, `show` and
`render` the same options for one reason — consistency — and that put them on
the one command whose output is committed.

**The narrow fix** is `add_common(apply_cmd, render=False)` and a line in the
README. **The cheaper fix,** if they stay, is for `apply` to refuse to write
when a drawing option departs from the specified value unless something like
`--draft` is passed.

## 3–6. The rest of § Derived names, and the geometry that served it

`discriminator` is specified in a table and produced by nothing: it is
`short_hash(key, 6)`, and no call site passes 6. A specification with a name
nothing emits is a name nobody has checked.

`icon_name` has the one real collision argument on this list — two tools writing
different filenames into a shared icon theme break each other — but nothing here
writes to an icon theme, and `Console-Colophon`, which does, vendors the rule.
`short_hash` exists only to feed it. Removing all three changes `SPEC.md` and
every port, not just this tree, which is why it is listed rather than assumed.

`fit_block` answers "the largest block that fits a canvas somebody else fixed".
Its docstring names both somebody-elses: "the XDG icon theme … and a terminal
handed a pixel budget". Both left. `render --edge` is what reaches it now, and
the `fitting` glossary entry exists for it.

## 7–9. Things that are other things

`tricolour_names` is called by nothing in the repository. Its docstring asserts
that vendoring consumers call it, which cannot be checked from here and is not
checked anywhere.

`.txt` is verified byte-for-byte equal to `.sextant` + `" "` + `.tricolour`, and
`SPEC.md` documents it as exactly that. Keeping it buys `cat` on one file for a
consumer who wants the whole mark, which is a real audience; the cost is a
derived file that can only ever be wrong.

`.sextant` and `.octant` carry the same twenty-five bits. Both ship because
which one renders is a fact about the reader's fonts — but the reader's fonts
are not a property of the repository, and the repository is what commits the
file. A consumer that knows its host can compute the other from `.grid` with
the table it already vendors.

## 16. The README insertion

63 lines that open somebody else's `README.md`, blank its fenced code, run a
regex for an existing mark, find the first heading and insert two lines after
it. On by default; `--no-readme` is the way out.

§ Scope's "in" is a key reaching a medium. Editing a markdown file in another
repository is placement, which is what the desktop half was removed for. It is
also the only heuristic in the tool — everything else is a pure function of the
key; this guesses where a heading is.

**The case for keeping it** is that it is what makes the tool useful on first
run, and that it is careful: it writes once, leaves a line the author moved
alone, and `--check` writes nothing. Dropping it means `apply` prints a line to
paste, which is worse for the common case and better for the boundary.

## 21. Weight

`work-in-progress/` is **4.25 MB of the repository's 4.54 MB — 94% by weight.**
The specification, both implementations, the vectors, the reference library, the
whole test suite and both workflows are the other 294 KB.

| file | size | referenced by |
|---|---:|---|
| `coverage3.svg` | 1.02 MB | one sentence in `HANDOVER.md` |
| `wheel81.svg` | 594 KB | `HANDOVER.md`; the current state |
| `wheel80.svg` | 440 KB | `HANDOVER.md`; the previous state |
| `sheet3.svg` + `sheet3-dark.svg` | 806 KB | one sentence in `HANDOVER.md` |
| `sheet4.svg` + `sheet4-dark.svg` | 779 KB | one sentence in `HANDOVER.md` |
| `routines.drawio` + `flow-routines.svg` | 30 KB | `HANDOVER.md` |

The four sheets are 1.6 MB of evidence for a settled decision. `coverage3.svg`
is 1 MB for a warp strength that was re-examined and stands. `wheel80.svg` is
the previous render, and `next_path` takes max + 1, so one accumulates per pass
by construction. `routines.drawio` and `flow-routines.svg` are a hand-maintained
call graph of the thing the system diagram now generates from a source that
cannot go stale.

None of it is wrong to keep. The question is whether a repository whose README
opens "This repository is the **standard**" should be 94% exploratory renders by
weight, when git holds every one of them at no cost to a clone's working tree.

---

# Checked, and not candidates

Written down so the same ground is not covered twice.

- **`_normalise_grid`'s leniency.** Accepting `"01101"`, `[0,1,1,0,1]` and
  booleans looks like generosity that blurs the contract. `CONTRIBUTING.md`
  states it as policy: "being fussy about JSON shape would be a validator
  failing a correct implementation." Deliberate, and argued.
- **`validate`, and its whole chain.** 133 lines and the only subprocess besides
  git. It is the point: the vectors are the contract, and this is what makes
  them usable without every implementer building a harness.
- **`doctor`.** 18 lines, four facts, no writes. Already split once.
- - **`--reseed`, `--remap`, `--check`, `--json`.** The first two are the only
  acts that move a mark; the other two let CI and dependent tools branch
  without parsing prose.
- **The seed resolution chain.** `resolve_seed` and everything under it is the
  key, which is the whole specification.
- **`hex_colour` existing twice.** The price of `text-identicon.py` vendoring
  alone, and worth paying.
- **`selftest` and `_recover`.** A test that must run where the module is
  vendored, which `tests/` cannot reach.
- - **`main`'s two exception handlers.** `UnknownMappingVersion` to exit 1 with
  the way out named, `BrokenPipeError` to exit 0 quietly. One situation each,
  with a known answer.
- - **`_quantise`, `_in_gamut`, `_png_chunk`, `_warp_bump`.** Small private
  helpers with one caller each, and each one is a named step of a specified
  rule.

---

# Two defects found on the way, neither a scope question

**`project_name` reads the key where it means the seed.** Table under №1. One
word in the code and one in `SPEC.md`; it moves no mark. Worth fixing whether or
not `badge_label` survives — and if it does not, both go together.

**`mapping_drift` is unreachable.** In `install_into_repo` it is computed
*after* the raise that rules it out, so it is always `None`, and the report
`cmd_apply` prints from it can never fire. Marked on page 6 of the system
diagram.

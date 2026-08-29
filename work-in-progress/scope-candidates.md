# Candidates for removal: what this repository could stop doing

**Nothing here is decided.** `scope-split.md` recorded two removals that
happened; this records what a third pass turns up, with the argument on both
sides where there is one. Every claim below was checked against the tree rather
than remembered, and the checks are written down so a disagreement is about the
judgement rather than about the facts.

The test is `SPEC.md` § Scope, unchanged:

> **In:** how to derive a key, and how a key reaches each medium. **Out:** where
> any tool chooses to display the result, and what it does with the rest of its
> interface.

And the README's claim about what this repository *is*: the standard — the
specification, the vectors that make it unambiguous, and a reference
implementation held to them.

Ordered by how strong the case is, not by how much they cost.

---

## A. The tool can produce output the specification forbids

This is the only group that is a defect rather than a preference. `apply` writes
the artifacts a repository commits, and it accepts drawing options that make
those artifacts disagree with the key sitting beside them.

**`apply --chroma` and `apply --lightness`.** Checked, in an empty repository at
`0.3:github.com/a/b`:

```
default                            .colour  #007fee
apply --chroma 0.40 --lightness 0.85   .colour  #acd1ff
the key file, unchanged                       0.3:github.com/a/b
what that key actually draws                  #007fee
```

The committed `.colour` is now a colour the committed `.key` does not produce.
Every artifact in the directory moves with it. A consumer re-deriving from the
key, or `validate` run against the repository, gets the other answer.

**`apply --background`.** `SPEC.md` § Where this departs from the reference:
"This specification renders **transparent**, and an implementation MUST NOT
paint the background." `apply --background ff0000` writes
`<rect width="27" height="27" fill="#ff0000"/>` into the committed SVG.

**`apply --block`.** `--block` accepts 1 through 5 where the specified artifact
is block 5. `apply --block 2` writes a 12×12 `.png` where `SPEC.md` § What goes
in the repository says 27px.

**The case for keeping them:** they are useful on `render`, whose output nobody
commits, and `add_common(render=True)` gives all three commands the same
options for one reason — consistency.

**The case against:** consistency is what put them on the one command where they
are dangerous. The reference implementation is the thing ports are checked
against; a flag that makes it emit non-conforming artifacts is worse than a
missing feature, because the output looks exactly like conforming output. The
narrow fix is to keep the options on `render` and drop them from `apply`, which
is `add_common(apply_cmd, render=False)` and a line in the README.

**A cheaper fix, if they stay:** `apply` refuses to write when any drawing
option departs from the specified value, unless something like `--draft` is
passed. That keeps the surface and closes the hazard.

---

## B. Surfaces whose only consumer has left

Each of these was built for something that went to `Console-Colophon`. They
still work; nothing here needs them.

| what | who used it | who uses it now | lines |
|---|---|---|---:|
| `render_ansi` | `emit`, and `show` | `show` only | 11 |
| `badge_label` | the Konsole D-Bus badge overlay | one line of `show` | 14 |
| `icon_name` + `ICON_PREFIX` | the XDG icon theme installer | one line of `show` | 3 |
| `fit_block` | the icon theme, and a terminal's pixel budget | `render --edge` only | 10 |
| `discriminator` | — | **nothing**; no caller passes `length=6` | 0 |

**`render_ansi` is the one worth arguing about.** It emits
`\x1b[48;2;r;g;bm` — an escape sequence, addressed to a terminal. The module
docstring says, three lines in: "**Nothing here writes outside the repository it
is run in, and nothing here addresses a terminal.**" That is the sentence the
whole terminal removal was written to make true, and this falsifies it. Every
other rendering of that class left. Either it goes, or the docstring's second
half does.

The counter-argument is real: `show` without a preview is four lines of text,
and looking at the mark is most of why anyone runs it. If it stays, the
docstring should say *why* this one is different rather than claiming it is not
there.

**`discriminator` is documented and unimplemented.** `SPEC.md` § Derived names
gives it a row — "first **6** characters, distinguishing two projects that share
a basename" — and nothing in the tree produces one. It is `short_hash(key, 6)`
and no call site passes 6. Either something should produce it or the row should
go; a specification with a name nothing emits is a specification nobody has
checked.

**`icon_name` is the honest hard case.** `scope-split.md` kept it on the ground
that § Derived names defines it, so it is the specification's rather than a
delivery detail. That is still true — which means removing it is a change to
`SPEC.md` and to every port, not a tidy-up. It is listed here so the question is
asked once rather than re-derived each time somebody notices nothing installs an
icon.

---

## C. Artifacts that are other artifacts

Eleven files. Two of them carry nothing the others do not, and a third group is
a judgement about how many sizes a repository owes a consumer.

**`.txt` is a concatenation.** Verified byte-for-byte: `.txt` equals `.sextant`,
one space, `.tricolour`. `SPEC.md` already documents it that way — ".sextant and
.tricolour, composed". The argument for keeping it is that `cat` on one file is
the whole integration for a consumer who wants the mark and nothing else, and
that is a real audience. The argument against is that a derived file in a
directory of derived files still has to be kept in step, and this one can only
ever be wrong.

**Both lattices ship.** `.sextant` and `.octant` carry the same twenty-five
bits. `lattice-comparison.md` settled that neither wins, and both were kept
because which one renders is a fact about the reader's fonts. But the reader's
fonts are not a property of the repository, and the repository is what commits
the file. A consumer that knows its host can compute the other lattice from
`.grid` with the table it already has to vendor.

**Four rasters and a vector.** 27, 104, 128 and 256 pixels, plus an SVG that is
any of them. `scope-split.md` already says the set is "four fixed rasters chosen
here, and a consumer with a different constraint has no way to say so". Both
halves of that are an argument for fewer, not more.

**`.prior.*`.** The rollback copies. `.gitignore` states the case against them
in its own comment: "A working-directory convenience, overwritten each run; git
already has the history." `SPEC.md` says SHOULD, not MUST.

None of these can be dropped without amending `SPEC.md` § What goes in the
repository, which is the list. That is the cost, and it is the right cost: the
artifact set is a specified thing.

---

## D. Writing to a file the tool does not own

**The README line.** `find_readme`, `without_code_fences`, `readme_state` — 63
lines that open somebody else's `README.md`, blank its fenced code, run a regex
looking for an existing mark, find the first heading, and insert two lines after
it. It is on by default; `--no-readme` is the way out.

§ Scope's "in" is a key reaching a medium. Editing a markdown file in another
repository is neither deriving nor rendering: it is placement, which is the
thing the Konsole half was removed for. The code's own justification — "an
identicon nobody put on the page is an identicon nobody sees" — is a product
argument, and a good one, but it is not the scope rule.

It is also the only heuristic in the tool. Everything else is a pure function of
the key; this guesses where a heading is.

**The case for keeping it:** it is what makes the tool useful on first run, and
it is careful — it writes once, leaves a line the author moved alone, and
`--check` writes nothing. Dropping it means `apply` prints a line to paste,
which is worse for the common case and better for the boundary.

---

## E. Weight

`work-in-progress/` is **4.25 MB of the repository's 4.54 MB — 94% by
weight.** The specification, both implementations, the vectors, the reference
library, the whole test suite and both workflows are the other 294 KB.

| file | size | referenced by |
|---|---:|---|
| `coverage3.svg` | 1.02 MB | one sentence in `HANDOVER.md` |
| `wheel81.svg` | 594 KB | `HANDOVER.md`; the current state |
| `wheel80.svg` | 440 KB | `HANDOVER.md`; the previous state |
| `sheet3.svg` + `sheet3-dark.svg` | 806 KB | one sentence in `HANDOVER.md` |
| `sheet4.svg` + `sheet4-dark.svg` | 779 KB | one sentence in `HANDOVER.md` |
| `routines.drawio` + `flow-routines.svg` | 30 KB | `HANDOVER.md` |

**The four sheets are 1.6 MB for one sentence.** They are 400-project contact
sheets in two palettes, kept as evidence for a decision that is settled. Git has
them for as long as the repository exists whether or not the working tree does.

**`coverage3.svg` is 1 MB for a decision that is closed.** `HANDOVER.md`: "the
warp strength was re-examined and stands" — this is the comparison that made it
stand.

**`wheel80.svg` is the previous render.** `next_path` takes max + 1, so the
directory accumulates one of these per rendering pass by construction.

**`routines.drawio` and `flow-routines.svg` are a call graph** — the same call
graph the generated system diagram now draws from a source that cannot go stale.
Two hand-maintained renderings of a thing that is now generated is one too many,
and probably two.

None of this is *wrong* to keep. The question is whether a repository whose
README opens "This repository is the **standard**" should be 94% exploratory
renders by weight, when git holds every one of them at no cost to a clone's
working tree.

---

## F. A second command line, and a diagnostic, inside the vendored file

`text-identicon.py` is the file consumers are expected to vendor. It carries:

- **`_main`, 27 lines** — its own argument parsing, its own `--help`, its own
  `--octant` flag. A second CLI in a repository with one.
- **`selftest` and `_recover`, 148 lines** — re-derives both lattice tables from
  `unicodedata` and reads every rendered mark back to its grid. This is a test,
  and `tests/` is where tests live; it is in the module because it must run
  wherever the module is vendored, on whatever Unicode the host has. That is a
  genuine reason, and it is the strongest case in this document for keeping
  something.
- **`tricolour_detail`, 27 lines with `tricolour_names`** — returns `delta_e`,
  `mix_hex` and `base`. Diagnostics, for explaining a result. Nothing here calls
  it; the docstring says the vendoring consumers do.

Between them, **175 of 617 lines** — 28% of the file every consumer copies — are
not the derivation.

---

## What was checked and is **not** a candidate

Written down so the same ground is not covered twice.

- **`_normalise_grid`'s leniency.** Accepting `"01101"`, `[0,1,1,0,1]` and
  booleans looks like generosity that blurs the contract. `CONTRIBUTING.md`
  states it as policy: "being fussy about JSON shape would be a validator
  failing a correct implementation." Deliberate, and argued.
- **`validate`.** Running somebody else's implementation is the only subprocess
  besides git, and it is the point: the vectors are the contract, and this is
  what makes them usable without building a harness.
- **`doctor`.** 18 lines, four facts, no writes. Already split once and already
  minimal.
- **`--reseed` and `--remap`.** The two deliberate acts that move a mark. Core.
- **The seed resolution chain.** `resolve_seed` and everything under it is the
  key, which is the whole specification.
- **`--json` and `--check`.** Both exist so a dependent tool or a CI job can
  branch without parsing prose. Cheap and load-bearing.

---

## One thing found on the way that is not a scope question

`CONTRIBUTING.md` still says "Versions 0 to 2 were drafts and have been
withdrawn". The bare `3` was withdrawn too, and re-issued as `0.3`. Fixed in the
commit that added this file.

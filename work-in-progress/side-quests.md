# Side quests, logged and not done

Work worth noticing and not worth interrupting for. When an idea arrives on a
branch that does not own it, it goes here instead of into that branch. Nothing
in this file is scheduled and nothing in it is decided.

## A diagramming library, in a repository of its own

Raised 2026-08-31. `work-in-progress/system-diagram.py` is 950 lines that read
MarkRight and emit SVG: column layout, box placement, text wrapping, edge
routing, a glossary, and a consistency check against the two sources. None of
it is about identicons, and none of it ships -- `work-in-progress/` is out of
the specification's scope and is not in any release.

It should be a library in its own repository, which this one uses. Splitting it
is not urgent and is explicitly not this branch's work.

What is already worth carrying across when it happens:

- The check that fails a page documenting a routine the source no longer has.
  It caught nine stale items in one run on 2026-08-31.
- Edge routing that tests a path against every box and detours through a clear
  lane or band. It took eighteen crossings to zero across ten pages.
- The layout table kept separate from the content, so the `.mr` says what the
  diagram means and the table says where it goes.

What it does not yet do, and a library should:

- Show how often an edge is traversed. Derived-on-every-run and derived-once
  draw identically today, which is how a re-derivation survived a review.
- Wrap or fold a signature too wide for its column, rather than warning and
  leaving a human to rebalance the columns by hand.

## A `.json` artifact carrying every derived value

Raised 2026-08-30. `.identicon/` holds thirteen files and each carries one
representation: the key, the grid, the colour, the two lattices, the tricolour,
the text mark, the SVG and four PNGs. A consumer that wants several of them
opens several files and parses four formats. One `.json` would carry the key,
the seed, the mapping version, the grid, the colour and the derived names in a
single document, parsed in one call.

Four questions to answer before writing any of it:

- Does it replace what `apply --json` already prints, or duplicate it?
- Is it written for outside consumers, or for this repository's own tests?
- Does it make candidate 20 easier, by giving a consumer the numbers to render
  its own raster instead of shipping four?
- What does adding a fourteenth artifact cost, when candidate 8 argues that
  `.txt` is already two other artifacts concatenated?

## Dynamic Huffman in `_deflate`

Raised 2026-08-30, on `byte-fixtures`. The deterministic deflate writer emits
one fixed-Huffman block, which spends about 13 bits on a length-distance pair
where dynamic codes spend two or three. The four rasters went from 1727 bytes to
5955. Dynamic Huffman recovers that and costs a code-length-alphabet
implementation of a few hundred lines. Candidate 20 proposes deleting four
rasters, so decide that first: if it carries, most of the weight this would
recover stops existing.

## A stored-block fallback in `_deflate`

Raised 2026-08-30, on `byte-fixtures`. Incompressible input expands by about
5.5% because the writer never falls back to a stored block — 20,000 random bytes
become 21,093. Unreachable for identicon rasters, whose input is a small palette
on flat runs, but `encode_png` reads as a general function and a caller could
believe it. About ten lines caps the output at the stored size.

## The key file becomes structured configuration

Raised 2026-08-30. `.identicon/repository-identicon.key` is three comment
lines and one data line, `<version>:<seed>`. One later-consideration item
already recorded — extra PNG sizes held in the key file — cannot fit that
line, so the format changes or the feature does not happen.

An aggregate `.json` carrying every derived value was considered and rejected
the same day: the repository would then hold both it and the individual
artifacts, and a second copy of a value is a second thing that can be stale.
Only the key file changes.

Justin's lean is YAML. The formats, with what each costs:

| format | comments | parser |
|---|---|---|
| the current line format | yes, and it uses them | hand-written, already exists |
| YAML | yes | third party; the repository is standard library only today |
| JSON | no | `json`, standard library |
| TOML | yes | `tomllib` reads only, and only from 3.11; CI runs 3.9 |

The comment lines are not decoration: they tell a human editing the file that
changing that line changes the mark. Any format that drops them loses that
warning at the point it is needed.

Three rules the change has to keep, whichever format wins:

- The string that gets hashed stays `<version>:<seed>`. The file stores the
  parts and the tool composes them. `apply --check` must report every artifact
  unchanged afterwards, in every repository. A moved mark means a wrong change.
- A file that does not parse makes the tool refuse and say so. It must never
  fall back to deriving from the remote, which would change the mark silently.
- `.repository-identicon`, the override, stays one line of text. It is written
  by a person and committed by hand, and being trivial to create is the whole
  of its value.

Do it in the same pass as mapping version 1, which rewrites every key file
anyway.

## Cross-machine PNG determinism

Recorded as the third defect in `scope-candidates.md`. Being addressed on the
`byte-fixtures` branch, so it is not outstanding — this entry exists so the
register does not read as though nobody noticed.

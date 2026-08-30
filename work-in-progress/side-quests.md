# Side quests, logged and not done

Work worth noticing and not worth interrupting for. When an idea arrives on a
branch that does not own it, it goes here instead of into that branch. Nothing
in this file is scheduled and nothing in it is decided.

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

## Cross-machine PNG determinism

Recorded as the third defect in `scope-candidates.md`. Being addressed on the
`byte-fixtures` branch, so it is not outstanding — this entry exists so the
register does not read as though nobody noticed.

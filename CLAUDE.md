# Repository-Identicon

Project-specific notes. `~/Code/CLAUDE.md` applies too and this file wins where
they disagree.

## The system diagram is written in MarkRight, which is specified elsewhere

`work-in-progress/system-diagram.mr` is the source; `system-diagram.py` reads it
and writes `system-diagram.html`. **MarkRight is a separate project and its
documentation lives in its own repository.** Read it there before editing the
`.mr` — do not infer the syntax from the file.

| document | what it fixes |
|---|---|
| `~/Code/Projects/MarkRight/markright-glyph-spec.md` | the depth rail, the five line markers, the separators, the line-prefix grammar |
| `~/Code/Projects/MarkRight/markright-markdown-mapping.md` | how each construct maps to Markdown. §4 is the metadata sigils |

The parts this diagram uses, so a glance is enough to read a line:

```
┋   depth rail, content          ━   node
┊   depth rail, everything else  ┄   metanode
                                 ┅   node, empty on purpose
```

One EM SPACE (U+2003) after the rail run and one EN SPACE (U+2002) after the
marker. Both mandatory. Readers accept any `Zs`; writers emit those two.

Metadata sigils, after a `┄` marker:

```
⸖ name=value    external attribute      ⸲ comment
⸆ text          description             ⸈ expansion
⸋ name=value    internal attribute
```

## Regenerating the diagram

```bash
python3 work-in-progress/system-diagram.py work-in-progress/system-diagram.html
```

It takes an output path as `sys.argv[1]` and parses no flags, so
`--help` writes a file called `--help`.

**It checks itself against the source.** An item of kind `fn` whose name is
gone from `repository-identicon.py` or `text-identicon.py`, an edge to a
missing item, and a `$term` with no glossary entry are all reported on stderr.
It still exits 0, so read the warnings; a clean run prints one line.

The `$source` line numbers in the `.mr` are not maintained and not checked.

**The notation shows what calls what, and not how often.** "Derived on every
run, then usually discarded" and "derived once, then stored" draw as the same
picture — which is how a re-derivation on every command survived a diagram
review. Frequency has to be stated in a description, or it is invisible.

## Documents that the tests hold to the code

`tests/test_conformance.py` fails when `SPEC.md` or `README.md` stops matching
the artifact set, or stops naming `.identicon/settings.json` and
`identiconSeed`. Change the code and these documents in the same commit.

`vectors.json` is the portable contract and `tests/fixtures/` is this
implementation's byte-for-byte serialisation. No seed appears in both, and a
test asserts it. Regenerate the fixtures with:

```bash
python3 tests/test_bytes.py --write
```

Only after deliberately changing `FIXTURE_COLOUR_MAP` or `FIXTURE_SEEDS`. A
failure with both untouched means the writer moved, and regenerating deletes
the evidence.

## Prose in this repository

`~/Code/CLAUDE.md` § *Reference prose carries facts, not images* is enforced
here in review. Docstrings, `SPEC.md`, glossary entries and diagram
descriptions state operations: creates, writes, reads, returns, raises,
refuses. `README.md` making a case for the project is argument and may be
written well.

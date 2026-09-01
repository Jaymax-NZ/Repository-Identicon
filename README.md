# Repository Identicon

![](.identicon/repository-identicon.svg)

A deterministic visual identity for a software project, derived from the project
itself and from nothing else. Any tool implementing this specification produces
the same identicon for the same project as any other, without coordination,
configuration, or a shared registry.

This repository is the **standard**: the specification, the test vectors that
hold implementations to it, and a reference implementation. It is deliberately
dull, because a specification should be findable by someone typing what it is.

## Give a repository its identicon

Run this inside the repository you want marked:

```bash
python3 /path/to/repository-identicon.py apply
```

On the first run it derives the seed from the git remote and writes it to
`.identicon/settings.json`; on every run after that it reads that file. Then it
writes these:

```
.identicon/repository-identicon.png            block 5, 27px canvas
.identicon/repository-identicon@4x.png         the mark magnified 4x, 104px
.identicon/repository-identicon-128.png        for a consumer that fixes the size
.identicon/repository-identicon-256.png        likewise
.identicon/repository-identicon.svg            vector, same geometry
```

Only the images are files — a file is what a README can point at. Everything
else lives beside them in one place:

```json
// .identicon/settings.json
{
  "identicon": {
    "current": {
      "seed": "owner/repo",
      "colourMap": 0,
      "matrix": [[true, true, false, true, true], …],
      "colour": "#a53ef9"
    },
    "history": []
  },
  "renders": {
    "tricolour": "🟦🟪🟪",
    "blockDrawing": {
      "ascii":   ["[][]  [][]", …],
      "sextant": ["🬚🬇🬓", "🬒🬁🬐"],
      "octant":  ["▂𜺠𜺣", "𜵂𜴃𜴺"]
    }
  }
}
```

`identicon.current.seed` is the string that gets hashed, exactly as it reads. It
is written when it is not set and never rewritten, so the mark survives a
rename, a move between forges and a clone. Edit it by hand to choose your own,
and `apply` fills in everything under it.

`identicon` holds the facts and `renders` holds spellings of them. The matrix
and the colour are enough to draw the mark with no PNG decoder and no SVG
parser. `renders` is it already drawn, for a medium that will take neither an
image nor an escape sequence — a shell prompt, a tab title, a status field.

Every lattice is stored because which one a host can draw depends on its fonts.
Sextants are Unicode 13.0 and octants 16.0, so sextants are the safer default;
octants are squarer where the glyphs exist; `ascii` needs no Unicode at all.
`ascii` is `[]` on two spaces, two characters a cell so the mark comes out
square — quote it, or the shell eats the blanks:

```bash
jq -r '.renders.blockDrawing.ascii[]' .identicon/settings.json
```

One file each. The mark holds its brightness right around the colour wheel, so
the same image sits on a white page and on a near-black one and the project
looks like itself in both. There is no light or dark variant to choose between.

To hand the mark to GitLab, copy one out yourself. GitLab reads `logo.png` at
the repository root when no avatar has been uploaded, so this is the whole
integration, and no other forge offers an equivalent:

```bash
cp .identicon/repository-identicon-256.png logo.png
```

It is a manual copy on purpose. Writing to your repository root is your
decision, not the tool's.

It also adds the mark to the repository's README, after the first heading:

```markdown
![](.identicon/repository-identicon.svg)
```

That happens by default because an identicon nobody put on the page is one
nobody sees. `--no-readme` declines it. It goes in once — a line you have since
moved, resized with an `<img>` tag or pointed at the PNG is recognised and left
exactly as you left it — and a repository with no README is never given one.

Commit the lot. To read the colour anywhere else,
`$(jq -r .identicon.current.colour .identicon/settings.json)` is the whole
integration.

**The seed is written once and hashed verbatim after that.** It is the one
thing the pattern depends on. Re-running refreshes the artifacts from it, so a
better renderer or a different size reaches every repository while leaving the
identity alone.

Nothing moves the mark on its own. Renaming the repository, moving it between
forges, and cloning it somewhere else all leave the seed where it is, because
the seed is a committed file rather than something re-derived on each run.
Changing an identity is asked for, and there is one way to ask:

```bash
apply --reseed          # today's seed: the remote, or the path if there is none
apply --reseed repo     # the git remote, as owner/repo
apply --reseed path     # the repository directory
apply --reseed uuid     # a fresh uuid4, tied to nothing
apply --seed owner/name # a seed you supply outright
```

`--reseed` moves the current seed to the front of `identiconSeedHistory` and
blanks the seed field; the ordinary rule then derives a new one and writes it,
so seeding a fresh repository and reseeding an old one are one rule and not
two. A named source that cannot answer — `--reseed repo` where there is no
remote — fails and says so rather than quietly using something else.

The change to your mark arrives as a diff you review rather than as a surprise
on somebody's next upgrade.

Anything it replaces is kept beside it as `repository-identicon.prior.<ext>`,
so rolling back is a `mv`. One level, overwritten each run — git has the rest.

`--check` reports what would change and exits 1 without writing, for CI or for
a tool asking whether a repository is current; `--json` gives a dependent tool
the whole result without parsing prose.

If the repository has no git remote the seed falls back to its path. That is
still committed and still travels with a clone; if you would rather it named
the project, edit `identiconSeed` in `.identicon/settings.json` before the
first `apply`.

**The colour map is beside the seed and never inside the hash.** `colourMap`
records which map drew this repository's colours. Improving a map — a wider
gamut, a palette gaining a colour Unicode did not have — repaints marks and
can never reshape one, because the pattern comes off the seed alone. There is
one map, numbered `0`.

`doctor` answers what a repository would derive today, if you want to compare
it against what is stored. `apply` does not raise the subject, because the
mark standing still through a rename is the design and not a problem.

## What is here

| file | what it is |
|---|---|
| `SPEC.md` | the specification: how to derive the seed, and how a seed becomes a pattern and a colour |
| `CONTRIBUTING.md` | how to write a conforming port, and what "a repository identicon" means |
| `vectors.json` | pinned test vectors — the part that makes the spec unambiguous |
| `repository-identicon.py` | the reference implementation, standard library only. Five commands: `apply`, `show`, `render`, `validate`, `doctor` |
| `text-identicon.py` | the two lattices and the emoji palette, for media that display no image. A pair with the file above, and four artifacts come from it |
| `reference/` | the library the derivation conforms to, committed rather than fetched, and the harness that regenerates the vectors from it |
| `tests/` | the implementation against the vectors, and the vectors against the library |
| `work-in-progress/` | what is settled but not yet adopted: the emoji-colour mapping, a fallback for media that can show neither an image nor styled text, and `scope-split.md`, which says where each half of `repository-identicon.py` belongs; nothing here is imported by anything |

```bash
python3 -m unittest discover -s tests -t tests
```

## The system diagram

**[Every top-level routine, one page per module][diagram]** — what each one is
for, what it hands back, and which other one calls it, with a typed glossary of
the words this repository uses in a particular way.

[diagram]: https://justin-maxwell.github.io/Repository-Identicon/

Its source is `work-in-progress/system-diagram.mr`, a MarkRight document that
knows nothing about pixels; `system-diagram-layout.py` says where things go and
`system-diagram.py` draws them. The published page is generated from that source
on every push to `main`, so it cannot be a version of the diagram nobody
generated.

Writing an implementation elsewhere? `validate` runs it against the pinned
vectors, so you do not have to build a harness to find out whether you agree:

```bash
python3 repository-identicon.py validate -- ./my-identicon --json
```

Nothing here reaches the network, and nothing needs installing.

## Why the vectors matter more than the prose

A specification that only describes a derivation can be read two ways by two
careful people, and both will be sure. `vectors.json` removes the argument: an
implementation either reproduces them or it does not.

They are regenerated from `reference/vendor/identicon.js`, which is **committed
rather than fetched**, so anyone can re-derive them offline for as long as this
repository exists. A reference that has to be downloaded is a reference that can
disappear, and one did during the week this was written. The test suite
regenerates them and compares, where `node` is available, and skips where it is
not — checking an implementation must never require the reference.

The harness reads the library's **SVG** output rather than its PNG, because the
matrix then comes back exactly: one `<rect>` per foreground cell, with no pixel
decoding and no resampling to argue about.

## Implementations vendor this; they do not depend on it

Three consumers exist, and each carries its own copy of the derivation:

- [`Console-Colophon`](../Console-Colophon) — the XDG icon theme, Konsole tabs,
  and `emit`, which writes the mark to a terminal in an escape sequence. All
  three used to be in this repository; `SPEC.md` § Scope puts every side effect
  out, so they left. Its copy is held to `vectors.json` by its own test suite,
  and `validate` can check it from outside.
- [`Claude-State-Panel`](../Claude-State-Panel) — panel glyphs and a terminal
  banner. Its copy differs in one line, `ICON_PREFIX`, which the specification
  explicitly leaves to the implementing tool.
- [`Claude-Colophon`](../Claude-Colophon) — a Claude Code plugin. It *must*
  vendor, because a plugin is copied whole and has no dependency mechanism at
  all.

That is the intended shape rather than a compromise. The whole point of pinned
vectors is that independent implementations agree without coordination, a shared
registry, or a package manager. What holds them together is this repository's
vectors, not an import.

## The layering

Three things, often confused, and the reason this repository is separate from
`Claude-Colophon`:

1. **The standard.** What identifies a project — the git remote, normalised so
   that every spelling of one repository derives one seed — and how a seed
   becomes a pattern and a colour. Language-agnostic. Must never drift.
2. **An implementation.** Code turning a seed into pixels, vector, blocks or a
   hex colour. There are two already; each carries its own copy of the
   derivation and is held to the vectors by test.
3. **A delivery.** Getting the mark in front of a human somewhere specific — a
   terminal tab, a panel glyph, a README, or the end of every Claude turn.

Implementations **vendor** the derivation rather than depending on it. That is
not a shortcut: the whole point of pinned vectors is that independent
implementations agree without a shared registry, and some consumers — a Claude
Code plugin, for one — have no dependency mechanism at all.

## Licence

AGPL-3.0-or-later, in `LICENSE`, inherited from `Claude-State-Panel` — and
provisional. It is a poor fit for a specification meant to be reimplemented
freely, and the better answer is likely something permissive, or a public-domain
dedication for the spec with a separate licence on the reference code. Recorded
here so the current state is unambiguous, not because the question is settled.

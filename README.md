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

It derives the key from the git remote and writes five files:

```
.identicon/repository-identicon.png       raster, 256px
.identicon/repository-identicon@4x.png    the same raster at 1024px
.identicon/repository-identicon.svg       vector
.identicon/repository-identicon.colour    "#rrggbb", and a newline
.identicon/repository-identicon.key       the seed the others came from
```

The `@4x` raster is there for native UIs — Qt, GTK, a desktop panel — which
pick an asset per scale factor and cannot resample the way a browser does. On
the web you want the SVG, or the 256px PNG and CSS.

It also adds the mark to the repository's README, after the first heading:

```markdown
![](.identicon/repository-identicon.svg)
```

That happens by default because an identicon nobody put on the page is one
nobody sees. `--no-readme` declines it. It goes in once — a line you have since
moved, resized with an `<img>` tag or pointed at the PNG is recognised and left
exactly as you left it — and a repository with no README is never given one.

Commit the lot. To read the colour anywhere else,
`$(cat .identicon/repository-identicon.colour)` is the whole integration.

**The seed is recorded once and reused after that.** Re-running refreshes the
artifacts from it — so a better renderer or a different size reaches every
repository — and leaves the identity alone. Renaming the repository, moving it
between forges, or cloning it somewhere else does not change the mark. That is
reported as seed drift and nothing more:

```bash
python3 /path/to/repository-identicon.py apply --reseed
```

is the only thing that adopts a new key and changes the mark, and it has to be
asked for.

Anything it replaces is kept beside it as `repository-identicon.prior.<ext>`,
so rolling back is a `mv`. One level, overwritten each run — git has the rest.

`--check` reports what would change and exits 1 without writing, for CI or for
a tool asking whether a repository is current; `--json` gives a dependent tool
the whole result without parsing prose.

If the repository has no git remote the key falls back to its path, which will
not survive being cloned. `apply` says so, and the fix is a
`.repository-identicon` file committed at the top level.

## What is here

| file | what it is |
|---|---|
| `SPEC.md` | the specification: how to derive the key, and how a key becomes a pattern and a colour |
| `CONTRIBUTING.md` | how to write a conforming port, and what "a repository identicon" means |
| `vectors.json` | pinned test vectors — the part that makes the spec unambiguous |
| `repository-identicon.py` | the reference implementation, standard library only |
| `text-identicon.py` | the text rendering, for media that display no image |
| `reference/` | the library the derivation conforms to, committed rather than fetched, and the harness that regenerates the vectors from it |
| `tests/` | the implementation against the vectors, and the vectors against the library |
| `work-in-progress/` | what is settled but not yet adopted: the emoji-square mapping, a fallback for media that can show neither an image nor styled text, and `scope-split.md`, which says where each half of `repository-identicon.py` belongs; nothing here is imported by anything |

```bash
python3 -m unittest discover -s tests -t tests
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
grid then comes back exactly: one `<rect>` per foreground cell, with no pixel
decoding and no resampling to argue about.

## Implementations vendor this; they do not depend on it

Two consumers exist, and each carries its own copy of the derivation:

- [`Claude-State-Panel`](../Claude-State-Panel) — Konsole tabs, panel glyphs, a
  terminal banner. Its copy differs in one line, `ICON_PREFIX`, which the
  specification explicitly leaves to the implementing tool.
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
   that every spelling of one repository collapses to one key — and how a key
   becomes a pattern and a colour. Language-agnostic. Must never drift.
2. **An implementation.** Code turning a key into pixels, vector, blocks or a
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

# Repository Identicon

A deterministic visual identity for a software project, derived from the project
itself and from nothing else. Any tool implementing this specification produces
the same identicon for the same project as any other, without coordination,
configuration, or a shared registry.

This repository is the **standard**: the specification, the test vectors that
hold implementations to it, and a reference implementation. It is deliberately
dull, because a specification should be findable by someone typing what it is.

## What is here

| file | what it is |
|---|---|
| `SPEC.md` | the specification: how to derive the key, and how a key becomes a pattern and a colour |
| `vectors.json` | pinned test vectors — the part that makes the spec unambiguous |
| `repository-identicon.py` | the reference implementation, standard library only |
| `text-identicon.py` | the text rendering, for media that display no image |
| `reference/` | the library the derivation conforms to, committed rather than fetched, and the harness that regenerates the vectors from it |
| `tests/` | the implementation against the vectors, and the vectors against the library |
| `work-in-progress/` | the emoji-square mapping, settled but not yet adopted — nothing here is imported by anything |

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

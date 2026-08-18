# Repository Identicon

A deterministic visual identity for a software project, derived from the project
itself and from nothing else. Any tool implementing this specification produces
the same identicon for the same project as any other, without coordination,
configuration, or a shared registry.

This repository is the **standard**: the specification, the test vectors that
hold implementations to it, and a reference implementation. It is deliberately
dull, because a specification should be findable by someone typing what it is.

## Status: empty on purpose

Nothing has moved here yet. The specification, the vendored reference library
and the pinned vectors currently live in
[`Claude-State-Panel`](../Claude-State-Panel), where they were written and where
three consumers already exercise them:

| what | where, today |
|---|---|
| specification | `docs/project-identicon-spec.md` |
| reference library | `identicon/reference/vendor/identicon.js` |
| pinned vectors | `identicon/vectors.json` |
| full implementation | `identicon/claude-state-identicon.py` |

They will move when there is a reason. Two implementations that one person owns
need a shared test, not a published standard — and that test exists. The reason
to cut this repo out is a **third** implementation, especially one written by
someone else, at which point the vectors have to be citable from outside.

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

Not yet chosen. `Claude-State-Panel` is AGPL-3.0-or-later, which is a poor fit
for a specification meant to be reimplemented freely. Something permissive, or a
public-domain dedication for the spec with a separate licence on the reference
code, is likely the better answer.

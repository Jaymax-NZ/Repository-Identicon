# Contributing

This repository is a **specification**, not a library. The most useful thing
anyone can contribute is an implementation in another language that reproduces
`vectors.json` exactly — and the second most useful is a demonstration that the
specification is ambiguous somewhere.

## The one rule

**An implementation either reproduces the pinned vectors or it does not.**

That is the whole conformance test, and it is deliberately the only one. Prose
can be read two ways by two careful people and both will be sure; the vectors
cannot. If your implementation disagrees with them, one of you is wrong, and
which one is a fact rather than a discussion.

```bash
python3 -m unittest discover -s tests -t tests
```

## Ports are welcome here rather than elsewhere

If you write a port, please open a pull request to add it under `ports/`
instead of publishing it separately. Not for control — the licence does not
require it and never will — but because a port that lives here is held to the
same vectors by the same CI run, and one that lives elsewhere drifts the first
time somebody has an opinion about the palette.

A port needs three things and nothing else:

1. Grid and colour derivation from a seed, hashing the seed exactly as given.
   `vectors.json` records the seeds verbatim, so there is nothing to infer, no
   prefix to add and no case to fold.
2. Seed derivation and remote normalisation, per `SPEC.md`, for repositories
   that are not seeded yet — and reading `.identicon/settings.json` in
   preference to deriving, for those that are.
3. A test that fails loudly when your output and the vectors disagree.

Renderings — image, terminal protocol, text — are optional. A port that only
derives the seed, the grid and the colour is a complete and useful port.

**While this is pre-release, there is one colour map and the vectors pin only
that.** A port implements one colour rule and refuses any `colourMap` it does
not have — refuses, rather than drawing it with the rule it has, because that
would produce a mark the settings file does not describe.

That changes at the first release. No colour map that reaches a release ever
retires, so from then on a port implements every released map and picks by the
`colourMap` a repository records, and `vectors.json` keeps the vectors for
each. Four earlier rules were drafts and have been withdrawn; the fourth is the
rule drawn today, numbered 0.

The digest and the grid do not depend on the colour map at all, so a port that
hashes what it is handed gets both for free and keeps them through every future
map.

### Checking it

You cannot run this repository's Python suite against a port in another
language, so the check is offered as a command instead:

```bash
python3 repository-identicon.py validate -- ./my-identicon --json
```

It runs your implementation once per pinned vector, with the seed as the last
argument, and expects `{"grid": [...], "colour": "#rrggbb"}` on stdout. The
grid rows may be `"01101"`, `[0,1,1,0,1]` or booleans — being fussy about JSON
shape would only fail correct ports. It exits 1 if any vector disagrees.

That is the same check this repository applies to itself, offered outward.
Nothing about your project has to change to use it, and it reads nothing but
what your command prints.

## What "a repository identicon" means

Anyone may implement this. Please call the result a repository identicon
**only if it passes the vectors.** That is not a legal claim and there is no
trademark behind it; it is a request, and the reason for it is narrow: the
whole value of this thing is that independent implementations agree without
coordination. Something that renders a different mark for the same repository
is welcome to exist, and is welcome to be better — it just is not this.

If you think the mapping should change, say so in an issue and bring the
reasoning. A change to the vectors is a change to every project's identity, so
it is a version bump, not a patch. `SPEC.md` records what would justify one.

## Style, such as it is

- **Standard library only** in the reference implementation. No dependency is
  worth making a specification harder to check.
- **Nothing reaches the network**, at any point, including in tests. CI has a
  job that fails if a networking import appears in the tree. If working here
  ever seems to need one, something has been designed wrong.
- **Comments explain the decision, not the mechanism.** The code says what it
  does. A comment earns its place by recording why it is not the obvious
  alternative, what was tried and failed, or what will break if it is changed.
  Several in this repository are the only record of a fault that took real time
  to find.
- **Say what was measured and what was assumed.** If a number came from
  running something, say so. If it came from reasoning, say that instead.

## Reporting an ambiguity

The best bug report against a specification is two reasonable readings of one
sentence and the different outputs they produce. That is a real defect, and it
is worth more than a patch.

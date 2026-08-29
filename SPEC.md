# Project identicon specification

A deterministic visual identity for a software project, derived from the project
itself and from nothing else. Any tool implementing this specification produces
the same identicon for the same project as any other, without coordination,
configuration, or a shared registry.

The valuable half of this document is **the key** — deciding what identifies a
project. The other half, how a key becomes a pattern, should come from an
established identicon implementation rather than from here; the derivation
below records what the tool does today and is not a standard worth conforming
to.

## Why it exists

Several tools in and around this repository need to answer *which project is
this*, in different media:

| Consumer | Medium | Uses |
|---|---|---|
| Return-of-control hook | terminal, ANSI | grid and colour |
| Konsole tab | icon theme PNG, profile | grid and colour |
| Konsole session badge | terminal overlay | label and colour |
| Panel glyph row | Qt Quick | colour only |

They must agree. A tab, a panel glyph and a terminal banner disagreeing about a
project's colour would be worse than none of them having one.

## Scope

**In:** how to derive a key, and how a key reaches each medium. **Out:** where
any tool chooses to display the result, and what it does with the rest of its
interface.

## The key

Everything derives from one string. Getting the key right matters more than
anything else here, because two tools that disagree about the key agree about
nothing else.

The key is the **mapping version, a colon, and the seed**:

```
key = "1:" + seed          e.g. "1:github.com/owner/repo"
```

The **seed** identifies the project and is resolved as below. The **mapping
version** says which derivation drew the mark.

An implementation MUST hash the key **exactly as recorded**, prefix included,
and MUST NOT add, strip or rewrite the prefix at hash time. Everything below
follows from that one rule.

A key with no `<digits>:` prefix is **mapping version 0** and is its own seed.
Version 0 is the derivation that existed before the version did, so an
unstamped key hashes to itself and still produces the mark it always produced.
An implementation MUST recognise the prefix only when it is a run of decimal
digits followed by a colon at the very start of the key, so that a seed
containing a colon — `ssh://…`, `C:/src/x`, `host:1234/x` — is never mistaken
for a stamped one.

### Why the version is in the key, and not in the seed

A change to the derivation is a change to every project's identity. Nothing
prevented one happening quietly: edit a constant, regenerate the vectors in the
same commit, and every mark in the world moves while the tests stay green.

With the version inside the key, "the mark changed" and "the key changed" are
the same event by construction. The recorded key is a tracked file, so that
event is a line in a diff that somebody reviews.

It stays out of the seed because the seed is the identity. A repository's seed
MUST NOT be rewritten by a version change: a new mapping is not a rename, and
MUST NOT be reported as seed drift or require re-seeding.

### The recorded key wins

An implementation MUST derive the mark from the recorded key, verbatim,
whenever a repository has one. It MUST NOT re-stamp that key with the version
it happens to ship, and MUST NOT treat a version it does not recognise as an
error: an unknown mapping version is somebody else's newer mapping, not a
corrupt file.

So the version an implementation carries decides one thing only — what a
**newly seeded** repository is stamped with. It reaches no repository that is
already seeded. An implementation SHOULD report the difference where one
exists, and MUST NOT act on it.

Moving an existing repository to a newer mapping is therefore a separate,
deliberate operation — `apply --remap` in the reference implementation — which
rewrites the recorded key, keeps the seed, and changes the mark. Its whole
output is one changed line in a tracked file, which is the record of the
decision.

### What justifies a bump

A change to the grid rule, to the colour rule, or to either set of constants —
anything that makes a conforming implementation produce a different mark for an
unchanged key. Such a change MUST increment the mapping version an
implementation seeds at, and MUST add vectors for the new version to
`vectors.json` in the same commit.

It MUST NOT remove the vectors for any version that reached a release. Those
keys are recorded in repositories, still hash to themselves, and must still draw
what they always drew; the vectors are what stops that promise being broken by
accident.

A version that never reached a release is a draft. It MAY be withdrawn, with its
rule and its vectors, and repositories seeded from a draft build are expected to
`remap`. This is the only circumstance in which vectors leave.

A change that cannot alter any mark — prose, renderings, tooling, a new file in
the artifact set, new seeds added to the vectors — MUST NOT increment it.

Neither a rename nor a move is a bump. Those change the seed, which is the
existing seed-drift path, and they change one repository rather than all of them.

### Resolving a seed

This is how a repository that has **not** been seeded gets its seed. Once it is
seeded, the recorded key outranks every row of this table; what follows is
reported as drift, never acted on.

Resolve most specific first, and stop at the first that yields a value:

| # | Source | Seed | Portable |
|---|---|---|---|
| 1 | `explicit` | supplied by the caller | — |
| 2 | `override` | first non-blank, non-`#` line of `.repository-identicon` at the repository top level, whitespace-stripped | yes, if committed |
| 3 | `remote` | the normalised git remote, below | **yes** |
| 4 | `toplevel` | the repository top level, as an absolute path | no |
| 5 | `path` | the directory itself, as an absolute path | no |

Sources 3 and 2 are the only ones that survive being cloned elsewhere. An
implementation SHOULD report which source it used, because a project silently
falling back to a path seed will change identity when checked out on another
machine, and that is worth seeing before it happens rather than after.

The override file was formerly `.claude-state-identicon`, named for one
consumer of a specification that has several and none of which is Claude. An
implementation SHOULD still honour that name where the current one is absent,
and MUST prefer the current one where both exist: the file is committed into
other people's repositories, and dropping it silently changes the identity it
was written to pin — the one outcome an override exists to prevent.

The git remote is `origin` where one exists, otherwise the first remote listed.

**Why not the path.** A path is not stable across machines, containers, cloud
sessions, or worktrees. That last one is decisive rather than theoretical: a git
worktree keeps the same `origin` but has its own top level, and Claude Code's
desktop app gives every parallel session its own worktree. A path key would
therefore give each parallel session in one project a different identity —
precisely inverting what an identicon is for.

A session started in a subdirectory has the same failure and the same fix, since
`rev-parse --show-toplevel` reports the repository root from anywhere inside it.

### Remote normalisation

Every spelling of one repository MUST collapse to one seed. Given a remote URL:

1. Trim whitespace; strip a trailing `/`.
2. Reject if empty, if it begins with `/`, or if the scheme is `file`. A
   local-path remote is no more portable than the working directory and earns no
   special treatment.
3. If the URL contains `://`, take the authority as everything up to the next
   `/`, and the path as the remainder. Otherwise, if it contains `:`, treat it
   as scp-like: authority before the first `:`, path after. Otherwise reject.
4. In the authority, discard everything up to and including the last `@`, then
   discard any `:port`. What remains is the host.
5. Strip `/` from both ends of the path, then strip a trailing `.git`,
   case-insensitively.
6. Reject if either the host or the path is now empty.
7. The seed is the host and the path segments, joined by `/`, **lowercased**.

Lowercasing is deliberate: forges treat owner and repository names
case-insensitively, so `Owner/Repo` and `owner/repo` are one project.

The host is retained, so `github.com/a/b` and `gitlab.com/a/b` stay distinct.

All of these MUST yield `github.com/owner/repo`:

```
https://github.com/Owner/Repo.git      git@github.com:Owner/Repo.git
https://github.com/Owner/Repo          git@github.com:Owner/Repo
https://github.com/owner/repo/         ssh://git@github.com/Owner/Repo.git
https://token@github.com/Owner/Repo.git    ssh://git@github.com:2222/Owner/Repo.git
https://user:pass@github.com/Owner/Repo.git    git://github.com/Owner/Repo.git
```

## The pattern

GitHub-style: a 5×5 grid, mirrored, so every identicon is vertically symmetric
and reads as a deliberate mark rather than as noise.

Let `h` be the **MD5 digest of the key encoded as UTF-8, as lowercase hex**,
thirty-two characters. The key, not the seed: `"1:github.com/owner/repo"`.

```
grid[row][col] = false for all row, col in 0..4

for index in 0..14:
    painted = hexval(h[index]) mod 2 == 0
    col, row = index div 5, index mod 5
    grid[row][2 - col] = painted
    grid[row][2 + col] = painted
```

The first fifteen hex **characters** are consumed, one per cell, drawn down the
middle column first and then mirrored outwards: characters 0-4 fill column 2,
5-9 fill columns 1 and 3, 10-14 fill columns 0 and 4. Even is foreground.

Note this indexes hex characters, not digest bytes, and works centre-out rather
than left-to-right. Both details are inherited rather than chosen — see
**Where these constants come from** below.

MD5 is used because this is an identity function, not a security one. It must
be fast, stable, and available everywhere.

## The colour

The hue is drawn from the same digest as the grid, so colour and pattern cannot
drift apart:

```
hue = hexval(h[-7:]) / 0xfffffff * 360      degrees, the last seven hex chars
```

**No rule that reaches a release ever retires.** Once a version has shipped,
repositories are seeded at it and it is theirs; an implementation MUST keep
drawing it, and MUST keep its vectors.

**Before a release, a rule is a draft and may be withdrawn.** Versions 0 to 2
were drafts — the reference's HSL, then Oklab without the warp — and no release
carried them, so they are gone along with their vectors. An implementation MUST
NOT reproduce them.

**A key stamped at a version the implementation does not draw MUST be refused,
not redrawn.** Drawing it with whatever rule is to hand moves a mark nobody
asked to move, which is the one thing the stamp exists to prevent. The refusal
should name `remap` as the way across.

The current release state is in `VERSION` in the reference implementation. While
it reads `0.0.*`, the mapping is a draft and only the current rule exists.

### Version 3, the only rule

Two steps: warp the drawn value into a hue, then build the colour at that hue.

**Step one — the warp.** The value from the digest is a position in the draw,
not an angle directly.

```
centre, half, peak = 215, 50, 4          degrees of Oklab hue

bump(t)  = 0                                              if t <= -half
         = half                                           if t >=  half
         = (t + half)/2 + half/(2*pi) * sin(pi*t/half)    otherwise

total    = 360 + (peak - 1) * half
hue      = 360 * (draw + (peak - 1) * bump(draw - centre)) / total
```

`draw` is the value from the digest, in degrees, reduced to `[0, 360)`.

The function is monotonic and onto `[0, 360)`, so **every hue is still
reachable**. What changes is how much of the draw each one gets: the hue
advances up to four times faster around 215 degrees, so that arc takes roughly a
quarter of the projects its width would otherwise give it. Measured over the
whole draw, the hundred degrees from 165 to 265 fall from 27.8% of projects to
11.0%.

**Why that arc.** The emoji-square fallback has no square between green and
blue, so every mixture of the two reads at essentially one hue and whole bands
there cannot be named at all. That is a property of the vocabulary and cannot be
fixed by choosing better triples. Spending less of the draw there puts the
projects saved where the fallback can tell them apart, at no cost to the other
renderings, which could always draw the colour exactly.

**Why a raised cosine.** Its derivative is zero at both ends, so the draw has no
corner and no project sits on a discontinuity, and its integral is elementary —
which is why the rule above is six lines rather than a spline nobody can
reimplement from prose.

**Step two — the colour at that hue.** The hue is an angle in **Oklab**.
Lightness is fixed. Chroma is the cap, or the most sRGB can carry at that hue,
whichever is smaller:

```
L      = 0.60
chroma = min(0.26, gamut_max(L, hue))
```

`gamut_max` is a bisection with fixed bounds and a fixed number of rounds,
because "search until it converges" is not reproducible:

```
low, high = 0.0, 0.4
repeat 30 times:
    mid = (low + high) / 2
    if OkLCh(L, mid, hue) converts to linear RGB with every channel
       within [-0.0001, 1.0001]:  low = mid
    else:                         high = mid
result = floor(low * 10000) / 10000
```

The truncation to four decimals is deliberate: a port whose cube roots differ in
the last bits still lands on the same number.

Convert OkLCh to linear RGB by the standard Oklab matrices, encode each channel
to sRGB, then quantise.

**Why one lightness.** HSL lightness does not control brightness — at a fixed
0.5, yellow carries several times the light of blue — so a single value is
illegible at one end of the wheel or the other, and covering that needs two
files whose colours differ. Oklab lightness does control brightness, so fixing
it fixes contrast, and one file serves both grounds.

**Why the chroma is capped and not fixed.** Holding every hue to what the
narrowest can manage costs about half the colour on the wheel to buy a
uniformity nobody asked for. A cap lets the hues that can be vivid be vivid and
bites only where sRGB has room to spare.

### Quantising

```
component_255 = floor(component * 255 + 0.5)
```

**Round half up, not half to even.** Stated explicitly because Python's `round`
is half to even while most languages' native rounding is half up; following the
reference language's default would have made this specification quietly
unportable.

### Where these constants come from

The pattern rule — the centre-out hex-character walk — and the seven-character
hue draw are taken from **`stewartlord/identicon.js`**, vendored at
`reference/vendor/identicon.js` and pinned by `vectors.json`. So are `0.7` and
`0.5`, which is why version 0 and 1 look the way they do.

**The version 2 and 3 colour rules are not.** They are this project's own, and
the vendored library cannot produce them. The library still generates the
digests and the grids in `vectors.json`, so the pattern remains pinned by an
implementation nobody here wrote; the colour column is generated by the
reference implementation and is therefore checked against itself. That is a real
weakening of the guarantee and it is stated here rather than hidden: until a
second independent implementation exists, those colours are asserted, not
corroborated.

That is deliberate, and it is the reason to state it here rather than to justify
each value on its merits. The PNGs are produced through that library, so any
constant we picked independently would be a second opinion that the rendered
image would immediately contradict. Deferring to the library removes the
decision entirely: there is one source, and conformance is testable rather than
arguable. An earlier draft of this document specified `saturation = 0.55` and a
byte-indexed left-to-right grid; both were plausible, neither matched what
shipped, and the committed identicon disagreed with its own specification until
this was reconciled.

The corollary is that the inherited values are not defended, only recorded.
Version 2's and 3's are the opposite: chosen, and defended above.

**Version 3's three constants are the ones the wheel was solved against**, and
the wheel is the argument for them: `work-in-progress/wheel.tsv` places all 165
triples of the emoji-square fallback against the gamut, and the arc this warp
compresses is the one where that vocabulary has nothing to say. They are a
judgement about a fallback rendering, made by eye, and they are recorded as such
rather than derived.

**The hue draw is uniform; under versions 0 and 1 the colours are not evenly
spaced.** Both halves of that are measured, and it is the defect version 2 was
made to fix — reading the same draw as an Oklab angle spaces it evenly by
construction. Over 200,000 plausible remotes the hue parameter is uniform
on `[0, 1)` — mean 0.500061, thirty-six bins all within 3.4% of expectation,
chi-square 30.6 on 35 degrees of freedom. But equal steps of HSL hue are not
equal steps of anything the eye uses: ten degrees of HSL buys between 1.7 and
21.2 degrees of Oklab hue, a ratio of 12.5 to 1. Green is the slowest, near HSL
110, and cyan the fastest, near 190.

So under versions 0 and 1 roughly a fifth of all projects land in the 100–130
band that occupies about six degrees of perceptual space, while the teal to blue
stretch runs at about half its share. Version 2 removes both.

**Version 3 makes the draw deliberately uneven again, which is not a reversal of
that.** Version 2's defect was that equal draw bought unequal *colour*; the
spacing was an accident of HSL and nobody chose it. Version 3 keeps the even
perceptual spacing and then spends the draw unevenly on purpose, for a stated
reason, in a stated place. An accident corrected and a choice made are different
things even when the measured histogram looks similar.

### Where this departs from the reference

One place, deliberately: **the background.**

`identicon.js` defaults to `background: [240, 240, 240, 255]` — opaque
`#f0f0f0`, alpha 255 — and writes it onto the SVG root. GitHub ships the same
thing. Two identicons pulled from `avatars.githubusercontent.com` and decoded
are PNG colour type 2, **no alpha channel at all**, with `(240, 240, 240)`
filling 69% and 80% of their pixels. Neither has a dark variant, because
neither needs one: the artifact is a light tile, and on a dark page it is a
light square.

This specification renders **transparent**, and an implementation MUST NOT
paint the background. `vectors.json` still records `#f0f0f0` for every vector
because that is what the library produced from the same digest, but no artifact
uses it and no conformance check reads it.

The reason is the consumers this exists for. A tile is a rectangle, and a
rectangle in a terminal badge or a status panel is chrome — it wants corners,
insets and a border reconciled against whatever surrounds it, none of which
belongs in a specification about deriving a mark. A transparent mark
composites into what is already there and asks for nothing.

**The tile is not the more legible choice, only the more predictable one.**
Measured against `#f0f0f0` at the reference lightness, 36 of 72 sampled hues
score below 3.0:1, worst 1.33:1 — GitHub's own identicons sit at 1.4–1.6:1
against their own ground, permanently, in every theme. What the tile buys is
invariance: the mark never depends on the page. What it costs is the rectangle.

This specification takes the opposite trade, and the dark variant is the price.
A fixed ground makes a fixed lightness work forever; an unknown ground does
not, so the mark is emitted at two lightnesses instead of on two grounds.

## Derived names

From `sha256(key)` as lowercase hex, take:

| Name | Definition | Purpose |
|---|---|---|
| short id | first **12** characters | icon file names, uniqueness |
| discriminator | first **6** characters | distinguishing two projects that share a basename |

The project name is the last `/`-separated segment of the key, or the key itself
if it contains no `/`.

An icon theme name is `<tool-prefix>-<short id>`. The prefix belongs to the
implementing tool: `Console-Colophon` uses `console-colophon`, `Claude-State-Panel`
uses `claude-state-identicon`, and this repository's reference implementation
forms the name under `repository-identicon` without installing anything. The
specification fixes the short id, not the prefix, so two tools installing icons
into the same theme do not collide.

**Badge label**, for media that can only show one or two characters: split the
project name on `-`, `_`, `.` and space. If two or more parts result, take the
first character of each of the first two. Otherwise take the first two
characters of the name. Upper-case the result.

## What goes in the repository

The mark is a pure function of the key, so a repository does not need to store
it. It stores it anyway, because a README, a shell prompt and a forge cannot
run a derivation. **The rendered files are a cache with a canonical location,
not a source of truth**; if they disagree with the key, the key wins and they
are stale.

The key file is the exception, and is the source of truth. It is not a note of
what the mark was made from; it is what the mark is made from.

```
.identicon/repository-identicon.png            block 5, 27px canvas
.identicon/repository-identicon@4x.png         the mark magnified 4x, 104px
.identicon/repository-identicon-128.png        for a consumer that fixes the size
.identicon/repository-identicon-256.png        likewise
.identicon/repository-identicon.svg            vector, same geometry
.identicon/repository-identicon.colour         "#rrggbb\n", nothing else
.identicon/repository-identicon.grid           five lines of "01010"
.identicon/repository-identicon.key            the key, hashed exactly as it reads
```

`.colour` and `.grid` are the whole identicon as text: the two values the text
rendering takes, in the spelling `vectors.json` uses. Together they let a
consumer with no PNG decoder, no SVG parser and no identicon machinery draw the
mark. Rows of characters rather than JSON, so a shell can read either without a
parser and a diff shows one line per changed row.

Both are derived and regenerable. Neither belongs in the key file: that file is
the source of truth, an implementation SHOULD leave it byte-for-byte alone, and
a derived value inside it would go stale with nothing entitled to correct it.

### One file, both grounds

There is one of each rendered artifact, and one `.colour`. A consumer picks by
size, never by theme.

That works because the colour rule holds one **perceived** brightness right
around the hue wheel. Every hue clears 3:1 against white and against
`#0d1117`, so the same file is legible on a light page and a dark one, and a
project looks like itself in both.

An implementation MUST NOT emit theme variants. Two files differing in colour
would mean a repository has two appearances, which is the opposite of an
identity, and it is only ever needed by a colour rule whose brightness wanders.

A README therefore takes a plain markdown image. `<picture>` and
`prefers-color-scheme` are unnecessary here, and CSS inside an SVG is not a
reliable route on a forge in any case — GitHub sanitises rendered SVG and does
not render it inline.

### Copying one out as a forge logo

GitLab uses `logo.png`, `logo.jpg` or `logo.gif` at the repository root as the
project avatar where none has been uploaded — 200 KB maximum, 192 pixels ideal.
`repository-identicon-256.png` satisfies it at about a kilobyte.

This is **a documented manual copy, not something an implementation does**.
Writing to the repository root is a decision about somebody's project, and the
whole of `.identicon/` exists so that a consumer can take what it needs without
the generator reaching outside its own directory.

```bash
cp .identicon/repository-identicon-256.png logo.png
```

**Three files rather than one.** A combined file would be readable by every
tool that knows the format, which is one tool. A README cannot address a
fragment inside a blob, `![](.identicon/repository-identicon.svg)` is a whole
integration, and `$(cat .identicon/repository-identicon.colour)` is a whole
parser. Each is usable by a consumer that knows nothing about this
specification.

**Each filename repeats the directory deliberately.** The directory is context,
and context is what does not travel: copied out, fetched from a raw URL or
dropped into `docs/`, a file called `icon.png` describes nothing. The prefix
also anticipates a repository carrying more than one mark — a user's alongside
the repository's — at which point the unqualified name is the ambiguous one.

### The key is recorded, and replacing it MUST be deliberate

An implementation MUST record the key, and on every later run MUST hash the
recorded key rather than re-deriving one. Re-deriving each time means a rename
silently changes a repository's identity, and not doing that is what an
identity is for.

The recorded key MUST be the whole key, mapping version included. The file
format is one payload line — the first non-blank line that is not a comment —
and an implementation MUST take that line verbatim, whitespace-stripped, with
no further interpretation. It SHOULD leave an existing file byte-for-byte alone
when the key is unchanged, comments included: a run that rewrites this file
under its owner makes every run a diff, and not moving is this file's whole
job.

This separates two unrelated reasons to re-run, which otherwise collide:

- **Refresh the artifacts.** A better renderer, a different size, a new file in
  the set. This must reach every repository without disturbing any identity, so
  it is the default.
- **Change the mark.** Only on explicit instruction — a `--reseed` switch to
  adopt today's seed, a `--remap` switch to keep the seed and move to a newer
  mapping, or equivalents. An implementation MUST NOT do either because the
  remote changed, or because it ships a newer mapping version.

Once seeded, the mark is stable against renaming, moving between forges, being
cloned to a path that would resolve differently, and a newer mapping version
shipping in the tool. Where the seed would now derive differently an
implementation SHOULD report it — call it seed drift; where the recorded
mapping version differs from the one it seeds at, it SHOULD report that too.
It MUST NOT act on either.

**Whatever is replaced SHOULD be kept beside its replacement**, as
`repository-identicon.prior.<ext>` — one level, overwritten each time. Anyone
who wants history has git; this is for the moment before a commit, when a run
has replaced a mark and the previous one is not recorded anywhere yet. The
audience is developers, so a file next to the new one is the whole recovery
procedure, and it is worth more than any amount of asking first.

For a fixed key the write is idempotent: the mark is a pure function of the
key, so a later run produces identical bytes and need not touch the files.

An implementation SHOULD offer a check mode that reports what would change and
writes nothing, for CI and for dependent tools.

### Pointing the README at it

The artifacts are inert until something references them, and the one thing a
repository reliably has is a README. An implementation SHOULD add the mark to
it by default, with a way to decline — an identicon nobody put on the page is
an identicon nobody sees.

```markdown
![](.identicon/repository-identicon.svg)
```

Three constraints on doing it politely:

- **Insert after the first heading**, so the file still opens with what the
  project is called.
- **Write once.** Recognise the mark by the artifact path, which never changes,
  and treat any line containing it as present. An author who has moved it,
  resized it with an `<img>` tag or pointed it at the PNG has decided
  something, and a tool that re-flattens that on every run is a tool people
  turn off.
- **Never create a README.** A repository without one has not asked for one.

The alt text is empty on purpose. The mark carries no information the project
name beside it does not already give, so it is decorative in the accessibility
sense, and an empty `alt` is what tells a screen reader to skip it rather than
announce a filename.

**Precedence**, most specific first: a key or seed supplied explicitly by the
caller; the **recorded key**, which is what the mark is; then the resolution
order in *Resolving a seed* above, of which a committed `.repository-identicon`
is the first row. The last of these applies on the first run, and after a
reseed or a remap.

The recorded key outranks a committed override, which reads backwards until you
notice that they answer different questions: the override says how this
repository *would* be seeded, and the recorded key says what it *is*. Editing
the override on a seeded repository is therefore reported as seed drift and not
acted on, exactly as a rename is. Re-seed to adopt it.

`SVG` carries a declared size so `![]()` renders it as an inline mark rather
than at column width; a consumer that wants it larger supplies the size
itself, which is the right way round.

## Renderings

### Raster

**The block is specified and the canvas is derived.** A block is a whole
number of pixels, the border is a whole number of pixels, and

```
canvas = 5 * block + 2 * border
```

The defined blocks are **1, 2, 3, 4 and 5** pixels at a border of 1, giving
canvases of 7, 12, 17, 22 and 27. Filled blocks take the colour; everything
else is transparent by default.

An implementation MUST NOT derive the block from a canvas. Doing so needs a
heuristic, heuristics do not scale linearly, and a mark that lands on a
different block at a different scale is two drawings rather than one.

#### Canvases a consumer fixes

Some consumers will not take a vector and will not take a 27-pixel raster: a
forge that asks for a logo of a stated size, a desktop icon directory, an
`.ico` or `.icns` member. Those canvases are still derived from a block, not
fitted to by a heuristic. For any canvas that is a multiple of 32:

```
block  = 3 * canvas / 16
border = canvas / 32
```

which satisfies `canvas = 5 * block + 2 * border` exactly, and puts the border
at 3.1% of the canvas at every size — near enough the 3.7% at block 5 that the
mark reads the same throughout.

**16 and 48 have no such geometry and MUST NOT be generated.** `canvas - 5 *
block` has to be even, so the block matches the canvas in parity, and the
thinnest border those two can carry is 18.8% and 8.3% respectively — several
times the family ratio, which would make them look like different marks. A
consumer needing them SHOULD take the SVG or downscale a larger raster.

An implementation MUST refuse a canvas with no exact geometry rather than
fitting the nearest block and padding the difference.

#### The 4x raster

`@4x` multiplies the **block by four and the border by two**:

| block | border | canvas | | 4x block | 4x border | 4x canvas |
|---|---|---|---|---|---|---|
| 1 | 1 | 7 | | 4 | 2 | 24 |
| 2 | 1 | 12 | | 8 | 2 | 44 |
| 3 | 1 | 17 | | 12 | 2 | 64 |
| 4 | 1 | 22 | | 16 | 2 | 84 |
| 5 | 1 | 27 | | 20 | 2 | 104 |

The mark is magnified exactly four times. The border is not, because the border
is chrome rather than content and quadrupling it would spend the new pixels on
empty edge. So `@4x` is not a magnification of the whole canvas, and an
implementation MUST NOT produce it by rendering at four times the canvas size.

### Terminal

**Send the real image where the terminal can take one.** The text rendering is
an approximation of a 5×5 grid and a colour; an inline image is both, exactly.
An implementation SHOULD prefer, in order:

1. **iTerm2 inline image protocol**, `OSC 1337`. The raster PNG, base64, in
   `ESC ] 1337 ; File = <args> : <base64> BEL`. Arguments SHOULD include
   `inline=1`, `size=<byte count>` and `preserveAspectRatio=1`. **No argument
   may contain a colon**, since the colon terminates the argument list and
   begins the payload.
2. **kitty graphics protocol**, `APC _G`. `a=T,f=100`, base64 payload chunked at
   4096 characters, every chunk but the last carrying `m=1`.
3. **Octants plus the emoji triple**, below. Two lines, always: the grid does
   not fit in one. Where the medium affords only one line — a tab title, a
   session name, a status field — send the triple alone or the badge label, and
   accept that the pattern is lost.

Konsole implements the iTerm2 protocol: `Vt102Emulation::osc_put` matches the
literal `1337;File=` and then waits for the `:` terminator, so arguments between
the two are accepted and ignored. It also handles kitty APC graphics and sixel.
Because Konsole ignores the protocol's own width and height arguments, the PNG's
own pixel size decides how large the identicon lands; 40 pixels is about two
text rows.

Protocol selection SHOULD be by environment — `KITTY_WINDOW_ID` or a `TERM`
containing `kitty`; `KONSOLE_VERSION` or `KONSOLE_DBUS_SESSION`; a known
`TERM_PROGRAM`. It MUST NOT be by querying the terminal and waiting for a reply:
this runs in a hook, and a reply that never comes hangs the turn.

**Nothing but the identicon is printed.** No project name, no key, no label. The
mark is the message.

### Text, the fallback

**The text rendering is one thing, not a menu: two lines of octants carrying the
pattern, with three emoji squares carrying the colour.** They are not
alternatives to each other and there is no useful intermediate.

Why it comes out that way, since each constraint rules something out:

- **The grid cannot be one line.** Five rows over a 2×4 lattice is two text
  lines, and there is no arrangement that makes it one. Any medium that affords
  a single line — prefixing a session name, a tab title, a status field — cannot
  take the grid at all. Its only option is the triple alone, or the badge label.
- **The octants are monochrome, and that is where colour has to come from.** The
  grid is one glyph per four cells, so a cell is not separately addressable and
  a foreground colour would tint the whole mark rather than the pattern within
  it. The colour therefore rides in the emoji squares, not in an escape
  sequence.
- **Per-cell true-colour octants are not worth pursuing.** It would mean one
  character per cell to make cells individually colourable, which is a 5×5 block
  of double-width glyphs — larger than the image it is standing in for, in a
  medium chosen because it could not show the image.

So an implementation SHOULD prefer, in order: **inline image**; **octants plus
the emoji triple**; **the emoji triple alone** where only one line is available.
Escape-sequence colour is not part of this rendering.

Both parts are implemented in `text-identicon.py`, which takes a colour and a
grid and nothing else — no key, no digest — so it can be vendored on its own
into a tool with no identicon machinery. The grid feeds the arrangement as well
as the pattern, and it was already being passed in, so that property is
unaffected.

#### Octants, carrying the pattern

Four grid cells per character, drawn with the **`BLOCK OCTANT-n`** set at
U+1CD00–U+1CDE5: a character is a 2×4 lattice of subcells, so five grid rows
fit in two text lines. Bit `i` of a pattern is subcell (`row i // 2`,
`col i % 2`), top to bottom, which is the order Unicode numbers the octants in.
Eight subcell rows hold a five-row grid with three to spare; all three go
**above**, which fills the lower line completely and lets anything appended sit
flush against it.

Two caveats an implementation must handle rather than discover:

- The all-blank pattern is `U+0020 SPACE`, which is genuinely correct and
  single-width where every other octant is double. Emit **two** spaces at the
  point of rendering, so a blank in the middle of a line does not skew the mark
  against the line below. The table stays canonical; the compensation does not.
- Twenty-six of the 256 patterns are quadrants and block elements that already
  existed and were not re-encoded when Unicode 16 specified the set. They are
  the right characters, but fonts commonly do not harmonise them with the 230
  drawn in 2024, and the seam is visible within one mark. There is no alternative
  encoding for most of them, so do not substitute lookalikes.

#### Emoji squares, carrying the colour

**The whole text rendering is a patch for when the identicon proper cannot be
emitted.** Where an image can be sent, send the image: it is the grid, at full
colour, in one glyph's worth of attention. Everything below is standing in for
that, and the triple is the part standing in for 24 bits of colour with nine
named squares — a lossy paraphrase that costs three double-width columns and
carries semantic weight a coloured pattern does not.

It is nonetheless *the* colour channel here rather than a third-tier fallback,
because the octants are monochrome and nothing else can carry it. Palette of
nine: red, orange, yellow, green, blue, purple, brown, black, white.

```
$ python3 text-identicon.py '#2692d9' '01010,01010,10001,10101,01010'
𜺠𜺠
𜶆𜶂🯦 🟦🟩🟦
```

**Which three squares appear is a function of the colour; what order they appear
in is a function of the grid.** Both are needed, and a caller rendering an
identicon holds both, so `text-identicon.py` still takes a colour and a grid and
nothing else — no key and no digest of its own.

The order is the low digit of the grid's fifteen bits, read as a number: columns
0–2 of each row, top to bottom, left to right, since columns 3 and 4 are the
mirror and carry nothing. Index the distinct permutations of the multiset, in
sorted order, modulo how many there are — one, three or six.

**This used to be a pure function of the colour**, so that a consumer holding
only `#rrggbb` could compute the whole mark. That property was real and it was
defended, but it made the order a function of an *output* of the mapping, which
cannot carry information the mapping has not already spent: two projects landing
on the same quantised colour got the same order, necessarily. Over four thousand
projects it produced fewer distinct marks than there were distinct colours. The
grid is fifteen bits of the key's digest, drawn from a slice disjoint from the
hue's, so the order now separates projects that share a colour.

**Which three squares stand for a colour is not yet normative.** The shipped
chooser searches the palette for the mix nearest the target, which produces
combinations that are numerically close and perceptually wrong. A replacement is
settled but not adopted: `work-in-progress/in-use.tsv` is a hand-placed table of
fifty arcs tiling 0–360, each naming its three squares, with `work-in-progress/`
carrying how it was arrived at. It will land here, with vectors, once it ships.

#### Colour vision, stated plainly

**The emoji triple encodes colour and only colour, so it is the weakest part of
this specification for anyone who does not see colour the way it assumes.** That
is not a defect to be argued away; it is the cost of a channel whose entire job
is to carry a hue through a medium that will not carry one.

Simulating dichromatic vision (Viénot, Brettel and Mollon 1999) over the nine
squares **as the emoji font actually paints them**, and calling a pair confusable
below 0.10 in Oklab: all 36 pairs are distinct for normal trichromatic vision;
**7 pairs collapse under deuteranopia, 5 under protanopia, 4 under tritanopia.**

| | worst collapses |
|---|---|
| deuteranopia | red/green 0.043, blue/purple 0.047, orange/green 0.059 |
| protanopia | orange/green 0.020, red/brown 0.051, blue/purple 0.054 |
| tritanopia | purple/brown 0.041, orange/yellow 0.041 |

Deuteranomaly and deuteranopia together affect on the order of one man in
twelve, so this is a common case rather than an edge one.

Three things limit the damage, and an implementation should understand which is
doing the work:

- **Colour is never the only channel.** The grid is the identity; the octants
  carry it with no colour at all, and they come first. A reader who cannot
  separate red from green still has the full 5×5 pattern.
- **Order is a channel, and it is colour-blind.** Which squares appear answers
  *what colour*; the order they appear in is separate information that survives
  any colour deficiency intact. It comes from the grid, so it is independent of
  the colour rather than derived from it — which is what makes it a second
  channel rather than a restatement of the first.
- **Shape, where it is used, is preattentive and independent of hue.** A circle
  among squares is found without search whatever the reader's cone response.

What is *not* claimed: that the triple names a colour reliably for a dichromat.
It does not, and an implementation that needs colour to be legible for everyone
should send the image or use the octants.

#### NO_COLOR

`NO_COLOR` set in the environment, per no-color.org, suppresses inline images
and the emoji triple. The octants remain and are emitted alone: the grid is the
identity and is legible with no colour at all, which is the property that lets
this degrade at all.

There is no colour-depth negotiation in this rendering: the octants are
monochrome by construction and the colour lives in the squares.

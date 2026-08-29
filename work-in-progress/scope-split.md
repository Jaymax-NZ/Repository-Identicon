# Splitting the delivery layers out of `repository-identicon.py`

**Status: the Konsole split is done.** `Console-Colophon` holds the icon theme
and the D-Bus half, with the derivation vendored and held to `vectors.json` by
its own suite; `repository-identicon.py` has lost all thirty of those symbols,
the eight subcommands that drove them, and `_bg`. `PERMISSIONS.md`, the README
command list and `SPEC.md` § Derived names are reconciled.

**Step 2 is dead, not pending.** `Claude-Colophon` shipped, and it does not use
a hook. Its `skills/repo-identicon/repo-identicon.py` is an installer — 33
routines, a hand-rolled flag parser, no subcommands — and the mark reaches the
end of a turn because the skill writes a base64 PNG and an instruction into the
target's `CLAUDE.md`, which Claude reads. There is nothing there for `emit`,
`hooks`, `payload_cwd`, `open_output` or `RETURN_OF_CONTROL_EVENTS` to attach
to, and nothing that would have to be rewritten if they went. **What happens to
those five is now a question about this repository alone**, answered by the rule
below and not by waiting.

**A worse finding came out of checking.** `Claude-Colophon` vendors the
derivation and is held to nothing: there is no `vectors.json` beside it and no
conformance test against one. It has drifted. For
`github.com/justin-maxwell/claude-colophon` its own skill draws `#d926b8`; this
build draws `#8d52ff`, which is also what that repository's committed
`.identicon` holds, because the artifacts there were written by this tool and
not by the skill that ships to users. It hashes the bare seed, so it is at the
unstamped version 0 rule — a different grid, not only a different colour.

That is exactly the failure *What `Console-Colophon` has to vendor* below was
written to prevent, and `Console-Colophon` was checked byte-for-byte across all
ten vectors before it was trusted. `Claude-Colophon` never was. **Fixing it is
work in that repository**, and it is not started.

Written because the file had grown three jobs and only one of them is this
repository's.

## The rule

`SPEC.md` § Scope already settles it, so this is not a new opinion:

> **In:** how to derive a key, and how a key reaches each medium. **Out:** where
> any tool chooses to display the result, and what it does with the rest of its
> interface.

A pure function from key to bytes, name or string is in. A side effect — a file
under `~/.local/share`, a D-Bus call, a hook registration — is out. That test
decides every symbol below, which is why the argument is short.

## Where everything goes

Every top-level symbol in the file is assigned. 123 of 123, none twice.

| destination | symbols | lines |
|---|---:|---:|
| `Repository-Identicon` (stays) | 85 | 958 |
| `Console-Colophon` (new) | 30 | 318 |
| `Claude-Colophon` (exists) | 5 | 84 |
| split between two | 1 | 20 |
| judgement call | 1 | 3 |
| delete, dead | 1 | 6 |

### To `Console-Colophon` — Konsole and D-Bus

Eight subcommands: `install`, `list`, `uninstall`, `sessions`, `probe`, `badge`,
`profile`, `demo`.

- Icon theme and profiles: `INSTALL_SIZES`, `icon_theme_root`,
  `konsole_profile_dir`, `install_icon`, `installed_icons`, `remove_icon`,
  `install_profile`, `installed_profiles`, `profile_filename`, `profile_body`
- D-Bus: `SESSION_IFACE`, `QDBUS_CANDIDATES`, `DBusError`, `find_qdbus`,
  `find_gdbus`, `_run`, `dbus_call`, `dbus_members`, `list_konsole_services`,
  `list_sessions`, `resolve_session`, `BADGE_METHODS`

This is the whole of what writes outside the repository. Once it is gone,
`PERMISSIONS.md`'s claim that "nothing writes outside this repository" becomes
true of the tool and not just of the test commands.

### The return-of-control hook — nowhere to send it

`RETURN_OF_CONTROL_EVENTS`, `payload_cwd`, `open_output`, `cmd_emit`,
`cmd_hooks`. Five symbols; the hook wiring and nothing else. This section
proposed sending them to `Claude-Colophon`, which took a different design, so
there is no recipient.

The text and inline-image rendering that `emit` uses was never going with them
in any case — `SPEC.md` §§ Renderings, Terminal and Text mandate the two
lattices, the tricolour, and the iTerm2 and kitty protocols, so they are the
standard and stay here as reference.

**`emit` is two jobs welded together, and the rule cuts between them.**
Printing the mark in a chosen style is a pure function from key to string, so it
is in; it is also the only command here that prints the terminal renderings at
all, `show` printing a labelled report and `render` writing image files. Reading
a cwd out of a hook payload on stdin, writing to `/dev/tty`, and swallowing
every error to exit 0 are the hook, so they are out. `cmd_hooks` prints a
registration for `~/.claude/settings.json` and is out entirely.

### Stays here

Everything `SPEC.md` defines: key resolution, the grid, the colour, the derived
names, and every rendering — raster, vector, ANSI, octants, inline image — plus
`apply`, `show`, `render` and `text-identicon.py`.

## What `Console-Colophon` has to vendor

34 symbols, 363 lines: the derivation, the derived names, and
`render_png`/`render_svg`/`render_ansi`. That is the intended shape rather than
a cost — the README's whole argument is that implementations vendor and are held
to `vectors.json` by test, not by an import. The new repository needs the same
conformance test against the same pinned vectors, or it is not a consumer of
this specification, just a fork of it.

## What actually happened, against the plan

`profile_name` went with the profile code and `show` stopped printing it, which
is the judgement call below resolved in the direction this document suggested.
`icon_name` stayed: `SPEC.md` § Derived names defines it, so it is the
specification's and not a delivery detail. `ICON_PREFIX` stayed with it, unused
by anything here, because the name it forms is specified.

`doctor` was split as loose end 1 proposed. This repository's now reports the
sibling module, `vectors.json`, the mapping version and the key that resolves
here; `Console-Colophon`'s reports qdbus, gdbus, the theme root, the profile
directory, the `KONSOLE_*` variables and the installed counts.

The receiving repository takes `INSTALL_SIZES` with the installer. The test that
used it here to check a fixed canvas now writes the sizes out itself, because
what it is testing is `edge`, not an icon theme.

## Three loose ends

1. **`doctor` is two reports in one.** It prints the `text-identicon.py` sibling
   check and then qdbus, gdbus, the icon theme root, the profile directory, the
   Konsole environment variables and the installed counts. The first line stays;
   the rest goes. Both halves are worth keeping — neither repository should end
   up without a `doctor`.
2. **`profile_name` is a judgement call.** `SPEC.md` § Derived names fixes the
   short id, the icon theme name and the badge label, but says nothing about
   Konsole profile naming. `cmd_show` prints it today, which is the only reason
   it looks like a derived name. Suggest it moves with the profile code and
   `show` stops printing it — but it is defensible either way, so it should be
   decided rather than left to fall out of a diff.
3. **`SPEC.md` and the code disagree about the icon prefix.** § Derived names
   says "this repository uses `claude-state-identicon-`", and `ICON_PREFIX` has
   said `repository-identicon` since before this branch. One of them is stale
   whatever happens to the split, and the spec is the one making a claim about
   code it can be checked against.
4. **The module docstring is about Konsole.** `repository-identicon.py` opens
   "Per-project identicons for Konsole tabs. A testbed for the two compile-free
   routes..." and points at `docs/konsole-identicons.md`, which this repository
   does not have. It needs a docstring about deriving and applying a mark, and
   the Konsole one has already gone to `Console-Colophon`.
5. **`_bg` is dead.** Defined at line 527, referenced from nowhere in any Python
   file in the tree. It is the background half of a pair with `_fg`, left behind
   when the half-block grid was removed and the octants stopped taking a
   per-cell background. Delete it in the same pass.

## Order of work

The two receiving repositories should have the code before this one drops it, so
that at no point does a working feature exist nowhere:

1. ~~`Console-Colophon` created, with the vendored core and its own conformance
   test against `vectors.json`.~~ Done. The vendored copy was checked
   byte-for-byte against this implementation across all ten vectors first.
2. ~~`Claude-Colophon` takes `emit` and `hooks`.~~ Dead. It shipped without a
   hook, so nothing is waiting and nothing would have to be rewritten.
3. `repository-identicon.py` drops the hook half of `emit` and the whole of
   `hooks`, in one commit that also deletes `_bg`. **Undecided**, and it is the
   only thing this document is still holding.

The ordering rule those three were written to satisfy — that no working feature
exists nowhere — is met either way now. `Claude-Colophon` delivers a mark at the
end of every turn; it just does not do it with a hook.

A fourth item, from checking the third: **`Claude-Colophon`'s vendored
derivation needs a `vectors.json` and a conformance test**, and then needs to be
brought to mapping version 3. It is drawing different marks than this
specification does. That is work in that repository, not this one.

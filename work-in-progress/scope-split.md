# Splitting the delivery layers out of `repository-identicon.py`

Status: proposed, nothing moved yet. Written because the file had grown three
jobs and only one of them is this repository's.

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

### To `Claude-Colophon` — the return-of-control hook

`RETURN_OF_CONTROL_EVENTS`, `payload_cwd`, `open_output`, `cmd_emit`,
`cmd_hooks`. Five symbols; the hook wiring and nothing else.

Note how small this is. The text and inline-image rendering that `emit` uses
does **not** go with it — `SPEC.md` §§ Renderings, Terminal and Text mandate the
octants, the emoji triple, and the iTerm2 and kitty protocols, so they are the
standard and stay here as reference. `Claude-Colophon` vendors them, as the
README says implementations should.

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
3. **`_bg` is dead.** Defined at line 527, referenced from nowhere in any Python
   file in the tree. It is the background half of a pair with `_fg`, left behind
   when the half-block grid was removed and the octants stopped taking a
   per-cell background. Delete it in the same pass.

## Order of work

The two receiving repositories should have the code before this one drops it, so
that at no point does a working feature exist nowhere:

1. `Console-Colophon` created, with the vendored core and its own conformance
   test against `vectors.json`.
2. `Claude-Colophon` takes `emit` and `hooks`.
3. Only then does `repository-identicon.py` lose them, in one commit that also
   deletes `_bg` and reconciles `PERMISSIONS.md` and the README's command list.

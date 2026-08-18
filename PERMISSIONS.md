# Permissions

What working in this repository causes Claude to run, and why.

**Documentation only.** Nothing here is installed automatically. It exists so
that the reason for a rule survives the prompt that requested it.

## Nothing yet

This repository holds a specification, test vectors and a reference
implementation. None of that has moved here (see the README), so there is
nothing to run.

When it does move, the expected set is small and entirely local:

| rule | why |
|---|---|
| `Bash(python3 *)` | The conformance tests, and probes. |
| `Bash(node *)` | Executing the vendored reference library to regenerate or check the pinned vectors. It runs a library committed here, not anything fetched. |

A specification should be implementable by reading it. If working in this
repository ever needs network access or anything that writes outside it, that is
a signal something has been designed wrong, not a rule to add.

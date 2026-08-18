# Permissions

What working in this repository causes Claude to run, and why.

**Documentation only.** Nothing here is installed automatically. It exists so
that the reason for a rule survives the prompt that requested it.

## The whole set

| rule | why |
|---|---|
| `Bash(python3 *)` | The conformance suite, the two modules' own command lines, and probes. |
| `Bash(node *)` | Executing the vendored reference library to regenerate or check the pinned vectors. It runs a library committed here, not anything fetched, and the suite skips it where `node` is absent. |

That is all of it. Nothing installs, nothing writes outside this repository, and
nothing reaches the network.

A specification should be implementable by reading it. If working in this
repository ever needs network access or anything that writes outside it, that is
a signal something has been designed wrong, not a rule to add.

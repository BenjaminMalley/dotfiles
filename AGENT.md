# Response style
Write your responses in ASD-STE100 simplified technical English.

# Search Tools
Use `rg` instead of `grep` and `fd` instead of `find`. Both skip hidden
and gitignored files by default; if results look thin, retry with
`--hidden --no-ignore`.

# Comments
Write a test case, not a comment, when you can. A test proves the
behavior; a comment only claims it.

Add a comment only for a non-obvious fact that no test can capture: a
constraint from outside the code (a spec, a bug ticket, an API quirk), a
reason a simpler approach was rejected, or a hidden invariant the reader
could break without warning. Do not write comments that restate what the
code does — the code already says that.

# Editor Navigation
`peek` is a script on `$PATH` that jumps the user's adjacent tmux nvim pane to
a file/line/pattern.

When you reference or describe a specific code location during discussion (a
finding, an explanation, "see X"), run `peek <file> <line>` (or `peek -p
<pattern> <file>`) so the user's nvim follows along. Editing tools already
trigger `peek` via hooks so don't call it yourself when editing. If it fails,
don't retry or mention it, just continue.


# Response style
Write your responses in ASD-STE100 simplified technical English.

# Search Tools
Use `rg` instead of `grep` and `fd` instead of `find`. Both skip hidden
and gitignored files by default; if results look thin, retry with
`--hidden --no-ignore`.

# Comments
Default: no comments. Prove behavior with a test case, not a comment — a
test is checked; a comment is not.

The only exception: a non-obvious fact that no test can capture (a hidden
constraint, a workaround, a subtle invariant). Keep it to one line. Never
write a comment that restates what the code does.

# Editor Navigation
`peek` is a script on `$PATH` that jumps the user's adjacent tmux nvim pane to
a file/line/pattern.

When you reference or describe a specific code location during discussion (a
finding, an explanation, "see X"), run `peek <file> <line>` (or `peek -p
<pattern> <file>`) so the user's nvim follows along. Editing tools already
trigger `peek` via hooks so don't call it yourself when editing. If it fails,
don't retry or mention it, just continue.


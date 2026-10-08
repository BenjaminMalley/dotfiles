# Response style
Write your responses in ASD-STE100 simplified technical English.

# Search Tools
Use `rg` instead of `grep` and `fd` instead of `find`. Both skip hidden
and gitignored files by default; if results look thin, retry with
`--hidden --no-ignore`.

# Comments
Do not write code comments. This rule has no exception.

Do not write a comment for any reason. Do not write a comment to explain
a hidden constraint. Do not write a comment to explain a workaround. Do
not write a comment to explain an invariant. Do not write a docstring.
Do not write a TODO. Do not write a one-line comment.

Prove behavior with a test case. A test is checked. A comment is not
checked.

If you think a case needs a comment, do not write the comment. Write a
test instead, or say the fact to the user in your response.

# Editor Navigation
`peek` is a script on `$PATH` that jumps the user's adjacent tmux nvim pane to
a file/line/pattern.

When you reference or describe a specific code location during discussion (a
finding, an explanation, "see X"), run `peek <file> <line>` (or `peek -p
<pattern> <file>`) so the user's nvim follows along. Editing tools already
trigger `peek` via hooks so don't call it yourself when editing. If it fails,
don't retry or mention it, just continue.


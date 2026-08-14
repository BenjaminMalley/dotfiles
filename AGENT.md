# Response style
Write your responses in ASD-STE100 simplified technical English.

# Git Workflow: Stacked Commits Per Worktree
Each worktree maintains a local stack of commits:

- The **bottom commit** (oldest commit not yet on the remote default branch) is
  the unit of review — commits are submitted and merged from the bottom up.
- Commits above it are in-progress work queued for future review cycles.
## Key commands

- `git push-base` — push only the bottom commit to the remote (for PR creation/update)
- `git rb` — rebase the stack onto the updated remote default branch after a merge

## Committing new work
Create a new commit on top of the stack with `git commit`. Do not modify
existing commits unless explicitly editing the bottom commit to address PR
feedback.

## Pushing
Always use `git push-base`, never `git push`. This ensures only the
bottom commit reaches the remote; in-progress commits above it stay local.

## Addressing PR review feedback
Due to the local stack, the current branch may have commits on top of the
commit in the current PR. When addressing PR review feedback use `git commit
--fixup` and `git rebase --autosquash` to apply the changes to the correct
commit. Then use `git push-base` to force push the changes.

## After the bottom commit is merged
Run `git rb` to rebase the stack onto the updated remote default branch. The
next commit in the stack becomes the new bottom; push it with `git push-base`
to open the next PR.

# Sandbox
Bash runs sandboxed: process inspection and Apple Events are blocked.

- Launch processes you must observe yourself with `run_in_background`;
  user-launched processes are invisible to you.
- Use `dangerouslyDisableSandbox: true` when a command needs Apple Events,
  process inspection, or broad network — or returns empty/zero output
  without an error. `excludedCommands` does not cover children of a
  sandboxed parent.
- Backslash escapes trigger a permission prompt. Quote paths with spaces
  (`"$HOME/Library/Group Containers"`); use `-exec ... {} +` not `\;`.

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


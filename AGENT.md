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

# Editor Navigation
`peek` is a script on `$PATH` that jumps the user's adjacent tmux nvim pane to
a file/line/pattern.

When you reference or describe a specific code location during discussion (a
finding, an explanation, "see X"), run `peek <file> <line>` (or `peek -p
<pattern> <file>`) so the user's nvim follows along. Editing tools already
trigger `peek` via hooks so don't call it yourself when editing. If it fails,
don't retry or mention it, just continue.


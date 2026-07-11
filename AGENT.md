# Git Workflow: Stacked Commits Per Worktree

Each worktree maintains a local stack of commits:

- The **bottom commit** (oldest commit not yet on the remote default branch) is the unit of review — commits are submitted and merged from the bottom up.
- Commits above it are in-progress work queued for future review cycles.

## Key commands

- `git push-base` — push only the bottom commit to the remote (for PR creation/update)
- `git rb` — rebase the stack onto the updated remote default branch after a merge

## Instructions for AI tools

### Committing new work
Create a new commit on top of the stack with `git commit`. Do not modify existing commits unless explicitly editing the bottom commit to address PR feedback.

### Pushing
Always use `git push-base`, never `git push`. This ensures only the bottom commit reaches the remote; in-progress commits above it stay local.

### Addressing PR review feedback
Do not add a new commit. Instead, edit the bottom commit via interactive rebase:
1. `git rebase -i` — mark the bottom commit as `edit`
2. Make the changes, then `git add`
3. `git rebase --continue` — replays the rest of the stack on top
4. `git push-base` — updates the PR

### After the bottom commit is merged
Run `git rb` to rebase the stack onto the updated remote default branch. The next commit in the stack becomes the new bottom; push it with `git push-base` to open the next PR.

### Reading the stack
A stack with several commits above the base is normal and expected. Do not squash, fixup, or collapse them — each represents intentional in-progress work.

# Editor Navigation

`v` is a script on `$PATH` that jumps the user's adjacent tmux nvim pane to a file/line/pattern.

When you reference or describe a specific code location during discussion (a finding, an explanation, "see X"), run `v <file> <line> --navigate` (or `v <file> -p <pattern> --navigate`) so the user's nvim follows along. Always pass `--navigate` for this — it switches buffers without discarding any unsaved edits the user may have. Editing tools already trigger `v` via hooks; don't call it yourself when editing.

This is best-effort: if it fails (no tmux, no editor pane), don't retry or mention it — just continue.

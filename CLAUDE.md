# YOLO Mode

You should always aim to work in "YOLO mode". This means you should:
1.  Prefer non-interactive commands.
2.  Use flags like `--yolo` or `--yes` if available for the tools you are using (e.g., when using `claude` CLI).
3.  Minimize the number of approvals required from the user by being proactive and confident in your actions.

# OneFlow Commands

When running oneflow via the `of` command, you must prefix it with the `DATA_DIR` environment variable pointing to the current data repo worktree. Ask the user for the data repo worktree path if you don't know it.

Example:
```bash
DATA_DIR=/path/to/data-worktree of <subcommand>
```

# YOLO Mode

You should always aim to work in "YOLO mode". This means you should:
1.  Prefer non-interactive commands.
2.  Use flags like `--yolo` or `--yes` if available for the tools you are using (e.g., when using `claude` CLI).
3.  Minimize the number of approvals required from the user by being proactive and confident in your actions.

# Project Utilities

## Notifications
You have access to a system notification tool `notify`.
You should use this tool to alert the user whenever:
1. You have completed a significant task.
2. You are paused and waiting for user input.

**Usage:**
```bash
notify "Message" "Title"
```

**Examples:**
- `notify "Unit tests passed" "Claude"`
- `notify "Waiting for approval" "Claude"`

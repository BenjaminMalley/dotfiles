# Project Utilities

## Notifications
You have access to a system notification tool located at `scripts/notify`.
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

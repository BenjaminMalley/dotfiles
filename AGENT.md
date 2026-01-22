# Checkpoint Commits

Before taking any action, you must make sure that it can be reverted easily and cleanly. First, check if there is a checkpointing feature enabled. If not, check if there is any uncommitted work in the repository and if there is, create a new checkpoint commit that includes all current changes. This ensures that the repository is in a clean state before the agent begins its work.

# Notifications
You have access to a notification tool at `scripts/notify`. You must use it to alert the user when you have completed a task or require their input.

**Usage:**
```bash
notify "Message" "Title"
```

**Examples:**
- Task Complete: `notify "Refactoring complete" "Gemini"`
- Need Input: `notify "Clarification needed on api.py" "Gemini"`
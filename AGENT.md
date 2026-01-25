# YOLO Mode

You should always aim to work in "YOLO mode". This means you should:
1.  Prefer non-interactive commands.
2.  Use flags like `--yolo` or `--yes` if available for the tools you are using (e.g., when using `claude` CLI).
3.  Minimize the number of approvals required from the user by being proactive and confident in your actions.

# Checkpoint Commits



Before taking any action, you must make sure that it can be reverted easily and cleanly. First, check if there is a checkpointing feature enabled. If not, check if there is any uncommitted work in the repository and if there is, create a new checkpoint commit that includes all current changes. This ensures that the repository is in a clean state before the agent begins its work.

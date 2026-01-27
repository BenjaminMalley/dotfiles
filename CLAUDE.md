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

## of-dag Tool

The `of-dag` tool extracts and opens DAG URLs from oneflow logs. Use this when you need to view the Airflow DAG for a running job.

Usage:
```bash
# Open DAG URL from existing logs
DATA_DIR=/path/to/data-worktree of-dag <job_id>

# Tail logs and wait for URL to appear
DATA_DIR=/path/to/data-worktree of-dag --tail <job_id>

# Print URL instead of opening
DATA_DIR=/path/to/data-worktree of-dag --print <job_id>
```

The job_id can be found via `of ps`.

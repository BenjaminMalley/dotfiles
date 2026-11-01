import subprocess
import sys

def run_command(command, check=True, capture_output=False, text=True):
    """
    Unified wrapper for subprocess.run.
    Returns the result object.
    """
    try:
        return subprocess.run(command, check=check, capture_output=capture_output, text=text)
    except FileNotFoundError:
        print(f"Warning: Command '{command[0]}' not found. Skipping.", file=sys.stderr)
        return None
    except subprocess.CalledProcessError as e:
        if check:
            raise e
        else:
            print(f"Warning: Command '{' '.join(command)}' failed with error: {e}", file=sys.stderr)
            return e

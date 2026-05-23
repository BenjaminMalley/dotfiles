import sys
import json
import os
import subprocess
import re
from lib.notifications import send_notification

def run_local_script(script_name, *args):
    """Helper to run a script in the scripts directory."""
    # We maintain this for now to interact with existing scripts like 'v'
    # but eventually 'v' can also be moved into the library.
    repo_root = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    script_path = os.path.join(repo_root, 'scripts', script_name)
    try:
        subprocess.run([script_path, *args], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        sys.stderr.write(f"Error running {script_name}: {e}\n")

def handle_gemini_payload(payload_str):
    """Processes the Gemini hook payload."""
    if not payload_str:
        return "{}"

    try:
        data = json.loads(payload_str)
        event = data.get('hook_event_name', '')

        # Refresh editor on completion or when attention is needed
        if event in ['AfterAgent', 'Notification']:
            run_local_script('v')

        # Check for file modification tools to trigger editor refresh/jump
        if event == 'AfterTool' and data.get('tool_name') in ['write_file', 'replace']:
            tool_input = data.get('tool_input', {})
            file_path = tool_input.get('file_path')
            if file_path:
                line_num = None
                try:
                    diff = data.get('tool_response', {}).get('returnDisplay', {}).get('fileDiff', '')
                    match = re.search(r'@@ -\d+,\d+ \+(\d+),\d+ @@', diff)
                    if match:
                        line_num = str(int(match.group(1)) + 3)
                except Exception:
                    pass

                if line_num:
                    run_local_script('v', file_path, line_num)
                else:
                    run_local_script('v', file_path)

    except Exception as e:
        sys.stderr.write(f"Error processing Gemini payload: {e}\n")

    return "{}"

def calculate_claude_line_number(data):
    """Calculate line number for Claude Edit/Write tools."""
    tool_name = data.get('tool_name')
    tool_input = data.get('tool_input', {})
    file_path = tool_input.get('file_path')

    if tool_name == 'Write':
        return 1  # New file or full rewrite, start at top

    if tool_name == 'Edit':
        new_string = tool_input.get('new_string', '')
        if file_path and new_string:
            try:
                with open(file_path, 'r') as f:
                    first_line = new_string.split('\n')[0]
                    for i, line in enumerate(f, 1):
                        if first_line in line:
                            return i
            except Exception:
                pass

    return None  # Fallback: open without line number


def handle_claude_edit(payload_str):
    """Handles Claude PostToolUse (Edit/Write) — opens file at edit location."""
    if not payload_str:
        return "{}"
    try:
        data = json.loads(payload_str)
        tool_input = data.get('tool_input', {})
        file_path = tool_input.get('file_path')
        if file_path:
            line_num = calculate_claude_line_number(data)
            if line_num:
                run_local_script('v', file_path, str(line_num))
            else:
                run_local_script('v', file_path)
    except Exception as e:
        sys.stderr.write(f"Error processing Claude edit payload: {e}\n")
    return "{}"


def handle_claude_stop(payload_str):
    """Handles Claude Stop — refreshes editor only."""
    if not payload_str:
        return "{}"
    try:
        run_local_script('v')
    except Exception as e:
        sys.stderr.write(f"Error processing Claude stop payload: {e}\n")
    return "{}"


def handle_claude_notification(payload_str):
    """Handles Claude Notification — refreshes editor and sends desktop notification."""
    if not payload_str:
        return "{}"
    try:
        data = json.loads(payload_str)
        cwd = data.get('cwd', '')
        project_name = os.path.basename(cwd) if cwd else 'Claude'
        run_local_script('v')
        send_notification("Input Required", f"Claude ({project_name})")
    except Exception as e:
        sys.stderr.write(f"Error processing Claude notification payload: {e}\n")
    return "{}"

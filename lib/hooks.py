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
        subprocess.run([script_path, *args], check=False)
    except Exception as e:
        sys.stderr.write(f"Error running {script_name}: {e}\n")

def handle_gemini_payload(payload_str):
    """Processes the Gemini hook payload."""
    if not payload_str:
        return "{}"
    
    try:
        data = json.loads(payload_str)
        ntype = data.get('notification_type', '')
        event = data.get('hook_event_name', '')
        cwd = data.get('cwd', '')
        
        project_name = os.path.basename(cwd) if cwd else 'Gemini'
        should_notify = False
        msg = ntype if ntype else 'Agent Finished'
        
        if event == 'Notification' and ntype in ['ToolPermission', 'InputRequired', 'IdleAlert']:
            should_notify = True
        elif event == 'AfterAgent':
            should_notify = True

        # Check for file modification tools to trigger editor refresh
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

        if should_notify:
            send_notification(msg, f"Gemini ({project_name})")

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


def handle_claude_payload(payload_str):
    """Processes the Claude hook payload."""
    if not payload_str:
        return "{}"

    try:
        data = json.loads(payload_str)
        event = data.get('hook_event_name', '')
        cwd = data.get('cwd', '')
        project_name = os.path.basename(cwd) if cwd else 'Claude'

        # Handle file edit events - open file at edit location
        if event == 'PostToolUse' and data.get('tool_name') in ['Edit', 'Write']:
            tool_input = data.get('tool_input', {})
            file_path = tool_input.get('file_path')
            if file_path:
                line_num = calculate_claude_line_number(data)
                if line_num:
                    run_local_script('v', file_path, str(line_num))
                else:
                    run_local_script('v', file_path)
            return "{}"

        # Handle notification/stop events - refresh editor and notify
        if event in ['Stop', 'Notification']:
            run_local_script('v')
            send_notification("Input Required", f"Claude ({project_name})")

    except Exception as e:
        sys.stderr.write(f"Error processing Claude payload: {e}\n")

    return "{}"

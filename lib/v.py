import sys
import os
import subprocess

def get_other_pane():
    """Finds a pane in the current window that is not the active one."""
    try:
        # List panes: id, active_flag, current_command
        output = subprocess.check_output(
            ['tmux', 'list-panes', '-F', '#{pane_id}:#{pane_active}:#{pane_current_command}'],
            text=True
        ).strip().split('\n')
        
        current_pane = None
        other_panes = []
        
        for line in output:
            parts = line.split(':')
            if len(parts) < 3:
                continue
            p_id, active, cmd = parts[0], parts[1], parts[2]
            if active == '1':
                current_pane = p_id
            else:
                other_panes.append((p_id, cmd))
        
        if not other_panes:
            return None, None
            
        # Return the first non-active pane
        return other_panes[0]
        
    except Exception:
        return None, None

def refresh_editor(filename=None, line=None):
    """Opens a file in the adjacent tmux pane's Vim or refreshes it."""
    # Find target pane
    target_pane_id, pane_cmd = get_other_pane()
    
    if not target_pane_id:
        print("Error: Could not find another pane in the current tmux window.", file=sys.stderr)
        return False
        
    # Check if the target pane is running vim, vi, or nvim
    is_vim = any(cmd in pane_cmd.lower() for cmd in ['vim', 'vi', 'nvim'])
    
    # Construct Tmux commands
    cmds = []
    
    if is_vim:
        # Escape twice to ensure we're out of any modes and back to Normal
        cmds.append(['tmux', 'send-keys', '-t', target_pane_id, 'Escape', 'Escape'])
        
        if filename:
            # Open/Reload specific file forcefully
            abs_path = os.path.abspath(filename)
            cmds.append(['tmux', 'send-keys', '-t', target_pane_id, f':e! {abs_path}', 'Enter', ':redraw!', 'Enter'])
            if line:
                cmds.append(['tmux', 'send-keys', '-t', target_pane_id, f':{line}', 'Enter'])
        else:
            # Just refresh current buffer
            cmds.append(['tmux', 'send-keys', '-t', target_pane_id, ':checktime', 'Enter', ':redraw!', 'Enter'])
    else:
        if filename:
            # Start nvim with the file
            abs_path = os.path.abspath(filename)
            cmds.append(['tmux', 'send-keys', '-t', target_pane_id, f'nvim {abs_path}', 'Enter'])
            if line:
                cmds.append(['tmux', 'send-keys', '-t', target_pane_id, f':{line}', 'Enter'])
        
    # Execute commands
    for cmd in cmds:
        subprocess.run(cmd, check=True)
    
    return True

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Open file in the adjacent tmux pane's Vim.")
    parser.add_argument("filename", nargs="?", help="File to open", default=None)
    parser.add_argument("line", nargs="?", help="Line number", default=None)
    args = parser.parse_args()
    
    # Ensure empty string is treated as None
    filename = args.filename if args.filename and args.filename.strip() else None
    
    if not refresh_editor(filename, args.line):
        sys.exit(1)
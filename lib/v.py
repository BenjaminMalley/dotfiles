import sys
import os
import subprocess

def get_other_pane_info():
    """Finds a pane in the current window that is not the active one and its details."""
    try:
        # List panes: id, active_flag, tty, current_command
        output = subprocess.check_output(
            ['tmux', 'list-panes', '-F', '#{pane_id}:#{pane_active}:#{pane_tty}:#{pane_current_command}'],
            text=True
        ).strip().split('\n')
        
        for line in output:
            parts = line.split(':')
            if len(parts) < 4:
                continue
            p_id, active, tty, cmd = parts[0], parts[1], parts[2], parts[3]
            if active == '0':
                # Check for any editor on this TTY
                try:
                    # 'ps -t' expects the TTY name without /dev/
                    tty_short = tty.replace('/dev/', '')
                    ps_output = subprocess.check_output(
                        ['ps', '-t', tty_short, '-o', 'command='],
                        text=True
                    ).strip().split('\n')
                    
                    editor_on_tty = None
                    for p_cmd in ps_output:
                        if any(e in p_cmd.lower() for e in ['nvim', 'vim', 'vi']):
                            # Match the binary name specifically
                            if 'nvim' in p_cmd.lower(): editor_on_tty = 'nvim'
                            elif 'vim' in p_cmd.lower(): editor_on_tty = 'vim'
                            elif 'vi' in p_cmd.lower(): editor_on_tty = 'vi'
                            break
                    
                    return p_id, cmd, editor_on_tty
                except Exception:
                    return p_id, cmd, None
        
        return None, None, None
        
    except Exception:
        return None, None, None

def refresh_editor(filename=None, line=None):
    """Opens a file in the adjacent tmux pane's Vim or refreshes it."""
    # Find target pane and editor info
    target_pane_id, foreground_cmd, editor_on_tty = get_other_pane_info()
    
    if not target_pane_id:
        print("Error: Could not find another pane in the current tmux window.", file=sys.stderr)
        return False
        
    # Check if the foreground command is an editor
    is_editor_foreground = any(e in foreground_cmd.lower() for e in ['nvim', 'vim', 'vi'])
    
    # Construct Tmux commands
    cmds = []
    
    # If an editor is on the TTY but NOT in the foreground, try to 'fg' it
    if editor_on_tty and not is_editor_foreground:
        # We send 'fg' and Enter to resume the editor. 
        # Using %nvim or %vim is safer if multiple jobs exist, but 'fg' usually works for the last one.
        cmds.append(['tmux', 'send-keys', '-t', target_pane_id, f'fg %{editor_on_tty}', 'Enter'])
        # Give it a moment to resume? No, send-keys is fast. 
        # But we need the subsequent keys to go to the resumed editor.
        is_editor_foreground = True

    if is_editor_foreground or editor_on_tty:
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
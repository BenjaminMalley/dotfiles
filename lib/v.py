import sys
import os
import subprocess
import time

class VRefresher:
    """Encapsulates the logic for refreshing an editor in a tmux pane."""

    EDITORS = ['nvim', 'vim', 'vi']
    SHELLS = ['bash', 'zsh', 'fish', 'sh']

    def __init__(self, filename=None, line=None, column=None, pattern=None, dry_run=False):
        self.filename = filename
        self.line = line
        self.column = column
        self.pattern = pattern
        self.dry_run = dry_run

        self.target_pane_id = None
        self.foreground_cmd = None
        self.editor_on_tty = None
        self.pane_content = ""
        self.is_editor_foreground = False

    def _get_pane_content(self, pane_id, lines=10):
        """Returns the last few lines of the specified tmux pane."""
        try:
            return subprocess.check_output(
                ['tmux', 'capture-pane', '-pt', pane_id, '-S', f'-{lines}'],
                text=True
            ).strip()
        except Exception:
            return ""

    def _discover_panes(self):
        """Finds all panes in the current window and identifies candidates."""
        try:
            output = subprocess.check_output(
                ['tmux', 'list-panes', '-F', '#{pane_id}:#{pane_active}:#{pane_tty}:#{pane_current_command}:#{pane_title}'],
                text=True
            ).strip().split('\n')

            candidates = []
            for line in output:
                parts = line.split(':')
                if len(parts) < 5: continue
                p_id, active, tty, cmd, title = parts[0], parts[1], parts[2], parts[3], parts[4]

                if active == '1': continue

                # Check for editor on TTY via ps
                editor_on_tty, is_foreground_ps = self._detect_editor_on_tty(tty)

                candidates.append({
                    'id': p_id,
                    'cmd': cmd.lower(),
                    'title': title,
                    'editor_on_tty': editor_on_tty,
                    'is_foreground_ps': is_foreground_ps
                })
            return candidates
        except Exception:
            return []

    def _detect_editor_on_tty(self, tty):
        """Uses ps to find editors on a specific TTY."""
        try:
            tty_short = os.path.basename(tty)
            ps_output = subprocess.check_output(
                ['ps', '-t', tty_short, '-o', 'stat=,command='],
                text=True
            ).strip().split('\n')

            for line in ps_output:
                parts = line.split(None, 1)
                if len(parts) < 2: continue
                stat, cmd = parts[0], parts[1].lower()

                for editor in self.EDITORS:
                    if editor in cmd:
                        return editor, ('+' in stat)
            return None, False
        except Exception:
            return None, False

    def select_target_pane(self):
        """Selects the pane titled 'Editor'."""
        candidates = self._discover_panes()
        for c in candidates:
            if c['title'] == 'Editor':
                self.target_pane_id = c['id']
                self.foreground_cmd = c['cmd']
                self.editor_on_tty = c['editor_on_tty'] or next((e for e in self.EDITORS if e in c['cmd']), None)
                self.is_editor_foreground = any(e in self.foreground_cmd for e in self.EDITORS) or c['is_foreground_ps']
                return True
        return False

    def run(self):
        """Executes the refresh logic."""
        if not self.select_target_pane():
            sys.stderr.write("Error: Could not find another pane in the current tmux window.\n")
            return False

        self.pane_content = self._get_pane_content(self.target_pane_id)

        # Attempt to 'fg' if in shell and editor is on TTY
        if self.editor_on_tty and not self.is_editor_foreground:
            if not any(msg in self.pane_content for msg in ["job not found", "no current job"]):
                if any(s in self.foreground_cmd for s in self.SHELLS):
                    fg_cmd = [['tmux', 'send-keys', '-t', self.target_pane_id, f'fg %{self.editor_on_tty}', 'Enter']]
                    if self.dry_run:
                        print(f"Would attempt to fg %{self.editor_on_tty}")
                        self.is_editor_foreground = True # Assume success for dry-run
                    else:
                        if not self._execute(fg_cmd):
                            return False
                        
                        # Wait a moment for the shell to process the job switch
                        time.sleep(0.1)
                        
                        # Re-verify foreground state
                        if not self.select_target_pane() or not self.is_editor_foreground:
                            sys.stderr.write(f"Error: Failed to foreground {self.editor_on_tty} or lost pane. Aborting to avoid command pollution.\n")
                            return False

        # Safety Check: Abort if we are about to send editor keys to a non-editor/non-shell
        if self.filename and not self.is_editor_foreground and not any(s in self.foreground_cmd for s in self.SHELLS):
            sys.stderr.write(f"Warning: Foreground command '{self.foreground_cmd}' is not an editor or shell. Aborting.\n")
            return False

        cmds = []
        if self.is_editor_foreground:
            cmds.extend(self._get_editor_cmds())
        elif self.filename and any(s in self.foreground_cmd for s in self.SHELLS):
            cmds.append(self._get_start_editor_cmd())

        return self._execute(cmds)

    def _get_editor_cmds(self):
        """Constructs commands to refresh an existing editor."""
        cmds = [
            ['tmux', 'send-keys', '-t', self.target_pane_id, 'C-[', 'C-[', 'Escape', 'Escape'],
            ['tmux', 'send-keys', '-t', self.target_pane_id, ':checktime', 'Enter']
        ]
        if self.filename:
            abs_path = os.path.abspath(self.filename)
            cmds.append(['tmux', 'send-keys', '-t', self.target_pane_id, f':e! {abs_path}', 'Enter'])
            if self.pattern:
                cmds.append(['tmux', 'send-keys', '-t', self.target_pane_id, f'/{self.pattern}', 'Enter'])
            elif self.line:
                if self.column:
                    cmds.append(['tmux', 'send-keys', '-t', self.target_pane_id, f':call cursor({self.line}, {self.column})', 'Enter'])
                else:
                    cmds.append(['tmux', 'send-keys', '-t', self.target_pane_id, f':{self.line}', 'Enter'])
        cmds.append(['tmux', 'send-keys', '-t', self.target_pane_id, ':redraw!', 'Enter'])
        return cmds

    def _get_start_editor_cmd(self):
        """Constructs a command to start a new editor."""
        abs_path = os.path.abspath(self.filename)
        editor = self.editor_on_tty or 'nvim'
        args = [editor]
        if self.pattern: args.extend(['-c', f'/{self.pattern}'])
        elif self.line:
            if self.column: args.extend(['-c', f'call cursor({self.line}, {self.column})'])
            else: args.append(f'+{self.line}')
        args.append(abs_path)
        return ['tmux', 'send-keys', '-t', self.target_pane_id, " ".join(args), 'Enter']

    def _execute(self, cmds):
        """Executes the gathered tmux commands."""
        if self.dry_run:
            print(f"Target Pane: {self.target_pane_id}")
            print(f"Foreground: {self.foreground_cmd}, Editor on TTY: {self.editor_on_tty}")
            print("Would execute:")
            for cmd in cmds: print(f"  {' '.join(cmd)}")
            return True

        try:
            for cmd in cmds:
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except subprocess.CalledProcessError as e:
            sys.stderr.write(f"Error executing tmux command: {e}\n")
            return False

def get_pane_content(pane_id, lines=5):
    return VRefresher()._get_pane_content(pane_id, lines)

def get_other_pane_info():
    v = VRefresher()
    if v.select_target_pane():
        return v.target_pane_id, v.foreground_cmd, v.editor_on_tty
    return None, None, None

def inspect_panes():
    try:
        output = subprocess.check_output(
            ['tmux', 'list-panes', '-F', '#{pane_id}:#{pane_active}:#{pane_tty}:#{pane_current_command}:#{pane_title}'],
            text=True
        ).strip().split('\n')
        print(f"{'ID':<6} {'Active':<8} {'TTY':<12} {'Command':<15} {'Title':<15} {'Content (Last Line)'}")
        print("-" * 100)
        v = VRefresher()
        for line in output:
            parts = line.split(':'); 
            if len(parts) < 5: continue
            p_id, active, tty, cmd, title = parts[0], parts[1], parts[2], parts[3], parts[4]
            content = v._get_pane_content(p_id, lines=1).replace('\n', ' ')
            print(f"{p_id:<6} {active:<8} {tty:<12} {cmd:<15} {title:<15} {content}")
    except Exception as e:
        print(f"Error inspecting panes: {e}")

def refresh_editor(filename=None, line=None, column=None, pattern=None, dry_run=False):
    return VRefresher(filename, line, column, pattern, dry_run).run()

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Open file in the adjacent tmux pane's Vim.")
    parser.add_argument("filename", nargs="?", help="File to open (can be filename:line:col)", default=None)
    parser.add_argument("line", nargs="?", help="Line number", default=None)
    parser.add_argument("column", nargs="?", help="Column number", default=None)
    parser.add_argument("-p", "--pattern", help="Search pattern to jump to", default=None)
    parser.add_argument("--inspect", action="store_true", help="Inspect panes and exit")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without doing it")
    args = parser.parse_args()

    if args.inspect:
        inspect_panes()
        return

    filename, line, column = args.filename, args.line, args.column
    if filename and ':' in filename:
        parts = filename.split(':')
        filename = parts[0]
        if len(parts) > 1 and parts[1].isdigit():
            line = parts[1]
            if len(parts) > 2 and parts[2].isdigit():
                column = parts[2]

    filename = filename if filename and filename.strip() else None
    if not refresh_editor(filename, line, column, args.pattern, dry_run=args.dry_run):
        sys.exit(1)

if __name__ == "__main__":
    main()
import sys
import os
import shlex
import subprocess
import time

RPC_TIMEOUT = 3            # seconds per nvim --remote-expr call
SOCKET_POLL_SECONDS = 2.0  # wait for init.lua to create the socket after starting nvim
BLOCKING_MODES = ('r', 'rm', 'r?', '!')  # hit-enter / more / confirm / shell-exec
SHELLS = ('bash', 'zsh', 'fish', 'sh')


class PeekError(Exception):
    pass


class Peek:
    """Opens files in the adjacent tmux pane's nvim via its RPC socket."""

    def __init__(self, filename=None, line=None, column=None, pattern=None):
        self.filename = filename
        self.line = line
        self.column = column
        self.pattern = pattern
        self.pane_id = None
        self.pane_cmd = None
        self.sock = None

    # --- discovery ---------------------------------------------------

    def find_editor_pane(self):
        """Returns (pane_id, pane_current_command) for the non-active pane
        titled 'Editor' in the invoking pane's window, or (None, None).

        Scopes list-panes with -t $TMUX_PANE when set: without it, tmux
        resolves the target against the attached client's window, so a hook
        firing in a background wts session would hit the wrong session."""
        cmd = ['tmux', 'list-panes', '-F',
               '#{pane_id}:#{pane_active}:#{pane_current_command}:#{pane_title}']
        tmux_pane = os.environ.get('TMUX_PANE')
        if tmux_pane:
            cmd.extend(['-t', tmux_pane])
        try:
            out = subprocess.check_output(cmd, text=True).strip().split('\n')
        except Exception:
            return None, None
        for line in out:
            parts = line.split(':')
            if len(parts) < 4:
                continue
            if parts[1] == '1':  # the invoking pane
                continue
            if parts[3] == 'Editor':
                return parts[0], parts[2]
        return None, None

    @staticmethod
    def socket_path(pane_id):
        return '/tmp/nvim-{}-{}.sock'.format(os.environ.get('USER', ''), pane_id)

    # --- RPC ----------------------------------------------------------

    def rpc(self, expr):
        """Evaluates expr in the pane's nvim. Raises PeekError on failure.

        The timeout is the guard against nvim sitting in a blocking dialog
        (e.g. swap-file ATTENTION raised by our own :drop): the request
        stalls, we give up, and nothing further is sent."""
        try:
            res = subprocess.run(
                ['nvim', '--server', self.sock, '--remote-expr', expr],
                capture_output=True, text=True, timeout=RPC_TIMEOUT)
        except subprocess.TimeoutExpired:
            raise PeekError('nvim is not responding (a dialog may be open)')
        if res.returncode != 0:
            raise PeekError('nvim RPC failed (dead socket?)')
        return res.stdout.strip()

    @staticmethod
    def _vim_str(s):
        """VimL single-quoted string literal: backslashes are literal,
        only single quotes need doubling."""
        return "'" + s.replace("'", "''") + "'"

    def _exprs(self):
        exprs = ["execute('checktime')"]
        if self.filename:
            path = os.path.abspath(self.filename)
            # :drop reuses an existing buffer without discarding unsaved
            # changes, unlike :e! which force-reloads from disk.
            exprs.append("execute('drop ' . fnameescape({}))".format(self._vim_str(path)))
            if self.pattern:
                exprs.append("search({})".format(self._vim_str(self.pattern)))
            elif self.line:
                if self.column:
                    exprs.append("cursor({}, {})".format(self.line, self.column))
                else:
                    exprs.append("execute(':{}')".format(self.line))  # digits only
        exprs.append("execute('redraw!')")
        return exprs

    # --- the one sanctioned send-keys --------------------------------

    def _start_nvim(self):
        """The Editor pane is at a shell: start nvim via tmux send-keys,
        then poll for the socket init.lua creates."""
        target = shlex.quote(os.path.abspath(self.filename))
        subprocess.run(['tmux', 'send-keys', '-t', self.pane_id,
                        'nvim ' + target, 'Enter'],
                       check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.time() + SOCKET_POLL_SECONDS
        while time.time() < deadline:
            if os.path.exists(self.sock):
                return True
            time.sleep(0.1)
        return False

    # --- main flow ----------------------------------------------------

    def _fail(self, msg):
        sys.stderr.write('peek: ' + msg + '\n')
        return False

    def run(self):
        self.pane_id, self.pane_cmd = self.find_editor_pane()
        if not self.pane_id:
            return self._fail("no pane titled 'Editor' in the current tmux window")
        self.sock = self.socket_path(self.pane_id)

        alive = os.path.exists(self.sock)
        if alive:
            try:
                mode = self.rpc('mode()')
            except PeekError:
                alive = False

        if not alive:
            # Recover only via shell foreground + a file to open; never send
            # keystrokes into an editor, and never start nvim for a bare refresh.
            if self.filename and self.pane_cmd in SHELLS:
                if not self._start_nvim():
                    return self._fail('started nvim but no socket appeared at ' + self.sock)
                try:
                    mode = self.rpc('mode()')
                except PeekError as e:
                    return self._fail(str(e))
            else:
                return self._fail('nvim socket {} not responding '
                                  '(is this nvim running the dotfiles init.lua?)'.format(self.sock))

        if mode in BLOCKING_MODES:
            return self._fail('nvim is showing a prompt; resolve it first')

        try:
            for expr in self._exprs():
                self.rpc(expr)
        except PeekError as e:
            return self._fail(str(e))
        return True


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Open a file in the adjacent tmux pane's nvim.")
    parser.add_argument("filename", nargs="?", default=None,
                        help="File to open (can be filename:line:col)")
    parser.add_argument("line", nargs="?", default=None, help="Line number")
    parser.add_argument("column", nargs="?", default=None, help="Column number")
    parser.add_argument("-p", "--pattern", default=None,
                        help="Search pattern to jump to")
    args = parser.parse_args()

    filename, line, column = args.filename, args.line, args.column
    if filename and ':' in filename:
        parts = filename.split(':')
        filename = parts[0]
        if len(parts) > 1 and parts[1].isdigit():
            line = parts[1]
            if len(parts) > 2 and parts[2].isdigit():
                column = parts[2]

    filename = filename if filename and filename.strip() else None
    if not Peek(filename, line, column, args.pattern).run():
        sys.exit(1)


if __name__ == "__main__":
    main()

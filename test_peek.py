import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import subprocess
import io

# Add the lib directory to sys.path so we can import peek
sys.path.append(os.path.join(os.path.dirname(__file__), 'lib'))
import peek


def list_panes_output(*panes):
    """Builds tmux list-panes output. Each pane: (id, active, cmd, title)."""
    return '\n'.join('{}:{}:{}:{}'.format(*p) for p in panes)


class TestFindEditorPane(unittest.TestCase):

    @patch.dict(os.environ, {}, clear=True)
    @patch('subprocess.check_output')
    def test_selects_inactive_editor_titled_pane(self, mock_out):
        mock_out.return_value = list_panes_output(
            ('%1', '1', 'zsh', 'Agent'),
            ('%2', '0', 'nvim', 'Editor'),
        )
        pane_id, cmd = peek.Peek().find_editor_pane()
        self.assertEqual(('%2', 'nvim'), (pane_id, cmd))

    @patch.dict(os.environ, {}, clear=True)
    @patch('subprocess.check_output')
    def test_skips_active_pane_even_if_titled_editor(self, mock_out):
        mock_out.return_value = list_panes_output(('%1', '1', 'nvim', 'Editor'),)
        pane_id, cmd = peek.Peek().find_editor_pane()
        self.assertEqual((None, None), (pane_id, cmd))

    @patch.dict(os.environ, {}, clear=True)
    @patch('subprocess.check_output')
    def test_no_editor_pane(self, mock_out):
        mock_out.return_value = list_panes_output(
            ('%1', '1', 'zsh', 'Agent'),
            ('%2', '0', 'zsh', 'Shell'),
        )
        self.assertEqual((None, None), peek.Peek().find_editor_pane())

    @patch.dict(os.environ, {}, clear=True)
    @patch('subprocess.check_output')
    def test_tmux_failure(self, mock_out):
        mock_out.side_effect = subprocess.CalledProcessError(1, 'tmux')
        self.assertEqual((None, None), peek.Peek().find_editor_pane())

    @patch.dict(os.environ, {'TMUX_PANE': '%17'})
    @patch('subprocess.check_output')
    def test_scopes_to_tmux_pane_when_set(self, mock_out):
        mock_out.return_value = list_panes_output(('%2', '0', 'nvim', 'Editor'),)
        peek.Peek().find_editor_pane()
        cmd = mock_out.call_args[0][0]
        self.assertIn('-t', cmd)
        self.assertIn('%17', cmd)

    @patch.dict(os.environ, {}, clear=True)
    @patch('subprocess.check_output')
    def test_no_scope_without_tmux_pane(self, mock_out):
        mock_out.return_value = list_panes_output(('%2', '0', 'nvim', 'Editor'),)
        peek.Peek().find_editor_pane()
        self.assertNotIn('-t', mock_out.call_args[0][0])


class TestSocketPath(unittest.TestCase):

    @patch.dict(os.environ, {'USER': 'ben'})
    def test_derived_from_user_and_pane_id(self):
        self.assertEqual('/tmp/nvim-ben-%5.sock', peek.Peek.socket_path('%5'))


class TestExprs(unittest.TestCase):

    def test_bare_refresh_is_checktime_and_redraw(self):
        self.assertEqual(
            ["execute('checktime')", "execute('redraw!')"],
            peek.Peek()._exprs())

    @patch('os.path.abspath', side_effect=lambda p: '/abs/' + p)
    def test_open_file_uses_drop_with_fnameescape(self, _):
        exprs = peek.Peek('file.txt')._exprs()
        self.assertIn("execute('drop ' . fnameescape('/abs/file.txt'))", exprs)

    @patch('os.path.abspath', side_effect=lambda p: '/abs/' + p)
    def test_path_with_quote_is_doubled(self, _):
        exprs = peek.Peek("it's a file.txt")._exprs()
        self.assertIn("execute('drop ' . fnameescape('/abs/it''s a file.txt'))", exprs)

    @patch('os.path.abspath', side_effect=lambda p: '/abs/' + p)
    def test_line_and_column(self, _):
        exprs = peek.Peek('f', '10', '5')._exprs()
        self.assertIn('cursor(10, 5)', exprs)

    @patch('os.path.abspath', side_effect=lambda p: '/abs/' + p)
    def test_line_only(self, _):
        exprs = peek.Peek('f', '10')._exprs()
        self.assertIn("execute(':10')", exprs)

    @patch('os.path.abspath', side_effect=lambda p: '/abs/' + p)
    def test_pattern_uses_search_with_escaping(self, _):
        exprs = peek.Peek('f', pattern="it's")._exprs()
        self.assertIn("search('it''s')", exprs)
        self.assertNotIn('cursor', ' '.join(exprs))


class TestRpc(unittest.TestCase):

    @patch('subprocess.run')
    def test_invokes_nvim_server_without_shell(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout='n\n')
        p = peek.Peek()
        p.sock = '/tmp/sock'
        self.assertEqual('n', p.rpc('mode()'))
        args, kwargs = mock_run.call_args
        self.assertEqual(['nvim', '--server', '/tmp/sock', '--remote-expr', 'mode()'],
                         args[0])
        self.assertEqual(peek.RPC_TIMEOUT, kwargs['timeout'])

    @patch('subprocess.run')
    def test_nonzero_exit_raises(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout='')
        p = peek.Peek()
        p.sock = '/tmp/sock'
        with self.assertRaises(peek.PeekError):
            p.rpc('mode()')

    @patch('subprocess.run')
    def test_timeout_raises_dialog_error(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired('nvim', 3)
        p = peek.Peek()
        p.sock = '/tmp/sock'
        with self.assertRaises(peek.PeekError) as ctx:
            p.rpc('mode()')
        self.assertIn('dialog', str(ctx.exception))


class TestRun(unittest.TestCase):
    """End-to-end run() flows with tmux/nvim subprocesses mocked."""

    def _patch_discovery(self, mock_out, panes):
        mock_out.return_value = list_panes_output(*panes)

    def _rpc_responder(self, modes):
        """subprocess.run side_effect: mode() returns given mode, exprs succeed."""
        def run(cmd, **kwargs):
            expr = cmd[-1]
            return MagicMock(returncode=0, stdout=modes.get(expr, '') + '\n')
        return run

    @patch.dict(os.environ, {'USER': 'ben', 'TMUX_PANE': '%1'}, clear=True)
    @patch('subprocess.check_output')
    @patch('subprocess.run')
    @patch('os.path.exists', return_value=True)
    def test_happy_path_sends_exprs(self, _exists, mock_run, mock_out):
        self._patch_discovery(mock_out, [('%1', '1', 'zsh', 'Agent'),
                                         ('%2', '0', 'nvim', 'Editor')])
        mock_run.side_effect = self._rpc_responder({'mode()': 'n'})
        with patch('os.path.abspath', side_effect=lambda p: '/abs/' + p):
            self.assertTrue(peek.Peek('file.txt', '10').run())
        exprs = [c[0][0][-1] for c in mock_run.call_args_list]
        self.assertEqual(['mode()', "execute('checktime')",
                          "execute('drop ' . fnameescape('/abs/file.txt'))",
                          "execute(':10')", "execute('redraw!')"], exprs)

    @patch.dict(os.environ, {'USER': 'ben', 'TMUX_PANE': '%1'}, clear=True)
    @patch('subprocess.check_output')
    def test_no_editor_pane_fails(self, mock_out):
        self._patch_discovery(mock_out, [('%1', '1', 'zsh', 'Agent')])
        stderr = io.StringIO()
        with patch('sys.stderr', stderr):
            self.assertFalse(peek.Peek('file.txt').run())
        self.assertIn('Editor', stderr.getvalue())

    @patch.dict(os.environ, {'USER': 'ben', 'TMUX_PANE': '%1'}, clear=True)
    @patch('subprocess.check_output')
    @patch('subprocess.run')
    @patch('os.path.exists', return_value=False)
    def test_dead_socket_with_nvim_foreground_never_sends_keys(self, _exists, mock_run, mock_out):
        self._patch_discovery(mock_out, [('%1', '1', 'zsh', 'Agent'),
                                         ('%2', '0', 'nvim', 'Editor')])
        stderr = io.StringIO()
        with patch('sys.stderr', stderr):
            self.assertFalse(peek.Peek('file.txt').run())
        self.assertIn('socket', stderr.getvalue())
        for c in mock_run.call_args_list:
            self.assertNotEqual('tmux', c[0][0][0])

    @patch.dict(os.environ, {'USER': 'ben', 'TMUX_PANE': '%1'}, clear=True)
    @patch('subprocess.check_output')
    @patch('subprocess.run')
    @patch('os.path.exists')
    def test_dead_socket_at_shell_starts_nvim(self, mock_exists, mock_run, mock_out):
        self._patch_discovery(mock_out, [('%1', '1', 'zsh', 'Agent'),
                                         ('%2', '0', 'zsh', 'Editor')])
        # Socket absent at first check, present once nvim has been started.
        mock_exists.side_effect = [False, True]
        mock_run.side_effect = self._rpc_responder({'mode()': 'n'})
        with patch('os.path.abspath', side_effect=lambda p: '/abs/' + p):
            self.assertTrue(peek.Peek('file.txt').run())
        send_keys = [c[0][0] for c in mock_run.call_args_list
                     if c[0][0][0] == 'tmux']
        self.assertEqual(1, len(send_keys))
        self.assertEqual(['tmux', 'send-keys', '-t', '%2', 'nvim /abs/file.txt', 'Enter'],
                         send_keys[0])

    @patch.dict(os.environ, {'USER': 'ben', 'TMUX_PANE': '%1'}, clear=True)
    @patch('subprocess.check_output')
    @patch('subprocess.run')
    @patch('os.path.exists', return_value=False)
    def test_bare_peek_never_starts_nvim(self, _exists, mock_run, mock_out):
        self._patch_discovery(mock_out, [('%1', '1', 'zsh', 'Agent'),
                                         ('%2', '0', 'zsh', 'Editor')])
        stderr = io.StringIO()
        with patch('sys.stderr', stderr):
            self.assertFalse(peek.Peek().run())
        for c in mock_run.call_args_list:
            self.assertNotEqual('tmux', c[0][0][0])

    @patch.dict(os.environ, {'USER': 'ben', 'TMUX_PANE': '%1'}, clear=True)
    @patch('subprocess.check_output')
    @patch('subprocess.run')
    @patch('os.path.exists', return_value=True)
    def test_blocking_mode_bails_without_exprs(self, _exists, mock_run, mock_out):
        self._patch_discovery(mock_out, [('%1', '1', 'zsh', 'Agent'),
                                         ('%2', '0', 'nvim', 'Editor')])
        mock_run.side_effect = self._rpc_responder({'mode()': 'r'})
        stderr = io.StringIO()
        with patch('sys.stderr', stderr):
            self.assertFalse(peek.Peek('file.txt').run())
        self.assertIn('prompt', stderr.getvalue())
        exprs = [c[0][0][-1] for c in mock_run.call_args_list]
        self.assertEqual(['mode()'], exprs)

    @patch.dict(os.environ, {'USER': 'ben', 'TMUX_PANE': '%1'}, clear=True)
    @patch('subprocess.check_output')
    @patch('subprocess.run')
    @patch('os.path.exists', return_value=True)
    def test_stale_socket_at_shell_recovers(self, _exists, mock_run, mock_out):
        """Socket file exists but the first mode() RPC fails (stale): with a
        shell foreground and a filename, peek starts a fresh nvim."""
        self._patch_discovery(mock_out, [('%1', '1', 'zsh', 'Agent'),
                                         ('%2', '0', 'zsh', 'Editor')])
        responder = self._rpc_responder({'mode()': 'n'})
        calls = {'n': 0}

        def run(cmd, **kwargs):
            calls['n'] += 1
            if calls['n'] == 1:
                return MagicMock(returncode=1, stdout='')  # stale socket
            return responder(cmd, **kwargs)

        mock_run.side_effect = run
        with patch('os.path.abspath', side_effect=lambda p: '/abs/' + p):
            self.assertTrue(peek.Peek('file.txt').run())
        send_keys = [c[0][0] for c in mock_run.call_args_list
                     if c[0][0][0] == 'tmux']
        self.assertEqual(1, len(send_keys))


class TestArgParsing(unittest.TestCase):

    def _parse(self, argv):
        with patch('sys.argv', ['peek'] + argv):
            with patch('peek.Peek.run', return_value=True) as mock_run:
                with patch('peek.Peek.__init__', return_value=None) as mock_init:
                    peek.main()
        return mock_init

    def test_file_line_col_split(self):
        init = self._parse(['file.py:10:5'])
        init.assert_called_once_with('file.py', '10', '5', None)

    def test_file_line_split(self):
        init = self._parse(['file.py:10'])
        init.assert_called_once_with('file.py', '10', None, None)

    def test_separate_line_arg(self):
        init = self._parse(['file.py', '10'])
        init.assert_called_once_with('file.py', '10', None, None)

    def test_pattern(self):
        init = self._parse(['-p', 'def main', 'file.py'])
        init.assert_called_once_with('file.py', None, None, 'def main')

    def test_bare(self):
        init = self._parse([])
        init.assert_called_once_with(None, None, None, None)

    def test_failure_exits_nonzero(self):
        with patch('sys.argv', ['peek']):
            with patch('peek.Peek.run', return_value=False):
                with self.assertRaises(SystemExit) as ctx:
                    peek.main()
        self.assertEqual(1, ctx.exception.code)


if __name__ == '__main__':
    unittest.main()

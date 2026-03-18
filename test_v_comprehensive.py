import unittest
from unittest.mock import patch, MagicMock, call
import sys
import os
import subprocess
import io

# Add the lib directory to sys.path so we can import v
sys.path.append(os.path.join(os.path.dirname(__file__), 'lib'))
import v

class TestVComprehensive(unittest.TestCase):

    @patch('subprocess.check_output')
    def test_get_other_pane_info_no_other_panes(self, mock_check_output):
        # Only active pane
        mock_check_output.return_value = "%0:1:/dev/pts/1:zsh:DefaultTitle"
        p_id, cmd, editor = v.get_other_pane_info()
        self.assertIsNone(p_id)
        self.assertIsNone(cmd)
        self.assertIsNone(editor)

    @patch('subprocess.check_output')
    def test_get_other_pane_info_tmux_failure(self, mock_check_output):
        mock_check_output.side_effect = subprocess.CalledProcessError(1, 'tmux')
        p_id, cmd, editor = v.get_other_pane_info()
        self.assertIsNone(p_id)

    @patch('subprocess.check_output')
    def test_get_other_pane_info_single_priority_editor_title(self, mock_check_output):
        # Scenario: Multiple panes, only one has title 'Editor'
        # %0: active
        # %1: nvim but title is 'Other'
        # %2: zsh but title is 'Editor'
        mock_check_output.side_effect = [
            "%0:1:/dev/pts/0:zsh:Shell\n%1:0:/dev/pts/1:nvim:Other\n%2:0:/dev/pts/2:zsh:Editor", # list-panes
            "S+  nvim", # ps for pts/1
            "Ss  -zsh", # ps for pts/2
        ]
        p_id, cmd, editor = v.get_other_pane_info()
        self.assertEqual(p_id, "%2")
        # editor should be None if not found on tty and cmd is zsh
        self.assertIsNone(editor)

    @patch('subprocess.check_output')
    def test_get_other_pane_info_no_editor_title_fails(self, mock_check_output):
        # %0 active
        # %1 nvim (Title: Other)
        mock_check_output.return_value = "%0:1:/dev/pts/0:zsh:Shell\n%1:0:/dev/pts/1:nvim:Other"
        p_id, cmd, editor = v.get_other_pane_info()
        self.assertIsNone(p_id)

    @patch('v.VRefresher._discover_panes')
    @patch('v.VRefresher._get_pane_content')
    @patch('subprocess.run')
    @patch('os.path.abspath')
    def test_refresh_editor_combinations(self, mock_abspath, mock_run, mock_get_content, mock_discover):
        mock_abspath.side_effect = lambda x: f"/abs/{x}"
        mock_get_content.return_value = "some content"
        
        # Test 1: Filename, line, column - Foreground Editor
        mock_discover.return_value = [
            {'id': '%1', 'cmd': 'nvim', 'title': 'Editor', 'editor_on_tty': 'nvim', 'is_foreground_ps': True}
        ]
        v.refresh_editor("file.txt", line="10", column="5")
        
        # Check that it sends escape, checktime, :e!, and cursor call
        calls = [
            call(['tmux', 'send-keys', '-t', '%1', 'C-[', 'C-[', 'Escape', 'Escape'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL),
            call(['tmux', 'send-keys', '-t', '%1', ':checktime', 'Enter'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL),
            call(['tmux', 'send-keys', '-t', '%1', ':e! /abs/file.txt', 'Enter'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL),
            call(['tmux', 'send-keys', '-t', '%1', ':call cursor(10, 5)', 'Enter'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL),
            call(['tmux', 'send-keys', '-t', '%1', ':redraw!', 'Enter'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL),
        ]
        mock_run.assert_has_calls(calls)

        # Test 2: Filename and Pattern - Foreground Editor
        mock_run.reset_mock()
        v.refresh_editor("file.txt", pattern="search_me")
        mock_run.assert_any_call(['tmux', 'send-keys', '-t', '%1', '/search_me', 'Enter'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Test 3: No filename - just refresh
        mock_run.reset_mock()
        v.refresh_editor()
        # Should not have :e! or cursor
        for c in mock_run.call_args_list:
            if len(c[0][0]) > 4:
                self.assertNotIn(':e!', c[0][0][4])

    @patch('v.VRefresher._discover_panes')
    @patch('v.VRefresher._get_pane_content')
    @patch('subprocess.run')
    @patch('os.path.abspath')
    def test_refresh_editor_fallback_start_editor(self, mock_abspath, mock_run, mock_get_content, mock_discover):
        mock_abspath.side_effect = lambda x: f"/abs/{x}"
        mock_get_content.return_value = "user@host:~$ "
        
        # Case: Shell in foreground, no editor on TTY
        mock_discover.return_value = [
            {'id': '%1', 'cmd': 'zsh', 'title': 'Editor', 'editor_on_tty': None, 'is_foreground_ps': False}
        ]
        v.refresh_editor("file.txt", line="10")
        
        # Should send 'nvim +10 /abs/file.txt'
        mock_run.assert_any_call(['tmux', 'send-keys', '-t', '%1', 'nvim +10 /abs/file.txt', 'Enter'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Case: Shell in foreground, vim on TTY (detected by ps but not fg)
        mock_run.reset_mock()
        mock_get_content.return_value = "job not found" # Prevent 'fg'
        mock_discover.return_value = [
            {'id': '%1', 'cmd': 'zsh', 'title': 'Editor', 'editor_on_tty': 'vim', 'is_foreground_ps': False}
        ]
        v.refresh_editor("file.txt", pattern="findme")
        mock_run.assert_any_call(['tmux', 'send-keys', '-t', '%1', 'vim -c /findme /abs/file.txt', 'Enter'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    @patch('v.VRefresher._discover_panes')
    @patch('v.VRefresher._get_pane_content')
    @patch('subprocess.run')
    def test_refresh_editor_safety_and_fg(self, mock_run, mock_get_content, mock_discover):
        # Case: Editor backgrounded, currently in shell. Should 'fg'.
        mock_discover.return_value = [
            {'id': '%1', 'cmd': 'zsh', 'title': 'Editor', 'editor_on_tty': 'vim', 'is_foreground_ps': False}
        ]
        mock_get_content.return_value = "user@host:~$ "
        v.refresh_editor("file.txt")
        mock_run.assert_any_call(['tmux', 'send-keys', '-t', '%1', 'fg %vim', 'Enter'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Case: 'fg' likely to fail (job not found in content)
        mock_run.reset_mock()
        mock_get_content.return_value = "zsh: job not found: fg"
        v.refresh_editor("file.txt")
        # Should NOT send 'fg'
        for c in mock_run.call_args_list:
            if len(c[0][0]) > 4:
                self.assertNotIn('fg %', c[0][0][4])

        # Case: Non-shell, non-editor foreground. Should abort if filename given.
        mock_run.reset_mock()
        mock_discover.return_value = [
            {'id': '%1', 'cmd': 'top', 'title': 'Editor', 'editor_on_tty': None, 'is_foreground_ps': False}
        ]
        mock_get_content.return_value = "top output..."
        result = v.refresh_editor("file.txt")
        self.assertFalse(result)
        mock_run.assert_not_called()

    @patch('v.VRefresher._discover_panes')
    @patch('v.VRefresher._get_pane_content')
    @patch('os.path.abspath')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_refresh_editor_dry_run(self, mock_stdout, mock_abspath, mock_get_content, mock_discover):
        mock_abspath.side_effect = lambda x: f"/abs/{x}"
        mock_discover.return_value = [
            {'id': '%1', 'cmd': 'nvim', 'title': 'Editor', 'editor_on_tty': 'nvim', 'is_foreground_ps': True}
        ]
        mock_get_content.return_value = ""
        v.refresh_editor("file.txt", dry_run=True)
        output = mock_stdout.getvalue()
        self.assertIn("Would execute:", output)
        self.assertIn("tmux send-keys -t %1 :e! /abs/file.txt", output)

    @patch('v.VRefresher._discover_panes')
    @patch('subprocess.run')
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_refresh_editor_execution_error(self, mock_stderr, mock_run, mock_discover):
        mock_discover.return_value = [
            {'id': '%1', 'cmd': 'nvim', 'title': 'Editor', 'editor_on_tty': 'nvim', 'is_foreground_ps': True}
        ]
        mock_run.side_effect = subprocess.CalledProcessError(1, 'tmux')
        result = v.refresh_editor("file.txt")
        self.assertFalse(result)
        self.assertIn("Error executing tmux command", mock_stderr.getvalue())

    @patch('subprocess.check_output')
    @patch('v.VRefresher._get_pane_content')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_inspect_panes(self, mock_stdout, mock_get_content, mock_check_output):
        mock_check_output.return_value = "%0:1:/dev/pts/0:zsh:Shell\n%1:0:/dev/pts/1:nvim:Editor"
        mock_get_content.return_value = "last line of content"
        v.inspect_panes()
        output = mock_stdout.getvalue()
        self.assertIn("ID", output)
        self.assertIn("Title", output)
        self.assertIn("%0", output)
        self.assertIn("%1", output)
        self.assertIn("Shell", output)
        self.assertIn("Editor", output)
        self.assertIn("last line of content", output)

    @patch('v.refresh_editor')
    @patch('sys.argv')
    def test_main_parsing(self, mock_argv, mock_refresh):
        # Test filename:line:col
        mock_argv.__getitem__.side_effect = lambda x: ["v", "file.py:10:5"][x]
        with patch('argparse._sys.argv', ["v", "file.py:10:5"]):
            v.main()
            mock_refresh.assert_called_with("file.py", "10", "5", None, dry_run=False)

        # Test filename:line
        mock_refresh.reset_mock()
        with patch('argparse._sys.argv', ["v", "file.py:10"]):
            v.main()
            mock_refresh.assert_called_with("file.py", "10", None, None, dry_run=False)

        # Test flags
        mock_refresh.reset_mock()
        with patch('argparse._sys.argv', ["v", "file.py", "-p", "pattern", "--dry-run"]):
            v.main()
            mock_refresh.assert_called_with("file.py", None, None, "pattern", dry_run=True)

    @patch('v.inspect_panes')
    def test_main_inspect(self, mock_inspect):
        with patch('argparse._sys.argv', ["v", "--inspect"]):
            v.main()
            mock_inspect.assert_called_once()

if __name__ == '__main__':
    unittest.main()

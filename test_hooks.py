import unittest
from unittest.mock import patch
import os
import sys
import json
import io

# Add the root directory to sys.path so we can import from lib/
sys.path.insert(0, os.path.dirname(__file__))

from lib.notifications import send_notification
from lib.hooks import handle_claude_edit, handle_claude_stop, handle_claude_notification

class TestNotifications(unittest.TestCase):
    @patch('platform.system', return_value='Darwin')
    @patch('subprocess.run')
    def test_send_notification_macos(self, mock_run, mock_system):
        send_notification("Hello", "Title")
        mock_run.assert_called_once()
        args, _ = mock_run.call_args
        self.assertIn('osascript', args[0])
        self.assertIn('Hello', args[0][2])

    @patch('platform.system', return_value='Linux')
    def test_send_notification_linux(self, mock_system):
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            send_notification("Hello", "Title")
            output = fake_out.getvalue()
            self.assertIn('Notification: Title - Hello', output)

class TestHooks(unittest.TestCase):
    @patch('lib.hooks.run_local_script')
    def test_claude_hook_stop_event(self, mock_run_script):
        handle_claude_stop("{}")
        mock_run_script.assert_called_with('peek')

    @patch('lib.hooks.run_local_script')
    @patch('lib.hooks.send_notification')
    def test_claude_hook_notification_event(self, mock_notify, mock_run_script):
        payload = {"cwd": "/path/to/claude-project", "notification_type": "permission_prompt"}
        handle_claude_notification(json.dumps(payload))
        mock_run_script.assert_called_with('peek')
        mock_notify.assert_called_with("Input Required", "Claude (claude-project)")

    @patch('lib.hooks.run_local_script')
    @patch('lib.hooks.send_notification')
    def test_claude_hook_notification_event_elicitation(self, mock_notify, mock_run_script):
        payload = {"cwd": "/path/to/claude-project", "notification_type": "elicitation_dialog"}
        handle_claude_notification(json.dumps(payload))
        mock_notify.assert_called_with("Input Required", "Claude (claude-project)")

    @patch('lib.hooks.run_local_script')
    @patch('lib.hooks.send_notification')
    def test_claude_hook_notification_event_ignores_other_types(self, mock_notify, mock_run_script):
        payload = {"cwd": "/path/to/claude-project", "notification_type": "idle_prompt"}
        handle_claude_notification(json.dumps(payload))
        mock_run_script.assert_not_called()
        mock_notify.assert_not_called()

    @patch('lib.hooks.run_local_script')
    def test_claude_hook_write_tool(self, mock_run_script):
        payload = {
            "tool_name": "Write",
            "tool_input": {"file_path": "/path/to/newfile.py", "content": "print('hello')"},
        }
        handle_claude_edit(json.dumps(payload))
        mock_run_script.assert_called_with('peek', '/path/to/newfile.py', '1')

    @patch('builtins.open', create=True)
    @patch('lib.hooks.run_local_script')
    def test_claude_hook_edit_tool_with_line(self, mock_run_script, mock_open):
        mock_open.return_value.__enter__.return_value = iter([
            "line 1\n",
            "line 2\n",
            "line 3\n",
            "line 4\n",
            "def hello():\n",  # Line 5 - matches first line of new_string
            "    pass\n",
        ])
        payload = {
            "tool_name": "Edit",
            "tool_input": {
                "file_path": "/path/to/file.py",
                "old_string": "def hello():\n    pass",
                "new_string": "def hello():\n    print('hello')"
            },
        }
        handle_claude_edit(json.dumps(payload))
        mock_run_script.assert_called_with('peek', '/path/to/file.py', '5')

    @patch('lib.hooks.run_local_script')
    def test_claude_hook_edit_tool_fallback(self, mock_run_script):
        payload = {
            "tool_name": "Edit",
            "tool_input": {
                "file_path": "/nonexistent/file.py",
                "old_string": "old",
                "new_string": "new"
            },
        }
        handle_claude_edit(json.dumps(payload))
        mock_run_script.assert_called_with('peek', '/nonexistent/file.py')

if __name__ == '__main__':
    unittest.main()

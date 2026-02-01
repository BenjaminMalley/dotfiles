import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import json
import io

# Add the root directory to sys.path so we can import from lib/
sys.path.insert(0, os.path.dirname(__file__))

from lib.notifications import send_notification
from lib.hooks import handle_gemini_payload, handle_claude_payload

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
    @patch('lib.hooks.send_notification')
    def test_gemini_hook_refresh(self, mock_notify, mock_run_script):
        payload = {
            "hook_event_name": "AfterTool",
            "tool_name": "write_file",
            "tool_input": {"file_path": "test.txt"},
            "tool_response": {"returnDisplay": {"fileDiff": "@@ -1,1 +1,4 @@\n+line1\n+line2\n+line3"}}
        }
        handle_gemini_payload(json.dumps(payload))
        # Line number should be calculated as 4
        mock_run_script.assert_any_call('v', 'test.txt', '4')

    @patch('lib.hooks.send_notification')
    def test_gemini_hook_notify(self, mock_notify):
        payload = {
            "hook_event_name": "Notification",
            "notification_type": "InputRequired",
            "cwd": "/path/to/project"
        }
        handle_gemini_payload(json.dumps(payload))
        mock_notify.assert_called_with('InputRequired', 'Gemini (project)')

    @patch('lib.hooks.run_local_script')
    @patch('lib.hooks.send_notification')
    def test_claude_hook(self, mock_notify, mock_run_script):
        payload = {"cwd": "/path/to/claude-project"}
        handle_claude_payload(json.dumps(payload))
        mock_run_script.assert_called_with('v')
        mock_notify.assert_called_with("Input Required", "Claude (claude-project)")

if __name__ == '__main__':
    unittest.main()

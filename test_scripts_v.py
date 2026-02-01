import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Add root to sys.path
sys.path.insert(0, os.path.dirname(__file__))

from lib.v import refresh_editor

class TestVLogic(unittest.TestCase):

    @patch('subprocess.check_output')
    @patch('subprocess.run')
    def test_v_refresh_current_vim(self, mock_run, mock_check_output):
        """Test with no args when target pane is running vim."""
        mock_check_output.return_value = "%1:1:zsh\n%2:0:vim"
        
        refresh_editor()
        
        calls = [c.args[0] for c in mock_run.call_args_list]
        self.assertIn(['tmux', 'send-keys', '-t', '%2', 'Escape', 'Escape'], calls)
        self.assertIn(['tmux', 'send-keys', '-t', '%2', ':checktime', 'Enter', ':redraw!', 'Enter'], calls)

    @patch('subprocess.check_output')
    @patch('subprocess.run')
    def test_v_open_file_vim(self, mock_run, mock_check_output):
        """Test 'test.py' when target pane is running vim."""
        mock_check_output.return_value = "%1:1:zsh\n%2:0:vim"
        
        refresh_editor('test.py')
        
        calls = [c.args[0] for c in mock_run.call_args_list]
        abs_path = os.path.abspath('test.py')
        self.assertIn(['tmux', 'send-keys', '-t', '%2', f':e! {abs_path}', 'Enter', ':redraw!', 'Enter'], calls)

    @patch('subprocess.check_output')
    @patch('subprocess.run')
    def test_v_open_file_line_vim(self, mock_run, mock_check_output):
        """Test 'test.py 42' when target pane is running vim."""
        mock_check_output.return_value = "%1:1:zsh\n%2:0:vim"
        
        refresh_editor('test.py', '42')
        
        calls = [c.args[0] for c in mock_run.call_args_list]
        self.assertIn(['tmux', 'send-keys', '-t', '%2', ':42', 'Enter'], calls)

    @patch('subprocess.check_output')
    @patch('subprocess.run')
    def test_v_start_nvim_new(self, mock_run, mock_check_output):
        """Test 'test.py' when target pane is NOT running nvim (starts it)."""
        mock_check_output.return_value = "%1:1:zsh\n%2:0:zsh"
        
        refresh_editor('test.py')
        
        calls = [c.args[0] for c in mock_run.call_args_list]
        abs_path = os.path.abspath('test.py')
        self.assertIn(['tmux', 'send-keys', '-t', '%2', f'nvim {abs_path}', 'Enter'], calls)

    @patch('subprocess.check_output')
    def test_v_no_other_pane(self, mock_check_output):
        """Test fails when no other pane is found."""
        mock_check_output.return_value = "%1:1:zsh"
        
        result = refresh_editor()
        self.assertFalse(result)

if __name__ == '__main__':
    unittest.main()
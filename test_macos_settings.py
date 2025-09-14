
import unittest
import platform
from unittest.mock import patch

# Import the module to be tested
import macos_settings

class TestMacOSSettingsScript(unittest.TestCase):

    @unittest.skipIf(platform.system() != 'Darwin', "macOS specific tests")
    @patch('macos_settings.run_command')
    def test_macos_settings(self, mock_run_command):
        """Test the macos_settings.py script."""
        # Act
        macos_settings.set_macos_preferences()

        # Assert
        mock_run_command.assert_any_call(['defaults', 'write', 'NSGlobalDomain', 'com.apple.swipescrolldirection', '-bool', 'false'])
        mock_run_command.assert_any_call(['defaults', 'write', 'com.apple.dock', 'autohide', '-bool', 'true'])
        mock_run_command.assert_any_call(['defaults', 'write', 'com.apple.finder', 'AppleShowAllFiles', '-bool', 'true'])
        mock_run_command.assert_any_call(['killall', 'Dock'])
        mock_run_command.assert_any_call(['killall', 'Finder'])
        mock_run_command.assert_any_call(['killall', 'WindowManager'])

if __name__ == '__main__':
    unittest.main()

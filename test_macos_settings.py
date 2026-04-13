import unittest
import platform
import subprocess
from unittest.mock import patch, MagicMock

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
        mock_run_command.assert_any_call(['defaults', 'write', 'NSGlobalDomain', 'AppleInterfaceStyle', '-string', 'Dark'])
        mock_run_command.assert_any_call(['defaults', 'write', 'NSGlobalDomain', 'AppleICUForce24HourTime', '-bool', 'true'])
        mock_run_command.assert_any_call(['defaults', 'write', 'com.apple.menuextra.clock', 'DateFormat', '-string', 'EEE d MMM HH:mm:ss'])

        # Check sound settings
        mock_run_command.assert_any_call(['defaults', 'write', 'NSGlobalDomain', 'com.apple.sound.beep.feedback', '-int', '0'])
        mock_run_command.assert_any_call(['defaults', 'write', 'NSGlobalDomain', 'com.apple.sound.beep.volume', '-float', '0'])
        mock_run_command.assert_any_call(['osascript', '-e', 'set volume alert volume 0'])

        mock_run_command.assert_any_call(['gh', 'config', 'set', 'prompt', 'disabled'], check=False)

        # Terminal profile settings (checking a few)
        # Note: In the refactored code, set_terminal_profile_setting calls run_command twice if Set fails.
        # Here we just verify that it was called at least once with the expected arguments and proper quoting.
        mock_run_command.assert_any_call(['/usr/libexec/PlistBuddy', '-c', 'Set :"Window Settings":"Basic":shellExitAction 1', unittest.mock.ANY], check=True)
        mock_run_command.assert_any_call(['/usr/libexec/PlistBuddy', '-c', 'Set :"Window Settings":"Clear Dark":shellExitAction 1', unittest.mock.ANY], check=True)

        mock_run_command.assert_any_call(['killall', 'Dock'], check=False)
        mock_run_command.assert_any_call(['killall', 'Finder'], check=False)
        mock_run_command.assert_any_call(['killall', 'WindowManager'], check=False)

if __name__ == '__main__':
    unittest.main()
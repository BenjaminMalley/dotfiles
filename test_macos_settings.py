
import unittest
import platform
import subprocess
from unittest.mock import patch

# Import the module to be tested
import macos_settings

class TestMacOSSettingsScript(unittest.TestCase):

    @unittest.skipIf(platform.system() != 'Darwin', "macOS specific tests")
    @patch('macos_settings.subprocess.run')
    @patch('macos_settings.run_command')
    def test_macos_settings(self, mock_run_command, mock_subprocess_run):
        """Test the macos_settings.py script."""
        # Setup mock for subprocess.run to simulate 'Set' failing so 'Add' is called via run_command
        mock_subprocess_run.side_effect = subprocess.CalledProcessError(1, 'cmd')

        # Act
        macos_settings.set_macos_preferences()

        # Assert
        mock_run_command.assert_any_call(['defaults', 'write', 'NSGlobalDomain', 'com.apple.swipescrolldirection', '-bool', 'false'])
        mock_run_command.assert_any_call(['defaults', 'write', 'com.apple.dock', 'autohide', '-bool', 'true'])
        mock_run_command.assert_any_call(['defaults', 'write', 'com.apple.finder', 'AppleShowAllFiles', '-bool', 'true'])

        # Check sound settings
        mock_run_command.assert_any_call(['defaults', 'write', 'NSGlobalDomain', 'com.apple.sound.beep.feedback', '-int', '0'])
        mock_run_command.assert_any_call(['defaults', 'write', 'NSGlobalDomain', 'com.apple.sound.beep.volume', '-float', '0'])
        mock_run_command.assert_any_call(['osascript', '-e', 'set volume alert volume 0'])

        mock_run_command.assert_any_call(['gh', 'config', 'set', 'prompt', 'disabled'])

        # Terminal profile settings (checking a few)
        mock_run_command.assert_any_call(['/usr/libexec/PlistBuddy', '-c', "Add :'Window Settings':Basic:shellExitAction integer 1", unittest.mock.ANY])
        mock_run_command.assert_any_call(['/usr/libexec/PlistBuddy', '-c', "Add :'Window Settings':Pro:BackgroundAlphaInactive real 0.5", unittest.mock.ANY])
        mock_run_command.assert_any_call(['/usr/libexec/PlistBuddy', '-c', "Add :'Window Settings':Basic:BackgroundSettingsForInactiveWindows bool true", unittest.mock.ANY])

        mock_run_command.assert_any_call(['killall', 'Terminal'])
        mock_run_command.assert_any_call(['killall', 'Dock'])
        mock_run_command.assert_any_call(['killall', 'Finder'])
        mock_run_command.assert_any_call(['killall', 'WindowManager'])

if __name__ == '__main__':
    unittest.main()


import unittest
import os
import platform
from unittest.mock import patch, call

# Import the module to be tested
import install

class TestInstallScript(unittest.TestCase):

    def setUp(self):
        """Set up a temporary environment for testing."""
        self.temp_dir = os.path.join(os.path.dirname(__file__), 'temp_test')
        os.makedirs(self.temp_dir, exist_ok=True)
        self.old_home = os.environ.get('HOME')
        os.environ['HOME'] = self.temp_dir

    def tearDown(self):
        """Clean up the temporary environment."""
        if self.old_home:
            os.environ['HOME'] = self.old_home
        else:
            del os.environ['HOME']
        
        # Safely remove the temp directory and its contents
        if os.path.exists(self.temp_dir):
            for root, dirs, files in os.walk(self.temp_dir, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            if os.path.exists(self.temp_dir):
                os.rmdir(self.temp_dir)

    @patch('install.set_macos_preferences')
    @patch('install.run_command')
    @patch('builtins.input', return_value='y')
    @patch('platform.system', return_value='Darwin')
    @patch('shutil.which', return_value=True)
    def test_install_macos(self, mock_which, mock_system, mock_input, mock_run_command, mock_set_macos):
        """Test the install script on macOS."""
        # Arrange
        brewfile = os.path.join(os.path.dirname(__file__), 'Brewfile')
        brewfile_opt = os.path.join(os.path.dirname(__file__), 'Brewfile.opt')
        with open(brewfile, 'w') as f:
            f.write('brew "test-package"')
        with open(brewfile_opt, 'w') as f:
            f.write('brew "optional-package"')

        # Act
        install.install_dotfiles()

        # Assert
        mock_run_command.assert_any_call(['brew', 'update'])
        mock_run_command.assert_any_call(['brew', 'bundle', f'--file={brewfile}'])
        mock_run_command.assert_any_call(['brew', 'bundle', f'--file={brewfile_opt}'])
        mock_set_macos.assert_called_once()
        self.assertTrue(os.path.islink(os.path.join(self.temp_dir, '.gitconfig')))

        # Clean up dummy files
        os.remove(brewfile)
        os.remove(brewfile_opt)

    @patch('install.set_macos_preferences')
    @patch('platform.system', return_value='Linux')
    def test_install_linux(self, mock_system, mock_set_macos):
        """Test the install script on Linux."""
        # Act
        install.install_dotfiles()

        # Assert
        mock_set_macos.assert_not_called()
        self.assertTrue(os.path.islink(os.path.join(self.temp_dir, '.gitconfig')))

if __name__ == '__main__':
    unittest.main()

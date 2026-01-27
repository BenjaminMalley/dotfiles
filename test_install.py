import unittest
import os
import platform
import shutil
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
            shutil.rmtree(self.temp_dir)

    def test_symlink_gitconfig(self):
        """Test that .gitconfig is symlinked correctly."""
        install.symlink_file('gitconfig', '.gitconfig')
        destination_path = os.path.join(self.temp_dir, '.gitconfig')
        self.assertTrue(os.path.islink(destination_path))
        source_path = os.path.abspath(os.path.join(os.path.dirname(install.__file__), 'gitconfig'))
        self.assertEqual(os.path.realpath(destination_path), source_path)

    def test_symlink_tmux_conf(self):
        """Test that .tmux.conf is symlinked correctly."""
        install.symlink_file('.tmux.conf', '.tmux.conf')
        destination_path = os.path.join(self.temp_dir, '.tmux.conf')
        self.assertTrue(os.path.islink(destination_path))
        source_path = os.path.abspath(os.path.join(os.path.dirname(install.__file__), '.tmux.conf'))
        self.assertEqual(os.path.realpath(destination_path), source_path)

    @patch('install.setup_newsyslog')
    @patch('install.set_macos_preferences')
    @patch('install.run_command')
    @patch('builtins.input', return_value='y')
    @patch('platform.system', return_value='Darwin')
    @patch('shutil.which', return_value=True)
    def test_install_macos(self, mock_which, mock_system, mock_input, mock_run_command, mock_set_macos, mock_setup_newsyslog):
        """Test the install script on macOS."""
        # Arrange
        brewfile = os.path.join(os.path.dirname(__file__), 'Brewfile')
        brewfile_opt = os.path.join(os.path.dirname(__file__), 'Brewfile.opt')
        agents_dir = os.path.join(os.path.dirname(__file__), 'agents')
        agent_files = os.listdir(agents_dir)

        # Expected calls for optional software
        expected_optional_calls = []
        with open(brewfile_opt, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split()
                command_type, package = parts[0], parts[1].strip('"')
                if command_type == 'cask':
                    expected_optional_calls.append(call(['brew', 'install', '--cask', package]))
                else:
                    expected_optional_calls.append(call(['brew', 'install', package]))

        # Act
        install.install_dotfiles()

        # Assert
        mock_run_command.assert_any_call(['brew', 'update'])
        mock_run_command.assert_any_call(['brew', 'bundle', f'--file={brewfile}'])
        
        # Add new assertions for individual optional software installs
        for expected_call in expected_optional_calls:
            mock_run_command.assert_any_call(*expected_call.args, **expected_call.kwargs)

        mock_run_command.assert_any_call(['/bin/bash', '-c', 'if tmux info &>/dev/null; then tmux source-file ~/.tmux.conf; echo "Tmux config reloaded."; else echo "Tmux not running, skipping reload."; fi'], check=False)
        mock_set_macos.assert_called_once()
        mock_setup_newsyslog.assert_called_once()
        self.assertTrue(os.path.islink(os.path.join(self.temp_dir, '.gitconfig')))
        self.assertTrue(os.path.islink(os.path.join(self.temp_dir, '.config', 'ghostty', 'config')))

        claude_agents_dir = os.path.join(self.temp_dir, '.claude', 'agents')
        self.assertTrue(os.path.isdir(claude_agents_dir))
        for agent_file in agent_files:
            self.assertTrue(os.path.islink(os.path.join(claude_agents_dir, agent_file)))

        self.assertTrue(os.path.islink(os.path.join(self.temp_dir, '.gemini', 'GEMINI.md')))
        self.assertTrue(os.path.islink(os.path.join(self.temp_dir, '.claude', 'CLAUDE.md')))
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, '.tmux.conf.local')))

    @patch('install.run_command')
    @patch('install.set_macos_preferences')
    @patch('platform.system', return_value='Linux')
    def test_install_linux(self, mock_system, mock_set_macos, mock_run_command):
        """Test the install script on Linux."""
        # Arrange
        agents_dir = os.path.join(os.path.dirname(__file__), 'agents')
        agent_files = os.listdir(agents_dir)

        # Act
        install.install_dotfiles()

        # Assert
        mock_run_command.assert_called_once_with(['/bin/bash', '-c', 'if tmux info &>/dev/null; then tmux source-file ~/.tmux.conf; echo "Tmux config reloaded."; else echo "Tmux not running, skipping reload."; fi'], check=False)
        mock_set_macos.assert_not_called()
        self.assertTrue(os.path.islink(os.path.join(self.temp_dir, '.gitconfig')))

        claude_agents_dir = os.path.join(self.temp_dir, '.claude', 'agents')
        self.assertTrue(os.path.isdir(claude_agents_dir))
        for agent_file in agent_files:
            self.assertTrue(os.path.islink(os.path.join(claude_agents_dir, agent_file)))

        self.assertTrue(os.path.islink(os.path.join(self.temp_dir, '.gemini', 'GEMINI.md')))
        self.assertTrue(os.path.islink(os.path.join(self.temp_dir, '.claude', 'CLAUDE.md')))
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, '.tmux.conf.local')))

    def test_symlink_gitconfig_with_existing_file(self):
        """Test symlinking with an existing file at the destination."""
        destination_path = os.path.join(self.temp_dir, '.gitconfig')
        with open(destination_path, 'w') as f:
            f.write('old config')

        # Act
        install.symlink_file('gitconfig', '.gitconfig')

        # Assert
        self.assertTrue(os.path.islink(destination_path))

        backup_path = f"{destination_path}.bak"
        self.assertTrue(os.path.exists(backup_path))
        with open(backup_path, 'r') as f:
            content = f.read()
        self.assertEqual(content, 'old config')

        source_path = os.path.abspath(os.path.join(os.path.dirname(install.__file__), 'gitconfig'))
        self.assertEqual(os.path.realpath(destination_path), source_path)

if __name__ == '__main__':
    unittest.main()

import unittest
import subprocess
import os
import sys

class TestDotfilesScript(unittest.TestCase):
    def test_dotfiles_script_help(self):
        """Test that the dotfiles script runs and displays help."""
        script_path = os.path.join(os.path.dirname(__file__), 'scripts', 'dotfiles')
        
        # Ensure the script is executable (it should be, but good to be safe in tests)
        os.chmod(script_path, 0o755)

        result = subprocess.run(
            [script_path, '--help'],
            capture_output=True,
            text=True
        )

        self.assertEqual(result.returncode, 0)
        # ansible-playbook help output
        self.assertIn("ansible-playbook", result.stdout)
        self.assertIn("--help", result.stdout)

if __name__ == '__main__':
    unittest.main()

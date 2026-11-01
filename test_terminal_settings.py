import os
import unittest

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))


class TestTerminalSettings(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(REPO_ROOT, "ansible", "group_vars", "all.yml")) as f:
            self.group_vars = f.read()

    def test_inactive_windows_are_opaque(self):
        self.assertIn('{ key: "BackgroundSettingsForInactiveWindows", type: "bool", value: "false" }', self.group_vars)
        self.assertNotIn("BackgroundAlphaInactive", self.group_vars)


if __name__ == "__main__":
    unittest.main()

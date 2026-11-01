import json
import os
import unittest

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))


class TestClaudeSettings(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(REPO_ROOT, "claude-settings.json")) as f:
            self.permissions = json.load(f)["permissions"]

    def test_default_mode_is_auto(self):
        self.assertEqual(self.permissions["defaultMode"], "auto")

    def test_only_commands_that_can_lose_work_ask(self):
        self.assertEqual(
            sorted(self.permissions["ask"]),
            sorted([
                "Bash(git reset --hard *)",
                "Bash(git clean *)",
                "Bash(git checkout -B *)",
                "Bash(git switch -C *)",
                "Bash(git branch -D *)",
                "Bash(git branch -f *)",
            ]),
        )

    def test_git_and_gh_are_allowed(self):
        self.assertIn("Bash(git *)", self.permissions["allow"])
        self.assertIn("Bash(gh *)", self.permissions["allow"])


if __name__ == "__main__":
    unittest.main()

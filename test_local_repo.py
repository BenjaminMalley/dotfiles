import json
import os
import shutil
import subprocess
import tempfile
import unittest

from test_ansible_ssh_origin import ANSIBLE_PLAYBOOK

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))


@unittest.skipUnless(ANSIBLE_PLAYBOOK, "ansible-playbook not found")
class TestLocalRepoSupplements(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp_dir, ignore_errors=True)
        self.local_dir = os.path.join(self.tmp_dir, "local")
        self.core_dir = os.path.join(self.local_dir, "dotfiles")
        self.home_dir = os.path.join(self.tmp_dir, "home")
        os.makedirs(self.home_dir)
        shutil.copytree(os.path.join(REPO_ROOT, "ansible"), os.path.join(self.core_dir, "ansible"))
        for name in ["AGENT.md", "claude-settings.json"]:
            shutil.copy(os.path.join(REPO_ROOT, name), self.core_dir)
        with open(os.path.join(self.core_dir, "ansible", "wrapper.yml"), "w") as f:
            f.write(
                "- hosts: localhost\n"
                "  connection: local\n"
                "  gather_facts: false\n"
                "  tasks:\n"
                "    - ansible.builtin.include_tasks: tasks/local.yml\n"
                "    - ansible.builtin.include_tasks: tasks/dotfiles.yml\n"
                "    - ansible.builtin.copy:\n"
                "        content: \"{{ {'formulae': brew_formulae, 'casks': brew_casks} | to_json }}\"\n"
                "        dest: \"{{ ansible_facts['user_dir'] }}/brew.json\"\n"
                "        mode: \"0644\"\n"
            )

    def _write_local(self, name, content):
        path = os.path.join(self.local_dir, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(content)

    def _run(self):
        return subprocess.run(
            [
                ANSIBLE_PLAYBOOK,
                os.path.join(self.core_dir, "ansible", "wrapper.yml"),
                "-e",
                json.dumps({"ansible_facts": {"user_dir": self.home_dir}}),
            ],
            cwd=self.core_dir,
            capture_output=True,
            text=True,
        )

    def _home(self, name):
        return os.path.join(self.home_dir, name)

    def test_requires_local_repo_with_submodule(self):
        result = self._run()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("has no .gitmodules", result.stdout)

    def test_core_only_when_local_repo_has_no_supplements(self):
        self._write_local(".gitmodules", "")
        result = self._run()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(os.readlink(self._home(".claude/rules/core.md")), os.path.join(os.path.realpath(self.core_dir), "AGENT.md"))
        self.assertFalse(os.path.lexists(self._home(".claude/CLAUDE.md")))
        with open(self._home("brew.json")) as f:
            self.assertIn("gh", json.load(f)["formulae"])

    def test_local_files_supplement_core(self):
        self._write_local(".gitmodules", "")
        self._write_local("AGENT.md", "local instructions\n")
        self._write_local("claude-settings.json", json.dumps({"permissions": {"allow": ["Bash(local)"]}}))
        self._write_local("config/tool", "local config\n")
        self._write_local(
            "local.yml",
            "homebrew_formulae: [local-formula]\n"
            "homebrew_casks: [local-cask]\n"
            "dotfiles:\n"
            "  - { source: config/tool, dest: .config/tool/config }\n",
        )
        result = self._run()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(os.readlink(self._home(".claude/CLAUDE.md")), os.path.join(os.path.realpath(self.local_dir), "AGENT.md"))
        with open(self._home(".config/tool/config")) as f:
            self.assertEqual(f.read(), "local config\n")
        with open(self._home(".claude/settings.json")) as f:
            allow = json.load(f)["permissions"]["allow"]
        self.assertIn("Bash(git *)", allow)
        self.assertEqual(allow[-1], "Bash(local)")
        with open(self._home("brew.json")) as f:
            brew = json.load(f)
        self.assertEqual(brew["formulae"][-1], "local-formula")
        self.assertIn("gh", brew["formulae"])
        self.assertEqual(brew["casks"][-1], "local-cask")
        self.assertIn("ghostty", brew["casks"])


@unittest.skipUnless(shutil.which("zsh"), "zsh not found")
class TestZshrcLocalRepo(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp_dir, ignore_errors=True)
        self.local_dir = os.path.join(self.tmp_dir, "local")
        self.core_dir = os.path.join(self.local_dir, "dotfiles")
        self.home_dir = os.path.join(self.tmp_dir, "home")
        for directory in [os.path.join(self.core_dir, "scripts"), os.path.join(self.local_dir, "scripts"), self.home_dir]:
            os.makedirs(directory)
        shutil.copy(os.path.join(REPO_ROOT, "zshrc"), self.core_dir)
        os.makedirs(os.path.join(self.core_dir, "ansible"))
        os.symlink(os.path.join(self.core_dir, "ansible", "..", "zshrc"), os.path.join(self.home_dir, ".zshrc"))

    def _source_zshrc(self):
        env = {"HOME": self.home_dir, "PATH": "/usr/bin:/bin", "TMUX": "1"}
        result = subprocess.run(
            ["zsh", "-f", "-c", 'source ~/.zshrc; print -r -- "$PATH"; print -r -- "$LOCAL_MARKER"'],
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.splitlines()

    def test_core_scripts_precede_local_scripts_on_path(self):
        path = self._source_zshrc()[0].split(":")
        core, local = os.path.join(os.path.realpath(self.core_dir), "scripts"), os.path.join(os.path.realpath(self.local_dir), "scripts")
        self.assertLess(path.index(core), path.index(local))

    def test_sources_local_zshrc(self):
        with open(os.path.join(self.local_dir, "zshrc"), "w") as f:
            f.write("export LOCAL_MARKER=loaded\n")
        self.assertEqual(self._source_zshrc()[1], "loaded")


if __name__ == "__main__":
    unittest.main()

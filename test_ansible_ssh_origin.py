import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(__file__)
SSH_TASKS = os.path.join(REPO_ROOT, "ansible", "tasks", "ssh.yml")


def _find_ansible_playbook():
    found = shutil.which("ansible-playbook")
    if found:
        return found
    venv_candidate = os.path.join(REPO_ROOT, ".venv", "bin", "ansible-playbook")
    if os.path.exists(venv_candidate):
        return venv_candidate
    return None


ANSIBLE_PLAYBOOK = _find_ansible_playbook()

# Real GitHub SSH responses, for realistic stubbing.
SSH_SUCCESS_MESSAGE = "Hi someone! You've successfully authenticated, but GitHub does not provide shell access."
SSH_FAILURE_MESSAGE = "someone@example.com: Permission denied (publickey)."


@unittest.skipUnless(ANSIBLE_PLAYBOOK, "ansible-playbook not found")
class TestSshOriginSwitch(unittest.TestCase):
    """Exercises the SSH-origin-switch tasks appended to ansible/tasks/ssh.yml.

    Runs the real task file (unmodified) inside a sandboxed fake "repo" via
    an include_tasks wrapper playbook, so playbook_dir resolves to the
    sandbox and never touches this actual checkout or the real ~/.ssh.
    """

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp_dir, ignore_errors=True)

        self.repo_dir = os.path.join(self.tmp_dir, "repo")
        self.home_dir = os.path.join(self.tmp_dir, "home")
        self.bin_dir = os.path.join(self.tmp_dir, "bin")
        os.makedirs(os.path.join(self.repo_dir, "ansible"))
        os.makedirs(self.home_dir)
        os.makedirs(self.bin_dir)

        with open(os.path.join(self.repo_dir, "ssh_config"), "w") as f:
            f.write("Host *\n")

        wrapper = os.path.join(self.repo_dir, "ansible", "wrapper.yml")
        with open(wrapper, "w") as f:
            f.write(
                "- hosts: localhost\n"
                "  connection: local\n"
                "  gather_facts: false\n"
                "  tasks:\n"
                "    - ansible.builtin.include_tasks: \"{{ ext_tasks }}\"\n"
            )
        self.wrapper_playbook = wrapper

        subprocess.run(["git", "init", "-q", self.repo_dir], check=True)

    def _set_origin(self, url):
        subprocess.run(
            ["git", "-C", self.repo_dir, "remote", "add", "origin", url], check=True
        )

    def _origin_url(self):
        return subprocess.run(
            ["git", "-C", self.repo_dir, "remote", "get-url", "origin"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def _stub_ssh(self, message, exit_code, call_log):
        ssh_stub = os.path.join(self.bin_dir, "ssh")
        with open(ssh_stub, "w") as f:
            f.write(
                "#!/bin/bash\n"
                'echo "$@" >> "{log}"\n'
                'echo "{message}" >&2\n'
                "exit {code}\n".format(log=call_log, message=message, code=exit_code)
            )
        os.chmod(ssh_stub, 0o755)

    def _run_ssh_yml(self):
        env = os.environ.copy()
        env["PATH"] = self.bin_dir + os.pathsep + env["PATH"]
        result = subprocess.run(
            [
                ANSIBLE_PLAYBOOK,
                self.wrapper_playbook,
                "-e",
                "ext_tasks=" + SSH_TASKS,
                "-e",
                '{"ansible_facts": {"user_dir": "%s"}}' % self.home_dir,
            ],
            cwd=self.repo_dir,
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode, 0, "ansible-playbook failed: " + result.stderr + result.stdout
        )
        return result

    def test_switches_origin_to_ssh_when_authenticated(self):
        self._set_origin("https://github.com/SomeOwner/somerepo.git")
        call_log = os.path.join(self.tmp_dir, "calls.log")
        self._stub_ssh(SSH_SUCCESS_MESSAGE, 1, call_log)

        self._run_ssh_yml()

        self.assertEqual(self._origin_url(), "git@github.com:SomeOwner/somerepo.git")
        self.assertTrue(os.path.exists(call_log), "expected the SSH auth check to run")

    def test_switches_origin_to_ssh_when_url_has_no_dot_git_suffix(self):
        self._set_origin("https://github.com/SomeOwner/somerepo")
        call_log = os.path.join(self.tmp_dir, "calls.log")
        self._stub_ssh(SSH_SUCCESS_MESSAGE, 1, call_log)

        self._run_ssh_yml()

        self.assertEqual(self._origin_url(), "git@github.com:SomeOwner/somerepo.git")

    def test_keeps_https_when_not_authenticated(self):
        self._set_origin("https://github.com/SomeOwner/somerepo.git")
        call_log = os.path.join(self.tmp_dir, "calls.log")
        self._stub_ssh(SSH_FAILURE_MESSAGE, 255, call_log)

        self._run_ssh_yml()

        self.assertEqual(self._origin_url(), "https://github.com/SomeOwner/somerepo.git")

    def test_already_ssh_origin_is_left_alone_and_not_checked(self):
        self._set_origin("git@github.com:SomeOwner/somerepo.git")
        call_log = os.path.join(self.tmp_dir, "calls.log")
        self._stub_ssh(SSH_SUCCESS_MESSAGE, 1, call_log)

        self._run_ssh_yml()

        self.assertEqual(self._origin_url(), "git@github.com:SomeOwner/somerepo.git")
        self.assertFalse(
            os.path.exists(call_log),
            "an already-SSH origin should never trigger a GitHub SSH auth check",
        )

    def test_non_github_https_origin_is_left_alone(self):
        self._set_origin("https://gitlab.com/SomeOwner/somerepo.git")
        call_log = os.path.join(self.tmp_dir, "calls.log")
        self._stub_ssh(SSH_SUCCESS_MESSAGE, 1, call_log)

        self._run_ssh_yml()

        self.assertEqual(self._origin_url(), "https://gitlab.com/SomeOwner/somerepo.git")
        self.assertFalse(
            os.path.exists(call_log),
            "a non-GitHub https origin should never trigger a GitHub SSH auth check",
        )


if __name__ == "__main__":
    unittest.main()

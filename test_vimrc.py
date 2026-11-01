import json
import os
import subprocess
import tempfile
import unittest

VIMRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vimrc')
PROBE = """
autocmd VimEnter * call writefile([json_encode({
  \\ 'syntax': exists('g:syntax_on'),
  \\ 'diff_change_bg': synIDattr(synIDtrans(hlID('DiffChange')), 'bg#', 'gui'),
  \\ 'diff_delete_bg': synIDattr(synIDtrans(hlID('DiffDelete')), 'bg#', 'gui'),
  \\ 'diff_text_bg': synIDattr(synIDtrans(hlID('DiffText')), 'bg#', 'gui'),
  \\ 'diff_add_bg': synIDattr(synIDtrans(hlID('DiffAdd')), 'bg#', 'gui'),
  \\ })], $PROBE_OUT) | qa!
"""


class VimrcTest(unittest.TestCase):
    def probe(self, *args):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, 'out.json')
            probe = os.path.join(tmp, 'probe.vim')
            with open(probe, 'w') as f:
                f.write(PROBE)
            for name in ('a', 'b'):
                with open(os.path.join(tmp, name), 'w') as f:
                    f.write(f'{name}\n')
            subprocess.run(
                ['vim', '-N', '-u', VIMRC, '-i', 'NONE', '-n', '-es', '-S', probe,
                 *args, os.path.join(tmp, 'a'), os.path.join(tmp, 'b')],
                env={**os.environ, 'PROBE_OUT': out},
                stdin=subprocess.DEVNULL,
                capture_output=True,
                timeout=30,
            )
            with open(out) as f:
                return json.load(f)

    def test_diff_mode_disables_syntax(self):
        self.assertEqual(self.probe('-d')['syntax'], 0)

    def test_normal_mode_keeps_syntax(self):
        self.assertEqual(self.probe()['syntax'], 1)

    def test_only_changed_text_and_added_lines_are_painted(self):
        result = self.probe('-d')
        self.assertEqual(result['diff_change_bg'], '')
        self.assertEqual(result['diff_delete_bg'], '')
        self.assertEqual(result['diff_text_bg'], '#46506a')
        self.assertEqual(result['diff_add_bg'], '#2b3a35')


if __name__ == '__main__':
    unittest.main()

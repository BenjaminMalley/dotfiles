import unittest
import os
import shutil
import subprocess
import sys

GIT_CHAIN = os.path.abspath(os.path.join(os.path.dirname(__file__), 'scripts', 'git-chain'))


class TestGitChain(unittest.TestCase):
    def setUp(self):
        self.test_dir = os.path.join(os.path.dirname(__file__), 'temp_git_chain_test')
        shutil.rmtree(self.test_dir, ignore_errors=True)
        os.makedirs(self.test_dir)

        # A bare origin and a clone, so refs/remotes/origin/HEAD exists.
        self.origin = os.path.join(self.test_dir, 'origin.git')
        subprocess.run(['git', 'init', '--bare', '-b', 'main', self.origin],
                       check=True, stdout=subprocess.DEVNULL)
        self.repo = os.path.join(self.test_dir, 'work')
        subprocess.run(['git', 'clone', self.origin, self.repo],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.git('config', 'user.email', 'test@example.com')
        self.git('config', 'user.name', 'Test User')
        self.commit_file('base.txt', 'base', 'initial commit')
        self.git('push', 'origin', 'main')
        self.git('remote', 'set-head', 'origin', '-a')
        self.git('checkout', '-b', 'feature')

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def git(self, *args, cwd=None, check=True):
        return subprocess.run(['git'] + list(args), cwd=cwd or self.repo, check=check,
                              capture_output=True, text=True)

    def chain(self, *args, check=True):
        res = subprocess.run([sys.executable, GIT_CHAIN] + list(args), cwd=self.repo,
                             capture_output=True, text=True)
        if check and res.returncode != 0:
            self.fail(f'git chain {args} failed: {res.stderr}')
        return res

    def commit_file(self, name, content, message):
        with open(os.path.join(self.repo, name), 'w') as f:
            f.write(content)
        self.git('add', name)
        self.git('commit', '-m', message)
        return self.git('rev-parse', 'HEAD').stdout.strip()

    def rev(self, ref):
        return self.git('rev-parse', ref).stdout.strip()

    def frames(self, rev_range):
        out = self.git('log', '--format=%s', rev_range).stdout.strip()
        return out.splitlines() if out else []

    def make_rest_state(self):
        """feature at f1 (pushed, under review); f2, f3 folded on feature-chain."""
        f1 = self.commit_file('f1.txt', 'f1', 'f1')
        self.git('push', 'origin', 'feature')
        self.chain('fold')  # bootstrap: creates feature-chain at f1
        self.commit_file('f2.txt', 'f2', 'f2')
        f3 = self.commit_file('f3.txt', 'f3', 'f3')
        self.chain('fold')
        return f1, f3

    def test_list_without_chain_branch(self):
        res = self.chain('list')
        self.assertIn("no chain branch 'feature-chain'", res.stdout)

    def test_bootstrap_fold_creates_chain_and_parks_beyond_origin(self):
        f1 = self.commit_file('f1.txt', 'f1', 'f1')
        self.git('push', 'origin', 'feature')
        f2 = self.commit_file('f2.txt', 'f2', 'f2')
        res = self.chain('fold')
        self.assertIn("created chain branch 'feature-chain'", res.stdout)
        self.assertEqual(self.rev('feature'), f1)
        self.assertEqual(self.rev('feature-chain'), f2)
        self.assertEqual(self.frames('feature..feature-chain'), ['f2'])

    def test_bootstrap_fold_without_remote_branch_folds_nothing(self):
        f1 = self.commit_file('f1.txt', 'f1', 'f1')
        res = self.chain('fold')
        self.assertEqual(self.rev('feature'), f1)
        self.assertEqual(self.rev('feature-chain'), f1)
        self.assertIn('0 frame(s)', res.stdout)

    def test_unfold_brings_chain_into_working_branch(self):
        f1, f3 = self.make_rest_state()
        self.chain('unfold')
        self.assertEqual(self.rev('feature'), f3)

    def test_unfold_when_nothing_folded(self):
        self.chain('fold')  # bootstrap
        res = self.chain('unfold')
        self.assertIn('nothing to unfold', res.stdout)

    def test_fold_when_nothing_to_fold(self):
        self.make_rest_state()
        res = self.chain('fold')
        self.assertIn('nothing to fold', res.stdout)

    def test_unfold_requires_clean_tree(self):
        self.make_rest_state()
        with open(os.path.join(self.repo, 'f1.txt'), 'a') as f:
            f.write('dirty')
        res = self.chain('unfold', check=False)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn('uncommitted changes', res.stderr)

    def test_fold_after_unfold_and_commit_parks_new_frames(self):
        f1, f3 = self.make_rest_state()
        self.chain('unfold')
        f4 = self.commit_file('f4.txt', 'f4', 'f4')
        self.chain('fold')
        self.assertEqual(self.rev('feature'), f1)
        self.assertEqual(self.rev('feature-chain'), f4)
        self.assertEqual(self.frames('feature..feature-chain'), ['f4', 'f3', 'f2'])

    def test_fold_after_amending_reviewed_frame_rebuilds_chain(self):
        f1, f3 = self.make_rest_state()
        # Address review feedback on f1 without unfolding the chain.
        self.commit_file('f1.txt', 'f1 amended', 'f1 amended')
        self.git('reset', '--soft', 'HEAD~1')
        self.git('commit', '--amend', '--no-edit')
        f1_new = self.rev('feature')
        self.assertNotEqual(f1_new, f1)

        self.chain('fold')

        self.assertEqual(self.rev('feature'), f1_new)
        # The folded frames were replayed onto the amended frame: the chain is
        # whole again and the chain tip still contains f2's and f3's changes.
        self.git('merge-base', '--is-ancestor', 'feature', 'feature-chain')
        self.assertEqual(self.frames('feature..feature-chain'), ['f3', 'f2'])
        tip = self.rev('feature-chain')
        self.assertEqual(self.git('show', f'{tip}:f2.txt').stdout, 'f2')
        self.assertEqual(self.git('show', f'{tip}:f1.txt').stdout, 'f1 amended')

    def test_refuses_to_run_on_chain_branch(self):
        self.make_rest_state()
        self.git('checkout', 'feature-chain')
        res = self.chain('fold', check=False)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn('refusing to run on chain branch', res.stderr)

    def test_merge_cycle_unfold_rebase_fold(self):
        """After the bottom frame merges: unfold, rebase onto trunk, fold."""
        f1, f3 = self.make_rest_state()

        # Merge f1 into main on the remote (fast-forward, as rebase-merge does).
        other = os.path.join(self.test_dir, 'other')
        subprocess.run(['git', 'clone', self.origin, other],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.git('merge', '--ff-only', 'origin/feature', cwd=other)
        self.git('push', 'origin', 'main', cwd=other)
        self.git('fetch', 'origin')

        self.chain('unfold')
        self.git('rebase', 'origin/main')
        self.chain('fold')

        # f1 is gone from the chain; the new bottom frame is the reviewed one.
        self.assertEqual(self.frames('origin/main..feature'), ['f2'])
        self.assertEqual(self.frames('feature..feature-chain'), ['f3'])
        tip = self.rev('feature-chain')
        self.assertEqual(self.git('show', f'{tip}:f3.txt').stdout, 'f3')

    def test_fold_after_entire_chain_merges_upstream(self):
        """The whole chain merged, leaving the chain branch at trunk: the
        pointer survives and fold rebuilds the chain from the working branch."""
        f1, f3 = self.make_rest_state()

        # Merge the whole chain into main on the remote (fast-forward).
        self.git('push', 'origin', 'feature-chain')
        other = os.path.join(self.test_dir, 'other')
        subprocess.run(['git', 'clone', self.origin, other],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.git('merge', '--ff-only', 'origin/feature-chain', cwd=other)
        self.git('push', 'origin', 'main', cwd=other)
        self.git('fetch', 'origin')

        # Rebase the folded branch onto the new trunk: every frame drops as
        # already upstream, so the branch cannot satisfy the pointer.
        self.git('rebase', 'origin/main')
        self.assertEqual(self.rev('feature'), self.rev('origin/main'))
        res = self.chain('fold', check=False)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn('stale pointer', res.stderr)

        # New work gives the branch the frames the pointer wants; fold
        # recovers, keeping the fold at frame 1 and parking the rest.
        f4 = self.commit_file('f4.txt', 'f4', 'f4')
        f5 = self.commit_file('f5.txt', 'f5', 'f5')
        self.chain('fold')
        self.assertEqual(self.rev('feature'), f4)
        self.assertEqual(self.rev('feature-chain'), f5)
        self.assertEqual(self.frames('origin/main..feature'), ['f4'])
        self.assertEqual(self.frames('feature..feature-chain'), ['f5'])
        frames = self.git('config', '--worktree', '--get', 'chain.frames').stdout.strip()
        self.assertEqual(frames, '1')
        # And the cycle works again from here.
        self.chain('unfold')
        self.assertEqual(self.rev('feature'), f5)

    def test_unfold_after_rebase_onto_merge_that_rewrote_frame(self):
        """The frame merged upstream with a new SHA (squash merge) and the
        branch was rebased onto the new trunk while still folded."""
        f1, f3 = self.make_rest_state()

        # Merge f1's patch into main as a new commit, as a squash merge does.
        other = os.path.join(self.test_dir, 'other')
        subprocess.run(['git', 'clone', self.origin, other],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.git('config', 'user.email', 'test@example.com', cwd=other)
        self.git('config', 'user.name', 'Test User', cwd=other)
        self.git('cherry-pick', '--no-commit', 'origin/feature', cwd=other)
        self.git('commit', '-m', 'f1 squashed', cwd=other)
        self.git('push', 'origin', 'main', cwd=other)

        # Rebase onto the new trunk while still folded ('git rb'): the local
        # f1 drops as already upstream and feature lands on the trunk tip.
        self.git('fetch', 'origin')
        self.git('rebase', 'origin/main')
        self.assertEqual(self.rev('feature'), self.rev('origin/main'))

        self.chain('unfold')

        # The chain was replayed onto the rebased branch; feature holds the rest.
        self.assertEqual(self.rev('feature'), self.rev('feature-chain'))
        self.assertEqual(self.frames('origin/main..feature'), ['f3', 'f2'])
        tip = self.rev('feature')
        self.assertEqual(self.git('show', f'{tip}:f3.txt').stdout, 'f3')
        self.assertEqual(self.git('show', f'{tip}:f2.txt').stdout, 'f2')

    def test_unfold_refuses_new_work_beyond_the_fold(self):
        self.make_rest_state()
        self.commit_file('extra.txt', 'extra', 'extra')
        res = self.chain('unfold', check=False)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn('unfolded changes', res.stderr)

    def test_pointer_survives_repeated_cycles(self):
        f1, f3 = self.make_rest_state()
        self.chain('unfold')
        self.commit_file('f4.txt', 'f4', 'f4')
        self.chain('fold')
        self.chain('unfold')
        self.commit_file('f5.txt', 'f5', 'f5')
        self.chain('fold')
        self.assertEqual(self.rev('feature'), f1)
        self.assertEqual(self.frames('feature..feature-chain'), ['f5', 'f4', 'f3', 'f2'])

    def test_branch_switch_keeps_same_chain(self):
        """A new branch continues the same chain, so it shares the worktree chain."""
        f1, f3 = self.make_rest_state()
        self.git('checkout', '-b', 'feature-2')
        self.commit_file('f4.txt', 'f4', 'f4')
        self.chain('fold')
        # Folded onto the original chain branch; no feature-2-chain was created.
        self.assertEqual(self.rev('feature-2'), f1)
        self.assertEqual(self.frames('feature-2..feature-chain'), ['f4', 'f3', 'f2'])
        res = self.git('show-ref', '--verify', '--quiet', 'refs/heads/feature-2-chain', check=False)
        self.assertNotEqual(res.returncode, 0)
        # And unfold still works from the new branch.
        self.chain('unfold')
        self.assertEqual(self.rev('feature-2'), self.rev('feature-chain'))

    def test_existing_default_chain_branch_is_adopted(self):
        """A restored worktree (no config) adopts <branch>-chain and records it."""
        f1, f3 = self.make_rest_state()
        self.git('config', '--worktree', '--unset', 'chain.branch')
        self.git('checkout', '-b', 'feature-2')
        res = self.chain('list')
        self.assertIn("no chain branch 'feature-2-chain'", res.stdout)
        # Back on feature, the existing branch is adopted and recorded...
        self.git('checkout', 'feature')
        self.chain('list')
        recorded = self.git('config', '--worktree', '--get', 'chain.branch').stdout.strip()
        self.assertEqual(recorded, 'feature-chain')
        # ...so switching branches again keeps the same chain.
        self.git('checkout', 'feature-2')
        res = self.chain('list')
        self.assertIn('folded on feature-chain', res.stdout)
    def test_grow_includes_next_folded_frame(self):
        f1, f3 = self.make_rest_state()
        self.chain('grow')
        self.assertEqual(self.frames('origin/main..feature'), ['f2', 'f1'])
        self.assertEqual(self.frames('feature..feature-chain'), ['f3'])
        # And the pointer moved, so fold returns to the new fold point.
        f2 = self.rev('feature')
        self.chain('fold')
        self.assertEqual(self.rev('feature'), f2)

    def test_grow_with_count_and_past_tip(self):
        f1, f3 = self.make_rest_state()
        self.chain('grow', '2')
        self.assertEqual(self.rev('feature'), f3)
        res = self.chain('grow', check=False)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn('cannot move', res.stderr)

    def test_shrink_excludes_top_frame(self):
        f1, f3 = self.make_rest_state()
        self.chain('grow')
        self.chain('shrink')
        self.assertEqual(self.rev('feature'), f1)
        self.assertEqual(self.frames('feature..feature-chain'), ['f3', 'f2'])

    def test_shrink_to_zero_and_below(self):
        f1, f3 = self.make_rest_state()
        self.chain('shrink')
        self.assertEqual(self.rev('feature'), self.rev('origin/main'))
        res = self.chain('shrink', check=False)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn('cannot move', res.stderr)

    def test_grow_requires_working_branch_at_the_fold(self):
        f1, f3 = self.make_rest_state()
        self.chain('unfold')
        res = self.chain('grow', check=False)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn('not at the fold', res.stderr)

    def test_grow_without_chain_branch(self):
        res = self.chain('grow', check=False)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn('nothing folded', res.stderr)


if __name__ == '__main__':
    unittest.main()

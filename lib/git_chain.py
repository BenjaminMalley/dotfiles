from lib.utils import run_command


class ChainError(Exception):
    pass


def _git(args, check=True, capture=True):
    res = run_command(['git'] + args, check=False, capture_output=capture)
    if res is None:
        raise ChainError('git not found')
    if check and res.returncode != 0:
        msg = res.stderr.strip() if capture and res.stderr else f"git {' '.join(args)} failed"
        raise ChainError(msg)
    return res


def _out(args):
    return _git(args).stdout.strip()


def _trunk():
    res = _git(['symbolic-ref', 'refs/remotes/origin/HEAD'], check=False)
    if res.returncode != 0 or not res.stdout.strip():
        raise ChainError('no origin HEAD found (set one with: git remote set-head origin -a)')
    return res.stdout.strip().replace('refs/remotes/', '')


def _current_branch():
    branch = _out(['rev-parse', '--abbrev-ref', 'HEAD'])
    if branch == 'HEAD':
        raise ChainError('detached HEAD')
    if branch.endswith('-chain'):
        raise ChainError(f"refusing to run on chain branch '{branch}'; check out the working branch")
    return branch


def _require_clean():
    if _out(['status', '--porcelain', '--untracked-files=no']):
        raise ChainError('working tree has uncommitted changes; commit or discard them first')


def _count(rev_range):
    return int(_out(['rev-list', '--count', rev_range]))


def _ref_exists(ref):
    return _git(['show-ref', '--verify', '--quiet', f'refs/heads/{ref}'], check=False).returncode == 0


def _is_ancestor(a, b):
    return _git(['merge-base', '--is-ancestor', a, b], check=False).returncode == 0


def _set_chain_branch(name):
    _git(['config', 'extensions.worktreeConfig', 'true'], check=False)
    _git(['config', '--worktree', 'chain.branch', name])


def _get_chain_branch(branch):
    """The chain branch for this worktree: one per worktree, not per branch.

    Recorded as chain.branch at bootstrap so that switching branches keeps the
    same chain. Falls back to <branch>-chain; an existing branch with that name
    is adopted (and recorded) so restored worktrees stay seamless.
    """
    res = _git(['config', '--worktree', '--get', 'chain.branch'], check=False)
    if res.returncode == 0 and res.stdout.strip():
        return res.stdout.strip()
    chain = f'{branch}-chain'
    if _ref_exists(chain):
        _set_chain_branch(chain)
    return chain


def _branch_and_chain():
    branch = _current_branch()
    chain = _get_chain_branch(branch)
    if branch == chain:
        raise ChainError(f"refusing to run on chain branch '{branch}'; check out the working branch")
    return branch, chain


def _get_frames(branch, trunk):
    """Number of frames (commits above trunk) that belong in the working branch.

    Stored per-worktree as chain.frames; an integer survives history rewrites,
    a SHA would not. Initialized from origin/<branch> when possible: what the
    reviewer sees is what belongs in the working branch.
    """
    res = _git(['config', '--worktree', '--get', 'chain.frames'], check=False)
    if res.returncode == 0 and res.stdout.strip():
        return int(res.stdout.strip())
    remote = f'origin/{branch}'
    if _git(['show-ref', '--verify', '--quiet', f'refs/remotes/{remote}'], check=False).returncode == 0:
        n = _count(f'{trunk}..{remote}')
    else:
        n = _count(f'{trunk}..{branch}')
    _set_frames(n)
    return n


def _set_frames(n):
    _git(['config', 'extensions.worktreeConfig', 'true'], check=False)
    _git(['config', '--worktree', 'chain.frames', str(n)])


def _frame_at(trunk, chain, n):
    """SHA of the nth frame on the chain branch (trunk itself when n is 0)."""
    if n == 0:
        return trunk
    commits = _out(['rev-list', '--reverse', f'{trunk}..{chain}']).splitlines()
    if n > len(commits):
        raise ChainError(f'chain has {len(commits)} frames but pointer is {n}')
    return commits[n - 1]


def _move_fold(delta):
    branch, chain = _branch_and_chain()
    trunk = _trunk()
    if not _ref_exists(chain):
        raise ChainError(f"no chain branch '{chain}' (nothing folded)")
    _require_clean()
    n = _get_frames(branch, trunk)
    count_a = _count(f'{trunk}..{branch}')
    if not (_is_ancestor(branch, chain) and count_a == n):
        raise ChainError("working branch is not at the fold; run 'git chain fold' first")
    total = _count(f'{trunk}..{chain}')
    new_n = n + delta
    if new_n < 0 or new_n > total:
        raise ChainError(f'fold is at frame {n} of {total}; cannot move by {delta}')
    _set_frames(new_n)
    _git(['reset', '--hard', _frame_at(trunk, chain, new_n)], capture=False)
    print(f'fold at frame {new_n} of {total}')


def cmd_grow(count=1):
    _move_fold(count)


def cmd_shrink(count=1):
    _move_fold(-count)


def cmd_list():
    branch, chain = _branch_and_chain()
    trunk = _trunk()
    print(f'on {branch}:')
    print(_out(['log', '--oneline', f'{trunk}..{branch}']) or '  (nothing)')
    if not _ref_exists(chain):
        print(f"no chain branch '{chain}' (nothing folded)")
        return
    print(f'folded on {chain}:')
    print(_out(['log', '--oneline', f'{branch}..{chain}']) or '  (nothing)')


def cmd_unfold():
    branch, chain = _branch_and_chain()
    trunk = _trunk()
    if not _ref_exists(chain):
        raise ChainError(f"nothing to unfold (no chain branch '{chain}')")
    _get_frames(branch, trunk)
    _require_clean()
    tip = _out(['rev-parse', chain])
    if _out(['rev-parse', branch]) == tip:
        print('nothing to unfold (working branch already at chain tip)')
        return
    if not _is_ancestor(branch, chain):
        if _out(['rev-list', branch, f'^{chain}', f'^{trunk}']):
            raise ChainError("working branch has unfolded changes; run 'git chain fold' first")
        # The fold's frames merged upstream (with new SHAs, as a squash or
        # rebase merge produces) and the branch was rebased onto the new trunk
        # before unfolding; replay the rest of the chain on top of it.
        base = _out(['merge-base', branch, chain])
        res = _git(['rebase', '--onto', branch, base, chain], check=False)
        if res.returncode != 0:
            raise ChainError(
                'rebase conflict while moving the chain onto the rebased branch; '
                "resolve it, run 'git rebase --continue', then check out the "
                "working branch and run 'git chain unfold' again")
        _git(['checkout', branch], capture=False)
        tip = _out(['rev-parse', chain])
    _git(['reset', '--hard', tip], capture=False)
    print(f'unfolded chain onto {branch}')


def cmd_fold():
    branch, chain = _branch_and_chain()
    trunk = _trunk()
    _require_clean()
    created = False
    if not _ref_exists(chain):
        _git(['branch', chain, branch])
        _set_chain_branch(chain)
        created = True
        print(f"created chain branch '{chain}'")
    n = _get_frames(branch, trunk)
    total = _count(f'{trunk}..{chain}')
    count_a = _count(f'{trunk}..{branch}')
    if not created and n > total and count_a >= n and _is_ancestor(chain, branch):
        # The chain shrank below the pointer (frames merged upstream, or the
        # chain branch was reset) and holds nothing the working branch lacks.
        # The pointer is positional, so it survives: rebuild the chain from
        # the working branch and fold at the pointer.
        _git(['branch', '-f', chain, branch])
        total = count_a
    tail = total - n
    if tail < 0 or count_a < n:
        raise ChainError(
            f'stale pointer: chain has {total} frames, working branch has {count_a}, '
            f'pointer says {n}; fix with: git config --worktree chain.frames N')

    if not created and _is_ancestor(branch, chain) and count_a == n:
        print('nothing to fold')
        return

    if not created:
        if count_a > n and count_a >= total:
            # Replace: the working branch holds the full chain (unfolded and
            # committed on, rebased, or rewritten) — it is authoritative.
            _git(['branch', '-f', chain, branch])
        elif count_a > n:
            # The working branch holds frame n plus frames not on the chain
            # (e.g. committed on a branch made from the reviewed frame):
            # replay the new frames onto the chain tip.
            res = _git(['rebase', '--onto', chain, _frame_at(trunk, branch, n)], check=False)
            if res.returncode != 0:
                raise ChainError(
                    'rebase conflict while adding frames to the chain; resolve it, run '
                    "'git rebase --continue', then run 'git chain fold' again")
            _git(['branch', '-f', chain, branch])
        elif tail == 0:
            _git(['branch', '-f', chain, branch])
        else:
            # Rebuild: the reviewed frames were amended; replay the folded
            # frames on top of their replacements.
            base = _out(['rev-parse', f'{chain}~{tail}'])
            res = _git(['rebase', '--onto', branch, base, chain], check=False)
            if res.returncode != 0:
                raise ChainError(
                    'rebase conflict while rebuilding the chain; resolve it, run '
                    "'git rebase --continue', then check out the working branch "
                    "and run 'git chain fold' again")
            _git(['checkout', branch], capture=False)

    _git(['reset', '--hard', _frame_at(trunk, chain, n)], capture=False)
    print(f"folded: {_count(f'{branch}..{chain}')} frame(s) on '{chain}'")

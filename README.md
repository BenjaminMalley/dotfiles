# Dotfiles

Personal configuration files for macOS.

## Installation

This repo is the core. A computer can also use a local repo that holds this repo
as a git subtree at `./dotfiles` and adds its own files. Run the bootstrap from
the local repo:

```bash
git clone <local repo> && cd <local repo>
./dotfiles/bootstrap.sh
```

Without a local repo, run `./bootstrap.sh` from this repo to install the core
only. The bootstrap uses the parent directory of this repo as the local repo when
that directory is the root of a git repo.

After the first run, `dotfiles` re-runs the setup from any directory.
** Note: The script assumes a working `python3` **

To add this repo to a local repo, or to update it there:

```bash
git subtree add --prefix dotfiles https://github.com/BenjaminMalley/dotfiles.git main --squash
git subtree pull --prefix dotfiles https://github.com/BenjaminMalley/dotfiles.git main --squash
```

## Local repo

Every file in the local repo is optional. Each one adds to the core file of the
same kind:

| Local file | Effect |
| --- | --- |
| `local.yml` | `homebrew_formulae`, `homebrew_casks` and `dotfiles` lists are appended to the core lists in `ansible/group_vars/all.yml`. `dotfiles` sources are relative to the local repo. |
| `AGENTS.md` | Linked to `~/.claude/CLAUDE.md`. The core `AGENTS.md` is linked to `~/.claude/rules/core.md`, so Claude Code loads both. |
| `claude-settings.json` | Merged into the core `claude-settings.json` to make `~/.claude/settings.json`. Lists are appended. |
| `zshrc` | Sourced by the core `zshrc`. |
| `scripts/` | Added to `PATH` after the core `scripts/`. |

Example `local.yml`:

```yaml
homebrew_formulae: [node]
homebrew_casks: [vlc]
dotfiles:
  - { source: "config/tool", dest: ".config/tool/config" }
```

## Neovim Cheatsheet

Neovim configuration uses **`lazy.nvim`** for plugin management and **`fzf-lua`** for fuzzy finding.

### General
- **Leader Key**: `\` (default)

### Fuzzy Finder (`fzf-lua`)
- `<C-p>`: Search for files in the project.
- `<leader>fg`: Live grep (search text across all files).
- `<leader>fb`: Switch between open buffers.
- `<leader>fr`: Browse recently opened files, including ones opened in the current session.
- `<leader>fh`: Search Neovim help tags.
- `<leader>gs`: Browse files changed in the current worktree (git status: modified/staged/untracked).

### LSP (Language Server Protocol)
- `gd`: Go to definition.
- `gr`: Find references (opens in fzf).
- `K`: Show hover documentation.
- `<leader>rn`: Rename the symbol under the cursor.
- `<leader>ca`: Show available code actions.
- `<leader>ds`: Search document symbols (functions, variables).
- `<leader>ws`: Search workspace symbols.

### Diagnostics
- `gl`: Show diagnostic message for the current line.
- `[d` / `]d`: Jump to the previous/next diagnostic.

### Autocompletion (`nvim-cmp`)
- `<C-Space>`: Manually trigger completion.
- `<CR>` (Enter): Confirm selection.

### Management
- `:Lazy`: Open the plugin manager UI.
- `:Mason`: Open the LSP/DAP/Linter manager UI.

## Tools included

- **zsh**: Configured in `.zshrc`
- **tmux**: Configured in `.tmux.conf`
- **Vim/Neovim**: Configured in `.vimrc` and `nvim/`
- **Scripts**: Located in `scripts/` (`dotfiles`, `git-chain`, `gh-create`)

## Git Shortcuts

`gitconfig` includes several helpful aliases for common workflows:

- **`git rb`**: Rebase your current branch against the default branch (e.g., `main` or `master`) after fetching from `origin`.
- **`git rst`**: Hard reset your current branch to match the `origin` default branch (warning: discards local changes).
- **`git cleanup`**: Prune remote branches and delete local branches that have already been merged into the default branch.

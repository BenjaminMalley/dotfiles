# Dotfiles

Personal configuration files for a high-performance development environment on macOS and Linux.

## Installation

```bash
python3 install.py
```

This will symlink the dotfiles, install Homebrew and software (on macOS), and set up agent configuration for Gemini and Claude.

## Neovim Cheatsheet

Your Neovim configuration uses **`lazy.nvim`** for plugin management and **`fzf-lua`** for fuzzy finding.

### General
- **Leader Key**: `` (default)

### Fuzzy Finder (`fzf-lua`)
- `<C-p>`: Search for files in the project.
- `<leader>fg`: Live grep (search text across all files).
- `<leader>fb`: Switch between open buffers.
- `<leader>fh`: Search Neovim help tags.

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
- **Ghostty**: Configured in `ghostty/config`
- **Scripts**: Located in `scripts/` (e.g., `v`, `wts`, `dotfiles`)

## Worktree Session Tool (`wts`)

`wts` is a script for managing git worktrees and tmux sessions in a unified way. It's designed for a "one branch per worktree/session" workflow.

### Features
- **Automatic Branch Prefixing**: Prefixes branches with `{user}/{repo}-` to avoid collisions in shared repositories.
- **Tmux Integration**: Automatically creates a new tmux session with a split-pane layout (Agent pane + Neovim pane).
- **Worktree Management**: Handles `git worktree` creation and removal.
- **Easy Cleanup**: One command to remove the worktree and kill the tmux session once finished.

### Usage
- `wts <branch-name>`: Create (or switch to) a worktree and tmux session for the specified branch.
- `wts -n <session-name>`: Create a tmux session without creating a git worktree.
- `wts -d`: (Done) Clean up the current session—removes the worktree (if it's in `~/worktrees`) and kills the tmux session.
- `wts -a <session-name>`: Attach to an existing tmux session.

### Configuration
- `WTS_AGENT_CMD`: Set this environment variable in your `.zshrc` to automatically run a command (like `gemini` or `claude`) in the Agent pane upon session creation.

## Git Shortcuts

Your `gitconfig` includes several helpful aliases for common workflows:

- **`git rb`**: Rebase your current branch against the default branch (e.g., `main` or `master`) after fetching from `origin`.
- **`git rst`**: Hard reset your current branch to match the `origin` default branch (warning: discards local changes).
- **`git cleanup`**: Prune remote branches and delete local branches that have already been merged into the default branch.

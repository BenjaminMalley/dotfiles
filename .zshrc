# Add dotfiles scripts to PATH
if [[ -L "$HOME/.zshrc" ]]; then
    DOTFILES_DIR=$(dirname "$(readlink "$HOME/.zshrc")")
    if [[ -d "$DOTFILES_DIR/scripts" ]]; then
        export PATH="$DOTFILES_DIR/scripts:$PATH"
    fi
fi

set -o vi
export EDITOR=nvim
export VISUAL=nvim
bindkey -M vicmd '/' history-incremental-search-backward

if command -v tmux &> /dev/null && [ -z "$TMUX" ]; then
    # Try to attach to the session if it exists (naming logic is inside wts)
    wts --attach &>/dev/null
fi

# Source local configuration
if [ -f ~/.zshrc.local ]; then
  . ~/.zshrc.local
fi

# Fix SSH Agent in tmux: symlink the dynamic socket to a static path
if [[ -S "$SSH_AUTH_SOCK" && "$SSH_AUTH_SOCK" != "$HOME/.ssh/ssh_auth_sock" ]]; then
  mkdir -p ~/.ssh
  ln -sf "$SSH_AUTH_SOCK" ~/.ssh/ssh_auth_sock
fi
export SSH_AUTH_SOCK="$HOME/.ssh/ssh_auth_sock"

# Disable audible beep
unsetopt BEEP
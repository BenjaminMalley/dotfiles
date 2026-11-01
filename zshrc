# Homebrew on macOS: PATH only, brew works fine without the rest of shellenv
if [ -d /opt/homebrew/bin ]; then
    export PATH="/opt/homebrew/bin:$PATH"
fi

# linuxbrew needs the full shellenv (MANPATH, INFOPATH, HOMEBREW_* vars), not
# just PATH
if [ -x /home/linuxbrew/.linuxbrew/bin/brew ]; then
    eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
fi

# Add dotfiles scripts to PATH
if [[ -L "$HOME/.zshrc" ]]; then
    zshrc_path="$HOME/.zshrc"
    DOTFILES_DIR=${zshrc_path:A:h}
    LOCAL_DIR=${DOTFILES_DIR:h}
    for scripts_dir in "$LOCAL_DIR/scripts" "$DOTFILES_DIR/scripts"; do
        if [[ -d "$scripts_dir" ]]; then
            export PATH="$scripts_dir:$PATH"
        fi
    done
fi

set -o vi
export EDITOR=nvim
export VISUAL=nvim
bindkey -M vicmd '/' history-incremental-search-backward

# Source local configuration
if [[ -n "$LOCAL_DIR" && -f "$LOCAL_DIR/zshrc" ]]; then
  . "$LOCAL_DIR/zshrc"
fi

# Fix SSH Agent in tmux: symlink the dynamic socket to a static path
if [[ -S "$SSH_AUTH_SOCK" && "$SSH_AUTH_SOCK" != "$HOME/.ssh/ssh_auth_sock" ]]; then
  mkdir -p ~/.ssh
  ln -sf "$SSH_AUTH_SOCK" ~/.ssh/ssh_auth_sock
fi
export SSH_AUTH_SOCK="$HOME/.ssh/ssh_auth_sock"

# Disable audible beep
unsetopt BEEP

# Add dotfiles scripts to PATH
if [[ -L "$HOME/.zshrc" ]]; then
    DOTFILES_DIR=$(dirname "$(readlink "$HOME/.zshrc")")
    if [[ -d "$DOTFILES_DIR/scripts" ]]; then
        export PATH="$DOTFILES_DIR/scripts:$PATH"
    fi
fi

set -o vi
export EDITOR=vim
export VISUAL=vim
bindkey -M vicmd '/' history-incremental-search-backward

if command -v tmux &> /dev/null && [ -z "$TMUX" ]; then
    SESSION_NAME="tmux-${PWD//\//-}"
    if tmux has-session -t "=${SESSION_NAME}" 2>/dev/null; then
        tmux attach-session -t "${SESSION_NAME}"
    fi
fi

# Source local configuration
if [ -f ~/.zshrc.local ]; then
  . ~/.zshrc.local
fi

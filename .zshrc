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
    tmux attach-session -t "$SESSION_NAME" || tmux new-session -s "$SESSION_NAME"
fi

# Source local configuration
if [ -f ~/.zshrc.local ]; then
  . ~/.zshrc.local
fi

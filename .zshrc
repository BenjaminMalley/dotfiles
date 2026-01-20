set -o vi
export EDITOR=vim
export VISUAL=vim
bindkey -M vicmd '/' history-incremental-search-backward

if ([[ "$TERM_PROGRAM" != "Apple_Terminal" ]] || [[ "$TERMINAL_EMULATOR" == "JetBrains-JediTerm" ]]) && command -v tmux &> /dev/null && [ -z "$TMUX" ]; then
    SESSION_NAME="tmux-${PWD//\//-}"
    tmux attach-session -t "$SESSION_NAME" || tmux new-session -s "$SESSION_NAME"
fi

# Source local configuration
if [ -f ~/.zshrc.local ]; then
  . ~/.zshrc.local
fi

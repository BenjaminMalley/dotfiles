set -o vi
export EDITOR=vim
export VISUAL=vim
bindkey -M vicmd '/' history-incremental-search-backward

if [ "$TERM_PROGRAM" != "Apple_Terminal" ] && command -v tmux &> /dev/null && [ -z "$TMUX" ]; then
    SESSION_NAME="tmux-${PWD//\//-}"
    tmux new-session -A -s "$SESSION_NAME"
fi

# Source local configuration
if [ -f ~/.zshrc.local ]; then
  . ~/.zshrc.local
fi

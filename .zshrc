set -o vi
export EDITOR=vim
export VISUAL=vim
bindkey -M vicmd '/' history-incremental-search-backward
# fix screen colors in the Zed terminal
alias screen="env -u COLORTERM screen"

# Automatically start screen
if [[ $- == *i* ]] && [[ -z "$STY" ]]; then
  screen -D -R
fi
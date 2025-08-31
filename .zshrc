set -o vi
export EDITOR=vim
export VISUAL=vim
bindkey -M vicmd '/' history-incremental-search-backward
alias screen="env -u COLORTERM screen"

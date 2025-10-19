set -o vi
export EDITOR=vim
export VISUAL=vim
bindkey -M vicmd '/' history-incremental-search-backward

if ([[ "$TERM_PROGRAM" != "Apple_Terminal" ]] || [[ "$TERMINAL_EMULATOR" == "JetBrains-JediTerm" ]]) && command -v screen &> /dev/null && [ -z "$STY" ]; then
    SESSION_NAME="screen-${PWD//\//-}"
    screen -R "$SESSION_NAME"
fi

# Source local configuration
if [ -f ~/.zshrc.local ]; then
  . ~/.zshrc.local
fi

" Enable syntax highlighting
syntax on

" Enable file type detection, plugins, and indentation
filetype plugin indent on

" Show line numbers
set number

" Use 4 spaces for tabs and auto-indenting
set tabstop=4
set shiftwidth=4
set expandtab

" Enable smart auto-indenting
set autoindent
set smartindent

" Highlight search results as you type
set hlsearch
set incsearch

" Show the command you are typing in the bottom right
set showcmd

" A modern color scheme (if your terminal supports it)
colorscheme desert

" Enable true color support
if has("termguicolors")
  set termguicolors
endif

" Allow tmux to dim the background by making Vim background transparent
" This must come AFTER the colorscheme command
highlight Normal guibg=NONE ctermbg=NONE
highlight NonText guibg=NONE ctermbg=NONE
highlight LineNr guibg=NONE ctermbg=NONE
highlight Folded guibg=NONE ctermbg=NONE
highlight EndOfBuffer guibg=NONE ctermbg=NONE

" Force a redraw on startup to prevent ghosting artifacts in tmux
augroup FixGhosting
  autocmd!
  autocmd VimEnter * redraw!
augroup END

" Kill the bells
set noerrorbells
set novisualbell
set t_vb=

" Enable mouse support
set mouse=a
if !has('nvim')
  if &term =~ 'xterm' || &term =~ 'tmux'
    set ttymouse=sgr
  endif
endif

" Fix visual artifacts in tmux (background color erase issues)
if &term =~ '256color'
  set t_ut=
endif

" Auto-reload files when they change on disk
set autoread


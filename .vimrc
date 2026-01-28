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

" Kill the bells
set noerrorbells
set novisualbell
set t_vb=

" Auto-reload files when they change on disk
set autoread

" Triger `checktime` when cursor stops moving or window focus changes
augroup AutoRead
  autocmd!
  autocmd FocusGained,BufEnter,CursorHold,CursorHoldI * if mode() != 'c' | checktime | endif
  " Notification when file changes
  autocmd FileChangedShellPost *
    \ echohl WarningMsg | echo "File changed on disk. Buffer reloaded." | echohl None
augroup END

-- Load existing .vimrc settings
vim.cmd('source ~/.vimrc')

-- Faster completion and diagnostic feedback
vim.opt.updatetime = 300

-- Bootstrap lazy.nvim
local lazypath = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
if not vim.loop.fs_stat(lazypath) then
  vim.fn.system({
    "git",
    "clone",
    "--filter=blob:none",
    "https://github.com/folke/lazy.nvim.git",
    "--branch=stable",
    lazypath,
  })
end
vim.opt.rtp:prepend(lazypath)

-- Set up plugins
require("lazy").setup({
  -- Fuzzy Finder
  {
    "ibhagwan/fzf-lua",
    dependencies = { "nvim-tree/nvim-web-devicons" },
    config = function()
      local fzf = require("fzf-lua")
      fzf.setup({
        -- Performance settings for massive monorepos
        files = {
          cmd = "git ls-files --exclude-standard --cached --others || fd --type f",
          git_icons = false,
          file_icons = true,
        },
        -- Window layout and behavior
        winopts = {
          preview = { layout = 'vertical' },
          on_create = function()
            -- Close with a single Esc
            vim.keymap.set('t', '<Esc>', '<C-c>', { silent = true, buffer = true })
          end,
        },
        keymap = {
          builtin = {
            ["<C-j>"] = "down",
            ["<C-k>"] = "up",
          },
          fzf = {
            ["ctrl-j"] = "down",
            ["ctrl-k"] = "up",
            ["ctrl-d"] = "half-page-down",
            ["ctrl-u"] = "half-page-up",
          }
        },
        grep = {
          rg_opts = "--column --line-number --no-heading --color=always --smart-case --max-columns=4096 -e",
        },
      })
      -- Mappings
      vim.keymap.set("n", "<C-p>", fzf.files, { desc = "Fzf Files" })
      vim.keymap.set("n", "<leader>fg", fzf.live_grep, { desc = "Fzf Live Grep" })
      vim.keymap.set("n", "<leader>fb", fzf.buffers, { desc = "Fzf Buffers" })
      vim.keymap.set("n", "<leader>fh", fzf.help_tags, { desc = "Fzf Help" })
      -- LSP integration via fzf-lua
      vim.keymap.set('n', 'gd', fzf.lsp_definitions, { desc = "Fzf Definition" })
      vim.keymap.set('n', 'gr', fzf.lsp_references, { desc = "Fzf References" })
      vim.keymap.set('n', '<leader>ds', fzf.lsp_document_symbols, { desc = "Fzf Document Symbols" })
      vim.keymap.set('n', '<leader>ws', fzf.lsp_workspace_symbols, { desc = "Fzf Workspace Symbols" })
    end,
  },

  -- LSP Support
  {
    "neovim/nvim-lspconfig",
    dependencies = {
      "williamboman/mason.nvim",
      "williamboman/mason-lspconfig.nvim",
      "hrsh7th/nvim-cmp",
      "hrsh7th/cmp-nvim-lsp",
    },
    config = function()
      require("mason").setup()
      require("mason-lspconfig").setup({
        ensure_installed = { "pyright", "jdtls" },
      })

      local capabilities = require("cmp_nvim_lsp").default_capabilities()

      -- Python Configuration
      vim.lsp.config("pyright", {
        capabilities = capabilities,
        root_dir = function(bufnr, on_dir)
          local fname = vim.api.nvim_buf_get_name(bufnr)
          local root = require("lspconfig.util").root_pattern(".git", "pyproject.toml", "setup.py")(fname)
            or vim.uv.cwd()
          on_dir(root)
        end,
      })
      vim.lsp.enable("pyright")

      -- Global LSP Mappings
      vim.keymap.set('n', 'K', vim.lsp.buf.hover, { desc = "Hover Documentation" })
      vim.keymap.set('n', '<leader>rn', vim.lsp.buf.rename, { desc = "Rename Symbol" })
      vim.keymap.set('n', '<leader>ca', vim.lsp.buf.code_action, { desc = "Code Action" })

      -- Diagnostic Mappings
      vim.keymap.set('n', '[d', vim.diagnostic.goto_prev, { desc = "Previous Diagnostic" })
      vim.keymap.set('n', ']d', vim.diagnostic.goto_next, { desc = "Next Diagnostic" })
      vim.keymap.set('n', 'gl', vim.diagnostic.open_float, { desc = "Show Line Diagnostic" })

      -- Show diagnostics in a floating window on hover
      vim.api.nvim_create_autocmd("CursorHold", {
        callback = function()
          vim.diagnostic.open_float(nil, { focusable = false })
        end,
      })
    end,
  },

  -- Completion
  {
    "hrsh7th/nvim-cmp",
    config = function()
      local cmp = require("cmp")
      cmp.setup({
        mapping = cmp.mapping.preset.insert({
          ['<C-b>'] = cmp.mapping.scroll_docs(-4),
          ['<C-f>'] = cmp.mapping.scroll_docs(4),
          ['<C-Space>'] = cmp.mapping.complete(),
          ['<CR>'] = cmp.mapping.confirm({ select = true }),
        }),
        sources = cmp.config.sources({
          { name = 'nvim_lsp' },
        })
      })
    end,
  },

  -- Java Support (Specialized)
  { "mfussenegger/nvim-jdtls" },
}, {
  ui = { border = "rounded" },
})

local project_name = vim.fn.fnamemodify(vim.fn.getcwd(), ":p:h:t")
local workspace_dir = vim.fn.expand("~/.cache/jdtls/workspace/") .. project_name

local config = {
  cmd = {
    "jdtls", -- Assumes jdtls is in your PATH (installed by Mason)
    "-data", workspace_dir,
  },
  root_dir = require("jdtls.setup").find_root({ ".git", "pom.xml", "build.gradle" }),
  settings = {
    java = {
      signatureHelp = { enabled = true },
      contentProvider = { preferred = "fernflower" },
    },
  },
}

require("jdtls").start_or_attach(config)

-- Java-specific mappings
vim.keymap.set("n", "<leader>oi", function() require("jdtls").organize_imports() end, { desc = "Organize Imports" })

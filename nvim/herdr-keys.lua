-- herdr 内なら、この Neovim のペインにフォーカスしている間、同じタブの右のキー表示ペイン (herdr プラグイン shang.keys) を
-- この Neovim の実際のキーマップに切り替え、終了時に戻す
if vim.env.HERDR_TAB_ID and vim.env.HERDR_PANE_ID then
  local dir = (vim.env.XDG_STATE_HOME or vim.fn.expand("~/.local/state")) .. "/herdr/plugins/shang.keys/"
  local file = dir .. "nvim-" .. vim.env.HERDR_PANE_ID .. ".json"
  local function notify()
    local f = io.open(dir .. "pane-" .. vim.env.HERDR_TAB_ID .. ".pid")
    local pid = f and tonumber(f:read("*l"))
    if f then
      f:close()
    end
    -- PID が再利用された別プロセスに送らないよう、キー表示ペインのプロセスか確かめる
    local cmd = pid and io.open("/proc/" .. pid .. "/cmdline")
    if cmd and cmd:read("*a"):find("keys.py", 1, true) then
      vim.uv.kill(pid, "sigusr1")
    end
    if cmd then
      cmd:close()
    end
  end
  local function dump()
    local maps = {}
    for _, mode in ipairs({ "n", "x", "i" }) do
      for _, m in ipairs(vim.api.nvim_get_keymap(mode)) do
        if m.desc and not m.lhs:find("^<Plug>") then
          table.insert(maps, { mode, m.lhs, m.desc })
        end
      end
    end
    -- avante のサイドバー内のキーはバッファローカルなので、読み込み済みなら設定値から渡す
    local avante = package.loaded["avante.config"] and require("avante.config").mappings
    vim.fn.mkdir(dir, "p")
    local f = io.open(file, "w")
    if not f then
      return
    end
    f:write(vim.json.encode({
      pid = vim.fn.getpid(),
      leader = vim.g.mapleader,
      runtime = vim.env.VIMRUNTIME,
      maps = maps,
      avante = avante or vim.empty_dict(),
    }))
    f:close()
    notify()
  end
  vim.schedule(dump)
  vim.api.nvim_create_autocmd("User", {
    pattern = "LazyLoad",
    callback = function(e)
      if e.data == "avante.nvim" then
        vim.schedule(dump)
      end
    end,
  })
  vim.api.nvim_create_autocmd("VimLeavePre", {
    callback = function()
      os.remove(file)
      notify()
    end,
  })
end

# herdr-keys

[herdr](https://herdr.dev) のタブの右側に、いま使えるキーバインドの一覧を常に表示するプラグインです。一覧の下には、キーについて質問できる AI (Claude Code) を置けます。

- シェルなどのペインにフォーカスしているときは **herdr keys**: herdr のキーバインド
- Neovim のペインにフォーカスしているときは **editor keys**: その Neovim のキーマップ (Vim / Avante / NeoVim / LazyVim)
- 下の **keys agent** に「〇〇をするには？」と聞くと、表示中の一覧を見て押すキーを答えます

キーは実際の設定から読み取るので、設定を変えれば表示も変わります。説明は日本語です。

## 前提

- OS: Linux または WSL
- ソフトウェア: [herdr](https://herdr.dev) と [Neovim](https://neovim.io)

作者は WSL 上で、ターミナルに WezTerm、Neovim に LazyVim と avante.nvim を入れた環境で使っています。これと違う環境では、表示が崩れたり、一部が動かなかったりするかもしれません。修正の Pull Request をもらえると嬉しいです。

keys agent は、上のキー一覧に表示している内容をもとに、聞かれたことに答えるだけです。使える権限をファイルの読み取り (Read) に絞っているので、ファイルの編集やコマンドの実行はできませんし、しません。

```
┌─────────────────────────────┬─ herdr keys ──────────────┐
│                             │ prefix = ctrl+b           │
│                             │                           │
│                             │ ペイン                    │
│   作業中のペイン            │   h         左のペインへ  │
│                             │   \         左右に分割    │
│                             │   ...                     │
│                             ├─ keys agent ──────────────┤
│                             │ > ペインを右に分割するには？│
│                             │   Ctrl+b を押してから \   │
└─────────────────────────────┴───────────────────────────┘
```

## 表示される内容

### herdr keys

herdr の既定のキーバインドに、`~/.config/herdr/config.toml` の `[keys]` の上書きを反映したものを、ペイン / タブ / ワークスペース / その他 に分けて表示します。`[[keys.command]]` で追加したキーも `description` 付きで出ます。

### editor keys

vim 初心者が「キーボードだけで作業を完結させる」のに要るキーに絞っています。範囲選択して AI に聞く・直させるといった Avante の操作は優先して載せています。

```
<leader> = Space

Vim
ノーマルモード: 移動
  h           左へ
  j           下へ
  ...
Avante
ビジュアルモード
  <leader>aa  選択範囲を AI に質問
  <leader>ae  選択範囲を AI に修正
  ...
LazyVim
ノーマルモード: バッファ (上部に並ぶファイル)
  H           左のバッファへ
  ...
```

- 見出しは Vim → Avante → NeoVim → LazyVim の順で、その中をモード別 (ノーマル / 挿入 / ビジュアル) に分けています。
- キーはその Neovim に実際に割り当てがあるものだけが出ます。例えば LazyVim の設定でキーを消せば、一覧からも消えます。
- Vim 本体のキーは `$VIMRUNTIME/doc/index.txt` から読み取ります。

## 必要なもの

- herdr 0.9 以上 (Linux または WSL)
- python3 3.11 以上、`less`、`strings` (binutils)、`jq`
- editor keys を使う場合: Neovim 0.10 以上。LazyVim / avante.nvim 向けに作っていますが、どちらも無くても動きます (そのキーが出ないだけです)
- keys agent を使う場合: [Claude Code](https://claude.com/claude-code) (`claude` コマンド) と claude.ai へのログイン

## インストール

### 1. プラグイン

```sh
herdr plugin install shang-shang95/herdr-keys
```

次に herdr を起動したときから、各タブの右にキー一覧と keys agent が開きます。新しく作ったタブにも自動で開きます。

### 2. キーバインド (任意)

一覧や keys agent を閉じたあとで開き直すためのキーです。`~/.config/herdr/config.toml` に追加します。

```toml
[[keys.command]]
key = "prefix+i"
type = "shell"
command = "herdr plugin action invoke open --plugin shang-shang95.herdr-keys"
description = "キー一覧を右に開く"

[[keys.command]]
key = "prefix+a"
type = "shell"
command = "herdr plugin action invoke ask --plugin shang-shang95.herdr-keys"
description = "keys agent を開く"
```

- `prefix+i`: フォーカス中のペインの右にキー一覧を開きます。
- `prefix+a`: キー一覧の下に keys agent を開きます。

どちらも、そのタブに既にあれば何もしません。キーバインドを設定しなくても、herdr のアクション一覧から `Open keys pane` / `Open keys agent` で開けます。

### 3. Neovim (editor keys を使う場合)

[`nvim/herdr-keys.lua`](nvim/herdr-keys.lua) の中身を Neovim の設定に追加します。LazyVim なら `~/.config/nvim/lua/config/autocmds.lua` の末尾に貼り付けます。herdr の外で起動した Neovim では何もしません。

### 4. avante.nvim の選択範囲のキー (任意)

LazyVim の avante extra は `<leader>aa` / `<leader>ae` をノーマルモードにしか割り当てません。範囲選択してから AI に聞く・直させるには、ビジュアルモードにも割り当てます。

```lua
-- ~/.config/nvim/lua/plugins/avante.lua
return {
  {
    "yetone/avante.nvim",
    keys = {
      { "<leader>aa", function() require("avante.api").ask() end, mode = "v", desc = "Ask Avante" },
      { "<leader>ae", function() require("avante.api").edit() end, mode = "v", desc = "Edit Avante" },
    },
  },
}
```

## 使い方

- 一覧はフォーカスすると `j` / `k` でスクロール、`/` で検索できます。`q` で描き直します。
- 一覧や keys agent にフォーカスを移しても、表示はその直前のペインのものから変わりません。
- keys agent には質問を打って Enter を押します。答える前に毎回、表示中の一覧を読みます。

### keys agent にできること

- keys agent が使える道具はファイルの読み取り (Read) だけです。ファイルの編集・コマンドの実行・git の操作はできません。頼まれても、手順を説明するだけです。
- Claude Code のユーザー設定 (フック・プラグイン・MCP) は読み込まず、claude.ai のログインで動きます。
  - `ANTHROPIC_API_KEY` が設定されていても使いません (API の従量課金にならないようにしています)。
- 初回だけ、状態ディレクトリ (`~/.local/state/herdr/plugins/shang-shang95.herdr-keys`) を信頼するかの確認が出ます。
- タブごとに Claude Code が 1 つずつ起動します。待機中はトークンを使いませんが、メモリは使います。

## 仕組み

どちらの一覧も、変化があったときだけ描き直します。定期的に状態を見に行くこと (ポーリング) はしません。

| ファイル | 役割 |
|---|---|
| `herdr-plugin.toml` | プラグインの定義。起動時・`tab.created` で `startup.sh`、`pane.focused` で `focus.sh`、アクション `open` / `ask` |
| `startup.sh` | タブごとにキー一覧と keys agent を開く (既にあれば開かない) |
| `keys.py` | 一覧の表示。`less` で表示し、SIGUSR1 / SIGUSR2 を受けて描き直す |
| `focus.sh` | フォーカスが移ったら、そのタブの一覧に SIGUSR2 を送る。表示するペインが変わったときだけ描き直す (スクロール位置を保つ) |
| `ask.sh` | keys agent (`claude --tools Read`) の起動 |
| `nvim/herdr-keys.lua` | Neovim 側。起動時と avante の読み込み時にキーマップを書き出して SIGUSR1、終了時に消して SIGUSR1 |

状態は `~/.local/state/herdr/plugins/shang-shang95.herdr-keys/` に置かれます。

- `pane-<タブ>.pid`: 一覧のプロセス
- `nvim-<ペイン>.json`: Neovim が書き出したキーマップ
- `view-<タブ>.txt`: 表示中の内容 (keys agent が読む)

## カスタマイズ

表示するキーと説明は `keys.py` の先頭で決めています。

- `NVIM_PICK`: editor keys に載せるキーと説明。`(見出し, [(小見出し, モード, [(キー, 説明)])])` の形です。キーの書き方は次の 3 通りです。
  - `"<leader>aa"`: Neovim のキーマップ
  - `"vim:gg"`: `index.txt` のタグ
  - `"avante:sidebar.close"`: avante の `mappings` の項目
- `HERDR_JA` / `GROUPS`: herdr のアクションの説明と、見出しへの振り分け

変更後は `python3 keys.py --check` で自己チェックできます。

## 注意

- herdr の既定のキーバインドは、herdr 本体に含まれる設定テンプレートから読み取っています。herdr の更新で読み取れなくなった場合は `--check` が失敗します。
- 一覧の幅は約 44 桁を想定しています。説明はそれに合わせて切り詰めて表示します。

## ライセンス

[MIT](LICENSE)

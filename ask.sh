#!/bin/sh
# キー表示ペインの下に常駐する質問用 AI。上に表示中のキーについて答えるだけで、ファイル編集やコマンド実行はさせない (使える道具は Read のみ)
cd "$HERDR_PLUGIN_STATE_DIR" || exit 1
if ! command -v claude >/dev/null; then
  echo "claude が見つからないため質問ペインは使えません"
  exec sleep infinity
fi
view="$HERDR_PLUGIN_STATE_DIR/view-$(printf %s "$HERDR_TAB_ID" | tr : -).txt"
# avante 用の API キーがあると従量課金になるので、claude.ai のログインを使わせる
unset ANTHROPIC_API_KEY
# ユーザー設定 (フック・プラグイン) は読まない。作業ディレクトリは状態ディレクトリなので Read もそこに限られる
exec claude --tools Read --setting-sources project --strict-mcp-config --disable-slash-commands \
  -n "keys agent" --append-system-prompt "あなたは vim 初心者向けのキーバインド相談役です。
ユーザーの画面の上のペインにキーバインド一覧が表示されています。その内容は $view にあり、1 行目が herdr keys (端末 herdr のキー) か editor keys (Neovim/LazyVim/avante のキー) かを示します。
質問のたびに $view を Read して最新の表示を確かめ、「〇〇をするには」に対して押すキーを具体的に答えてください。<leader> は Space です。
一覧に無いキーでも標準の vim / Neovim / LazyVim / avante / herdr のキーで答えられるならそう答え、一覧に無いことを添えてください。
ファイルの編集・コマンドの実行・git の操作はしません。頼まれても手順を説明するだけにしてください。日本語で短く答えてください。"

#!/bin/sh
# タブごとにキー表示ペインとその下の keys agent を開く。起動時: 全タブ / tab.created・アクション: そのタブ
# 引数: なし = 両方、keys = キー表示ペインだけ、ask = keys agent だけ。既に開いているものは開かない
h="$HERDR_BIN_PATH"
if [ "$HERDR_PLUGIN_EVENT" = startup ]; then
  # セッション復元ではペインが中身なし(ただのシェル)で戻るので閉じて開き直す
  for p in $("$h" pane list | jq -r '.result.panes[] | select(.label == "herdr keys" or .label == "editor keys" or .label == "keys agent") | .pane_id'); do
    "$h" pane close "$p" >/dev/null
  done
  tabs=$("$h" pane list | jq -r '[.result.panes[].tab_id] | unique[]')
else
  tabs=$HERDR_TAB_ID
fi
# そのタブで条件に合うペイン (無ければ空)
find() {
  "$h" pane list | jq -r --arg t "$1" "[.result.panes[] | select(.tab_id == \$t) | select($2)][0].pane_id // empty"
}
keys='.label == "herdr keys" or .label == "editor keys"'
for tab in $tabs; do
  id=$(find "$tab" "$keys")
  if [ "$1" != ask ] && [ -z "$id" ]; then
    # 分割元: そのタブのフォーカス中ペイン (無ければ先頭)
    target=$(find "$tab" '.focused')
    [ -n "$target" ] || target=$(find "$tab" true)
    id=$("$h" plugin pane open --plugin shang.keys --entrypoint keys --target-pane "$target" \
      --placement split --direction right --no-focus | jq -r '.result.plugin_pane.pane.pane_id')
    # 分割比 0.5 -> 0.85 (幅約15%)
    "$h" pane resize --pane "$id" --direction right --amount 0.35 >/dev/null
  fi
  if [ "$1" != keys ] && [ -z "$(find "$tab" '.label == "keys agent"')" ]; then
    # キー表示ペインの下に開く (無ければフォーカス中ペインの下)
    [ -n "$id" ] || id=$(find "$tab" '.focused')
    "$h" plugin pane open --plugin shang.keys --entrypoint ask --target-pane "$id" \
      --placement split --direction down --no-focus >/dev/null
  fi
done

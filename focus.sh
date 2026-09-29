#!/bin/sh
# フォーカスが移ったら、そのタブのキー表示ペインに知らせる (keys.py が対象のペインが変わったときだけ描き直す)
tab=$("$HERDR_BIN_PATH" pane list | jq -r '.result.panes[] | select(.focused) | .tab_id')
pid=$(cat "$HERDR_PLUGIN_STATE_DIR/pane-$tab.pid" 2>/dev/null) || exit 0
# PID が再利用された別プロセスに送らない
grep -q keys.py "/proc/$pid/cmdline" 2>/dev/null && kill -USR2 "$pid"

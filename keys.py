"""キー表示ペイン。通常は herdr の実際のキーバインド (バイナリ内蔵の既定値 + config.toml の上書き) を、
同じタブで Neovim が起動中はその Neovim の実際のキーマップ (vim / neovim / LazyVim / avante) を表示する。
Neovim 側 (nvim/herdr-keys.lua) が状態ファイルを書いて SIGUSR1 を送ると描き直す。
キーは実際の設定から引き、説明だけここの日本語訳を使う (訳が無い herdr のアクションは英語のまま出す)。"""
import json
import os
import re
import shutil
import subprocess
import signal
import sys
import tomllib
import unicodedata

BIN = os.environ.get("HERDR_BIN_PATH") or shutil.which("herdr")
CONFIG = os.path.expanduser("~/.config/herdr/config.toml")
STATE = os.environ.get("HERDR_PLUGIN_STATE_DIR") or os.path.expanduser("~/.local/state/herdr/plugins/shang.keys")
TAB = os.environ.get("HERDR_TAB_ID", "")
PANE = os.environ.get("HERDR_PANE_ID")
PIDFILE = os.path.join(STATE, f"pane-{TAB}.pid")
LABELS = ("herdr keys", "editor keys", "keys agent")  # このプラグインのペイン
# 下の質問ペイン (ask.sh) の AI が読む、いま表示している内容
VIEWFILE = os.path.join(STATE, f"view-{TAB.replace(':', '-')}.txt")  # ":" は Read がパスとして扱いにくい
# navigate_* はナビゲーションモード内のキー、remote_image_paste は --remote 時のみなので表示しない
SKIP = re.compile(r"^navigate_|^remote_image_paste$")
GROUPS = [
    ("ペイン", re.compile(r"pane|split|zoom|resize|copy_mode|scrollback")),
    ("タブ", re.compile(r"tab")),
    ("ワークスペース", re.compile(r"workspace|worktree|goto|sidebar|detach|agent")),
    ("その他", re.compile(r"")),
]
HERDR_JA = {
    "rename_pane": "ペイン名を変更", "edit_scrollback": "履歴をエディタで開く",
    "focus_pane_left": "左のペインへ", "focus_pane_down": "下のペインへ",
    "focus_pane_up": "上のペインへ", "focus_pane_right": "右のペインへ",
    "cycle_pane_next": "次のペインへ", "cycle_pane_previous": "前のペインへ",
    "split_vertical": "左右に分割", "split_horizontal": "上下に分割", "close_pane": "ペインを閉じる",
    "zoom": "ペインを最大化 / 戻す", "resize_mode": "サイズ変更モード", "copy_mode": "コピーモード",
    "swap_pane_left": "左のペインと入替", "swap_pane_down": "下のペインと入替",
    "swap_pane_up": "上のペインと入替", "swap_pane_right": "右のペインと入替",
    "new_tab": "新しいタブ", "rename_tab": "タブ名を変更", "previous_tab": "前のタブへ",
    "next_tab": "次のタブへ", "close_tab": "タブを閉じる",
    "detach": "デタッチ", "workspace_picker": "ワークスペース一覧", "goto": "移動先を選ぶ",
    "new_workspace": "新しいワークスペース", "new_worktree": "新しい worktree",
    "rename_workspace": "ワークスペース名を変更", "close_workspace": "ワークスペースを閉じる",
    "toggle_sidebar": "サイドバー表示切替",
    "help": "ヘルプ", "settings": "設定", "reload_config": "設定を再読込", "open_notification_target": "通知元を開く",
    # 以下は既定では割り当てなし (config.toml で割り当てたときに表示される)
    "open_worktree": "worktree を開く", "remove_worktree": "worktree を削除",
    "previous_workspace": "前のワークスペースへ", "next_workspace": "次のワークスペースへ",
    "previous_agent": "前のエージェントへ", "next_agent": "次のエージェントへ", "focus_agent": "エージェントへ移動",
    "move_tab_previous": "タブを左へ移動", "move_tab_next": "タブを右へ移動",
    "switch_tab": "タブを切替", "switch_workspace": "ワークスペースを切替", "last_pane": "直前のペインへ",
    "resize_pane_left": "ペインを左へ広げる", "resize_pane_down": "ペインを下へ広げる",
    "resize_pane_up": "ペインを上へ広げる", "resize_pane_right": "ペインを右へ広げる",
}
INDEXED_JA = {"tab": "タブ", "workspace": "ワークスペース", "pane": "ペイン"}
# Neovim は「キーボードだけで完結する」のに要るものに絞る。(見出し, [(小見出し, モード, [(キー, 説明)])])
# キーの書き方:
#   "<leader>aa" など = Neovim のキーマップの lhs。そのモードに実際に割り当てがあるものだけ出す
#   "avante:x.y" = avante の設定 mappings.x.y (サイドバー内などバッファローカルのキー)
#   "vim:tag" = $VIMRUNTIME/doc/index.txt のタグ (vim 本体のキー)
NVIM_PICK = [
    ("Vim", [
        ("ノーマルモード: 移動", "n", [
            ("vim:h", "左へ"), ("vim:j", "下へ"), ("vim:k", "上へ"), ("vim:l", "右へ"),
            ("vim:w", "次の単語へ"), ("vim:b", "前の単語へ"), ("vim:0", "行頭へ"), ("vim:$", "行末へ"),
            ("vim:gg", "先頭行へ"), ("vim:G", "最終行へ"), ("vim:CTRL-D", "半画面下へ"), ("vim:CTRL-U", "半画面上へ"),
            ("vim:/", "ファイル内を検索"), ("vim:n", "次の検索結果へ")]),
        ("ノーマルモード: 編集", "n", [
            ("vim:i", "カーソル位置から入力"), ("vim:A", "行末から入力"), ("vim:o", "下に行を足して入力"),
            ("vim:x", "1 文字削除"), ("vim:dd", "行を削除"), ("vim:yy", "行をコピー"), ("vim:p", "貼り付け"),
            ("vim:u", "元に戻す"), ("vim:CTRL-R", "やり直す"), ("vim:.", "直前の変更を繰り返す"),
            ("vim:v", "文字単位で選択開始"), ("vim:V", "行単位で選択開始")]),
        ("ノーマルモード: タブ", "n", [("vim:gt", "次のタブへ"), ("vim:gT", "前のタブへ")]),
        ("挿入モード", "i", [("vim:i_<Esc>", "入力を終える"), ("vim:i_CTRL-W", "前の単語を削除")]),
        ("ビジュアルモード", "x", [
            ("vim:v_iw", "単語を選択"), ("vim:v_iquote", "\"…\" の中を選択"), ("vim:v_ib", "(…) の中を選択"),
            ("vim:v_y", "コピー"), ("vim:v_d", "削除"), ("vim:v_<Esc>", "選択をやめる")]),
    ]),
    ("Avante", [
        ("ノーマルモード", "n", [
            ("<leader>aa", "AI に質問"), ("<leader>ac", "チャットを開く"), ("<leader>an", "新しいチャット"),
            ("<leader>at", "サイドバー表示切替"), ("<leader>af", "サイドバーへ移動"), ("<leader>as", "応答を止める")]),
        ("ビジュアルモード", "x", [("<leader>aa", "選択範囲を AI に質問"), ("<leader>ae", "選択範囲を AI に修正")]),
        ("サイドバー: ノーマルモード", None, [
            ("avante:submit.normal", "送信"), ("avante:sidebar.switch_windows", "欄を移動"),
            ("avante:sidebar.add_file", "ファイルを追加"), ("avante:sidebar.apply_cursor", "カーソル位置の提案を適用"),
            ("avante:sidebar.apply_all", "提案をすべて適用"), ("avante:sidebar.close", "閉じる")]),
        ("サイドバー: 挿入モード", None, [("avante:submit.insert", "送信")]),
        ("差分: ノーマルモード", None, [
            ("avante:diff.theirs", "AI の案を採用"), ("avante:diff.ours", "元のコードを採用"),
            ("avante:diff.next", "次の差分へ")]),
    ]),
    ("NeoVim", [
        ("ノーマルモード", "n", [("gcc", "行のコメント切替"), ("grn", "名前を一括変更"),
                                  ("gra", "修正候補を出す"), ("grr", "参照箇所の一覧")]),
        ("ビジュアルモード", "x", [("gc", "選択範囲のコメント切替"), ("gra", "修正候補を出す")]),
    ]),
    ("LazyVim", [
        ("ノーマルモード", "n", [
            ("s", "画面内の任意の位置へ"),
            ("<leader><leader>", "ファイルを探して開く"), ("<leader>/", "プロジェクト内を文字列検索"),
            ("<leader>e", "ファイルツリー"), ("<C-S>", "保存"), ("<leader>qq", "すべて終了"),
            ("<C-H>", "左のウィンドウへ"), ("<C-J>", "下のウィンドウへ"),
            ("<C-K>", "上のウィンドウへ"), ("<C-L>", "右のウィンドウへ"),
            ("<leader>|", "左右に分割"), ("<leader>-", "上下に分割"), ("<leader>wd", "ウィンドウを閉じる"),
            ("]d", "次のエラー・警告へ"), ("<leader>cd", "行のエラー・警告を表示"), ("<leader>cf", "整形"),
            ("<C-/>", "ターミナル"), ("<leader>sk", "キーマップを検索")]),
        # 上部にタブのように並ぶのはバッファ (開いているファイル)。タブはウィンドウの配置ごと切り替える別物
        ("ノーマルモード: バッファ (上部に並ぶファイル)", "n", [
            ("<leader>fn", "新しいファイル"), ("<leader>,", "一覧から選ぶ"), ("<leader>bj", "表示中から選ぶ"),
            ("H", "左のバッファへ"), ("L", "右のバッファへ"), ("[B", "並びを左へ動かす"), ("]B", "並びを右へ動かす"),
            ("<leader>bd", "閉じる"), ("<leader>bo", "ほかをすべて閉じる"),
            ("<leader>bl", "左側をすべて閉じる"), ("<leader>br", "右側をすべて閉じる"),
            ("<leader>bp", "ピン留め切替"), ("<leader>bP", "ピン留め以外を閉じる")]),
        ("ノーマルモード: タブ (ウィンドウ配置ごと)", "n", [
            ("<leader><Tab><Tab>", "新しいタブ"), ("<leader><Tab>]", "次のタブへ"), ("<leader><Tab>[", "前のタブへ"),
            ("<leader><Tab>f", "最初のタブへ"), ("<leader><Tab>l", "最後のタブへ"),
            ("<leader><Tab>d", "タブを閉じる"), ("<leader><Tab>o", "ほかのタブを閉じる")]),
        ("挿入モード", "i", [("<C-S>", "保存")]),
    ]),
]


def defaults():
    """バイナリ内蔵の設定テンプレートの [keys] 節から '# action = "key"' を拾う。"""
    text = subprocess.run(["strings", BIN], capture_output=True, text=True).stdout
    section = re.search(r"^\[keys\]$(.*?)^\[server\]$", text, re.M | re.S)
    if not section:
        return {}
    # 後ろにある [[keys.command]] の記入例は拾わない
    body = section.group(1).split("# [[keys.command]]")[0]
    return dict(re.findall(r'^# ([a-z_]+) = "([^"]*)"[ \t]*(?:#.*)?$', body, re.M))


def fmt(key):
    parts = key.split("+")
    if parts[0] == "prefix":
        parts = parts[1:]
    names = {"shift": "S", "ctrl": "C", "alt": "M", "minus": "-"}
    parts = [names.get(p, p) for p in parts]
    return "".join(p + "-" if p in ("S", "C", "M") else p for p in parts)


def load():
    try:
        with open(CONFIG, "rb") as f:
            keys = tomllib.load(f).get("keys", {})
    except FileNotFoundError:
        keys = {}  # config.toml が無ければ既定のキーだけ
    except (OSError, tomllib.TOMLDecodeError) as e:
        return None, [], f"config.toml を読めません: {e}"
    binds = defaults()
    # command ([[keys.command]]) と indexed は下で別に扱う
    binds.update({k: v for k, v in keys.items() if isinstance(v, str) or k != "command" and isinstance(v, list)})
    prefix = binds.pop("prefix", "ctrl+b")
    rows = []
    for action, key in binds.items():
        key = " / ".join(key) if isinstance(key, list) else key
        if key and not SKIP.search(action):
            rows.append((action, fmt(key), HERDR_JA.get(action, action.replace("_", " "))))
    for cmd in keys.get("command", []):
        rows.append(("command", fmt(cmd.get("key", "")), cmd.get("description") or cmd.get("command", "")))
    for kind, mod in keys.get("indexed", {}).items():
        if mod:
            rows.append((kind, fmt(mod + "+1..9"), f"{INDEXED_JA.get(kind, kind)}を番号で切替"))
    return prefix, rows, None


def width(s):
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


def section(title, items, gap="\n"):
    # 細いペインで折り返すと読みにくいので、説明は 1 行に収まるよう切り詰める (幅は描き直し時点のもの)
    cols = shutil.get_terminal_size().columns
    out = [f"{gap}\033[1m{title}\033[0m\n"]
    for k, label in items:
        room = cols - 3 - max(11, len(k))
        if width(label) > room:
            while label and width(label) > room - 1:
                label = label[:-1]
            label += "…"
        out.append(f"  \033[36m{k:<11}\033[0m {label}\n")
    return out


def render_herdr():
    prefix, rows, err = load()
    if err:
        return err + "\n"
    out = [f"\033[2mprefix = {prefix}\033[0m\n"]
    seen = set()
    for name, pat in GROUPS:
        items = [r for r in rows if r[0] not in seen and pat.search(r[0])]
        if items:
            seen.update(r[0] for r in items)
            out += section(name, [(k, label) for _, k, label in items])
    return "".join(out)


def vim_index(runtime):
    """index.txt の表を {タグ: キー} にする (例: "dd" -> "dd", "CTRL-D" -> "C-D")。"""
    try:
        with open(os.path.join(runtime, "doc", "index.txt")) as f:
            text = f.read()
    except OSError:
        return {}
    index = {}
    for tag, key in re.findall(r"^\|([^|]+)\|\t+([^\t]+?)\t", text, re.M):
        # 同じタグが複数の節にあれば最初のもの。レジスタ指定 ["x] は省く
        index.setdefault(tag, re.sub(r'^\["x\]', "", key).replace("CTRL-", "C-"))
    return index


def flatten(d, path=()):
    for k, v in d.items():
        if isinstance(v, dict):
            yield from flatten(v, path + (k,))
        else:
            yield ".".join(path + (k,)), " / ".join(v) if isinstance(v, list) else v


def render_nvim(data):
    leader = data.get("leader") or "\\"
    maps = {}
    for mode, key, _ in data.get("maps", []):
        maps.setdefault(key.replace(leader, "<leader>"), set()).add(mode)
    avante = dict(flatten(data.get("avante") or {}))
    vim = vim_index(data.get("runtime", ""))

    def row(pick, label, mode):
        kind, _, name = pick.rpartition(":")
        if kind == "avante":
            return (avante[name], label) if name in avante else None
        if kind == "vim":
            return (vim[name], label) if name in vim else None
        return (pick, label) if mode in maps.get(pick, ()) else None

    names = {" ": "Space", "\\": "\\", ",": ","}
    out = [f"\033[2m<leader> = {names.get(leader, leader)}\033[0m\n"]
    for title, groups in NVIM_PICK:
        out.append(f"\n\033[1;4m{title}\033[0m\n")
        for sub, mode, picks in groups:
            rows = [r for r in (row(k, label, mode) for k, label in picks) if r]
            if rows:
                out += section(sub, rows, gap="")
    return "".join(out)


def focused(last=[None]):
    """このタブでフォーカス中のペイン。このプラグインのペイン (一覧を読んでいる・質問している) なら直前のペインのまま。"""
    try:
        panes = json.loads(subprocess.run([BIN, "pane", "list"], capture_output=True, text=True).stdout)["result"]["panes"]
    except (OSError, ValueError, KeyError, TypeError):
        return last[0]
    mine = [p for p in panes if p["tab_id"] == TAB and p.get("label") not in LABELS]
    for p in mine:
        if p.get("focused"):
            last[0] = p["pane_id"]
    # 別のタブを見ている間に開いたときは、このタブの先頭のペイン
    if not any(p["pane_id"] == last[0] for p in mine):
        last[0] = mine[0]["pane_id"] if mine else None
    return last[0]


def nvim_state(pane):
    """そのペインで起動中の Neovim が書いた状態。プロセスが既に無ければ (強制終了など) 無視する。"""
    try:
        with open(os.path.join(STATE, f"nvim-{pane}.json")) as f:
            data = json.load(f)
        os.kill(data["pid"], 0)
        return data
    except (OSError, ValueError, KeyError, TypeError):
        return None


shown = [None]  # いま表示しているのがどのペインのキーか


def render():
    shown[0] = focused()
    data = nvim_state(shown[0])
    # ペインのタイトルも表示内容に合わせる (startup.sh はどちらのタイトルでも自分のペインとみなす)
    if PANE:
        subprocess.run([BIN, "pane", "rename", PANE, "editor keys" if data else "herdr keys"], capture_output=True)
    text = render_nvim(data) if data else render_herdr()
    with open(VIEWFILE, "w") as f:
        f.write(("editor keys" if data else "herdr keys") + "\n" + re.sub(r"\x1b\[[0-9;]*m", "", text))
    return text


def main():
    os.makedirs(STATE, exist_ok=True)
    with open(PIDFILE, "w") as f:
        f.write(str(os.getpid()))
    less = [None]

    def reload(*_):
        if less[0] and less[0].poll() is None:
            less[0].terminate()

    def quit(*_):
        reload()
        try:
            if open(PIDFILE).read() == str(os.getpid()):
                os.remove(PIDFILE)
        except OSError:
            pass
        sys.exit()

    def refocus(*_):
        # フォーカスが移ったとき (focus.sh)。対象のペインが変わったときだけ描き直す (スクロール位置を保つ)
        if focused() != shown[0]:
            reload()

    signal.signal(signal.SIGUSR1, reload)
    signal.signal(signal.SIGUSR2, refocus)
    signal.signal(signal.SIGTERM, quit)
    signal.signal(signal.SIGHUP, quit)
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    if not shutil.which("less"):
        sys.stdout.write(render())
        sys.stdout.flush()
        while True:
            signal.pause()
    # less で表示 (フォーカスすると j/k でスクロール)。-Q で端に来てもベルを鳴らさない、-c で上から描く (短い内容が下に寄らない)。q (終了) か SIGUSR1 で描き直す
    while True:
        less[0] = subprocess.Popen(["less", "-R", "-Q", "-c", "-~", "-Ps/ search  q reload"], stdin=subprocess.PIPE, text=True)
        try:
            less[0].stdin.write(render())
            less[0].stdin.close()
        except BrokenPipeError:
            pass
        less[0].wait()


if __name__ == "__main__":
    if sys.argv[1:] == ["--check"]:
        assert fmt("prefix+shift+tab") == "S-tab" and fmt("prefix+minus") == "-" and fmt("ctrl+alt+x") == "C-M-x"
        d = defaults()
        assert d.get("new_tab") and "type" not in d and "key" not in d, d
        # herdr の既定アクションに訳の漏れが無いか (herdr の更新でアクションが増えたら気づける)
        untranslated = [a for a in d if a != "prefix" and not SKIP.search(a) and a not in HERDR_JA]
        assert not untranslated, untranslated
        rt = subprocess.run(["nvim", "--clean", "--headless", "-c", "lua io.write(vim.env.VIMRUNTIME)", "-c", "qa"],
                            capture_output=True, text=True).stdout
        idx = vim_index(rt)
        assert idx["dd"] == "dd" and idx["CTRL-D"] == "C-D" and idx["v_ib"] == "ib", idx.get("dd")
        # 選んだ vim: タグが index.txt に実在するか (打ち間違いの検出)
        missing = [p for _, groups in NVIM_PICK for _, _, picks in groups for p, _ in picks if p.startswith("vim:") and p[4:] not in idx]
        assert not missing, missing
        text = render_nvim({"leader": " ", "runtime": rt, "maps": [["n", " aa", "Ask"], ["x", " aa", "Ask"],
                            ["n", " ae", "Edit"], ["n", " ff", "Find"]],
                            "avante": {"ask": "<leader>aa", "sidebar": {"close": ["q"], "add_file": "@"}}})
        plain = re.sub(r"\033\[[0-9;]*m", "", text)
        # 割り当てのあるモードの小見出しにだけ出る (<leader>ae は n だけなのでビジュアルには出ない)
        assert "選択範囲を AI に質問" in plain and "選択範囲を AI に修正" not in plain, plain
        assert plain.index("Vim") < plain.index("Avante") < plain.index("NeoVim") < plain.index("LazyVim")
        assert "ノーマルモード: 移動" in plain and "ビジュアルモード" in plain
        assert "<leader> = Space" in plain and "閉じる" in plain and "ファイルを探して" not in plain and "先頭行へ" in plain
        assert width("あa") == 3
        # 実際の config.toml が読めて、[[keys.command]] は説明付きで出る
        prefix, rows, err = load()
        assert not err and all(isinstance(k, str) for _, k, _ in rows), err
        print("ok")
        sys.exit()
    main()

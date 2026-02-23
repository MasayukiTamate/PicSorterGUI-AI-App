'''
PicSorterGUI メインアプリケーション (UI)
AI Visual Sorting に特化した画像整理ツール
'''
import os
import sys
import tkinter as tk

if getattr(sys, 'frozen', False):
    app_dir = os.path.dirname(sys.executable)
    sys.path.insert(0, app_dir)

from tkinter import filedialog, messagebox
from PIL import ImageTk, Image
from tkinterdnd2 import *
import shutil
import threading

from lib.PicSorterGUILogger import setup_logging, get_logger
setup_logging(debug_mode=False)
logger = get_logger(__name__)

from PicSorterGUILogic import (
    load_config, save_config, ImageDataManager, PicController,
    calculate_file_hash, VectorBatchProcessor,
    open_visual_sort_window, get_vector_data_info,
    clear_vectors, clear_analysis_cache, check_model_cached
)
from lib.PicSorterGUILib import GetKoFolder, GetGazoFiles
from lib.PicSorterGUIState import get_app_state
from lib.config_defaults import (
    AI_MODELS, DEFAULT_AI_MODEL,
)
from lib.PicSorterGUIWidgets import SplashWindow, ModelSelectDialog, AutoSortDialog
from lib.PicSorterGUIAI import VectorEngine, apply_model_cache_dir

# --- アプリケーション状態の初期化 ---
app_state = get_app_state()

# --- スプラッシュ表示 ---
koRoot = TkinterDnD.Tk()
koRoot.withdraw()

_icon_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
_icon_path = os.path.join(_icon_dir, 'PicClass.ico')
if os.path.exists(_icon_path):
    koRoot.iconbitmap(default=_icon_path)
splash = SplashWindow(koRoot)

def close_splash():
    try:
        splash.close()
        koRoot.deiconify()
        if app_state.topmost:
            koRoot.attributes("-topmost", True)
    except:
        pass
    # スプラッシュ後にモデル確認
    koRoot.after(100, check_model_on_startup)

koRoot.after(1500, close_splash)


def check_model_on_startup():
    """起動時にAIモデルがダウンロード済みか確認し、なければ選択ダイアログを表示"""
    current_model = app_state.ai_model
    # VectorEngine にモデルキーを設定（まだインスタンスは作らない）
    VectorEngine._current_model_key = current_model
    if not check_model_cached(current_model):
        open_model_select_dialog()


def open_model_select_dialog():
    """モデル選択ダイアログを開く"""
    current_model = app_state.ai_model

    def on_model_selected(new_key):
        old_key = app_state.ai_model
        if new_key != old_key:
            if messagebox.askyesno("確認",
                    "モデルを変更すると既存のベクトルデータと分析キャッシュがリセットされます。\n\nよろしいですか？"):
                clear_vectors()
                clear_analysis_cache()
                VectorEngine.reset_instance()
                logger.info(f"AIモデル変更: {old_key} -> {new_key}")
            else:
                return

        # 設定を保存
        app_state.ai_model = new_key
        VectorEngine._current_model_key = new_key
        cfg = app_state.to_dict()
        save_config(cfg["last_folder"], cfg.get("geometries", {}), cfg["settings"])
        app_state.from_dict(cfg)

        # VectorEngine をリセットして新モデルで初期化準備
        VectorEngine.reset_instance()

        update_model_info()
        update_vector_info()

    ModelSelectDialog(koRoot, current_model, on_select=on_model_selected)

# --- 設定の読み込みと初期化 ---
try:
    CONFIG_DATA = load_config()
    logger.info(f"設定ファイル読み込み成功: {CONFIG_DATA.get('last_folder')}")
    app_state.from_dict(CONFIG_DATA)
    apply_model_cache_dir()  # 保存済みの格納先を TORCH_HOME に適用
except Exception as e:
    logger.error(f"設定ファイル読み込み失敗: {e}")
    messagebox.showerror("エラー", f"設定ファイルの読み込みに失敗しました:\n{e}")
    CONFIG_DATA = {
        "last_folder": os.getcwd(),
        "geometries": {},
        "settings": {}
    }
    app_state.current_folder = os.getcwd()

DEFOLDER = app_state.current_folder
SAVED_GEOS = app_state.window_geometries


# --- 共通のUI更新処理 ---
def on_app_state_changed(event_name, data):
    try:
        if event_name == "folder_changed":
            refresh_ui(data["path"])
    except Exception as e:
        logger.error(f"UI更新コールバックエラー ({event_name}): {e}", exc_info=True)

app_state.register_callback(on_app_state_changed)


def refresh_ui(new_path):
    global DEFOLDER
    if not new_path or not os.path.exists(new_path):
        logger.warning(f"パスが存在しません: {new_path}")
        return

    DEFOLDER = new_path

    try:
        all_items = os.listdir(DEFOLDER)
        folders = GetKoFolder(all_items, DEFOLDER)
        files = GetGazoFiles(all_items, DEFOLDER)
        logger.info(f"UI更新: {DEFOLDER} (フォルダ:{len(folders)}件, ファイル:{len(files)}件)")
    except Exception as e:
        logger.error(f"再読み込みエラー: {e}", exc_info=True)
        messagebox.showerror("エラー", f"フォルダの読み込みに失敗しました:\n{e}")
        return

    app_state.set_current_files(files)
    app_state.set_current_folders(folders)

    data_manager.SetGazoFiles(files, DEFOLDER)
    pic_controller.SetFolder(DEFOLDER)

    koRoot.title("PicSorterGUI - " + DEFOLDER)
    save_config(DEFOLDER)
    try:
        update_vector_info()
    except Exception:
        pass


# --- メイン処理 ---
koRoot.attributes("-topmost", True)
koRoot.title("PicSorterGUI")

# 実体生成
data_manager = ImageDataManager(DEFOLDER)
pic_controller = PicController(koRoot, DEFOLDER)
koRoot.attributes("-topmost", app_state.topmost)


def execute_move(file_path, dest_folder, refresh=True):
    if not dest_folder or not os.path.exists(dest_folder):
        logger.error(f"移動先フォルダが無効: {dest_folder}")
        messagebox.showerror("エラー", "移動先フォルダが正しく登録されていません。")
        return
    try:
        filename = os.path.basename(file_path)
        shutil.move(file_path, os.path.join(dest_folder, filename))
        logger.info(f"ファイル移動成功: {filename} -> {dest_folder}")
        if refresh:
            refresh_ui(DEFOLDER)
    except FileNotFoundError:
        messagebox.showerror("エラー", f"ファイルが見つかりません: {os.path.basename(file_path)}")
    except PermissionError:
        messagebox.showerror("エラー", f"ファイルを移動する権限がありません: {os.path.basename(file_path)}")
    except Exception as e:
        logger.error(f"ファイル移動エラー: {file_path} -> {dest_folder}", exc_info=True)
        if messagebox.askyesno("失敗",
                f"移動中にエラー: {e}\n\nエラーを報告しますか？"):
            send_error_report(f"ファイル移動エラー: {file_path} -> {dest_folder}\n{e}")


pic_controller.set_move_callback(execute_move)
pic_controller.set_refresh_callback(refresh_ui)


def on_closing_main():
    try:
        app_state.set_window_geometry("main", koRoot.winfo_geometry())
        app_state.set_topmost(koRoot.attributes("-topmost"))

        config_to_save = app_state.to_dict()
        save_config(config_to_save["last_folder"], config_to_save["geometries"], config_to_save["settings"])

        logger.info("アプリケーション終了: 設定を保存しました")
    except Exception as e:
        logger.error(f"終了処理エラー: {e}", exc_info=True)

    koRoot.destroy()
    sys.exit()


def safe_select_folder():
    prev_state = koRoot.attributes("-topmost")
    koRoot.attributes("-topmost", False)
    path = filedialog.askdirectory(title="画像フォルダを選択してください")
    koRoot.attributes("-topmost", prev_state)
    return path


# --- メニュー ---
menubar = tk.Menu(koRoot)
koRoot.config(menu=menubar)

# ファイルメニュー
file_menu = tk.Menu(menubar, tearoff=0)
menubar.add_cascade(label="ファイル(F)", menu=file_menu)
file_menu.add_command(label="フォルダを開く...", command=lambda: refresh_ui(safe_select_folder()))

def open_explorer():
    try:
        os.startfile(DEFOLDER)
    except Exception as e:
        messagebox.showerror("エラー", f"エクスプローラーを開けませんでした: {e}")

file_menu.add_command(label="エクスプローラーで開く(E)", command=open_explorer)
file_menu.add_separator()
file_menu.add_command(label="終了(X)", command=on_closing_main)

# 設定メニュー
config_menu = tk.Menu(menubar, tearoff=0)
menubar.add_cascade(label="設定(S)", menu=config_menu)
config_menu.add_command(label="常に最前面(T) ON/OFF", command=lambda: koRoot.attributes("-topmost", not koRoot.attributes("-topmost")))
config_menu.add_separator()

# 画像表示サイズ設定ダイアログ
def open_image_size_settings():
    win = tk.Toplevel(koRoot)
    win.title("画像表示サイズ設定")
    win.attributes("-topmost", True)

    min_w = tk.IntVar(value=app_state.image_min_width)
    min_h = tk.IntVar(value=app_state.image_min_height)
    max_w = tk.IntVar(value=app_state.image_max_width)
    max_h = tk.IntVar(value=app_state.image_max_height)

    from lib.config_defaults import MIN_IMAGE_SIZE_LIMIT, MAX_IMAGE_SIZE_LIMIT

    tk.Label(win, text="最小幅 (ピクセル):").grid(row=0, column=0, sticky="w", padx=10, pady=5)
    tk.Spinbox(win, from_=MIN_IMAGE_SIZE_LIMIT, to=MAX_IMAGE_SIZE_LIMIT,
               textvariable=min_w, width=10).grid(row=0, column=1, padx=10, pady=5)

    tk.Label(win, text="最小高さ (ピクセル):").grid(row=1, column=0, sticky="w", padx=10, pady=5)
    tk.Spinbox(win, from_=MIN_IMAGE_SIZE_LIMIT, to=MAX_IMAGE_SIZE_LIMIT,
               textvariable=min_h, width=10).grid(row=1, column=1, padx=10, pady=5)

    tk.Label(win, text="最大幅 (0=画面の80%):").grid(row=2, column=0, sticky="w", padx=10, pady=5)
    tk.Spinbox(win, from_=0, to=MAX_IMAGE_SIZE_LIMIT,
               textvariable=max_w, width=10).grid(row=2, column=1, padx=10, pady=5)

    tk.Label(win, text="最大高さ (0=画面の80%):").grid(row=3, column=0, sticky="w", padx=10, pady=5)
    tk.Spinbox(win, from_=0, to=MAX_IMAGE_SIZE_LIMIT,
               textvariable=max_h, width=10).grid(row=3, column=1, padx=10, pady=5)

    def on_ok():
        app_state.set_image_size_limits(
            min_w.get(), min_h.get(), max_w.get(), max_h.get()
        )
        cfg_all = app_state.to_dict()
        save_config(cfg_all["last_folder"], cfg_all.get("geometries", {}), cfg_all["settings"])
        win.destroy()

    btn_frame = tk.Frame(win)
    btn_frame.grid(row=4, column=0, columnspan=2, pady=10)
    tk.Button(btn_frame, text="OK", width=10, command=on_ok).pack(side=tk.LEFT, padx=5)
    tk.Button(btn_frame, text="キャンセル", width=10, command=win.destroy).pack(side=tk.LEFT, padx=5)


config_menu.add_command(label="画像表示サイズ設定...", command=open_image_size_settings)
config_menu.add_separator()

# AIベクトル更新（旧ツールメニューから移動）
processor = None
def run_vector_update():
    global processor
    if processor and processor.is_alive():
        messagebox.showinfo("情報", "既にバックグラウンドで処理中です。")
        return

    msg = "AI(MobileNetV3)を使って画像のベクトル化を行います。\n処理はバックグラウンドで行われます。\n\n開始しますか？"
    if not messagebox.askyesno("確認", msg):
        return

    def on_progress(current, total, filename):
        koRoot.after(0, lambda: koRoot.title(f"PicSorterGUI - {current}/{total} {filename} を解析中..."))

    def on_finish(message):
        def _finish_ui():
            koRoot.title(f"PicSorterGUI - {DEFOLDER}")
            messagebox.showinfo("完了", message)
        koRoot.after(0, _finish_ui)

    processor = VectorBatchProcessor(DEFOLDER, on_progress, on_finish)
    processor.start()

config_menu.add_command(label="AIベクトルを更新・作成", command=run_vector_update)
config_menu.add_command(label="AIモデル変更...", command=open_model_select_dialog)

# ヘルプメニュー
help_menu = tk.Menu(menubar, tearoff=0)
menubar.add_cascade(label="ヘルプ(H)", menu=help_menu)

FEEDBACK_EMAIL = "tamaya2473616@gmail.com"


def open_send_message_dialog(subject_prefix="", body_prefix="", attach_log=False):
    """メッセージ送信ダイアログを開く"""
    import urllib.parse
    import webbrowser
    from lib.PicSorterGUILogger import get_full_log_path, get_log_dir

    win = tk.Toplevel(koRoot)
    win.title("メッセージを送信")
    win.geometry("480x420")
    win.attributes("-topmost", True)
    win.resizable(True, True)
    win.transient(koRoot)

    tk.Label(win, text=f"送信先: {FEEDBACK_EMAIL}",
             font=("MS Gothic", 8), fg="#888888").pack(anchor="w", padx=10, pady=(8, 0))

    # 件名
    tk.Label(win, text="件名:", font=("MS Gothic", 9)).pack(anchor="w", padx=10, pady=(8, 2))
    var_subject = tk.StringVar(value=subject_prefix or "[PicSorterGUI] ")
    tk.Entry(win, textvariable=var_subject, font=("MS Gothic", 9)).pack(
        fill=tk.X, padx=10)

    # ログ添付チェック
    var_attach_log = tk.BooleanVar(value=attach_log)
    log_path = get_full_log_path()

    if log_path and os.path.exists(log_path):
        log_frame = tk.Frame(win)
        log_frame.pack(fill=tk.X, padx=10, pady=(6, 0))
        tk.Checkbutton(log_frame, text="ログファイルを本文に含める",
                       variable=var_attach_log, font=("MS Gothic", 8)
                       ).pack(side=tk.LEFT)
        tk.Button(log_frame, text="ログフォルダを開く", font=("MS Gothic", 8),
                  relief="groove",
                  command=lambda: os.startfile(get_log_dir())
                  ).pack(side=tk.RIGHT)

    # 本文
    tk.Label(win, text="本文:", font=("MS Gothic", 9)).pack(anchor="w", padx=10, pady=(8, 2))
    txt_body = tk.Text(win, font=("MS Gothic", 9), height=12, wrap=tk.WORD)
    txt_body.pack(fill=tk.BOTH, expand=True, padx=10)
    if body_prefix:
        txt_body.insert("1.0", body_prefix)

    def _build_body():
        """本文を組み立て（ログ添付オプション対応）"""
        body = txt_body.get("1.0", tk.END).strip()
        if var_attach_log.get() and log_path and os.path.exists(log_path):
            try:
                with open(log_path, "r", encoding="utf-8") as f:
                    log_content = f.read()
                # 本文に既にログが含まれていなければ追加
                if "--- 全ログ ---" not in body:
                    body += f"\n\n--- 全ログ ({os.path.basename(log_path)}) ---\n"
                    body += log_content
            except Exception:
                pass
        return body

    def send_via_mailto():
        body = _build_body()
        subject = var_subject.get()
        if not body:
            messagebox.showwarning("入力エラー", "本文を入力してください", parent=win)
            return
        # mailto URLは長さ制限があるため、長い場合はクリップボードを案内
        params = urllib.parse.urlencode({"subject": subject, "body": body},
                                        quote_via=urllib.parse.quote)
        mailto_url = f"mailto:{FEEDBACK_EMAIL}?{params}"
        if len(mailto_url) > 2000:
            # URLが長すぎる場合はクリップボードにコピーしてメールクライアントを開く
            text = f"To: {FEEDBACK_EMAIL}\nSubject: {subject}\n\n{body}"
            win.clipboard_clear()
            win.clipboard_append(text)
            short_params = urllib.parse.urlencode(
                {"subject": subject,
                 "body": "（本文が長いためクリップボードにコピーしました。貼り付けてください）"},
                quote_via=urllib.parse.quote)
            short_url = f"mailto:{FEEDBACK_EMAIL}?{short_params}"
            try:
                webbrowser.open(short_url)
                messagebox.showinfo("情報",
                    "本文が長いためクリップボードにコピーしました。\n"
                    "メール本文に貼り付けてください。", parent=win)
                win.destroy()
            except Exception as e:
                messagebox.showerror("エラー",
                    f"メールクライアントを開けませんでした:\n{e}", parent=win)
        else:
            try:
                webbrowser.open(mailto_url)
                win.destroy()
            except Exception as e:
                messagebox.showerror("エラー",
                    f"メールクライアントを開けませんでした:\n{e}", parent=win)

    def copy_to_clipboard():
        body = _build_body()
        subject = var_subject.get()
        text = f"To: {FEEDBACK_EMAIL}\nSubject: {subject}\n\n{body}"
        win.clipboard_clear()
        win.clipboard_append(text)
        messagebox.showinfo("コピー完了",
            "メール内容をクリップボードにコピーしました", parent=win)

    btn_frame = tk.Frame(win)
    btn_frame.pack(pady=(4, 8))
    tk.Button(btn_frame, text="メールで送信", font=("MS Gothic", 9, "bold"),
              command=send_via_mailto).pack(side=tk.LEFT, padx=4)
    tk.Button(btn_frame, text="クリップボードにコピー", font=("MS Gothic", 9),
              command=copy_to_clipboard).pack(side=tk.LEFT, padx=4)
    tk.Button(btn_frame, text="閉じる", font=("MS Gothic", 9),
              command=win.destroy).pack(side=tk.LEFT, padx=4)


def send_error_report(error_info=""):
    """エラー情報を含むメッセージ送信ダイアログを開く"""
    import platform
    from lib.PicSorterGUILogger import get_full_log_path, get_log_dir

    body = "--- エラー情報 ---\n"
    body += f"OS: {platform.system()} {platform.release()}\n"
    body += f"Python: {platform.python_version()}\n"
    if error_info:
        body += f"\n{error_info}\n"

    # 全レベルログから末尾を取得
    log_path = get_full_log_path()
    if log_path and os.path.exists(log_path):
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            tail = lines[-50:] if len(lines) > 50 else lines
            body += "\n--- アプリログ (最新50行) ---\n"
            body += "".join(tail)
        except Exception:
            pass

    # エラーログからも取得
    try:
        from datetime import datetime
        err_log = os.path.join(get_log_dir(),
            f"error_{datetime.now().strftime('%Y%m%d')}.log")
        if os.path.exists(err_log):
            with open(err_log, "r", encoding="utf-8") as f:
                err_lines = f.readlines()
            err_tail = err_lines[-30:] if len(err_lines) > 30 else err_lines
            body += "\n--- エラーログ (最新30行) ---\n"
            body += "".join(err_tail)
    except Exception:
        pass

    body += "\n--- ここに詳細を記入してください ---\n\n"
    open_send_message_dialog(
        subject_prefix="[PicSorterGUI] エラー報告",
        body_prefix=body,
        attach_log=True)


help_menu.add_command(label="フィードバックを送る...", command=open_send_message_dialog)
help_menu.add_command(label="エラーを報告する...", command=send_error_report)


def run_visual_sort():
    try:
        target_path = filedialog.askopenfilename(
            title="AI Visual Sort のターゲット画像を選択してください",
            initialdir=DEFOLDER,
            filetypes=[("Image Files", "*.jpg;*.jpeg;*.png;*.bmp;*.webp")]
        )
        if target_path:
            open_visual_sort_window(target_path, app_state, execute_move, refresh_ui, koRoot)
    except Exception as e:
        logger.error(f"Visual Sort Launch Error: {e}")
        if messagebox.askyesno("エラー",
                f"起動に失敗しました: {e}\n\nエラーを報告しますか？"):
            send_error_report(f"Visual Sort Launch Error: {e}")


def run_auto_sort():
    """オート仕分け: フォルダを選択して全画像が群体/孤立になるまで自動処理"""
    prev_state = koRoot.attributes("-topmost")
    koRoot.attributes("-topmost", False)
    path = filedialog.askdirectory(
        title="自動仕分けするフォルダを選択してください",
        initialdir=DEFOLDER
    )
    koRoot.attributes("-topmost", prev_state)
    if path:
        AutoSortDialog(koRoot, path, execute_move, refresh_ui)


# --- メインウィンドウ UI (シンプル構成) ---

# AI Visual Sort ボタン (メインアクション)
btn_visual_sort = tk.Button(koRoot, text="AI Visual Sort\n(視覚的仕分け)",
                            command=run_visual_sort,
                            bg="#e8f0fe", font=("MS Gothic", 18, "bold"),
                            relief="groove", cursor="hand2", height=3)
btn_visual_sort.pack(fill=tk.BOTH, padx=8, pady=(8, 4), expand=True)

# オート仕分けボタン
btn_auto = tk.Button(koRoot, text="オート仕分け (全自動グループ化)",
                     command=run_auto_sort,
                     bg="#fff3e0", font=("MS Gothic", 10, "bold"),
                     relief="groove", cursor="hand2", height=1)
btn_auto.pack(fill=tk.X, padx=8, pady=(0, 4))

# --- 参照フォルダ管理エリア ---
frame_ref_folders = tk.LabelFrame(koRoot, text="参照フォルダ", font=("MS Gothic", 9), padx=4, pady=4)
frame_ref_folders.pack(fill=tk.X, padx=8, pady=(4, 0))

frame_ref_list = tk.Frame(frame_ref_folders)
frame_ref_list.pack(fill=tk.X)


def refresh_ref_folder_ui():
    for w in frame_ref_list.winfo_children():
        w.destroy()

    for i, entry in enumerate(app_state.reference_folders):
        row = tk.Frame(frame_ref_list)
        row.pack(fill=tk.X, pady=1)

        basename = os.path.basename(entry["path"]) or entry["path"]
        lbl = tk.Label(row, text=basename, font=("MS Gothic", 8), anchor="w", width=20)
        lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

        sub_var = tk.BooleanVar(value=entry["include_subfolders"])

        def make_toggle(idx, var):
            def toggle():
                app_state.toggle_subfolder(idx)
                save_ref_folders()
            return toggle

        chk = tk.Checkbutton(row, text="子フォルダ", variable=sub_var,
                             font=("MS Gothic", 8), command=make_toggle(i, sub_var))
        chk.pack(side=tk.LEFT, padx=2)

        def make_remove(idx):
            def remove():
                app_state.remove_reference_folder(idx)
                save_ref_folders()
                refresh_ref_folder_ui()
            return remove

        btn_del = tk.Button(row, text="x", font=("MS Gothic", 7), width=2,
                            command=make_remove(i), relief="flat", fg="red")
        btn_del.pack(side=tk.RIGHT)

    if not app_state.reference_folders:
        lbl_empty = tk.Label(frame_ref_list, text="(なし - ターゲット画像のフォルダのみ検索)",
                             font=("MS Gothic", 8), fg="#888888")
        lbl_empty.pack(anchor="w")


def add_reference_folder():
    prev_state = koRoot.attributes("-topmost")
    koRoot.attributes("-topmost", False)
    path = filedialog.askdirectory(title="参照フォルダを選択")
    koRoot.attributes("-topmost", prev_state)
    if path:
        if app_state.add_reference_folder(path):
            save_ref_folders()
            refresh_ref_folder_ui()


def save_ref_folders():
    cfg = app_state.to_dict()
    save_config(cfg["last_folder"], cfg.get("geometries", {}), cfg["settings"])


btn_add_folder = tk.Button(frame_ref_folders, text="+ フォルダを追加",
                           command=add_reference_folder,
                           font=("MS Gothic", 9), relief="groove", cursor="hand2")
btn_add_folder.pack(fill=tk.X, pady=(4, 0))

refresh_ref_folder_ui()

# --- 移動先フォルダ設定エリア ---
frame_move_dest = tk.LabelFrame(koRoot, text="移動先フォルダ", font=("MS Gothic", 9), padx=4, pady=4)
frame_move_dest.pack(fill=tk.X, padx=8, pady=(4, 0))

var_move_dest = tk.StringVar(value=app_state.move_dest_folder)

frame_move_dest_row = tk.Frame(frame_move_dest)
frame_move_dest_row.pack(fill=tk.X)

lbl_move_dest = tk.Label(frame_move_dest_row, textvariable=var_move_dest,
                          font=("MS Gothic", 8), anchor="w", fg="#333333",
                          bg="#f0f0f0", relief=tk.SUNKEN, padx=4, pady=2)
lbl_move_dest.pack(side=tk.LEFT, fill=tk.X, expand=True)


def _update_move_dest_display():
    path = var_move_dest.get()
    if path:
        lbl_move_dest.config(fg="#333333")
    else:
        var_move_dest.set("(未設定 - フォルダをD&Dまたは参照)")
        lbl_move_dest.config(fg="#888888")

_update_move_dest_display()


def set_move_dest_folder(path):
    """移動先フォルダを設定して保存"""
    path = path.strip().strip('"').strip("'").replace("{", "").replace("}", "")
    if os.path.isdir(path):
        app_state.move_dest_folder = path
        var_move_dest.set(path)
        lbl_move_dest.config(fg="#333333")
        save_ref_folders()
    elif path:
        messagebox.showwarning("無効なフォルダ", f"フォルダが見つかりません:\n{path}")


def browse_move_dest():
    prev_state = koRoot.attributes("-topmost")
    koRoot.attributes("-topmost", False)
    path = filedialog.askdirectory(title="移動先フォルダを選択",
                                   initialdir=app_state.move_dest_folder or DEFOLDER)
    koRoot.attributes("-topmost", prev_state)
    if path:
        set_move_dest_folder(path)


def clear_move_dest():
    app_state.move_dest_folder = ""
    var_move_dest.set("")
    _update_move_dest_display()
    save_ref_folders()


btn_browse_dest = tk.Button(frame_move_dest_row, text="参照", font=("MS Gothic", 8),
                             command=browse_move_dest, relief="groove", cursor="hand2")
btn_browse_dest.pack(side=tk.LEFT, padx=(4, 2))

btn_clear_dest = tk.Button(frame_move_dest_row, text="x", font=("MS Gothic", 7),
                            command=clear_move_dest, relief="flat", fg="red", width=2)
btn_clear_dest.pack(side=tk.RIGHT)

# ドラッグ&ドロップ対応
try:
    lbl_move_dest.drop_target_register(DND_FILES)
    lbl_move_dest.dnd_bind("<<Drop>>", lambda e: set_move_dest_folder(e.data))
    frame_move_dest.drop_target_register(DND_FILES)
    frame_move_dest.dnd_bind("<<Drop>>", lambda e: set_move_dest_folder(e.data))
except Exception:
    pass  # tkinterdnd2 が利用不可の場合はスキップ

# 使用中AIモデル表示
lbl_model_info = tk.Label(koRoot, text="", font=("MS Gothic", 9), fg="#4a90d9", anchor="center")
lbl_model_info.pack(fill=tk.X, padx=8, pady=(4, 0))

def update_model_info():
    try:
        current_key = app_state.ai_model
        if current_key == "custom":
            basename = os.path.basename(app_state.custom_model_path) if app_state.custom_model_path else "未設定"
            model_name = f"カスタム ({basename})"
        else:
            model_name = AI_MODELS.get(current_key, {}).get("name", current_key)
        lbl_model_info.config(text=f"使用モデル: {model_name}")
    except Exception:
        lbl_model_info.config(text="使用モデル: 不明")

# ベクトルデータサイズ表示
lbl_vector_info = tk.Label(koRoot, text="", font=("MS Gothic", 9), fg="#888888", anchor="center")
lbl_vector_info.pack(fill=tk.X, padx=8, pady=(0, 8))

def update_vector_info():
    try:
        size_bytes, count = get_vector_data_info()
        if size_bytes == 0:
            lbl_vector_info.config(text="AIデータ: なし")
        else:
            size_mb = size_bytes / (1024 * 1024)
            lbl_vector_info.config(text=f"AIデータ: {size_mb:.1f} MB ({count:,}件)")
    except Exception:
        lbl_vector_info.config(text="AIデータ: 取得失敗")

update_model_info()
update_vector_info()


# --- ウィンドウ初期設定 ---
if "main" in SAVED_GEOS and SAVED_GEOS["main"]:
    koRoot.geometry(SAVED_GEOS["main"])
else:
    koRoot.geometry("320x340")

koRoot.protocol("WM_DELETE_WINDOW", on_closing_main)

# フォルダの初期読み込み
try:
    all_items = os.listdir(DEFOLDER)
    files = GetGazoFiles(all_items, DEFOLDER)
    folders = GetKoFolder(all_items, DEFOLDER)
    app_state.set_current_files(files)
    app_state.set_current_folders(folders)
    data_manager.SetGazoFiles(files, DEFOLDER)
    koRoot.title("PicSorterGUI - " + DEFOLDER)
except Exception as e:
    logger.error(f"初期フォルダ読み込みエラー: {e}")


# --- キーバインド ---
def on_ctrl_f(event):
    koRoot.attributes("-topmost", True)
    koRoot.focus_force()

def on_ctrl_e(event):
    open_explorer()

koRoot.bind_all("<Control-f>", on_ctrl_f)
koRoot.bind_all("<Control-e>", on_ctrl_e)


koRoot.mainloop()

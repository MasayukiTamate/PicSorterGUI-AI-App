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
    MOVE_DESTINATION_OPTIONS, AI_MODELS, DEFAULT_AI_MODEL,
)
from lib.PicSorterGUIWidgets import SplashWindow, ModelSelectDialog
from lib.PicSorterGUIAI import VectorEngine

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
    current_model = app_state.to_dict().get("settings", {}).get("ai_model", DEFAULT_AI_MODEL)
    # VectorEngine にモデルキーを設定（まだインスタンスは作らない）
    VectorEngine._current_model_key = current_model
    if not check_model_cached(current_model):
        open_model_select_dialog()


def open_model_select_dialog():
    """モデル選択ダイアログを開く"""
    current_model = app_state.to_dict().get("settings", {}).get("ai_model", DEFAULT_AI_MODEL)

    def on_model_selected(new_key):
        old_key = app_state.to_dict().get("settings", {}).get("ai_model", DEFAULT_AI_MODEL)
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
        cfg = app_state.to_dict()
        cfg["settings"]["ai_model"] = new_key
        save_config(cfg["last_folder"], cfg.get("geometries", {}), cfg["settings"])
        app_state.from_dict(cfg)

        # VectorEngine をリセットして新モデルで初期化準備
        VectorEngine.reset_instance()

        update_vector_info()

    ModelSelectDialog(koRoot, current_model, on_select=on_model_selected)

# --- 設定の読み込みと初期化 ---
try:
    CONFIG_DATA = load_config()
    logger.info(f"設定ファイル読み込み成功: {CONFIG_DATA.get('last_folder')}")
    app_state.from_dict(CONFIG_DATA)
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
        messagebox.showerror("失敗", f"移動中にエラー: {e}")


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
file_menu.add_command(label="全ての画像を閉じる(R)", command=lambda: pic_controller.CloseAll())
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

# 移動先フォルダ数の設定
count_var = tk.IntVar(value=app_state.move_dest_count)
def change_move_count():
    if not app_state.set_move_dest_count(count_var.get()):
        messagebox.showerror("エラー", "無効な個数です")
        count_var.set(app_state.move_dest_count)

move_count_menu = tk.Menu(config_menu, tearoff=0)
config_menu.add_cascade(label="移動先フォルダ数", menu=move_count_menu)
for c in MOVE_DESTINATION_OPTIONS:
    move_count_menu.add_radiobutton(label=f"{c}個", variable=count_var, value=c, command=change_move_count)

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
        messagebox.showerror("エラー", f"起動に失敗しました: {e}")


# --- メインウィンドウ UI (シンプル構成) ---

# AI Visual Sort ボタン (メインアクション)
btn_visual_sort = tk.Button(koRoot, text="AI Visual Sort\n(視覚的仕分け)",
                            command=run_visual_sort,
                            bg="#e8f0fe", font=("MS Gothic", 18, "bold"),
                            relief="groove", cursor="hand2", height=3)
btn_visual_sort.pack(fill=tk.BOTH, padx=8, pady=(8, 4), expand=True)

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

update_vector_info()


# --- ウィンドウ初期設定 ---
if "main" in SAVED_GEOS and SAVED_GEOS["main"]:
    koRoot.geometry(SAVED_GEOS["main"])
else:
    koRoot.geometry("320x220")

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

def on_ctrl_r(event):
    pic_controller.CloseAll()

def on_ctrl_e(event):
    open_explorer()

koRoot.bind_all("<Control-f>", on_ctrl_f)
koRoot.bind_all("<Control-r>", on_ctrl_r)
koRoot.bind_all("<Control-e>", on_ctrl_e)


koRoot.mainloop()

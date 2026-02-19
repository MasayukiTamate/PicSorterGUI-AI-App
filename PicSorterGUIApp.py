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

from tkinter import filedialog, messagebox, simpledialog
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
    calculate_window_layout, open_visual_sort_window
)
from lib.PicSorterGUIBasicLib import tkConvertWinSize
from lib.PicSorterGUILib import GetKoFolder, GetGazoFiles
from lib.PicSorterGUIState import get_app_state
from lib.config_defaults import (
    calculate_folder_window_width, calculate_folder_window_height,
    calculate_file_window_width, calculate_file_window_height,
    WINDOW_SPACING, SCREEN_MARGIN, COLOR_MOVE_BG_1,
    get_move_grid_columns, MOVE_DESTINATION_SLOTS, MOVE_DESTINATION_MIN,
    MOVE_DESTINATION_OPTIONS, COLOR_MOVE_BG_2, COLOR_REGISTER_BG,
)
from lib.PicSorterGUIWidgets import SplashWindow, SimilarityMoveDialog

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

koRoot.after(1500, close_splash)

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

# --- 子ウィンドウ (遅延生成) ---
folder_win = None
folder_listbox = None
file_win = None
file_listbox = None


# --- 共通のUI更新処理 ---
def on_app_state_changed(event_name, data):
    try:
        if event_name == "folder_changed":
            refresh_ui(data["path"])
        elif event_name == "show_folder_window_changed":
            if data["show"]:
                ensure_folder_win()
                folder_win.deiconify()
            elif folder_win:
                folder_win.withdraw()
        elif event_name == "show_file_window_changed":
            if data["show"]:
                ensure_file_win()
                file_win.deiconify()
            elif file_win:
                file_win.withdraw()
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
    lbl_folder_path.config(text=DEFOLDER)
    save_config(DEFOLDER)

    # 子ウィンドウが存在していれば更新
    if folder_listbox:
        folder_listbox.delete(0, tk.END)
        try:
            current_name = os.path.basename(DEFOLDER) or DEFOLDER
            folder_listbox.insert(tk.END, f"({len(files)}) [現在] {current_name}")
        except:
            folder_listbox.insert(tk.END, "(-) [現在] ???")

        for f in folders:
            try:
                sub_items = os.listdir(os.path.join(DEFOLDER, f))
                count = len(GetGazoFiles(sub_items, os.path.join(DEFOLDER, f)))
                folder_listbox.insert(tk.END, f"({count}) {f}")
            except:
                folder_listbox.insert(tk.END, f"(-) {f}")

    if file_listbox:
        file_listbox.delete(0, tk.END)
        for f in files:
            file_listbox.insert(tk.END, f)

    if folder_win and file_win:
        adjust_window_layouts(folders, files)


def adjust_window_layouts(folders, files):
    root_x, root_y = koRoot.winfo_x(), koRoot.winfo_y()
    root_w = koRoot.winfo_width()
    screen_w = koRoot.winfo_screenwidth()

    f_geo, g_geo = calculate_window_layout(
        root_x, root_y, root_w, screen_w,
        folders, files, DEFOLDER
    )

    folder_win.geometry(f_geo)
    file_win.geometry(g_geo)


# --- 子ウィンドウ生成関数 ---
def ensure_folder_win():
    global folder_win, folder_listbox
    if folder_win:
        return

    all_items = os.listdir(DEFOLDER)
    folders = GetKoFolder(all_items, DEFOLDER)

    folder_win, folder_listbox = create_folder_list_window(koRoot, folders)
    pic_controller.SetUI(folder_win, file_win)

    if "folder" in SAVED_GEOS and SAVED_GEOS["folder"]:
        folder_win.geometry(SAVED_GEOS["folder"])

    folder_win.protocol("WM_DELETE_WINDOW", lambda: (show_folder_win.set(False), folder_win.withdraw()))

    # 内容を最新にする
    refresh_folder_list()


def ensure_file_win():
    global file_win, file_listbox
    if file_win:
        return

    all_items = os.listdir(DEFOLDER)
    files = GetGazoFiles(all_items, DEFOLDER)

    file_win, file_listbox = create_file_list_window(koRoot, files, pic_controller.Drawing)
    pic_controller.SetUI(folder_win, file_win)

    if "file" in SAVED_GEOS and SAVED_GEOS["file"]:
        file_win.geometry(SAVED_GEOS["file"])

    file_win.protocol("WM_DELETE_WINDOW", lambda: (show_file_win.set(False), file_win.withdraw()))

    # 内容を最新にする
    refresh_file_list()


def refresh_folder_list():
    if not folder_listbox:
        return
    all_items = os.listdir(DEFOLDER)
    folders = GetKoFolder(all_items, DEFOLDER)
    files = GetGazoFiles(all_items, DEFOLDER)

    folder_listbox.delete(0, tk.END)
    try:
        current_name = os.path.basename(DEFOLDER) or DEFOLDER
        folder_listbox.insert(tk.END, f"({len(files)}) [現在] {current_name}")
    except:
        folder_listbox.insert(tk.END, "(-) [現在] ???")

    for f in folders:
        try:
            sub_items = os.listdir(os.path.join(DEFOLDER, f))
            count = len(GetGazoFiles(sub_items, os.path.join(DEFOLDER, f)))
            folder_listbox.insert(tk.END, f"({count}) {f}")
        except:
            folder_listbox.insert(tk.END, f"(-) {f}")


def refresh_file_list():
    if not file_listbox:
        return
    all_items = os.listdir(DEFOLDER)
    files = GetGazoFiles(all_items, DEFOLDER)

    file_listbox.delete(0, tk.END)
    for f in files:
        file_listbox.insert(tk.END, f)


def create_folder_list_window(parent, folders):
    win = tk.Toplevel(parent)
    win.title("フォルダ一覧")
    win.attributes("-topmost", True)

    btn_frame = tk.Frame(win)
    btn_frame.pack(fill=tk.X, padx=5, pady=5)
    tk.Button(btn_frame, text="↑ 上のフォルダへ", command=lambda: app_state.set_current_folder(os.path.dirname(DEFOLDER))).pack(fill=tk.X)

    frame = tk.Frame(win)
    frame.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)
    scrollbar = tk.Scrollbar(frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    lb = tk.Listbox(frame, yscrollcommand=scrollbar.set)
    for folder in folders: lb.insert(tk.END, folder)
    lb.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
    scrollbar.config(command=lb.yview)

    def on_right_click(event):
        try:
            idx = lb.nearest(event.y)
            lb.selection_clear(0, tk.END)
            lb.selection_set(idx)
            lb.activate(idx)

            sel = lb.get(idx)
            if idx == 0:
                target_path = DEFOLDER
            else:
                if ") " in sel: sel = sel.split(") ", 1)[1]
                target_path = os.path.join(DEFOLDER, sel)

            if not os.path.isdir(target_path): return

            popup = tk.Menu(win, tearoff=0)

            def insert_reg():
                app_state.set_move_destination(app_state.move_reg_idx, target_path)
                app_state.rotate_move_reg_idx()

            popup.add_command(label="登録を挿入", font=("MS Gothic", 9, "bold"), command=insert_reg)
            popup.add_separator()

            def make_reg_func(s_idx, p):
                def reg():
                    app_state.set_move_destination(s_idx, p)
                return reg

            for i in range(app_state.move_dest_count):
                cur_path = app_state.move_dest_list[i]
                if cur_path:
                    label_text = f"{i+1}: [{os.path.basename(cur_path)}]"
                else:
                    label_text = f"{i+1}: (未登録)"

                popup.add_command(label=label_text, command=make_reg_func(i, target_path))

            popup.post(event.x_root, event.y_root)
        except Exception as e:
            print(f"右クリックエラー: {e}")

    def on_double_click(event):
        try:
            idx = lb.curselection()[0]
            sel = lb.get(idx)
            if idx == 0: app_state.set_current_folder(DEFOLDER); return
            if ") " in sel: sel = sel.split(") ", 1)[1]
            app_state.set_current_folder(os.path.join(DEFOLDER, sel))
        except: pass

    lb.bind("<Button-3>", on_right_click)
    lb.bind("<Double-Button-1>", on_double_click)
    return win, lb


def create_file_list_window(parent, files, draw_func):
    win = tk.Toplevel(parent)
    win.title("ファイル一覧")
    win.attributes("-topmost", True)
    tk.Label(win, text="画像ファイル一覧 (Wクリックで表示)", font=("Helvetica", "9", "bold")).pack(pady=5)

    frame = tk.Frame(win)
    frame.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)
    scrollbar = tk.Scrollbar(frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    lb = tk.Listbox(frame, yscrollcommand=scrollbar.set)
    for f in files: lb.insert(tk.END, f)
    lb.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
    scrollbar.config(command=lb.yview)

    def on_double_click(event):
        try:
            idx = lb.curselection()
            if idx: draw_func(lb.get(idx[0]))
        except: pass
    lb.bind("<Double-Button-1>", on_double_click)

    def on_right_click(event):
        try:
            idx = lb.nearest(event.y)
            lb.selection_clear(0, tk.END)
            lb.selection_set(idx)
            lb.activate(idx)
            filename = lb.get(idx)
            full_path = os.path.join(DEFOLDER, filename)

            popup = tk.Menu(win, tearoff=0)

            def rename_file():
                root, ext = os.path.splitext(filename)
                new_root = simpledialog.askstring("名前変更", f"新しいファイル名を入力（{ext}は自動付与）:", initialvalue=root, parent=win)
                if new_root and new_root != root:
                    try:
                        new_name = new_root + ext
                        new_path = os.path.join(DEFOLDER, new_name)
                        os.rename(full_path, new_path)
                        app_state.set_current_folder(DEFOLDER)
                    except Exception as e:
                        messagebox.showerror("エラー", f"名前変更に失敗: {e}")

            popup.add_command(label="名前変更", command=rename_file)

            move_menu = tk.Menu(popup, tearoff=0)
            popup.add_cascade(label="登録フォルダに移動", menu=move_menu)

            def make_move_func(dest):
                return lambda: execute_move(full_path, dest)

            for i in range(app_state.move_dest_count):
                dest = app_state.move_dest_list[i]
                if dest:
                    move_menu.add_command(label=f"{i+1}: {os.path.basename(dest)}", command=make_move_func(dest))
                else:
                    move_menu.add_command(label=f"{i+1}: (未登録)", state="disabled")

            def search_similar():
                try:
                    target_dest = app_state.move_dest_list[app_state.move_reg_idx] if app_state.move_dest_list[app_state.move_reg_idx] else ""
                    SimilarityMoveDialog(win, full_path, target_dest, DEFOLDER, execute_move, refresh_callback=None)
                except Exception as e:
                    messagebox.showerror("エラー", f"類似画像検索起動エラー: {e}")

            popup.add_command(label="類似画像を探す", command=search_similar)

            popup.post(event.x_root, event.y_root)
        except Exception as e:
            print(f"ファイル一覧右クリックエラー: {e}")

    lb.bind("<Button-3>", on_right_click)

    return win, lb


# --- メイン処理 ---
koRoot.attributes("-topmost", True)
koRoot.title("PicSorterGUI")

# 実体生成
data_manager = ImageDataManager(DEFOLDER)
pic_controller = PicController(koRoot, DEFOLDER)
koRoot.attributes("-topmost", app_state.topmost)

# スプラッシュ設定
splash_tips_var = tk.BooleanVar(value=app_state.show_splash_tips)
def on_splash_tips_change():
    app_state.set_show_splash_tips(splash_tips_var.get())
    cfg = app_state.to_dict()
    save_config(cfg["last_folder"], cfg["geometries"], cfg["settings"])


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
        if folder_win:
            app_state.set_window_geometry("folder", folder_win.winfo_geometry())
        if file_win:
            app_state.set_window_geometry("file", file_win.winfo_geometry())

        app_state.set_topmost(koRoot.attributes("-topmost"))
        app_state.set_show_folder_window(show_folder_win.get())
        app_state.set_show_file_window(show_file_win.get())

        config_to_save = app_state.to_dict()
        save_config(config_to_save["last_folder"], config_to_save["geometries"], config_to_save["settings"])

        logger.info("アプリケーション終了: 設定を保存しました")
    except Exception as e:
        logger.error(f"終了処理エラー: {e}", exc_info=True)

    koRoot.destroy()
    sys.exit()


def safe_select_folder():
    wins = [koRoot]
    if folder_win: wins.append(folder_win)
    if file_win: wins.append(file_win)
    prev_states = [w.attributes("-topmost") for w in wins]
    for w in wins: w.attributes("-topmost", False)
    path = filedialog.askdirectory(title="画像フォルダを選択してください")
    for i, w in enumerate(wins): w.attributes("-topmost", prev_states[i])
    return path


def disable_all_topmost():
    koRoot.attributes("-topmost", False)
    if folder_win: folder_win.attributes("-topmost", False)
    if file_win: file_win.attributes("-topmost", False)
    pic_controller.disable_all_topmost()


# --- メニュー ---
menubar = tk.Menu(koRoot)
koRoot.config(menu=menubar)

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

show_folder_win = tk.BooleanVar(value=False)
show_file_win = tk.BooleanVar(value=False)

def toggle_folder_win():
    if show_folder_win.get():
        ensure_folder_win()
        folder_win.deiconify()
        app_state.set_show_folder_window(True)
    else:
        if folder_win:
            folder_win.withdraw()
        app_state.set_show_folder_window(False)

def toggle_file_win():
    if show_file_win.get():
        ensure_file_win()
        file_win.deiconify()
        app_state.set_show_file_window(True)
    else:
        if file_win:
            file_win.withdraw()
        app_state.set_show_file_window(False)

view_menu = tk.Menu(menubar, tearoff=0)
menubar.add_cascade(label="表示(V)", menu=view_menu)
view_menu.add_checkbutton(label="フォルダ一覧を表示", variable=show_folder_win, command=toggle_folder_win)
view_menu.add_checkbutton(label="ファイル一覧を表示", variable=show_file_win, command=toggle_file_win)
view_menu.add_separator()
view_menu.add_command(label="全ての画像を閉じる(R)", command=lambda: pic_controller.CloseAll())
view_menu.add_separator()
view_menu.add_command(label="全ての最前面表示をOFF", command=disable_all_topmost)

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
config_menu.add_checkbutton(label="起動時にTipsを表示", variable=splash_tips_var, command=on_splash_tips_change)

# ツールメニュー
tools_menu = tk.Menu(menubar, tearoff=0)
menubar.add_cascade(label="ツール(T)", menu=tools_menu)

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

tools_menu.add_command(label="AIベクトルを更新・作成", command=run_vector_update)

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

tools_menu.add_separator()
tools_menu.add_command(label="AI Visual Sort (視覚的仕分け)", command=run_visual_sort)


# --- メインウィンドウ UI (シンプル構成) ---

# フォルダパス表示
lbl_folder_path = tk.Label(koRoot, text=DEFOLDER, font=("MS Gothic", 9), fg="#555555",
                           anchor="w", padx=8, pady=4, relief="sunken", bg="#f8f8f8")
lbl_folder_path.pack(fill=tk.X, padx=8, pady=(8, 4))

# フォルダ選択ボタン
btn_open_folder = tk.Button(koRoot, text="フォルダを開く", command=lambda: refresh_ui(safe_select_folder()),
                            font=("MS Gothic", 10), relief="groove", cursor="hand2", height=1)
btn_open_folder.pack(fill=tk.X, padx=8, pady=(0, 8))

# AI Visual Sort ボタン (メインアクション)
btn_visual_sort = tk.Button(koRoot, text="AI Visual Sort\n(視覚的仕分け)",
                            command=run_visual_sort,
                            bg="#e8f0fe", font=("MS Gothic", 18, "bold"),
                            relief="groove", cursor="hand2", height=3)
btn_visual_sort.pack(fill=tk.BOTH, padx=8, pady=(0, 8), expand=True)


# --- ウィンドウ初期設定 ---
if "main" in SAVED_GEOS and SAVED_GEOS["main"]:
    koRoot.geometry(SAVED_GEOS["main"])
else:
    koRoot.geometry("320x220")

koRoot.protocol("WM_DELETE_WINDOW", on_closing_main)

# フォルダの初期読み込み (子ウィンドウは生成しない)
try:
    all_items = os.listdir(DEFOLDER)
    files = GetGazoFiles(all_items, DEFOLDER)
    folders = GetKoFolder(all_items, DEFOLDER)
    app_state.set_current_files(files)
    app_state.set_current_folders(folders)
    data_manager.SetGazoFiles(files, DEFOLDER)
    koRoot.title("PicSorterGUI - " + DEFOLDER)
    lbl_folder_path.config(text=DEFOLDER)
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

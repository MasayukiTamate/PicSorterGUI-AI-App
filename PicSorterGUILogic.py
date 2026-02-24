'''
PicSorterGUI のデータ管理、設定管理、およびロジック制御
'''
import os
import json
import random
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
from PIL import ImageTk, Image, ImageOps
import math
import ctypes

class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long)]

from lib.PicSorterGUILib import GetKoFolder, GetGazoFiles
from lib.PicSorterGUIData import (
    load_config, save_config, calculate_file_hash,
    load_vectors, save_vectors, ImageDataManager,
    get_vector_data_info, load_analysis_cache, save_analysis_cache,
    clear_vectors, clear_analysis_cache
)
from lib.PicSorterGUIAI import VectorEngine, VectorBatchProcessor, check_model_cached, download_model
from lib.PicSorterGUIState import get_app_state

from lib.PicSorterGUILogger import LoggerManager
logger = LoggerManager.get_logger(__name__)

app_state = get_app_state()

from lib.config_defaults import (
    calculate_folder_window_width, calculate_folder_window_height,
    calculate_file_window_width, calculate_file_window_height,
    WINDOW_SPACING
)

# ----------------------------------------------------------------------
# 画面レイアウト計算ロジック
# ----------------------------------------------------------------------
def calculate_window_layout(root_x, root_y, root_w, screen_w, folders, files, current_folder_name):
    """メインウィンドウの位置とサイズを基準に、サブウィンドウの最適な配置を計算する。"""
    f_count = len(folders) + 1
    current_base = os.path.basename(current_folder_name) or current_folder_name

    f_names = [f"({len(files)}) [現在] {current_base}"] + [f"({len(folders)}) {f}" for f in folders]
    max_f = max([len(f) for f in f_names]) if f_names else 5
    w_f = calculate_folder_window_width(max_f)
    h_f = calculate_folder_window_height(f_count)
    x_f, y_f = root_x + root_w + WINDOW_SPACING, root_y
    f_geo = f"{w_f}x{h_f}+{x_f}+{y_f}"

    g_count = len(files)
    max_g = max([len(f) for f in files]) if files else 5
    w_g = calculate_file_window_width(max_g)
    h_g = calculate_file_window_height(g_count)
    x_g, y_g = x_f + w_f + WINDOW_SPACING, root_y

    if x_g + w_g > screen_w:
        x_g = max(10, root_x - w_g - WINDOW_SPACING)

    g_geo = f"{w_g}x{h_g}+{x_g}+{y_g}"

    return f_geo, g_geo


# ----------------------------------------------------------------------
# AI Visual Sort 連携ロジック
# ----------------------------------------------------------------------
def open_visual_sort_window(target_path, app_state, move_callback, refresh_callback, parent=None):
    """AI Visual Sort ウィンドウを開き、GUIからのアクションを処理する関数"""
    try:
        from lib.PicSorterGUIWidgets import VisualSortWindow
        import shutil
        from send2trash import send2trash

        def gui_logic_callback(action_type, file_list, win_ref, dest_path=None):
            success_count = 0

            dest_root = None
            if dest_path:
                os.makedirs(dest_path, exist_ok=True)
                dest_root = dest_path

            if not file_list:
                return

            if action_type == "move":
                if not dest_root:
                    messagebox.showerror("エラー", "移動先フォルダが指定されていません。\nフォルダ名を入力してください。")
                    return

                try:
                     for f in file_list:
                         if move_callback:
                             try:
                                 move_callback(f, dest_root, refresh=False)
                                 success_count += 1
                             except TypeError:
                                 move_callback(f, dest_root)
                                 success_count += 1
                         else:
                             shutil.move(f, os.path.join(dest_root, os.path.basename(f)))
                             success_count += 1
                except Exception as e:
                     logger.error(f"Move error: {e}")

                if refresh_callback:
                    refresh_callback(os.path.dirname(target_path))

                messagebox.showinfo("完了", f"{success_count}ファイルを移動しました")
                try:
                    win_ref.destroy()
                except:
                    pass

            elif action_type == "copy":
                for f in file_list:
                    try:
                        shutil.copy2(f, dest_root)
                        success_count += 1
                    except Exception as e:
                        logger.error(f"Copy error ({f}): {e}")

                messagebox.showinfo("完了", f"{success_count}ファイルをコピーしました")

            elif action_type == "trash":
                if messagebox.askyesno("確認", f"{len(file_list)}ファイルをゴミ箱に捨てますか？"):
                    for f in file_list:
                        try:
                            send2trash(f)
                            success_count += 1
                        except Exception as e:
                            logger.error(f"Trash error ({f}): {e}")

                    if refresh_callback:
                        refresh_callback(os.path.dirname(target_path))

                    messagebox.showinfo("完了", f"{success_count}ファイルをゴミ箱に送りました")

        VisualSortWindow(parent, target_path, app_state, gui_logic_callback)

    except ImportError as e:
        messagebox.showerror("エラー", f"モジュール読み込みエラー: {e}")
    except Exception as e:
        logger.error(f"Visual Sort Error: {e}")
        messagebox.showerror("エラー", f"予期せぬエラー: {e}")


class PicController():
    """画像表示制御クラス"""

    def __init__(self, parent, def_folder):
        self.parent = parent
        self.StartFolder = def_folder
        self.open_windows = {}
        self.folder_win = None
        self.file_win = None
        self.vectors_cache = load_vectors()

        self._move_callback = None
        self._refresh_callback = None

    def set_move_callback(self, callback):
        self._move_callback = callback

    def set_refresh_callback(self, callback):
        self._refresh_callback = callback

    def SetUI(self, folder_win, file_win):
        self.folder_win = folder_win
        self.file_win = file_win

    def SetFolder(self, folder):
        self.StartFolder = folder
        self.CloseAll()

    def CloseAll(self):
        for win in list(self.open_windows.values()):
            try:
                win.destroy()
            except: pass
        self.open_windows.clear()

    def Drawing(self, fileName):
        if not fileName: return

        if os.path.isabs(fileName):
            fullName = os.path.normcase(os.path.abspath(fileName))
            imageFolder = self.StartFolder
        else:
            imageFolder = self.StartFolder
            fullName = os.path.normcase(os.path.abspath(os.path.join(imageFolder, fileName)))

        if fullName in self.open_windows:
            try:
                self.open_windows[fullName].destroy()
            except: pass
            if fullName in self.open_windows:
                del self.open_windows[fullName]

        try:
            with Image.open(fullName) as img:
                orig_w, orig_h = img.width, img.height
                screen_w = self.parent.winfo_screenwidth()
                screen_h = self.parent.winfo_screenheight()

                if app_state.image_max_width > 0:
                    limit_w = app_state.image_max_width
                else:
                    limit_w = screen_w * 0.8

                if app_state.image_max_height > 0:
                    limit_h = app_state.image_max_height
                else:
                    limit_h = screen_h * 0.8

                scale = min(limit_w / orig_w, limit_h / orig_h)
                new_w, new_h = int(orig_w * scale), int(orig_h * scale)

                if new_w < app_state.image_min_width and new_h < app_state.image_min_height:
                    scale_w = app_state.image_min_width / orig_w
                    scale_h = app_state.image_min_height / orig_h
                    scale = max(scale_w, scale_h)
                    new_w, new_h = int(orig_w * scale), int(orig_h * scale)
                elif new_w < app_state.image_min_width:
                    scale = app_state.image_min_width / orig_w
                    new_w = app_state.image_min_width
                    new_h = int(orig_h * scale)
                elif new_h < app_state.image_min_height:
                    scale = app_state.image_min_height / orig_h
                    new_w = int(orig_w * scale)
                    new_h = app_state.image_min_height

                if app_state.image_max_width > 0 and new_w > app_state.image_max_width:
                    scale = app_state.image_max_width / new_w
                    new_w = app_state.image_max_width
                    new_h = int(new_h * scale)
                if app_state.image_max_height > 0 and new_h > app_state.image_max_height:
                    scale = app_state.image_max_height / new_h
                    new_w = int(new_w * scale)
                    new_h = app_state.image_max_height

                img_resized = img.resize((new_w, new_h), Image.LANCZOS)
                tkimg = ImageTk.PhotoImage(img_resized)
                del img_resized

            # 表示位置の計算
            try:
                if self.file_win:
                    base_x = self.file_win.winfo_x() + self.file_win.winfo_width() + 20
                    base_y = self.file_win.winfo_y()
                    if base_x + new_w > screen_w and self.folder_win:
                        base_x = max(10, self.folder_win.winfo_x() - new_w - 20)
                else:
                    base_x, base_y = 400, 100
            except:
                base_x, base_y = 400, 100

            win = tk.Toplevel(self.parent)
            display_name = os.path.basename(fileName) if os.path.sep in fileName or os.path.altsep in fileName else fileName
            win.title(f"{display_name} ({int(scale*100)}%)")
            self.open_windows[fullName] = win

            def on_img_close():
                if fullName in self.open_windows:
                    del self.open_windows[fullName]
                win.destroy()
            win.protocol("WM_DELETE_WINDOW", on_img_close)

            win._image_path = fullName
            win._image_hash = calculate_file_hash(fullName)

            win.geometry(f"{new_w}x{new_h}+{base_x}+{base_y}")

            frame = tk.Frame(win)
            frame.pack(expand=True, fill=tk.BOTH)
            canvas = tk.Canvas(frame, width=new_w, height=new_h)
            canvas.pack(side=tk.TOP)
            canvas.image = tkimg
            canvas.create_image(0, 0, image=tkimg, anchor=tk.NW)

            # ウィンドウドラッグ移動
            def start_drag(event, target_win):
                target_win._drag_start_x = event.x_root - target_win.winfo_x()
                target_win._drag_start_y = event.y_root - target_win.winfo_y()

            def do_drag(event, target_win):
                nx = event.x_root - target_win._drag_start_x
                ny = event.y_root - target_win._drag_start_y
                target_win.geometry(f"+{nx}+{ny}")

            def open_context_menu(event):
                menu = tk.Menu(win, tearoff=0)

                # 移動メニュー
                move_menu = tk.Menu(menu, tearoff=0)
                menu.add_cascade(label="登録フォルダに移動", menu=move_menu)

                move_dest_count = app_state.move_dest_count
                move_dest_list = app_state.move_dest_list

                def create_wrapped_move_cb():
                    def wrapped_move_cb(f_path, d_folder, refresh=True):
                        if self._move_callback:
                            self._move_callback(f_path, d_folder, refresh)

                        if f_path == fullName:
                            try:
                                win.destroy()
                            except: pass
                            if fullName in self.open_windows:
                                del self.open_windows[fullName]
                    return wrapped_move_cb

                def make_move_func(dest):
                    def _move():
                        target_folder = os.path.dirname(fullName)
                        try:
                            from lib.PicSorterGUIWidgets import SimilarityMoveDialog
                            SimilarityMoveDialog(self.parent, fullName, dest, target_folder, create_wrapped_move_cb(), self._refresh_callback)
                        except ImportError:
                            logger.error("PicSorterGUIWidgetsが見つかりません")
                    return _move

                for i in range(move_dest_count):
                    dest = move_dest_list[i]
                    if dest:
                        move_menu.add_command(label=f"{i+1}: {os.path.basename(dest)}", command=make_move_func(dest))
                    else:
                        move_menu.add_command(label=f"{i+1}: (未登録)", state="disabled")

                # 類似画像検索
                def search_similar():
                    target_folder = os.path.dirname(fullName)
                    idx = app_state.move_reg_idx
                    dest = move_dest_list[idx] if idx < len(move_dest_list) else ""
                    try:
                        from lib.PicSorterGUIWidgets import SimilarityMoveDialog
                        SimilarityMoveDialog(self.parent, fullName, dest, target_folder, create_wrapped_move_cb(), self._refresh_callback)
                    except ImportError:
                        messagebox.showerror("エラー", "GUIモジュールが見つかりません")

                menu.add_command(label="類似画像を探す", command=search_similar)

                # AI Visual Sort
                def open_visual_sort():
                    open_visual_sort_window(fullName, app_state, self._move_callback, self._refresh_callback, self.parent)

                menu.add_command(label="AI Visual Sort", command=open_visual_sort)

                menu.post(event.x_root, event.y_root)

            canvas.bind("<Button-1>", lambda e: start_drag(e, win))
            canvas.bind("<B1-Motion>", lambda e: do_drag(e, win))
            canvas.bind("<Button-3>", open_context_menu)

        except Exception as e:
            print(f"画像表示エラー: {e}")

    def disable_all_topmost(self):
        pass

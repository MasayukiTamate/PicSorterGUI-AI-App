
import os
import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image, ImageTk
import random
import threading
import time

from lib.PicSorterGUILogger import get_logger
from lib.PicSorterGUIState import get_app_state
from lib.PicSorterGUIAI import VectorEngine
from lib.PicSorterGUILib import GetGazoFiles

import sys

try:
    from PicSorterGUILogic import calculate_file_hash, load_vectors
except ImportError:
    pass

logger = get_logger(__name__)
app_state = get_app_state()


class ScrollableFrame(tk.Frame):
    """スクロール可能なフレームウィジェット"""
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0, bg="#ffffff")
        self.scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)

        self.scrollable_frame = tk.Frame(self.canvas, bg="#ffffff")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.window_id = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfig(self.window_id, width=e.width)
        )

        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.bind_mouse_wheel(self.canvas)
        self.bind_mouse_wheel(self.scrollable_frame)

    def bind_mouse_wheel(self, widget):
        widget.bind("<MouseWheel>", self._on_mouse_wheel)

    def _on_mouse_wheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")


class RowWidget(tk.Frame):
    """リストの1行を表すウィジェット"""
    def __init__(self, parent, filepath, score, is_target=False, show_thumb=True):
        super().__init__(parent, bg="#e6ffe6" if is_target else "#ffffff", pady=2, padx=2, bd=1, relief=tk.SOLID if is_target else tk.FLAT)
        self.filepath = filepath
        self.score = score
        self.show_thumb = show_thumb
        self.is_target = is_target
        self._image_loaded = False
        self._thumb_img = None

        self.lbl_thumb = tk.Label(self, bg="#dddddd", width=64, height=64) if show_thumb else None
        if self.lbl_thumb:
            self.lbl_thumb.pack(side=tk.LEFT, padx=(0, 5))
            if show_thumb:
                self.load_thumbnail()

        text = f"[基準] {os.path.basename(filepath)}" if is_target else f"({score:.1%}) {os.path.basename(filepath)}"
        fg = "blue" if is_target else "black"
        self.lbl_text = tk.Label(self, text=text, font=("MS Gothic", 9), anchor="w", bg=self.cget("bg"), fg=fg)
        self.lbl_text.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def load_thumbnail(self):
        if self._image_loaded: return
        try:
            with Image.open(self.filepath) as img:
                img.thumbnail((64, 64))
                self._thumb_img = ImageTk.PhotoImage(img)
                if self.lbl_thumb:
                    self.lbl_thumb.config(image=self._thumb_img, width=0, height=0)
        except Exception:
            pass
        self._image_loaded = True

    def set_thumbnail_visible(self, visible):
        if visible:
            if not self.lbl_thumb:
                self.lbl_thumb = tk.Label(self, bg="#dddddd")
            self.lbl_thumb.pack(side=tk.LEFT, padx=(0, 5), before=self.lbl_text)
            self.load_thumbnail()
        else:
            if self.lbl_thumb:
                self.lbl_thumb.pack_forget()


class SimilarityMoveDialog(tk.Toplevel):
    """類似画像をまとめて移動するためのダイアログクラス"""
    def __init__(self, parent, target_file, dest_folder, folder_path, move_callback, refresh_callback=None):
        super().__init__(parent)
        self.title("スマート移動 - 準備中...")
        self.geometry("500x600")
        self.attributes("-topmost", True)

        self.target_file = target_file
        self.dest_folder = dest_folder
        self.folder_path = folder_path
        self.move_callback = move_callback
        self.refresh_callback = refresh_callback

        self.row_widgets = []
        self.selected_files = []
        self.is_calculating = True
        self.stop_thread = False

        tk.Label(self, text=f"[基準] {os.path.basename(target_file)}", font=("MS Gothic", 10, "bold"), fg="blue").pack(pady=5)
        tk.Label(self, text=f"[移動先] {os.path.basename(dest_folder)}", font=("MS Gothic", 10, "bold"), fg="red").pack(pady=5)

        frame_ctrl = tk.LabelFrame(self, text="設定 (AI判定)", padx=10, pady=5)
        frame_ctrl.pack(fill=tk.X, padx=10, pady=5)

        default_threshold = app_state.smart_move_threshold
        self.var_threshold = tk.DoubleVar(value=default_threshold)

        self.lbl_threshold = tk.Label(frame_ctrl, text=f"閾値: {int(default_threshold*100)}%")
        self.lbl_threshold.pack(anchor="w")

        def on_scale(val):
            self.lbl_threshold.config(text=f"閾値: {float(val)*100:.1f}%")
            self.update_list_filter()

        self.scale = tk.Scale(frame_ctrl, variable=self.var_threshold, from_=0.0, to=1.0, resolution=0.01, orient=tk.HORIZONTAL, command=on_scale)
        self.scale.pack(fill=tk.X, expand=True)

        self.var_show_thumb = tk.BooleanVar(value=app_state.smart_move_show_thumbnails)
        def on_thumb_toggle():
            app_state.set_smart_move_show_thumbnails(self.var_show_thumb.get())
            self.update_thumbnail_visibility()

        tk.Checkbutton(frame_ctrl, text="サムネイルを表示（重い場合はOFF推奨）", variable=self.var_show_thumb, command=on_thumb_toggle).pack(anchor="w")

        self.lb_status = tk.Label(self, text="初期化中...", font=("MS Gothic", 9), fg="#666666")
        self.lb_status.pack()

        frame_list_container = tk.Frame(self, bd=1, relief=tk.SUNKEN)
        frame_list_container.pack(expand=True, fill=tk.BOTH, padx=10, pady=5)

        self.scroll_frame = ScrollableFrame(frame_list_container)
        self.scroll_frame.pack(expand=True, fill=tk.BOTH)

        frame_btn = tk.Frame(self)
        frame_btn.pack(fill=tk.X, pady=10)
        self.btn_execute = tk.Button(frame_btn, text="移動実行", bg="#ffcccc", width=15, height=2, command=self.on_execute, state=tk.DISABLED)
        self.btn_execute.pack(side=tk.RIGHT, padx=10)
        tk.Button(frame_btn, text="キャンセル", width=10, height=2, command=self.on_cancel).pack(side=tk.RIGHT, padx=10)

        self.thread = threading.Thread(target=self.prepare_data_thread, daemon=True)
        self.thread.start()

    def on_cancel(self):
        self.stop_thread = True
        self.destroy()

    def prepare_data_thread(self):
        try:
            from PicSorterGUILogic import calculate_file_hash, load_vectors, save_vectors

            def update_status(text, loaded_count=0, total_count=0):
                 self.after(0, lambda: self.lb_status.config(text=text))
                 if total_count > 0:
                     self.after(0, lambda: self.title(f"準備中... {loaded_count}/{total_count}"))

            engine = VectorEngine.get_instance()
            vectors = load_vectors()

            t_hash = calculate_file_hash(self.target_file)
            if t_hash not in vectors:
                 vec = engine.get_image_feature(self.target_file)
                 if vec: vectors[t_hash] = vec
            t_vec = vectors.get(t_hash)

            if not t_vec:
                self.after(0, lambda: messagebox.showerror("エラー", "基準画像のベクトル計算に失敗しました"))
                self.after(0, self.destroy)
                return

            all_items = os.listdir(self.folder_path)
            files = GetGazoFiles(all_items, self.folder_path)
            total = len(files)

            candidates_data = []
            vectors_updated = False

            start_time = time.time()
            chunk_start_time = start_time

            count = 0
            for i, f in enumerate(files):
                if self.stop_thread: return

                full = os.path.join(self.folder_path, f)
                if full == self.target_file: continue

                h = calculate_file_hash(full)
                if h not in vectors:
                    try:
                        vec = engine.get_image_feature(full)
                        if vec:
                            vectors[h] = vec
                            vectors_updated = True
                    except Exception as e:
                        logger.warning(f"オンデマンドベクトル計算失敗: {f} - {e}")

                if h in vectors:
                    score = engine.compare_features(t_vec, vectors[h])
                    candidates_data.append((full, score))

                count += 1

                if count % 10 == 0:
                    current = time.time()
                    elapsed = current - chunk_start_time
                    chunk_start_time = current
                    update_status(f"計算中... {count}/{total}", count, total)

            if vectors_updated:
                self.after(0, lambda: self.lb_status.config(text="ベクトル保存中..."))
                try:
                    save_vectors(vectors)
                except Exception as e:
                    logger.error(f"ベクトル保存エラー: {e}")

            candidates_data.sort(key=lambda x: x[1], reverse=True)

            self.after(0, lambda: self.finalize_preparation(candidates_data))

        except Exception as e:
            logger.error(f"データ準備スレッドエラー: {e}", exc_info=True)
            self.after(0, lambda: messagebox.showerror("エラー", f"データ準備中にエラー: {e}"))
            self.after(0, self.destroy)

    def finalize_preparation(self, candidates_data):
        if self.stop_thread: return

        self.is_calculating = False
        self.lb_status.config(text="リスト構築中...")
        self.title("スマート移動 - 類似画像も一緒に移動")

        self.row_widgets.append(RowWidget(self.scroll_frame.scrollable_frame, self.target_file, 1.0, is_target=True, show_thumb=self.var_show_thumb.get()))

        for f, score in candidates_data:
            rw = RowWidget(self.scroll_frame.scrollable_frame, f, score, show_thumb=self.var_show_thumb.get())
            self.row_widgets.append(rw)

        self.btn_execute.config(state=tk.NORMAL)
        self.update_list_filter()
        self.lb_status.config(text="準備完了")

    def update_thumbnail_visibility(self):
        show = self.var_show_thumb.get()
        for rw in self.row_widgets:
            rw.set_thumbnail_visible(show)

    def update_list_filter(self):
        if self.is_calculating: return

        threshold = self.var_threshold.get()
        count = 0
        visible_widgets = []
        self.selected_files = []

        for rw in self.row_widgets:
            if rw.is_target:
                visible_widgets.append(rw)
                self.selected_files.append(rw.filepath)
                count += 1
            elif rw.score >= threshold:
                visible_widgets.append(rw)
                self.selected_files.append(rw.filepath)
                count += 1

        for child in self.scroll_frame.scrollable_frame.winfo_children():
            child.pack_forget()

        for rw in visible_widgets:
            rw.pack(fill=tk.X, expand=True)
            if rw.show_thumb:
                rw.load_thumbnail()

        self.lb_status.config(text=f"移動対象: {count}件")

    def on_execute(self):
        if not self.move_callback: return
        count = len(self.selected_files)
        if messagebox.askyesno("確認", f"{count}件のファイルを移動してよいですか？"):
            non_target_files = [f for f in self.selected_files if f != self.target_file]
            targets = [f for f in self.selected_files if f == self.target_file]

            sorted_files = non_target_files + targets

            success_count = 0
            for f in sorted_files:
                try:
                    self.move_callback(f, self.dest_folder, refresh=False)
                    success_count += 1
                except TypeError:
                    self.move_callback(f, self.dest_folder)
                    success_count += 1

            if self.refresh_callback:
                try:
                    self.refresh_callback(self.folder_path)
                except Exception as e:
                    logger.error(f"一括リフレッシュ失敗: {e}")

            app_state.set_smart_move_threshold(self.var_threshold.get())

            try:
                messagebox.showinfo("完了", f"{success_count}件の移動が完了しました")
                self.destroy()
            except Exception:
                pass


class SplashWindow(tk.Toplevel):
    """起動時のスプラッシュスクリーン"""
    def __init__(self, parent):
        super().__init__(parent)
        self.title("PicSorterGUI")

        w, h = 400, 300

        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        x = (ws/2) - (w/2)
        y = (hs/2) - (h/2)

        self.geometry('%dx%d+%d+%d' % (w, h, x, y))
        self.overrideredirect(True)
        self.configure(bg='#2b2b2b')
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.0)

        self.canvas = tk.Canvas(self, width=w, height=h, bg="#2b2b2b", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.canvas.create_rectangle(0, 0, w, h, fill="#2b2b2b", outline="")
        self.canvas.create_rectangle(0, 0, w, 5, fill="#4a90e2", outline="")

        self.canvas.create_text(w//2, h//2 - 40, text="AI Visual Sorting Tool", fill="#aaaaaa", font=("MS Gothic", 16))
        self.canvas.create_text(w//2, h//2 + 10, text="PicSorterGUI", fill="#ffffff", font=("MS Gothic", 28, "bold"))

        self.canvas.create_text(w-20, h-20, text="Ver 3.0.0", fill="#666666", font=("Helvetica", 12), anchor="se")

        if app_state.show_splash_tips:
            tips = [
                "Tips: 右クリックでAI Visual Sortが使えます",
                "Tips: 類似画像をまとめて移動できます",
                "Tips: D&Dでフォルダを登録できます"
            ]
            tip = random.choice(tips)
            self.canvas.create_text(w//2, h-60, text=tip, fill="#4a90e2", font=("MS Gothic", 10))

        self.fade_in()

    def fade_in(self):
        try:
            alpha = self.attributes("-alpha")
            if alpha < 1.0:
                alpha += 0.05
                self.attributes("-alpha", alpha)
                self.after(20, self.fade_in)
        except:
            pass

    def close(self):
        self.destroy()


class VisualSortWindow(tk.Toplevel):
    """AI Visual Sort 用のウィンドウ"""
    def __init__(self, parent, target_file, app_state_ref, logic_callback):
        super().__init__(parent)
        self.title("AI Visual Sort - 視覚的仕分け")
        self.geometry("1000x800")
        self.target_file = target_file
        self.app_state = app_state_ref
        self.logic_callback = logic_callback

        self.frame_top = tk.Frame(self, bg="#222222", height=300)
        self.frame_top.pack(fill=tk.X, side=tk.TOP)

        self.frame_mid = tk.Frame(self, bg="#444444", pady=5)
        self.frame_mid.pack(fill=tk.X, side=tk.TOP)

        self.frame_bot = tk.Frame(self, bg="#dddddd")
        self.frame_bot.pack(fill=tk.BOTH, expand=True, side=tk.TOP)

        self.init_top_frame()
        self.init_control_frame()
        self.init_bottom_frame()

        self.candidates = []
        self.is_loading = False
        self.stop_thread = False
        self.all_results = []
        self.score_boundaries = []

        self.col_count = 5
        self.bind("<Configure>", self.on_resize)
        self.resize_timer = None

        self.start_analysis()

    def on_refresh(self):
        if self.is_loading: return

        for widget in self.grid_frame.winfo_children():
            widget.destroy()
        self.candidates = []
        self.all_results = []

        self.start_analysis()

    def on_resize(self, event):
        if self.resize_timer:
            self.after_cancel(self.resize_timer)
        self.resize_timer = self.after(200, self._process_resize)

    def _process_resize(self):
        try:
            width = self.scroll_view.winfo_width()
            if width <= 100: return

            card_width = 220
            new_col_count = max(1, width // card_width)

            if new_col_count != self.col_count:
                self.col_count = new_col_count
                self.refresh_grid()
        except:
            pass

    def init_top_frame(self):
        self.canvas_target = tk.Canvas(self.frame_top, bg="#222222", highlightthickness=0)
        self.canvas_target.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        try:
            pil_img = Image.open(self.target_file)
            base_height = 280
            h_percent = (base_height / float(pil_img.size[1]))
            w_size = int((float(pil_img.size[0]) * float(h_percent)))
            pil_img = pil_img.resize((w_size, base_height), Image.Resampling.LANCZOS)
            self.tk_target = ImageTk.PhotoImage(pil_img)

            self.canvas_id = self.canvas_target.create_image(
                500, 150, image=self.tk_target, anchor=tk.CENTER
            )
        except Exception as e:
            logger.error(f"基準画像ロードエラー: {e}")

        lbl_path = tk.Label(self.frame_top, text=self.target_file, bg="#222222", fg="#ffffff", font=("MS Gothic", 9))
        lbl_path.place(relx=0, rely=0.9, relwidth=1)

    def init_control_frame(self):
        tk.Label(self.frame_mid, text="類似度:", bg="#444444", fg="white").pack(side=tk.LEFT, padx=5)
        self.var_threshold = tk.DoubleVar(value=0.85)
        self.scale = tk.Scale(self.frame_mid, variable=self.var_threshold, from_=0.0, to=1.0, resolution=0.01,
                              orient=tk.HORIZONTAL, bg="#444444", fg="white", length=200, command=self.on_slider_change)
        self.scale.pack(side=tk.LEFT, padx=5)

        btn_prev = tk.Button(self.frame_mid, text="▲", width=3, command=self.jump_to_prev_boundary)
        btn_prev.pack(side=tk.LEFT, padx=(2, 0))
        btn_next = tk.Button(self.frame_mid, text="▼", width=3, command=self.jump_to_next_boundary)
        btn_next.pack(side=tk.LEFT, padx=(0, 2))
        self.lbl_visible_count = tk.Label(self.frame_mid, text="0枚", bg="#444444", fg="#00ff00", font=("MS Gothic", 10, "bold"))
        self.lbl_visible_count.pack(side=tk.LEFT, padx=5)

        self.btn_select_all = tk.Button(self.frame_mid, text="全選択", command=self.select_all)
        self.btn_select_all.pack(side=tk.LEFT, padx=(10, 2))

        self.btn_deselect_all = tk.Button(self.frame_mid, text="全解除", command=self.deselect_all)
        self.btn_deselect_all.pack(side=tk.LEFT, padx=(2, 10))

        btn_config = {'width': 12, 'pady': 2}

        btn_refresh = tk.Button(self.frame_mid, text="更新 (Refresh)", bg="#eeeeee", command=self.on_refresh, **btn_config)
        btn_refresh.pack(side=tk.LEFT, padx=5)

        dest_options = []
        self.dest_index_map = {}
        for i, d in enumerate(self.app_state.move_dest_list):
            if d:
                label = f"{i+1}: {os.path.basename(d)}"
                dest_options.append(label)
                self.dest_index_map[len(dest_options) - 1] = i

        self.var_dest = tk.StringVar()
        self._dest_style = ttk.Style()
        self._dest_style.map("Dest.TCombobox",
                             foreground=[("readonly", "black")])
        self.combo_dest = ttk.Combobox(self.frame_mid, textvariable=self.var_dest,
                                        values=dest_options, state="readonly", width=20,
                                        style="Dest.TCombobox")
        if dest_options:
            self.combo_dest.current(0)
        self.combo_dest.bind("<<ComboboxSelected>>", self._on_dest_changed)
        self.combo_dest.pack(side=tk.RIGHT, padx=5)
        self._update_dest_color()

        tk.Label(self.frame_mid, text="移動先:", bg="#444444", fg="white").pack(side=tk.RIGHT)

        btn_move = tk.Button(self.frame_mid, text="移動 (Move)", bg="#ccccff", command=lambda: self.execute_action("move"), **btn_config)
        btn_move.pack(side=tk.RIGHT, padx=5)

        btn_copy = tk.Button(self.frame_mid, text="コピー (Copy)", bg="#ccffcc", command=lambda: self.execute_action("copy"), **btn_config)
        btn_copy.pack(side=tk.RIGHT, padx=5)

        btn_trash = tk.Button(self.frame_mid, text="ゴミ箱 (Trash)", bg="#ffcccc", command=lambda: self.execute_action("trash"), **btn_config)
        btn_trash.pack(side=tk.RIGHT, padx=5)

        self.lbl_status = tk.Label(self.frame_mid, text="待機中...", bg="#444444", fg="#aaaaaa")
        self.lbl_status.pack(side=tk.RIGHT, padx=20)

    def init_bottom_frame(self):
        self.scroll_view = ScrollableFrame(self.frame_bot)
        self.scroll_view.pack(fill=tk.BOTH, expand=True)

        self.grid_frame = self.scroll_view.scrollable_frame

    def start_analysis(self):
        self.lbl_status.config(text="AI分析中...")
        thread = threading.Thread(target=self._analysis_task, daemon=True)
        thread.start()

    def _analysis_task(self):
        try:
            from PicSorterGUILogic import calculate_file_hash, load_vectors, save_vectors

            engine = VectorEngine.get_instance()
            vectors = load_vectors()

            t_hash = calculate_file_hash(self.target_file)

            if t_hash not in vectors:
                vec = engine.get_image_feature(self.target_file)
                if vec: vectors[t_hash] = vec

            t_vec = vectors.get(t_hash)
            if not t_vec:
                self.after(0, lambda: messagebox.showerror("Error", "Failed to compute vector"))
                return

            folder = os.path.dirname(self.target_file)
            files = GetGazoFiles(os.listdir(folder), folder)

            results = []
            count = 0
            start_time = time.time()
            vectors_updated = False

            for f in files:
                full_path = os.path.join(folder, f)
                if full_path == self.target_file: continue

                f_hash = calculate_file_hash(full_path)

                if f_hash not in vectors:
                    try:
                        v = engine.get_image_feature(full_path)
                        if v:
                            vectors[f_hash] = v
                            vectors_updated = True
                    except Exception:
                        pass

                if f_hash in vectors:
                    score = engine.compare_features(t_vec, vectors[f_hash])
                    results.append((full_path, score))

                count += 1
                if count % 10 == 0:
                     self.after(0, lambda c=count, t=len(files): self.lbl_status.config(text=f"分析中... {c}/{t}枚"))

            if vectors_updated:
                 save_vectors(vectors)

            results.sort(key=lambda x: x[1], reverse=True)
            elapsed = time.time() - start_time

            self.after(0, lambda: self._on_analysis_complete(results, elapsed))

        except Exception as e:
            logger.error(f"Analysis error: {e}")
            self.after(0, lambda: messagebox.showerror("Error", str(e)))

    def _on_analysis_complete(self, results, elapsed):
        self.lbl_status.config(text=f"完了 ({elapsed:.2f}秒, {len(results)}枚)")
        self.all_results = results
        self._compute_score_boundaries()
        self.refresh_grid()

    def refresh_grid(self):
        for widget in self.grid_frame.winfo_children():
            widget.destroy()

        self.candidates = []
        threshold = self.var_threshold.get()

        col_count = self.col_count
        row = 0
        col = 0

        visible_count = 0

        for path, score in self.all_results:
            if score < threshold: continue

            card = self.create_image_card(self.grid_frame, path, score)
            card.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")

            self.candidates.append({'path': path, 'score': score, 'widget': card})

            visible_count += 1
            col += 1
            if col >= col_count:
                col = 0
                row += 1

        self.lbl_visible_count.config(text=f"{visible_count}枚")

    def create_image_card(self, parent, path, score):
        frame = tk.Frame(parent, bd=2, relief=tk.RIDGE, bg="white", width=200, height=220)
        frame.pack_propagate(False)

        try:
            with Image.open(path) as img:
                img.thumbnail((180, 150))
                tk_img = ImageTk.PhotoImage(img)
        except:
             tk_img = None

        lbl_img = tk.Label(frame, image=tk_img, bg="white")
        lbl_img.image = tk_img
        lbl_img.pack(pady=5)

        color = "red" if score > 0.9 else "black"
        tk.Label(frame, text=f"{score:.1%}", fg=color, bg="white", font=("Arial", 10, "bold")).pack()

        var = tk.BooleanVar(value=False)
        chk = tk.Checkbutton(frame, text=os.path.basename(path), bg="white", anchor="w", variable=var)
        chk.pack(fill=tk.X, padx=5)

        frame.var_selected = var

        return frame

    def on_slider_change(self, val):
        self.refresh_grid()

    def _compute_score_boundaries(self):
        scores = sorted(set(score for _, score in self.all_results), reverse=True)
        self.score_boundaries = scores

    def jump_to_next_boundary(self):
        if not self.score_boundaries:
            return
        current = self.var_threshold.get()
        for s in self.score_boundaries:
            if s < current:
                self.var_threshold.set(s)
                self.scale.set(s)
                self.refresh_grid()
                return

    def jump_to_prev_boundary(self):
        if not self.all_results:
            return
        threshold = self.var_threshold.get()
        visible_scores = [score for _, score in self.all_results if score >= threshold]
        if not visible_scores:
            return
        min_score = min(visible_scores)
        new_threshold = min_score + 0.001
        if new_threshold > 1.0:
            new_threshold = 1.0
        self.var_threshold.set(new_threshold)
        self.scale.set(new_threshold)
        self.refresh_grid()

    def select_all(self):
        for c in self.candidates:
            c['widget'].var_selected.set(True)

    def deselect_all(self):
        for c in self.candidates:
            c['widget'].var_selected.set(False)

    def _on_dest_changed(self, event=None):
        self._update_dest_color()

    def _update_dest_color(self):
        combo_idx = self.combo_dest.current()
        if combo_idx >= 0 and combo_idx in self.dest_index_map:
            list_idx = self.dest_index_map[combo_idx]
            path = self.app_state.move_dest_list[list_idx]
            if path and os.path.exists(path):
                self._dest_style.map("Dest.TCombobox",
                                     foreground=[("readonly", "black")])
            else:
                self._dest_style.map("Dest.TCombobox",
                                     foreground=[("readonly", "red")])

    def execute_action(self, action_type):
        targets = [c['path'] for c in self.candidates if c['widget'].var_selected.get()]
        if not targets:
            messagebox.showinfo("info", "画像が選択されていません")
            return

        if self.logic_callback:
            dest_path = None
            if action_type in ("move", "copy"):
                combo_idx = self.combo_dest.current()
                if combo_idx >= 0 and combo_idx in self.dest_index_map:
                    list_idx = self.dest_index_map[combo_idx]
                    dest_path = self.app_state.move_dest_list[list_idx]
            self.logic_callback(action_type, targets, self, dest_path=dest_path)

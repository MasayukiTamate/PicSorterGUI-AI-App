
import os
import tkinter as tk
from tkinter import messagebox, ttk, filedialog
from PIL import Image, ImageTk
import random
import threading
import time

from lib.PicSorterGUILogger import get_logger
from lib.PicSorterGUIState import get_app_state
from lib.PicSorterGUIAI import (VectorEngine, check_model_cached, download_model,
                                get_model_cache_dir, apply_model_cache_dir, move_model_files)
from lib.PicSorterGUILib import GetGazoFiles
from lib.config_defaults import AI_MODELS, DEFAULT_AI_MODEL, SUPPORTED_IMAGE_FORMATS

import sys

try:
    from PicSorterGUILogic import calculate_file_hash, load_vectors
except ImportError:
    pass

logger = get_logger(__name__)
app_state = get_app_state()


class ModelSelectDialog(tk.Toplevel):
    """AIモデル選択ダイアログ"""
    def __init__(self, parent, current_model_key=None, on_select=None):
        super().__init__(parent)
        self.title("AIモデル選択")
        self.geometry("540x640")
        self.attributes("-topmost", True)
        self.resizable(False, False)

        self.on_select = on_select
        self.result_model = current_model_key or DEFAULT_AI_MODEL
        self.cancelled = True

        # カスタムモデル設定の読み込み
        self._custom_path = app_state.custom_model_path
        self._custom_arch = app_state.custom_model_arch

        tk.Label(self, text="使用するAIモデルを選択してください",
                 font=("MS Gothic", 11, "bold")).pack(pady=(15, 10))

        self.var_model = tk.StringVar(value=self.result_model)

        self.frame_models = tk.Frame(self)
        self.frame_models.pack(fill=tk.BOTH, padx=20, pady=5, expand=True)

        self.status_labels = {}
        self._custom_frame_inner = None  # カスタムモデル用追加UI

        for key, info in AI_MODELS.items():
            frame = tk.Frame(self.frame_models, bd=1, relief=tk.GROOVE, padx=10, pady=8)
            frame.pack(fill=tk.X, pady=3)

            rb = tk.Radiobutton(frame, text=info["name"], variable=self.var_model,
                                value=key, font=("MS Gothic", 10, "bold"), anchor="w",
                                command=self._on_model_radio_changed)
            rb.pack(fill=tk.X)

            desc_frame = tk.Frame(frame)
            desc_frame.pack(fill=tk.X, padx=20)

            tk.Label(desc_frame, text=info["description"],
                     font=("MS Gothic", 9), fg="#555555", anchor="w").pack(side=tk.LEFT)

            if key == "custom":
                # カスタムモデル用の追加UI
                self._custom_frame_inner = tk.Frame(frame, padx=5)
                self._custom_frame_inner.pack(fill=tk.X, pady=(4, 0))
                self._build_custom_ui(self._custom_frame_inner)
                lbl_status = tk.Label(desc_frame, text="",
                                      font=("MS Gothic", 9, "bold"))
                lbl_status.pack(side=tk.RIGHT)
            else:
                cached = check_model_cached(key)
                status_text = "ダウンロード済み" if cached else "未ダウンロード"
                status_color = "#008800" if cached else "#cc0000"
                lbl_status = tk.Label(desc_frame, text=status_text,
                                      font=("MS Gothic", 9, "bold"), fg=status_color)
                lbl_status.pack(side=tk.RIGHT)

            self.status_labels[key] = lbl_status

        self._update_custom_status()
        self._on_model_radio_changed()

        # --- モデル格納場所セクション ---
        self._old_checkpoints_dir = get_model_cache_dir()
        self._pending_torch_home = None  # ユーザーが選択した新しい TORCH_HOME

        frame_storage = tk.LabelFrame(self, text="モデルの格納場所",
                                      font=("MS Gothic", 9), padx=8, pady=6)
        frame_storage.pack(fill=tk.X, padx=20, pady=(2, 4))

        # 現在のパス表示行
        path_row = tk.Frame(frame_storage)
        path_row.pack(fill=tk.X)
        tk.Label(path_row, text="格納先:", font=("MS Gothic", 9), width=6, anchor="w").pack(side=tk.LEFT)
        self._var_cache_display = tk.StringVar(value=self._old_checkpoints_dir)
        tk.Label(path_row, textvariable=self._var_cache_display,
                 font=("MS Gothic", 8), fg="#333333", anchor="w",
                 wraplength=360, justify="left").pack(side=tk.LEFT, fill=tk.X, expand=True)

        # ボタン行
        btn_row = tk.Frame(frame_storage)
        btn_row.pack(fill=tk.X, pady=(4, 0))
        tk.Button(btn_row, text="フォルダを変更...", font=("MS Gothic", 9),
                  command=self._change_cache_dir).pack(side=tk.LEFT)
        self.btn_move_models = tk.Button(btn_row, text="既存モデルを移動",
                                         font=("MS Gothic", 9), state=tk.DISABLED,
                                         command=self._on_move_models)
        self.btn_move_models.pack(side=tk.LEFT, padx=(4, 0))
        self.lbl_move_status = tk.Label(btn_row, text="", font=("MS Gothic", 9))
        self.lbl_move_status.pack(side=tk.LEFT, padx=(6, 0))

        # ステータスラベル
        self.lbl_progress = tk.Label(self, text="", font=("MS Gothic", 9), fg="#0055aa")
        self.lbl_progress.pack(pady=5)

        # ボタン
        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=(5, 15))

        self.btn_download = tk.Button(btn_frame, text="ダウンロード", width=14,
                                      command=self._on_download, font=("MS Gothic", 10))
        self.btn_download.pack(side=tk.LEFT, padx=5)

        self.btn_ok = tk.Button(btn_frame, text="OK", width=10,
                                command=self._on_ok, font=("MS Gothic", 10))
        self.btn_ok.pack(side=tk.LEFT, padx=5)

        tk.Button(btn_frame, text="キャンセル", width=10,
                  command=self._on_cancel, font=("MS Gothic", 10)).pack(side=tk.LEFT, padx=5)

        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

        # モーダルにする
        self.transient(parent)
        self.grab_set()

    def _build_custom_ui(self, parent):
        """カスタムモデル選択UIを構築"""
        # ファイルパス選択
        path_frame = tk.Frame(parent)
        path_frame.pack(fill=tk.X, pady=2)

        tk.Label(path_frame, text=".pthファイル:", font=("MS Gothic", 9), width=12, anchor="w").pack(side=tk.LEFT)
        self._var_custom_path = tk.StringVar(value=self._custom_path)
        entry = tk.Entry(path_frame, textvariable=self._var_custom_path,
                         font=("MS Gothic", 8), state="readonly", width=28)
        entry.pack(side=tk.LEFT, padx=(0, 4))
        tk.Button(path_frame, text="参照...", font=("MS Gothic", 9),
                  command=self._browse_custom_file).pack(side=tk.LEFT)

        # ベースアーキテクチャ選択
        arch_frame = tk.Frame(parent)
        arch_frame.pack(fill=tk.X, pady=2)

        tk.Label(arch_frame, text="アーキテクチャ:", font=("MS Gothic", 9), width=12, anchor="w").pack(side=tk.LEFT)
        arch_keys = [k for k in AI_MODELS if k != "custom"]
        arch_labels = [AI_MODELS[k]["name"] for k in arch_keys]
        self._arch_keys = arch_keys

        self._var_custom_arch = tk.StringVar()
        arch_combo = ttk.Combobox(arch_frame, textvariable=self._var_custom_arch,
                                  values=arch_labels, state="readonly", width=22,
                                  font=("MS Gothic", 9))
        arch_combo.pack(side=tk.LEFT)
        # 現在のアーキテクチャを選択
        if self._custom_arch in arch_keys:
            arch_combo.current(arch_keys.index(self._custom_arch))
        else:
            arch_combo.current(0)
        arch_combo.bind("<<ComboboxSelected>>", lambda e: self._update_custom_status())

        self._arch_combo = arch_combo

    def _browse_custom_file(self):
        """カスタム.pthファイルを選択"""
        prev_topmost = self.attributes("-topmost")
        self.attributes("-topmost", False)
        path = filedialog.askopenfilename(
            title="PyTorch重みファイル (.pth) を選択",
            filetypes=[("PyTorchモデルファイル", "*.pth *.pt"), ("全ファイル", "*.*")]
        )
        self.attributes("-topmost", prev_topmost)
        if path:
            self._var_custom_path.set(path)
            self._custom_path = path
            self._update_custom_status()

    def _update_custom_status(self):
        """カスタムモデルのステータスラベルを更新"""
        if "custom" not in self.status_labels:
            return
        path = self._var_custom_path.get() if hasattr(self, "_var_custom_path") else self._custom_path
        if path and os.path.isfile(path):
            self.status_labels["custom"].config(text="ファイル確認済み", fg="#008800")
        else:
            self.status_labels["custom"].config(text="未選択", fg="#cc0000")

    def _on_model_radio_changed(self):
        """モデル選択変更時にダウンロードボタンの表示を切り替え"""
        key = self.var_model.get()
        if key == "custom":
            self.btn_download.config(state=tk.DISABLED)
        else:
            self.btn_download.config(state=tk.NORMAL)

    def _on_download(self):
        key = self.var_model.get()
        if key == "custom":
            return
        if check_model_cached(key):
            self.lbl_progress.config(text=f"{AI_MODELS[key]['name']} は既にダウンロード済みです")
            return

        self.btn_download.config(state=tk.DISABLED)
        self.btn_ok.config(state=tk.DISABLED)
        self.lbl_progress.config(text="ダウンロード中... しばらくお待ちください")
        self.update()

        def do_download():
            success = download_model(key, progress_callback=lambda msg: self.after(0, lambda: self.lbl_progress.config(text=msg)))
            self.after(0, lambda: self._on_download_complete(key, success))

        threading.Thread(target=do_download, daemon=True).start()

    def _on_download_complete(self, key, success):
        self.btn_download.config(state=tk.NORMAL)
        self.btn_ok.config(state=tk.NORMAL)
        if success:
            self.lbl_progress.config(text=f"{AI_MODELS[key]['name']} のダウンロードが完了しました")
            self.status_labels[key].config(text="ダウンロード済み", fg="#008800")
        else:
            self.lbl_progress.config(text="ダウンロードに失敗しました")

    def _change_cache_dir(self):
        """格納フォルダ（TORCH_HOME）を変更する"""
        prev_topmost = self.attributes("-topmost")
        self.attributes("-topmost", False)
        new_torch_home = filedialog.askdirectory(
            title="モデルの格納フォルダ（TORCH_HOME）を選択",
            initialdir=self._pending_torch_home or os.path.expanduser("~")
        )
        self.attributes("-topmost", prev_topmost)
        if not new_torch_home:
            return

        self._pending_torch_home = new_torch_home
        new_checkpoints = os.path.join(new_torch_home, 'hub', 'checkpoints')
        self._var_cache_display.set(new_checkpoints)

        # 旧ディレクトリに移動できるファイルがあるか確認
        has_files = any(
            os.path.isfile(os.path.join(self._old_checkpoints_dir, info["weight_file"]))
            for info in AI_MODELS.values()
            if info.get("weight_file") and
               os.path.normpath(self._old_checkpoints_dir) != os.path.normpath(new_checkpoints)
        )
        if has_files:
            self.btn_move_models.config(state=tk.NORMAL)
            self.lbl_move_status.config(text="← 旧フォルダからモデルを移動できます", fg="#888888")
        else:
            self.btn_move_models.config(state=tk.DISABLED)
            self.lbl_move_status.config(text="(移動するファイルなし)", fg="#888888")

        # 新しいパスでのキャッシュ状態を反映
        self._refresh_model_statuses(new_checkpoints)

    def _refresh_model_statuses(self, checkpoints_dir):
        """指定ディレクトリを基準にモデルのステータスラベルを更新する"""
        for key, info in AI_MODELS.items():
            if key == "custom" or key not in self.status_labels:
                continue
            weight_file = info.get("weight_file")
            if not weight_file:
                continue
            cached = os.path.isfile(os.path.join(checkpoints_dir, weight_file))
            self.status_labels[key].config(
                text="ダウンロード済み" if cached else "未ダウンロード",
                fg="#008800" if cached else "#cc0000"
            )

    def _on_move_models(self):
        """モデルファイルを旧ディレクトリから新ディレクトリに移動する（スレッド実行）"""
        if not self._pending_torch_home:
            return
        new_checkpoints = os.path.join(self._pending_torch_home, 'hub', 'checkpoints')
        self.btn_move_models.config(state=tk.DISABLED)
        self.btn_ok.config(state=tk.DISABLED)
        self.btn_download.config(state=tk.DISABLED)
        self.lbl_move_status.config(text="移動中...", fg="#0055aa")

        def do_move():
            moved, failed = move_model_files(
                self._old_checkpoints_dir, new_checkpoints,
                progress_callback=lambda msg: self.after(
                    0, lambda m=msg: self.lbl_move_status.config(text=m, fg="#0055aa"))
            )
            self.after(0, lambda: self._on_move_complete(moved, failed, new_checkpoints))

        threading.Thread(target=do_move, daemon=True).start()

    def _on_move_complete(self, moved, failed, new_checkpoints):
        self.btn_ok.config(state=tk.NORMAL)
        self.btn_download.config(state=tk.NORMAL if self.var_model.get() != "custom" else tk.DISABLED)
        if failed:
            names = ", ".join(f for f, _ in failed)
            self.lbl_move_status.config(
                text=f"{len(moved)}件移動済み / {len(failed)}件失敗: {names}", fg="#cc0000")
        else:
            self.lbl_move_status.config(text=f"{len(moved)}件を移動しました", fg="#008800")
        # 移動元を新ディレクトリとして更新（再移動を防ぐ）
        self._old_checkpoints_dir = new_checkpoints
        self._refresh_model_statuses(new_checkpoints)

    def _on_ok(self):
        key = self.var_model.get()

        if key == "custom":
            path = self._var_custom_path.get() if hasattr(self, "_var_custom_path") else ""
            if not path or not os.path.isfile(path):
                messagebox.showwarning("警告", ".pthファイルを選択してください。", parent=self)
                return
            arch_idx = self._arch_combo.current()
            arch_key = self._arch_keys[arch_idx] if arch_idx >= 0 else "mobilenet_v3_small"
            app_state.custom_model_path = path
            app_state.custom_model_arch = arch_key
        else:
            if not check_model_cached(key):
                messagebox.showwarning("警告", f"{AI_MODELS[key]['name']} がダウンロードされていません。\n先にダウンロードしてください。", parent=self)
                return

        # 格納先の変更を適用
        if self._pending_torch_home is not None:
            app_state.model_cache_dir = self._pending_torch_home
            apply_model_cache_dir(self._pending_torch_home)

        self.result_model = key
        self.cancelled = False
        self.grab_release()
        self.destroy()
        if self.on_select:
            self.on_select(key)

    def _on_cancel(self):
        self.cancelled = True
        self.grab_release()
        self.destroy()



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


class GroupDetailWindow(tk.Toplevel):
    """グループ詳細ウィンドウ: グループ内の全画像をサムネイルで表示、個別除外・実行可能"""

    def __init__(self, parent_dialog, group):
        super().__init__(parent_dialog)
        self.parent_dialog = parent_dialog
        self.group = group
        self._thumb_refs = []
        self._member_vars = []  # 各画像のチェック状態
        self._thumb_size = 100  # サムネイルサイズ（ホイールで変更可能）
        self._cols = 4
        self._original_members = list(group["members"])  # 元のメンバー保持
        self._prev_members = list(group["members"])  # グリッド描画時のメンバー追跡
        self._seed_path = group["members"][0] if group["members"] else None

        # 親ダイアログの現在しきい値を取得
        self._parent_threshold = 0.80
        if hasattr(parent_dialog, 'var_threshold'):
            self._parent_threshold = parent_dialog.var_threshold.get()

        # 全画像に対する類似度を事前計算（スライダー操作のリアルタイム性のため）
        self._all_similarities = {}  # {path: similarity}
        self._compute_similarities()

        self.title(f"グループ {group['group_num']} ({len(group['members'])}枚)")
        self.geometry("520x600")
        self.attributes("-topmost", True)
        self.resizable(True, True)
        self.transient(parent_dialog)

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _compute_similarities(self):
        """シード画像と全画像の類似度を事前計算"""
        cache = getattr(self.parent_dialog, '_vec_cache', None)
        if not cache or not self._seed_path:
            return
        hash_map = cache["hash_map"]
        vec_map = cache["vec_map"]
        engine = cache["engine"]

        seed_hash = hash_map.get(self._seed_path)
        if not seed_hash or seed_hash not in vec_map:
            return
        seed_vec = vec_map[seed_hash]

        for path, h in hash_map.items():
            if path == self._seed_path:
                self._all_similarities[path] = 1.0
                continue
            if h in vec_map:
                sim = engine.compare_features(seed_vec, vec_map[h])
                self._all_similarities[path] = sim

    def _build_ui(self):
        # ヘッダー
        header = tk.Frame(self)
        header.pack(fill=tk.X, padx=10, pady=(8, 4))
        self._lbl_header = tk.Label(header,
                 text=f"グループ {self.group['group_num']}: {len(self.group['members'])}枚",
                 font=("MS Gothic", 11, "bold"), fg="#0055cc")
        self._lbl_header.pack(side=tk.LEFT)

        tk.Label(header, text="チェックを外すと対象から除外 / Ctrl+ホイールでサイズ変更",
                 font=("MS Gothic", 8), fg="#888888").pack(side=tk.RIGHT)

        # 閾値スライダー
        thresh_frame = tk.Frame(self)
        thresh_frame.pack(fill=tk.X, padx=10, pady=(0, 4))
        tk.Label(thresh_frame, text="閾値:", font=("MS Gothic", 9)).pack(side=tk.LEFT)
        self._var_threshold = tk.DoubleVar(value=self._parent_threshold)
        self._lbl_thresh_val = tk.Label(thresh_frame,
                                        text=f"{self._parent_threshold*100:.0f}%",
                                        font=("MS Gothic", 10, "bold"), width=5,
                                        fg="#0055cc")
        self._lbl_thresh_val.pack(side=tk.RIGHT)
        self._scale = tk.Scale(thresh_frame, variable=self._var_threshold,
                               from_=0.10, to=1.0, resolution=0.01,
                               orient=tk.HORIZONTAL, showvalue=False,
                               command=self._on_threshold_change)
        self._scale.pack(fill=tk.X, expand=True)

        # サムネイル一覧（スクロール可能）
        self._list_frame = tk.Frame(self, bd=1, relief=tk.SUNKEN)
        self._list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(4, 4))

        self._canvas = tk.Canvas(self._list_frame, bg="#ffffff", highlightthickness=0)
        self._scrollbar = tk.Scrollbar(self._list_frame, orient=tk.VERTICAL,
                                       command=self._canvas.yview)
        self._inner = tk.Frame(self._canvas, bg="#ffffff")

        self._inner.bind("<Configure>",
                         lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")))
        self._canvas.create_window((0, 0), window=self._inner, anchor="nw")
        self._canvas.configure(yscrollcommand=self._scrollbar.set)

        self._scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # マウスホイール: スクロール / Ctrl+ホイール: サムネイルサイズ変更
        def _on_mousewheel(event):
            if event.state & 0x4:  # Ctrl押下
                self._resize_thumbnails(event.delta)
            else:
                self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.bind("<MouseWheel>", _on_mousewheel)
        self._canvas.bind("<MouseWheel>", _on_mousewheel)
        self._inner.bind("<MouseWheel>", _on_mousewheel)
        self._mousewheel_handler = _on_mousewheel

        # サムネイルグリッドを描画
        self._render_grid()

        # 実行設定フレーム
        exec_frame = tk.LabelFrame(self, text="この群を実行", font=("MS Gothic", 9),
                                   padx=6, pady=4)
        exec_frame.pack(fill=tk.X, padx=10, pady=(4, 4))

        exec_row = tk.Frame(exec_frame)
        exec_row.pack(fill=tk.X)
        # フォルダ名入力
        tk.Label(exec_row, text="フォルダ名:", font=("MS Gothic", 8)).pack(side=tk.LEFT)
        self._var_folder_name = tk.StringVar(
            value=f"グループ_{self.group['group_num']:03d}")
        tk.Entry(exec_row, textvariable=self._var_folder_name,
                 font=("MS Gothic", 8), width=16).pack(side=tk.LEFT, padx=(2, 8))

        # 単語入力
        tk.Label(exec_row, text="単語:", font=("MS Gothic", 8)).pack(side=tk.LEFT)
        self._var_word = tk.StringVar(value="")
        tk.Entry(exec_row, textvariable=self._var_word,
                 font=("MS Gothic", 8), width=12).pack(side=tk.LEFT, padx=(2, 4))

        exec_row2 = tk.Frame(exec_frame)
        exec_row2.pack(fill=tk.X, pady=(4, 0))
        tk.Button(exec_row2, text="フォルダに移動", font=("MS Gothic", 8),
                  command=lambda: self._execute_group("move")).pack(side=tk.LEFT, padx=(0, 4))
        tk.Button(exec_row2, text="リネーム", font=("MS Gothic", 8),
                  command=lambda: self._execute_group("rename")).pack(side=tk.LEFT, padx=(0, 4))
        tk.Button(exec_row2, text="移動+リネーム", font=("MS Gothic", 8),
                  command=lambda: self._execute_group("both")).pack(side=tk.LEFT)

        # 下部ボタン
        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=(4, 8))
        tk.Button(btn_frame, text="全選択", font=("MS Gothic", 8),
                  command=lambda: self._set_all(True)).pack(side=tk.LEFT, padx=4)
        tk.Button(btn_frame, text="全解除", font=("MS Gothic", 8),
                  command=lambda: self._set_all(False)).pack(side=tk.LEFT, padx=4)
        tk.Button(btn_frame, text="適用して閉じる", font=("MS Gothic", 9, "bold"),
                  command=self._apply_and_close).pack(side=tk.LEFT, padx=(12, 4))

    def _render_grid(self):
        """サムネイルグリッドを描画（サイズ変更・閾値変更時にも呼ばれる）"""
        # 既存のチェック状態をパス単位で保存
        old_check_map = {}
        if self._member_vars:
            for path, var in zip(self._prev_members, self._member_vars):
                old_check_map[path] = var.get()

        self._prev_members = list(self.group["members"])

        # 内部フレームをクリア
        for w in self._inner.winfo_children():
            w.destroy()
        self._thumb_refs = []
        self._member_vars = []

        cols = self._cols
        size = self._thumb_size
        max_name_len = max(14, size // 7)

        for i, path in enumerate(self.group["members"]):
            r, c = divmod(i, cols)
            cell = tk.Frame(self._inner, bg="#ffffff", padx=2, pady=2)
            cell.grid(row=r, column=c, sticky="nsew")
            cell.bind("<MouseWheel>", self._mousewheel_handler)

            # サムネイル
            try:
                with Image.open(path) as img:
                    img.thumbnail((size, size))
                    tk_img = ImageTk.PhotoImage(img)
                    self._thumb_refs.append(tk_img)
                    lbl = tk.Label(cell, image=tk_img, bg="#ffffff")
                    lbl.pack()
                    lbl.bind("<MouseWheel>", self._mousewheel_handler)
            except Exception:
                tk.Label(cell, text="?", bg="#eeeeee",
                         width=size // 8, height=size // 16).pack()

            # 類似度表示
            sim = self._all_similarities.get(path)
            sim_text = f" ({sim*100:.0f}%)" if sim is not None and path != self._seed_path else ""

            # ファイル名 + 類似度 + チェックボックス（名前の後に配置）
            name_row = tk.Frame(cell, bg="#ffffff")
            name_row.pack(fill=tk.X)
            name_row.bind("<MouseWheel>", self._mousewheel_handler)

            name = os.path.basename(path)
            if len(name) > max_name_len:
                name = name[:max_name_len - 3] + "..."
            lbl_name = tk.Label(name_row, text=name + sim_text,
                                font=("MS Gothic", 7),
                                bg="#ffffff", fg="#666666")
            lbl_name.pack(side=tk.LEFT)
            lbl_name.bind("<MouseWheel>", self._mousewheel_handler)

            # チェック状態: パスが以前あればその状態を引き継ぎ、新規はTrue
            default_checked = old_check_map.get(path, True)
            var = tk.BooleanVar(value=default_checked)
            self._member_vars.append(var)
            cb = tk.Checkbutton(name_row, variable=var, bg="#ffffff",
                                activebackground="#ffffff",
                                command=self._update_count)
            cb.pack(side=tk.LEFT)

        for c in range(cols):
            self._inner.columnconfigure(c, weight=1)

    def _resize_thumbnails(self, delta):
        """Ctrl+ホイールでサムネイルサイズ変更"""
        step = 20
        if delta > 0:
            self._thumb_size = min(300, self._thumb_size + step)
        else:
            self._thumb_size = max(40, self._thumb_size - step)
        self._render_grid()

    def _on_threshold_change(self, value):
        """閾値スライダー変更時: メンバーをリアルタイム更新"""
        thresh = float(value)
        self._lbl_thresh_val.config(text=f"{thresh*100:.0f}%")

        if not self._all_similarities:
            return

        # 閾値以上の画像を収集（シードは常に含む）
        new_members = []
        for path, sim in self._all_similarities.items():
            if sim >= thresh and os.path.isfile(path):
                new_members.append(path)

        # シードを先頭にし、残りは類似度降順
        if self._seed_path in new_members:
            new_members.remove(self._seed_path)
        new_members.sort(key=lambda p: self._all_similarities.get(p, 0), reverse=True)
        new_members.insert(0, self._seed_path)

        self.group["members"] = new_members
        self._render_grid()
        self._update_count()

    def _set_all(self, value):
        for var in self._member_vars:
            var.set(value)
        self._update_count()

    def _update_count(self):
        checked = sum(1 for v in self._member_vars if v.get())
        total = len(self._member_vars)
        self._lbl_header.config(
            text=f"グループ {self.group['group_num']}: {checked}/{total}枚 選択中")

    def _get_checked_members(self):
        """チェックされたメンバーのパスリストを返す"""
        return [path for path, var in zip(self.group["members"], self._member_vars)
                if var.get()]

    def _execute_group(self, mode):
        """この群のみ実行（move / rename / both）"""
        members = self._get_checked_members()
        if not members:
            return

        parent = self.parent_dialog
        folder = parent.folder

        # リネーム設定を親ダイアログから取得
        rename_config = None
        if mode in ("rename", "both"):
            word = self._var_word.get().strip()
            if not word:
                messagebox.showwarning("入力エラー", "単語を入力してください",
                                          parent=self)
                return
            if not hasattr(parent, 'var_position'):
                messagebox.showwarning("設定不足",
                    "リネーム設定は確認画面のモード設定から行ってください",
                    parent=self)
                return
            rename_config = {
                "word": word,
                "position": parent.var_position.get(),
                "num_type": parent.var_num_type.get(),
                "digits": parent.var_digits.get(),
                "separator": parent.var_separator.get(),
            }

        folder_name = self._var_folder_name.get().strip()
        if mode in ("move", "both") and not folder_name:
            folder_name = f"グループ_{self.group['group_num']:03d}"

        def _do_execute():
            try:
                current_members = list(members)

                # フォルダ移動
                if mode in ("move", "both"):
                    group_folder = os.path.join(folder, folder_name)
                    os.makedirs(group_folder, exist_ok=True)
                    new_members = []
                    for fp in current_members:
                        try:
                            parent.move_callback(fp, group_folder, refresh=False)
                            new_members.append(os.path.join(
                                group_folder, os.path.basename(fp)))
                        except TypeError:
                            parent.move_callback(fp, group_folder)
                            new_members.append(os.path.join(
                                group_folder, os.path.basename(fp)))
                        except Exception:
                            new_members.append(fp)
                    current_members = new_members

                # リネーム
                if mode in ("rename", "both") and rename_config:
                    word = rename_config["word"]
                    sep = rename_config["separator"]
                    digits = rename_config["digits"]
                    use_alpha = rename_config["num_type"] == "alpha"
                    is_prefix = rename_config["position"] == "prefix"
                    for file_idx, fp in enumerate(current_members):
                        try:
                            dirname = os.path.dirname(fp)
                            stem, ext = os.path.splitext(os.path.basename(fp))
                            num = parent._format_number(file_idx, digits, use_alpha)
                            if is_prefix:
                                new_name = f"{word}{sep}{num}{sep}{stem}{ext}"
                            else:
                                new_name = f"{stem}{sep}{word}{sep}{num}{ext}"
                            os.rename(fp, os.path.join(dirname, new_name))
                        except Exception:
                            pass

                if parent.refresh_callback:
                    self.after(0, lambda: parent.refresh_callback(parent.folder))
                self.after(0, lambda: messagebox.showinfo(
                    "完了", f"グループ {self.group['group_num']} の処理が完了しました",
                    parent=self))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror(
                    "エラー", str(e), parent=self))

        threading.Thread(target=_do_execute, daemon=True).start()

    def _apply_and_close(self):
        """チェック状態を反映してグループのメンバーを更新"""
        new_members = [
            path for path, var in zip(self.group["members"], self._member_vars)
            if var.get()
        ]
        self.group["members"] = new_members

        # 親ダイアログのグループ一覧の枚数表示を更新
        if hasattr(self.parent_dialog, '_update_group_counts'):
            self.parent_dialog._update_group_counts()

        self.destroy()

    def _on_close(self):
        self._apply_and_close()


class AutoSortDialog(tk.Toplevel):
    """オート仕分けダイアログ: フォルダ内の全画像が群体/孤立になるまで自動処理する"""

    def __init__(self, parent, folder, move_callback, refresh_callback):
        super().__init__(parent)
        self.title("オート仕分け")
        self.geometry("520x560")
        self.attributes("-topmost", True)
        self.resizable(False, False)

        self.folder = folder
        self.move_callback = move_callback
        self.refresh_callback = refresh_callback
        self.stop_flag = False
        self._thread = None

        # ベクトルキャッシュ（初回計算後に保持）
        self._vec_cache = None
        # サムネイル参照保持（GC防止）
        self._thumb_refs = []
        # 全グループ（確認画面で表示中）
        self.all_groups = []

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.transient(parent)

    def _build_ui(self):
        tk.Label(self, text=f"フォルダ: {os.path.basename(self.folder)}",
                 font=("MS Gothic", 10, "bold"), anchor="w", fg="#333333").pack(fill=tk.X, padx=12, pady=(10, 0))
        tk.Label(self, text=self.folder, font=("MS Gothic", 8), anchor="w",
                 fg="#888888", wraplength=490).pack(fill=tk.X, padx=12)

        # 類似度しきい値
        frame_thresh = tk.LabelFrame(self, text="類似度しきい値", font=("MS Gothic", 9), padx=8, pady=4)
        frame_thresh.pack(fill=tk.X, padx=12, pady=(8, 0))

        self.var_threshold = tk.DoubleVar(value=0.80)
        self.lbl_thresh_val = tk.Label(frame_thresh, text="80%",
                                       font=("MS Gothic", 10, "bold"), width=5, fg="#0055cc")
        self.lbl_thresh_val.pack(side=tk.RIGHT)
        self.scale = tk.Scale(frame_thresh, variable=self.var_threshold,
                              from_=0.20, to=1.0, resolution=0.01,
                              orient=tk.HORIZONTAL, showvalue=False,
                              command=lambda v: self.lbl_thresh_val.config(text=f"{float(v)*100:.0f}%"))
        self.scale.pack(fill=tk.X, expand=True)

        # 統計表示
        frame_stats = tk.Frame(self, bd=1, relief=tk.SUNKEN, padx=10, pady=8)
        frame_stats.pack(fill=tk.X, padx=12, pady=8)

        def stat_col(label, color="#000000"):
            f = tk.Frame(frame_stats)
            f.pack(side=tk.LEFT, padx=(0, 20))
            tk.Label(f, text=label, font=("MS Gothic", 8), fg="#666666").pack()
            var = tk.StringVar(value="-")
            tk.Label(f, textvariable=var, font=("MS Gothic", 13, "bold"), fg=color).pack()
            return var

        self.var_total     = stat_col("総数")
        self.var_processed = stat_col("処理済")
        self.var_groups    = stat_col("グループ", "#0055cc")
        self.var_isolated  = stat_col("孤立", "#888888")

        self.lbl_status = tk.Label(self, text="閾値を設定して「分析開始」を押してください",
                                   font=("MS Gothic", 9), fg="#0055aa", anchor="w")
        self.lbl_status.pack(fill=tk.X, padx=12)

        # ログ
        self._log_frame = tk.Frame(self)
        self._log_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(4, 0))
        self.txt_log = tk.Text(self._log_frame, font=("MS Gothic", 8), state=tk.DISABLED,
                               bg="#f8f8f8", relief=tk.SUNKEN, bd=1)
        sb = tk.Scrollbar(self._log_frame, command=self.txt_log.yview)
        self.txt_log.config(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt_log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # ボタン
        self._btn_frame = tk.Frame(self)
        self._btn_frame.pack(pady=10)
        self.btn_action = tk.Button(self._btn_frame, text="分析開始", width=12,
                                    command=self._start_analysis, font=("MS Gothic", 10))
        self.btn_action.pack(side=tk.LEFT, padx=5)
        self.btn_close = tk.Button(self._btn_frame, text="閉じる", width=10,
                                   command=self._on_close, font=("MS Gothic", 10))
        self.btn_close.pack(side=tk.LEFT, padx=5)

    def _log(self, msg):
        def _do():
            self.txt_log.config(state=tk.NORMAL)
            self.txt_log.insert(tk.END, msg + "\n")
            self.txt_log.see(tk.END)
            self.txt_log.config(state=tk.DISABLED)
        self.after(0, _do)

    def _set_status(self, msg):
        self.after(0, lambda: self.lbl_status.config(text=msg))

    def _set_stats(self, **kwargs):
        def _do():
            if "total"     in kwargs: self.var_total.set(str(kwargs["total"]))
            if "processed" in kwargs: self.var_processed.set(str(kwargs["processed"]))
            if "groups"    in kwargs: self.var_groups.set(str(kwargs["groups"]))
            if "isolated"  in kwargs: self.var_isolated.set(str(kwargs["isolated"]))
        self.after(0, _do)

    def _stop(self):
        self.stop_flag = True
        self.after(0, lambda: self.btn_action.config(state=tk.DISABLED))
        self._set_status("停止中...")
        self._log("--- 停止要求を受け付けました ---")

    def _start_analysis(self):
        """分析を開始（初回はベクトル計算+クラスタリング、2回目以降はクラスタリングのみ）"""
        self.stop_flag = False
        self.scale.config(state=tk.DISABLED)
        self.btn_action.config(text="停止", command=self._stop, state=tk.NORMAL)
        self.btn_close.config(state=tk.DISABLED)
        self._thread = threading.Thread(target=self._run_sort, daemon=True)
        self._thread.start()

    def _on_close(self):
        if self._thread and self._thread.is_alive():
            self.stop_flag = True
        try:
            self.unbind_all("<MouseWheel>")
        except Exception:
            pass
        self.destroy()

    def _create_group_folder(self, group_num):
        path = os.path.join(self.folder, f"グループ_{group_num:03d}")
        os.makedirs(path, exist_ok=True)
        return path

    def _finish(self, stopped=False, group_count=0, isolated_count=0):
        if stopped:
            self._set_status("停止しました")
            self._log("--- 処理を停止しました ---")
        else:
            msg = f"完了！ グループ: {group_count}件  孤立: {isolated_count}枚"
            self._set_status(msg)
            self._log(f"--- {msg} ---")

        def _ui():
            self.btn_action.config(text="分析開始", command=self._start_analysis,
                                   state=tk.NORMAL)
            self.btn_close.config(text="閉じる", state=tk.NORMAL)
            self.scale.config(state=tk.NORMAL)
        self.after(0, _ui)

    def _run_sort(self):
        try:
            from PicSorterGUILogic import calculate_file_hash, load_vectors, save_vectors

            # ベクトル計算（初回のみ）
            if self._vec_cache is None:
                self._set_status("画像を読み込み中...")
                all_items = os.listdir(self.folder)
                files = GetGazoFiles(all_items, self.folder)
                total = len(files)

                if total == 0:
                    self._set_status("画像がありません")
                    self._log("フォルダに対象画像がありませんでした")
                    self._finish()
                    return

                self._set_stats(total=total, processed=0, groups=0, isolated=0)
                self._log(f"対象画像: {total}枚")

                self._set_status("AIモデルを準備中...")
                engine = VectorEngine.get_instance()

                try:
                    vectors = load_vectors()
                except Exception:
                    vectors = {}

                full_paths = [os.path.join(self.folder, f) for f in files]
                hash_map = {}
                vec_map = {}

                start_time = time.time()
                for i, path in enumerate(full_paths):
                    if self.stop_flag:
                        self._finish(stopped=True)
                        return

                    # 経過時間と推定残り時間
                    elapsed = time.time() - start_time
                    elapsed_str = self._format_elapsed(elapsed)
                    if i > 0:
                        avg = elapsed / i
                        remaining = avg * (total - i)
                        eta_str = self._format_elapsed(remaining)
                        time_info = f" [{elapsed_str} / 残り約{eta_str}]"
                    else:
                        time_info = ""

                    fname = os.path.basename(path)
                    self._set_status(
                        f"ベクトル計算中... {i+1}/{total} {fname}{time_info}")
                    try:
                        h = calculate_file_hash(path)
                        hash_map[path] = h
                        if h not in vectors:
                            vec = engine.get_image_feature(path)
                            if vec:
                                vectors[h] = vec
                        if h in vectors:
                            vec_map[h] = vectors[h]
                    except Exception as e:
                        self._log(f"スキップ: {os.path.basename(path)} ({e})")

                total_elapsed = time.time() - start_time
                self._log(f"ベクトル計算完了: {self._format_elapsed(total_elapsed)}")

                try:
                    save_vectors(vectors)
                except Exception:
                    pass

                self._vec_cache = {
                    "hash_map": hash_map,
                    "vec_map": vec_map,
                    "engine": engine,
                    "full_paths": full_paths,
                }
            else:
                self._log("キャッシュ済みベクトルを使用")

            # キャッシュからデータ取得
            hash_map = self._vec_cache["hash_map"]
            vec_map = self._vec_cache["vec_map"]
            engine = self._vec_cache["engine"]

            # 移動・リネーム済みファイルを除外（現在フォルダに存在するもののみ）
            current_files = set()
            try:
                for f in os.listdir(self.folder):
                    fp = os.path.join(self.folder, f)
                    if os.path.isfile(fp):
                        current_files.add(fp)
            except Exception:
                pass

            full_paths = [p for p in self._vec_cache["full_paths"]
                          if p in current_files]

            if not full_paths:
                self._set_status("フォルダに対象画像がありません")
                self._log("移動済み等により対象画像がなくなりました")
                self._finish()
                return

            threshold = self.var_threshold.get()
            self._log(f"しきい値: {threshold*100:.0f}%  対象: {len(full_paths)}枚")

            # 貪欲クラスタリング（全画像対象）
            unprocessed = list(full_paths)
            unprocessed_set = set(full_paths)
            group_count = 0
            isolated_count = 0
            processed_count = 0
            groups = []

            self._set_stats(total=len(full_paths), processed=0, groups=0, isolated=0)
            self._set_status("グループ分析中...")

            while unprocessed and not self.stop_flag:
                while unprocessed and unprocessed[0] not in unprocessed_set:
                    unprocessed.pop(0)
                if not unprocessed:
                    break

                seed_path = unprocessed.pop(0)
                unprocessed_set.discard(seed_path)

                seed_hash = hash_map.get(seed_path)
                if not seed_hash or seed_hash not in vec_map:
                    isolated_count += 1
                    processed_count += 1
                    self._set_stats(processed=processed_count, isolated=isolated_count)
                    continue

                seed_vec = vec_map[seed_hash]

                similar_paths = []
                for candidate in unprocessed:
                    if candidate not in unprocessed_set:
                        continue
                    c_hash = hash_map.get(candidate)
                    if not c_hash or c_hash not in vec_map:
                        continue
                    if engine.compare_features(seed_vec, vec_map[c_hash]) >= threshold:
                        similar_paths.append(candidate)

                processed_count += 1

                if similar_paths:
                    group_count += 1
                    group_members = [seed_path] + similar_paths
                    groups.append({
                        "group_num": group_count,
                        "members": group_members,
                    })
                    self._log(f"グループ {group_count}: {len(group_members)}枚")

                    for fp in similar_paths:
                        unprocessed_set.discard(fp)

                    processed_count += len(similar_paths)
                    self._set_stats(processed=processed_count, groups=group_count)
                else:
                    isolated_count += 1
                    self._set_stats(processed=processed_count, isolated=isolated_count)

            if self.stop_flag:
                self._finish(stopped=True)
            elif not groups:
                self._set_status("グループが見つかりませんでした")
                self._log("類似画像のグループは見つかりませんでした")
                self._finish(stopped=False, group_count=0, isolated_count=isolated_count)
            else:
                self.all_groups = groups
                self._set_status(f"分析完了: {len(groups)}グループ / 孤立{isolated_count}枚")
                self._log(f"--- 分析完了: {len(groups)}グループ / 孤立{isolated_count}枚 ---")
                self.after(0, self._show_confirmation)

        except Exception as e:
            logger.error(f"オート仕分けエラー: {e}", exc_info=True)
            self._set_status(f"エラー: {e}")
            self._log(f"エラーが発生しました: {e}")
            self.after(0, lambda: self.btn_close.config(state=tk.NORMAL))

    def _load_thumbnail(self, path, size=(64, 64)):
        """サムネイル画像を読み込んでImageTk.PhotoImageを返す"""
        try:
            with Image.open(path) as img:
                img.thumbnail(size)
                tk_img = ImageTk.PhotoImage(img)
                self._thumb_refs.append(tk_img)
                return tk_img
        except Exception:
            return None

    def _show_confirmation(self):
        """クラスタリング結果の確認UIを表示（サムネイル付き、クリックで詳細）"""
        self._thumb_refs = []

        # ログエリアを非表示にして確認フレームに差し替え
        self._log_frame.pack_forget()

        # 確認用フレーム
        self._confirm_frame = tk.Frame(self)
        self._confirm_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(4, 0))

        # === 実行モード設定 ===
        mode_frame = tk.LabelFrame(self._confirm_frame, text="実行モード",
                                   font=("MS Gothic", 9), padx=6, pady=4)
        mode_frame.pack(fill=tk.X, pady=(0, 4))

        self.var_do_move = tk.BooleanVar(value=True)
        self.var_do_rename = tk.BooleanVar(value=False)

        mode_row = tk.Frame(mode_frame)
        mode_row.pack(fill=tk.X)
        tk.Checkbutton(mode_row, text="フォルダに移動", variable=self.var_do_move,
                       font=("MS Gothic", 9),
                       command=self._on_mode_change).pack(side=tk.LEFT, padx=(0, 12))
        tk.Checkbutton(mode_row, text="ファイル名を変更", variable=self.var_do_rename,
                       font=("MS Gothic", 9),
                       command=self._on_mode_change).pack(side=tk.LEFT)

        # リネーム設定フレーム（リネームモード時のみ表示）
        self._rename_frame = tk.Frame(mode_frame)

        rename_row1 = tk.Frame(self._rename_frame)
        rename_row1.pack(fill=tk.X, pady=(4, 2))
        tk.Label(rename_row1, text="位置:", font=("MS Gothic", 8)).pack(side=tk.LEFT)
        self.var_position = tk.StringVar(value="prefix")
        tk.Radiobutton(rename_row1, text="前に追加", variable=self.var_position,
                       value="prefix", font=("MS Gothic", 8),
                       command=self._update_rename_preview).pack(side=tk.LEFT, padx=(4, 8))
        tk.Radiobutton(rename_row1, text="後ろに追加", variable=self.var_position,
                       value="suffix", font=("MS Gothic", 8),
                       command=self._update_rename_preview).pack(side=tk.LEFT)

        rename_row2 = tk.Frame(self._rename_frame)
        rename_row2.pack(fill=tk.X, pady=2)
        tk.Label(rename_row2, text="番号:", font=("MS Gothic", 8)).pack(side=tk.LEFT)
        self.var_num_type = tk.StringVar(value="number")
        tk.Radiobutton(rename_row2, text="番号(01,02...)", variable=self.var_num_type,
                       value="number", font=("MS Gothic", 8),
                       command=self._update_rename_preview).pack(side=tk.LEFT, padx=(4, 8))
        tk.Radiobutton(rename_row2, text="アルファベット(a,b...)", variable=self.var_num_type,
                       value="alpha", font=("MS Gothic", 8),
                       command=self._update_rename_preview).pack(side=tk.LEFT)

        rename_row3 = tk.Frame(self._rename_frame)
        rename_row3.pack(fill=tk.X, pady=2)
        tk.Label(rename_row3, text="桁数:", font=("MS Gothic", 8)).pack(side=tk.LEFT)
        self.var_digits = tk.IntVar(value=2)
        sp = tk.Spinbox(rename_row3, from_=1, to=4, textvariable=self.var_digits,
                   width=3, font=("MS Gothic", 8),
                   command=self._update_rename_preview)
        sp.pack(side=tk.LEFT, padx=(4, 12))
        tk.Label(rename_row3, text="区切り:", font=("MS Gothic", 8)).pack(side=tk.LEFT)
        self.var_separator = tk.StringVar(value="_")
        sep_entry = tk.Entry(rename_row3, textvariable=self.var_separator, width=3,
                 font=("MS Gothic", 8))
        sep_entry.pack(side=tk.LEFT, padx=4)
        self.var_separator.trace_add("write", lambda *_: self._update_rename_preview())

        # リネームプレビュー
        self._lbl_preview = tk.Label(self._rename_frame, text="",
                                     font=("MS Gothic", 8), fg="#006600", anchor="w")
        self._lbl_preview.pack(fill=tk.X, pady=(2, 0))

        # 一括操作ボタン + ヒント
        ctrl_frame = tk.Frame(self._confirm_frame)
        ctrl_frame.pack(fill=tk.X, pady=(0, 4))
        tk.Button(ctrl_frame, text="全選択", font=("MS Gothic", 8),
                  command=lambda: self._set_all_checks(True)).pack(side=tk.LEFT, padx=(0, 4))
        tk.Button(ctrl_frame, text="全解除", font=("MS Gothic", 8),
                  command=lambda: self._set_all_checks(False)).pack(side=tk.LEFT)
        tk.Label(ctrl_frame, text="(クリックで詳細表示)",
                 font=("MS Gothic", 8), fg="#888888").pack(side=tk.RIGHT)

        # スクロール可能なグループ一覧
        list_frame = tk.Frame(self._confirm_frame, bd=1, relief=tk.SUNKEN)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self._canvas = tk.Canvas(list_frame, bg="#f8f8f8", highlightthickness=0)
        scrollbar = tk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self._canvas.yview)
        self._inner_frame = tk.Frame(self._canvas, bg="#f8f8f8")

        self._inner_frame.bind(
            "<Configure>",
            lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all"))
        )
        self._canvas.create_window((0, 0), window=self._inner_frame, anchor="nw")
        self._canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # マウスホイールスクロール
        def _on_mousewheel(event):
            self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.bind_all("<MouseWheel>", _on_mousewheel)

        # グループ一覧表示
        self._group_vars = []
        self._group_folder_entries = []
        self._group_word_entries = []
        self._group_checkbuttons = []
        for group in self.all_groups:
            var = tk.BooleanVar(value=True)
            self._group_vars.append(var)
            row = tk.Frame(self._inner_frame, bg="#f0f4ff", bd=1, relief=tk.GROOVE)
            row.pack(fill=tk.X, padx=6, pady=2)

            # サムネイル
            thumb = self._load_thumbnail(group["members"][0])
            if thumb:
                lbl_img = tk.Label(row, image=thumb, bg="#f0f4ff", cursor="hand2")
                lbl_img.pack(side=tk.LEFT, padx=(4, 6), pady=2)
                lbl_img.bind("<Button-1>", lambda e, g=group: self._open_group_detail(g))

            cb = tk.Checkbutton(
                row, variable=var, bg="#f0f4ff", activebackground="#f0f4ff",
                text=f"{len(group['members'])}枚",
                font=("MS Gothic", 9), anchor="w",
            )
            cb.pack(side=tk.LEFT)
            self._group_checkbuttons.append(cb)

            # フォルダ名入力欄
            folder_var = tk.StringVar(value=f"グループ_{group['group_num']:03d}")
            tk.Entry(row, textvariable=folder_var, font=("MS Gothic", 9),
                     width=14).pack(side=tk.LEFT, padx=(4, 2))
            self._group_folder_entries.append(folder_var)

            # 単語入力欄
            word_var = tk.StringVar(value="")
            tk.Entry(row, textvariable=word_var, font=("MS Gothic", 9),
                     width=10).pack(side=tk.LEFT, padx=(2, 4))
            self._group_word_entries.append(word_var)

            # 詳細ボタン
            btn_detail = tk.Button(row, text="詳細", font=("MS Gothic", 8),
                                   command=lambda g=group: self._open_group_detail(g),
                                   bg="#dde4f0", relief=tk.FLAT, cursor="hand2")
            btn_detail.pack(side=tk.RIGHT, padx=(0, 4), pady=2)

        # 閾値スライダーを有効化
        self.scale.config(state=tk.NORMAL)

        # ボタンを差し替え: 「再分析」「実行」「閉じる」
        for w in self._btn_frame.winfo_children():
            w.destroy()

        self.btn_reanalyze = tk.Button(self._btn_frame, text="再分析", width=10,
                                       command=self._start_reanalyze, font=("MS Gothic", 10))
        self.btn_reanalyze.pack(side=tk.LEFT, padx=5)
        self.btn_action = tk.Button(self._btn_frame, text="実行", width=10,
                                    command=self._execute_selected, font=("MS Gothic", 10))
        self.btn_action.pack(side=tk.LEFT, padx=5)
        self.btn_close = tk.Button(self._btn_frame, text="閉じる", width=10,
                                   command=self._on_close, font=("MS Gothic", 10))
        self.btn_close.pack(side=tk.LEFT, padx=5)

        # ウィンドウサイズ調整
        self.geometry("520x620")

    def _on_mode_change(self):
        """モード切替時にリネーム設定の表示/非表示を切り替え"""
        do_rename = self.var_do_rename.get()
        if do_rename:
            self._rename_frame.pack(fill=tk.X)
            self._update_rename_preview()
        else:
            self._rename_frame.pack_forget()

    def _update_rename_preview(self):
        """リネーム例のプレビューを更新"""
        if not hasattr(self, '_lbl_preview'):
            return
        try:
            sep = self.var_separator.get()
            digits = self.var_digits.get()
            use_alpha = self.var_num_type.get() == "alpha"
            is_prefix = self.var_position.get() == "prefix"
            num = self._format_number(0, digits, use_alpha)
            word = "<単語>"

            if is_prefix:
                example = f"{word}{sep}{num}{sep}photo.jpg"
            else:
                example = f"photo{sep}{word}{sep}{num}.jpg"

            self._lbl_preview.config(text=f"例: {example}")
        except Exception:
            self._lbl_preview.config(text="")

    def _update_group_counts(self):
        """グループ一覧の枚数表示を更新（詳細ウィンドウでメンバー変更後）"""
        if not hasattr(self, '_group_checkbuttons'):
            return
        for group, cb_widget in zip(self.all_groups, self._group_checkbuttons):
            cb_widget.config(text=f"{len(group['members'])}枚")

    def _open_group_detail(self, group):
        """グループ詳細ウィンドウを開く"""
        GroupDetailWindow(self, group)

    def _set_all_checks(self, value):
        for var in self._group_vars:
            var.set(value)

    def _start_reanalyze(self):
        """再分析を開始（全画像対象でグローバル再クラスタリング）"""
        # 確認フレームを破棄
        try:
            self.unbind_all("<MouseWheel>")
        except Exception:
            pass
        if hasattr(self, '_confirm_frame') and self._confirm_frame.winfo_exists():
            self._confirm_frame.destroy()
        self._thumb_refs = []

        # ログ表示に戻す
        self._log_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(4, 0))

        # ボタンを再構築
        for w in self._btn_frame.winfo_children():
            w.destroy()
        self.btn_action = tk.Button(self._btn_frame, text="停止", width=12,
                                    command=self._stop, font=("MS Gothic", 10))
        self.btn_action.pack(side=tk.LEFT, padx=5)
        self.btn_close = tk.Button(self._btn_frame, text="閉じる", width=10,
                                   command=self._on_close, font=("MS Gothic", 10),
                                   state=tk.DISABLED)
        self.btn_close.pack(side=tk.LEFT, padx=5)

        self._log(f"\n--- 再分析開始 (しきい値: {self.var_threshold.get()*100:.0f}%) ---")
        self.stop_flag = False
        self.scale.config(state=tk.DISABLED)
        self.geometry("520x560")
        self._thread = threading.Thread(target=self._run_sort, daemon=True)
        self._thread.start()

    def _format_elapsed(self, seconds):
        """秒数を 分:秒 or 時:分:秒 の文字列に変換"""
        s = int(seconds)
        if s < 60:
            return f"{s}秒"
        elif s < 3600:
            return f"{s // 60}分{s % 60:02d}秒"
        else:
            return f"{s // 3600}時間{(s % 3600) // 60:02d}分{s % 60:02d}秒"

    def _format_number(self, idx, digits, use_alpha):
        """ナンバリング文字列を生成"""
        if use_alpha:
            # a, b, ..., z, aa, ab, ...
            result = ""
            n = idx
            for _ in range(digits):
                result = chr(ord('a') + (n % 26)) + result
                n //= 26
            return result
        else:
            return str(idx + 1).zfill(digits)

    def _execute_selected(self):
        """チェックONのグループをモードに応じて実行"""
        do_move = self.var_do_move.get()
        do_rename = self.var_do_rename.get()

        if not do_move and not do_rename:
            self._set_status("実行モードを選択してください")
            return

        selected = []
        for group, var, folder_var, word_var in zip(
                self.all_groups, self._group_vars,
                self._group_folder_entries, self._group_word_entries):
            if var.get():
                group["folder_name"] = folder_var.get()
                group["word"] = word_var.get()
                selected.append(group)

        if not selected:
            self._set_status("グループが選択されていません")
            return

        # リネーム時に単語が空のグループをチェック
        if do_rename:
            empty = [g for g in selected if not g["word"].strip()]
            if empty:
                self._set_status(f"単語が未入力のグループがあります ({len(empty)}件)")
                return

        # 設定を保存
        self._exec_config = {
            "do_move": do_move,
            "do_rename": do_rename,
            "position": self.var_position.get() if do_rename else None,
            "num_type": self.var_num_type.get() if do_rename else None,
            "digits": self.var_digits.get() if do_rename else None,
            "separator": self.var_separator.get() if do_rename else None,
        }

        # 確認フレームを削除してログ表示に戻す
        try:
            self.unbind_all("<MouseWheel>")
        except Exception:
            pass
        self._confirm_frame.destroy()
        self._thumb_refs = []
        self._log_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(4, 0))

        # ボタンを再構築
        for w in self._btn_frame.winfo_children():
            w.destroy()
        self.btn_action = tk.Button(self._btn_frame, text="停止", width=12,
                                    command=self._stop, font=("MS Gothic", 10))
        self.btn_action.pack(side=tk.LEFT, padx=5)
        self.btn_close = tk.Button(self._btn_frame, text="閉じる", width=10,
                                   command=self._on_close, font=("MS Gothic", 10),
                                   state=tk.DISABLED)
        self.btn_close.pack(side=tk.LEFT, padx=5)

        self._selected_groups = selected
        self.stop_flag = False
        self.geometry("520x560")
        self._thread = threading.Thread(target=self._run_execute, daemon=True)
        self._thread.start()

    def _run_execute(self):
        """選択グループの実行（フォルダ移動 / リネーム / 両方）"""
        try:
            config = self._exec_config
            do_move = config["do_move"]
            do_rename = config["do_rename"]
            done_groups = 0
            total_selected = len(self._selected_groups)

            for idx, group in enumerate(self._selected_groups):
                if self.stop_flag:
                    break
                members = list(group["members"])

                # フォルダに移動
                if do_move:
                    folder_name = (group.get("folder_name", "").strip()
                                   or f"グループ_{group['group_num']:03d}")
                    group_folder = os.path.join(self.folder, folder_name)
                    os.makedirs(group_folder, exist_ok=True)

                    self._set_status(f"移動中... ({idx+1}/{total_selected})")
                    self._log(f"{folder_name}: {len(members)}枚")

                    new_members = []
                    for fp in members:
                        if self.stop_flag:
                            break
                        try:
                            self.move_callback(fp, group_folder, refresh=False)
                            new_members.append(os.path.join(
                                group_folder, os.path.basename(fp)))
                        except TypeError:
                            self.move_callback(fp, group_folder)
                            new_members.append(os.path.join(
                                group_folder, os.path.basename(fp)))
                        except Exception as e:
                            self._log(f"  移動失敗: {os.path.basename(fp)} ({e})")
                            new_members.append(fp)
                    members = new_members

                # リネーム
                if do_rename:
                    word = (group.get("word", "").strip())
                    sep = config["separator"]
                    digits = config["digits"]
                    use_alpha = config["num_type"] == "alpha"
                    is_prefix = config["position"] == "prefix"

                    self._set_status(f"リネーム中... ({idx+1}/{total_selected})")
                    self._log(f"「{word}」: {len(members)}枚")

                    for file_idx, fp in enumerate(members):
                        if self.stop_flag:
                            break
                        try:
                            dirname = os.path.dirname(fp)
                            basename = os.path.basename(fp)
                            stem, ext = os.path.splitext(basename)
                            num = self._format_number(file_idx, digits, use_alpha)

                            if is_prefix:
                                new_name = f"{word}{sep}{num}{sep}{stem}{ext}"
                            else:
                                new_name = f"{stem}{sep}{word}{sep}{num}{ext}"

                            new_path = os.path.join(dirname, new_name)
                            os.rename(fp, new_path)
                        except Exception as e:
                            self._log(f"  リネーム失敗: {os.path.basename(fp)} ({e})")

                done_groups += 1

            if self.refresh_callback:
                self.after(0, lambda: self.refresh_callback(self.folder))

            if self.stop_flag:
                self._log(f"--- 停止: {done_groups}/{total_selected}グループ処理済み ---")
                self._finish(stopped=True)
            else:
                actions = []
                if do_move:
                    actions.append("移動")
                if do_rename:
                    actions.append("リネーム")
                action = "+".join(actions)
                self._log(f"--- 完了: {done_groups}グループを{action}しました ---")
                self._finish(stopped=False, group_count=done_groups,
                             isolated_count=0)

        except Exception as e:
            logger.error(f"仕分け実行エラー: {e}", exc_info=True)
            self._set_status(f"エラー: {e}")
            self._log(f"エラーが発生しました: {e}")
            self.after(0, lambda: self.btn_close.config(state=tk.NORMAL))


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

        self.frame_status_bar = tk.Frame(self, bg="#333333")
        self.frame_status_bar.pack(fill=tk.X, side=tk.TOP)

        self.frame_bot = tk.Frame(self, bg="#dddddd")
        self.frame_bot.pack(fill=tk.BOTH, expand=True, side=tk.TOP)

        self.init_top_frame()
        self.init_control_frame()
        self.init_status_bar()
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

    def init_status_bar(self):
        """分析プロセスの詳細表示バー"""
        self.lbl_detail_step = tk.Label(self.frame_status_bar, text="", bg="#333333", fg="#88ccff",
                                        font=("MS Gothic", 9), anchor="w", padx=10)
        self.lbl_detail_step.pack(side=tk.LEFT)

        self.lbl_detail_file = tk.Label(self.frame_status_bar, text="", bg="#333333", fg="#aaaaaa",
                                        font=("MS Gothic", 9), anchor="w")
        self.lbl_detail_file.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.lbl_detail_progress = tk.Label(self.frame_status_bar, text="", bg="#333333", fg="#00ff00",
                                            font=("MS Gothic", 9, "bold"), anchor="e", padx=10)
        self.lbl_detail_progress.pack(side=tk.RIGHT)

    def _update_detail(self, step="", file="", progress=""):
        """ステータスバーの詳細を更新（メインスレッドから呼ぶ）"""
        if step:
            self.lbl_detail_step.config(text=step)
        if file is not None:
            self.lbl_detail_file.config(text=file)
        if progress is not None:
            self.lbl_detail_progress.config(text=progress)

    def _clear_detail(self):
        self.lbl_detail_step.config(text="")
        self.lbl_detail_file.config(text="")
        self.lbl_detail_progress.config(text="")

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
            from PicSorterGUILogic import (
                calculate_file_hash, load_vectors, save_vectors,
                load_analysis_cache, save_analysis_cache
            )

            folder = os.path.dirname(self.target_file)
            folder_name = os.path.basename(folder)

            # ステップ1: フォルダスキャン（複数フォルダ対応）
            self.after(0, lambda: self._update_detail(
                step="[1/5] フォルダスキャン",
                file=folder_name,
                progress=""))

            # ターゲット画像のフォルダからファイル収集
            all_full_paths = set()
            base_files = GetGazoFiles(os.listdir(folder), folder)
            for f in base_files:
                all_full_paths.add(os.path.normpath(os.path.join(folder, f)))

            # 参照フォルダからファイル収集
            ref_folders = self.app_state.reference_folders
            for ref_entry in ref_folders:
                ref_path = ref_entry.get("path", "")
                include_sub = ref_entry.get("include_subfolders", False)
                if not os.path.isdir(ref_path):
                    continue

                self.after(0, lambda rp=ref_path: self._update_detail(
                    file=os.path.basename(rp),
                    progress=f"スキャン中..."))

                if include_sub:
                    for root_dir, dirs, filenames in os.walk(ref_path):
                        for fn in filenames:
                            if fn.lower().endswith(SUPPORTED_IMAGE_FORMATS):
                                all_full_paths.add(os.path.normpath(os.path.join(root_dir, fn)))
                else:
                    try:
                        ref_items = os.listdir(ref_path)
                        ref_files = GetGazoFiles(ref_items, ref_path)
                        for f in ref_files:
                            all_full_paths.add(os.path.normpath(os.path.join(ref_path, f)))
                    except PermissionError:
                        logger.warning(f"アクセス権限がありません: {ref_path}")

            files_full = sorted(all_full_paths)
            file_count = len(files_full)
            folder_info = f"{folder_name}"
            if ref_folders:
                folder_info += f" + {len(ref_folders)}フォルダ"
            self.after(0, lambda n=file_count, info=folder_info: self._update_detail(
                progress=f"{n}枚検出 ({info})"))

            # ステップ2: キャッシュ確認
            self.after(0, lambda: self._update_detail(
                step="[2/5] キャッシュ確認",
                file=os.path.basename(self.target_file)))
            t_hash = calculate_file_hash(self.target_file)

            # キャッシュキーにフォルダ情報を含める
            ref_key = folder
            if ref_folders:
                sorted_refs = sorted(e["path"] + (":sub" if e.get("include_subfolders") else "") for e in ref_folders)
                ref_key = folder + "|" + "|".join(sorted_refs)
            cached = load_analysis_cache(ref_key, t_hash, file_count)
            if cached is not None:
                valid = all(os.path.exists(path) for path, _ in cached)
                if valid:
                    self.after(0, lambda: self._update_detail(
                        step="キャッシュヒット",
                        file="前回の分析結果を使用",
                        progress=f"{len(cached)}枚"))
                    self.after(0, lambda: self._on_analysis_complete(cached, 0, from_cache=True))
                    return

            # ステップ3: AIモデル準備
            self.after(0, lambda: self._update_detail(
                step="[3/5] AIモデル準備",
                file="ベクトルデータ読み込み中...",
                progress=""))
            engine = VectorEngine.get_instance()
            vectors = load_vectors()
            self.after(0, lambda n=len(vectors): self._update_detail(
                file=f"既存ベクトル: {n:,}件",
                progress=""))

            # 基準画像のベクトル化
            self.after(0, lambda: self._update_detail(
                step="[3/5] 基準画像ベクトル化",
                file=os.path.basename(self.target_file)))
            if t_hash not in vectors:
                vec = engine.get_image_feature(self.target_file)
                if vec: vectors[t_hash] = vec

            t_vec = vectors.get(t_hash)
            if not t_vec:
                self.after(0, lambda: messagebox.showerror("Error", "Failed to compute vector"))
                return

            # ステップ4: 類似度計算
            results = []
            count = 0
            new_vectors = 0
            start_time = time.time()
            vectors_updated = False

            target_norm = os.path.normpath(self.target_file)
            for full_path in files_full:
                if os.path.normpath(full_path) == target_norm:
                    continue

                f_name = os.path.basename(full_path)
                f_hash = calculate_file_hash(full_path)

                if f_hash not in vectors:
                    self.after(0, lambda fn=f_name: self._update_detail(
                        step="[4/5] ベクトル化 + 類似度計算",
                        file=f"[新規] {fn}"))
                    try:
                        v = engine.get_image_feature(full_path)
                        if v:
                            vectors[f_hash] = v
                            vectors_updated = True
                            new_vectors += 1
                    except Exception:
                        pass
                else:
                    if count % 5 == 0:
                        self.after(0, lambda fn=f_name: self._update_detail(
                            step="[4/5] 類似度計算",
                            file=fn))

                if f_hash in vectors:
                    score = engine.compare_features(t_vec, vectors[f_hash])
                    results.append((full_path, score))

                count += 1
                elapsed = time.time() - start_time
                self.after(0, lambda c=count, t=file_count, e=elapsed, nv=new_vectors: self._update_detail(
                    progress=f"{c}/{t}枚  {e:.1f}秒" + (f"  新規{nv}件" if nv > 0 else "")))

            # ステップ5: 保存
            if vectors_updated:
                self.after(0, lambda: self._update_detail(
                    step="[5/5] ベクトルデータ保存",
                    file=f"新規{new_vectors}件を保存中..."))
                save_vectors(vectors)

            self.after(0, lambda: self._update_detail(
                step="[5/5] 結果整理",
                file="スコア順にソート中..."))
            results.sort(key=lambda x: x[1], reverse=True)
            elapsed = time.time() - start_time

            # キャッシュ保存
            self.after(0, lambda: self._update_detail(
                step="[5/5] キャッシュ保存",
                file="分析結果をキャッシュに保存中..."))
            save_analysis_cache(ref_key, t_hash, results, file_count)

            self.after(0, lambda: self._on_analysis_complete(results, elapsed))

        except Exception as e:
            logger.error(f"Analysis error: {e}")
            self.after(0, lambda: messagebox.showerror("Error", str(e)))

    def _on_analysis_complete(self, results, elapsed, from_cache=False):
        if from_cache:
            self.lbl_status.config(text=f"キャッシュから読込 ({len(results)}枚)")
        else:
            self.lbl_status.config(text=f"完了 ({elapsed:.2f}秒, {len(results)}枚)")
        self._clear_detail()
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

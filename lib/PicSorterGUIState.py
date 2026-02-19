'''
PicSorterGUI のアプリケーション状態管理クラス
'''
import os
from lib.PicSorterGUILogger import get_logger

logger = get_logger(__name__)


class AppState:
    """アプリケーション全体の状態を管理するシングルトンクラス"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True

        # フォルダ・ファイル関連
        self.current_folder = os.getcwd()
        self.current_files = []
        self.current_folders = []

        # 移動先フォルダ関連
        self.move_dest_list = [""] * 12
        self.move_reg_idx = 0
        self.move_dest_count = 2

        # UI 表示設定
        self.show_folder_window = False
        self.show_file_window = False
        self.topmost = True

        # スマート移動設定
        self.smart_move_threshold = 0.90
        self.smart_move_show_thumbnails = True

        # スプラッシュ設定
        self.show_splash_tips = False

        # 参照フォルダリスト [{"path": str, "include_subfolders": bool}, ...]
        self.reference_folders = []

        # ウィンドウジオメトリ
        self.window_geometries = {
            "main": None,
            "folder": None,
            "file": None
        }

        # 画像表示サイズ設定
        from lib.config_defaults import (
            DEFAULT_IMAGE_MIN_WIDTH, DEFAULT_IMAGE_MIN_HEIGHT,
            DEFAULT_IMAGE_MAX_WIDTH, DEFAULT_IMAGE_MAX_HEIGHT
        )
        self.image_min_width = DEFAULT_IMAGE_MIN_WIDTH
        self.image_min_height = DEFAULT_IMAGE_MIN_HEIGHT
        self.image_max_width = DEFAULT_IMAGE_MAX_WIDTH
        self.image_max_height = DEFAULT_IMAGE_MAX_HEIGHT

        # UI更新コールバック
        self._ui_callbacks = []

        logger.info("AppState を初期化しました")

    # ==================== フォルダ・ファイル管理 ====================

    def set_current_folder(self, path):
        if not os.path.exists(path):
            logger.warning(f"パスが存在しません: {path}")
            return False

        self.current_folder = path
        self.current_files = []
        self.current_folders = []

        logger.info(f"現在のフォルダを変更: {path}")
        self._notify_callbacks("folder_changed", {"path": path})
        return True

    def set_current_files(self, files):
        self.current_files = files
        logger.debug(f"ファイル一覧を更新: {len(files)}件")
        self._notify_callbacks("files_changed", {"files": files, "count": len(files)})

    def set_current_folders(self, folders):
        self.current_folders = folders
        logger.debug(f"フォルダ一覧を更新: {len(folders)}件")
        self._notify_callbacks("folders_changed", {"folders": folders, "count": len(folders)})

    # ==================== 移動先管理 ====================

    def set_move_destination(self, index, path):
        if not (0 <= index < len(self.move_dest_list)):
            logger.error(f"無効なインデックス: {index}")
            return False

        if path and not os.path.exists(path):
            logger.warning(f"フォルダが存在しません: {path}")
            return False

        self.move_dest_list[index] = path
        logger.info(f"移動先スロット{index+1}に登録: {path if path else '(クリア)'}")
        self._notify_callbacks("move_destination_changed", {"index": index, "path": path})
        return True

    def set_move_reg_idx(self, index):
        self.move_reg_idx = index % self.move_dest_count
        self._notify_callbacks("move_reg_idx_changed", {"index": self.move_reg_idx})

    def rotate_move_reg_idx(self):
        self.move_reg_idx = (self.move_reg_idx + 1) % self.move_dest_count
        self._notify_callbacks("move_reg_idx_changed", {"index": self.move_reg_idx})

    def set_move_dest_count(self, count):
        valid_counts = [2, 4, 6, 8, 10, 12]
        if count not in valid_counts:
            logger.error(f"無効な個数: {count}")
            return False

        old_count = self.move_dest_count
        self.move_dest_count = count

        if count > len(self.move_dest_list):
            self.move_dest_list.extend([""] * (count - len(self.move_dest_list)))
        else:
            self.move_dest_list = self.move_dest_list[:count]

        if self.move_reg_idx >= count:
            self.move_reg_idx = 0

        logger.info(f"移動先個数を変更: {old_count} → {count}")
        self._notify_callbacks("move_dest_count_changed", {"count": count})
        return True

    def reset_move_destinations(self):
        self.move_dest_list = [""] * self.move_dest_count
        self.move_reg_idx = 0
        logger.info("移動先をリセットしました")
        self._notify_callbacks("move_destinations_reset", {})

    # ==================== UI 設定 ====================

    def set_show_folder_window(self, show):
        self.show_folder_window = show
        self._notify_callbacks("show_folder_window_changed", {"show": show})

    def set_show_file_window(self, show):
        self.show_file_window = show
        self._notify_callbacks("show_file_window_changed", {"show": show})

    def set_topmost(self, enabled):
        self.topmost = enabled
        self._notify_callbacks("topmost_changed", {"enabled": enabled})

    def set_smart_move_threshold(self, threshold):
        self.smart_move_threshold = max(0.0, min(1.0, threshold))
        self._notify_callbacks("smart_move_threshold_changed", {"threshold": self.smart_move_threshold})

    def set_smart_move_show_thumbnails(self, enabled):
        self.smart_move_show_thumbnails = enabled
        self._notify_callbacks("smart_move_show_thumbnails_changed", {"enabled": enabled})

    def set_show_splash_tips(self, enabled):
        self.show_splash_tips = enabled
        self._notify_callbacks("show_splash_tips_changed", {"enabled": enabled})

    # ==================== 参照フォルダ管理 ====================

    def add_reference_folder(self, path, include_subfolders=False):
        if not os.path.isdir(path):
            logger.warning(f"参照フォルダが存在しません: {path}")
            return False
        norm_path = os.path.normpath(path)
        for entry in self.reference_folders:
            if os.path.normpath(entry["path"]) == norm_path:
                logger.info(f"参照フォルダは既に登録済み: {path}")
                return False
        self.reference_folders.append({"path": path, "include_subfolders": include_subfolders})
        logger.info(f"参照フォルダを追加: {path} (子フォルダ: {include_subfolders})")
        self._notify_callbacks("reference_folders_changed", {"folders": self.reference_folders})
        return True

    def remove_reference_folder(self, index):
        if 0 <= index < len(self.reference_folders):
            removed = self.reference_folders.pop(index)
            logger.info(f"参照フォルダを削除: {removed['path']}")
            self._notify_callbacks("reference_folders_changed", {"folders": self.reference_folders})
            return True
        return False

    def toggle_subfolder(self, index):
        if 0 <= index < len(self.reference_folders):
            self.reference_folders[index]["include_subfolders"] = not self.reference_folders[index]["include_subfolders"]
            entry = self.reference_folders[index]
            logger.info(f"子フォルダ設定変更: {entry['path']} -> {entry['include_subfolders']}")
            self._notify_callbacks("reference_folders_changed", {"folders": self.reference_folders})
            return True
        return False

    # ==================== ウィンドウジオメトリ ====================

    def set_window_geometry(self, window_name, geometry):
        if window_name not in self.window_geometries:
            logger.warning(f"不明なウィンドウ: {window_name}")
            return

        self.window_geometries[window_name] = geometry

    def get_window_geometry(self, window_name):
        return self.window_geometries.get(window_name)

    def set_image_size_limits(self, min_w, min_h, max_w, max_h):
        self.image_min_width = min_w
        self.image_min_height = min_h
        self.image_max_width = max_w
        self.image_max_height = max_h
        self._notify_callbacks("image_size_limits_changed", {
            "min_w": min_w, "min_h": min_h, "max_w": max_w, "max_h": max_h
        })

    # ==================== コールバック管理 ====================

    def register_callback(self, callback):
        self._ui_callbacks.append(callback)

    def unregister_callback(self, callback):
        if callback in self._ui_callbacks:
            self._ui_callbacks.remove(callback)

    def _notify_callbacks(self, event_name, data):
        for callback in self._ui_callbacks:
            try:
                callback(event_name, data)
            except Exception as e:
                logger.error(f"コールバック実行エラー ({callback.__name__}): {e}", exc_info=True)

    # ==================== 状態の保存・復元 ====================

    def to_dict(self):
        return {
            "last_folder": self.current_folder,
            "geometries": self.window_geometries,
            "settings": {
                "topmost": self.topmost,
                "show_folder": self.show_folder_window,
                "show_file": self.show_file_window,
                "move_dest_list": self.move_dest_list,
                "move_reg_idx": self.move_reg_idx,
                "move_dest_count": self.move_dest_count,
                "image_min_width": self.image_min_width,
                "image_min_height": self.image_min_height,
                "image_max_width": self.image_max_width,
                "image_max_height": self.image_max_height,
                "smart_move_threshold": self.smart_move_threshold,
                "smart_move_show_thumbnails": self.smart_move_show_thumbnails,
                "show_splash_tips": self.show_splash_tips,
                "reference_folders": self.reference_folders,
            }
        }

    def from_dict(self, data):
        try:
            if "last_folder" in data:
                self.current_folder = data["last_folder"]

            if "geometries" in data:
                self.window_geometries.update(data["geometries"])

            if "settings" in data:
                settings = data["settings"]
                self.topmost = settings.get("topmost", True)
                self.show_folder_window = settings.get("show_folder", False)
                self.show_file_window = settings.get("show_file", False)

                from lib.config_defaults import (
                    DEFAULT_IMAGE_MIN_WIDTH, DEFAULT_IMAGE_MIN_HEIGHT,
                    DEFAULT_IMAGE_MAX_WIDTH, DEFAULT_IMAGE_MAX_HEIGHT
                )
                self.image_min_width = settings.get("image_min_width", DEFAULT_IMAGE_MIN_WIDTH)
                self.image_min_height = settings.get("image_min_height", DEFAULT_IMAGE_MIN_HEIGHT)
                self.image_max_width = settings.get("image_max_width", DEFAULT_IMAGE_MAX_WIDTH)
                self.image_max_height = settings.get("image_max_height", DEFAULT_IMAGE_MAX_HEIGHT)

                move_list = settings.get("move_dest_list", [])
                if len(move_list) < 12:
                    move_list = (move_list + [""] * 12)[:12]
                self.move_dest_list = move_list

                self.move_reg_idx = settings.get("move_reg_idx", 0)
                self.move_dest_count = settings.get("move_dest_count", 2)

                self.smart_move_threshold = settings.get("smart_move_threshold", 0.90)
                self.smart_move_show_thumbnails = settings.get("smart_move_show_thumbnails", True)
                self.show_splash_tips = settings.get("show_splash_tips", False)

                ref_folders = settings.get("reference_folders", [])
                self.reference_folders = [
                    {"path": f["path"], "include_subfolders": f.get("include_subfolders", False)}
                    for f in ref_folders if isinstance(f, dict) and "path" in f
                ]

            logger.info("状態を復元しました")
        except Exception as e:
            logger.error(f"状態復元エラー: {e}", exc_info=True)

    def clear(self):
        self.__init__()
        logger.info("AppState をリセットしました")


def get_app_state():
    return AppState()

"""
PicSorterGUI 画像キャッシング機構

LRU（最近最少使用）キャッシュで、頻繁にアクセスされる画像をメモリに保持。
"""

from collections import OrderedDict
import threading
from pathlib import Path
from PIL import Image
from .PicSorterGUILogger import LoggerManager

logger = LoggerManager.get_logger(__name__)


class ImageCache:
    """LRUキャッシュで画像を管理するシングルトンクラス。"""

    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls, max_size_mb=256):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(max_size_mb=max_size_mb)
        return cls._instance

    def __init__(self, max_size_mb=256):
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.current_size_bytes = 0
        self.cache = OrderedDict()
        logger.info(f"ImageCache初期化: 最大{max_size_mb}MB")

    def get(self, image_path, target_size=None):
        try:
            if image_path in self.cache:
                self.cache.move_to_end(image_path)
                img = self.cache[image_path]

                if target_size and img.size != target_size:
                    img = img.resize(target_size, Image.Resampling.LANCZOS)

                return img

            img = Image.open(image_path).convert("RGB")

            if target_size:
                img = img.resize(target_size, Image.Resampling.LANCZOS)

            self._add_to_cache(image_path, img)

            return img

        except FileNotFoundError:
            logger.error(f"画像ファイルが見つかりません: {image_path}")
            raise
        except Exception as e:
            logger.error(f"画像読み込みエラー: {image_path} - {e}")
            raise

    def preload(self, image_paths, target_size=None):
        loaded = 0
        skipped = 0

        for path in image_paths:
            if path in self.cache:
                skipped += 1
                continue

            try:
                self.get(path, target_size)
                loaded += 1
            except Exception:
                continue

        logger.info(f"プリロード完了: {loaded}個読み込み, {skipped}個スキップ")

    def _add_to_cache(self, image_path, img):
        width, height = img.size
        estimated_size = width * height * 4

        while self.current_size_bytes + estimated_size > self.max_size_bytes:
            if not self.cache:
                break

            removed_path, removed_img = self.cache.popitem(last=False)
            removed_size = removed_img.size[0] * removed_img.size[1] * 4
            self.current_size_bytes -= removed_size

        self.cache[image_path] = img
        self.current_size_bytes += estimated_size

    def clear(self):
        self.cache.clear()
        self.current_size_bytes = 0
        logger.info("ImageCacheをクリア")

    def get_stats(self):
        size_mb = self.current_size_bytes / (1024 * 1024)
        return {
            "count": len(self.cache),
            "size_mb": size_mb,
            "max_mb": self.max_size_bytes / (1024 * 1024)
        }

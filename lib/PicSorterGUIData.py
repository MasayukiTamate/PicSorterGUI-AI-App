'''
PicSorterGUI データアクセス層 (Config, Vectors)
'''
import os
import json
import hashlib
from lib.PicSorterGUIExceptions import (
    ConfigError, FileHashError,
    VectorProcessingError, FileOperationError
)
from lib.PicSorterGUILogger import LoggerManager
from lib.config_defaults import (
    get_default_config, MOVE_DESTINATION_SLOTS,
    VECTOR_DATA_FILE, ANALYSIS_CACHE_FILE, CONFIG_FILE
)

logger = LoggerManager.get_logger(__name__)


def load_config():
    config = get_default_config()

    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                config["last_folder"] = data.get("last_folder", os.getcwd())
                config["geometries"] = data.get("geometries", {})
                saved_settings = data.get("settings", {})
                config["settings"].update(saved_settings)

                cur_list = config["settings"].get("move_dest_list", [])
                if len(cur_list) < MOVE_DESTINATION_SLOTS:
                    config["settings"]["move_dest_list"] = (cur_list + [""] * MOVE_DESTINATION_SLOTS)[:MOVE_DESTINATION_SLOTS]

                if not os.path.exists(config["last_folder"]):
                    config["last_folder"] = os.getcwd()
        except json.JSONDecodeError as e:
            logger.error(f"設定ファイルのJSON解析に失敗: {CONFIG_FILE}", exc_info=True)
            raise ConfigError(f"Invalid JSON in config file: {e}") from e
        except IOError as e:
            logger.error(f"設定ファイルの読み込み失敗: {CONFIG_FILE}", exc_info=True)
            raise ConfigError(f"Cannot read config file: {e}") from e
        except Exception as e:
            logger.error(f"設定ファイル読み込み中に予期しないエラー: {e}", exc_info=True)
            raise ConfigError(f"Unexpected error loading config: {e}") from e
    return config


def save_config(path, geometries=None, settings=None):
    try:
        prev = load_config()
        data = {
            "last_folder": path,
            "geometries": geometries if geometries is not None else prev.get("geometries", {}),
            "settings": settings if settings is not None else prev.get("settings", {})
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        logger.info(f"設定を保存しました: {path}")
    except IOError as e:
        logger.error(f"設定ファイルの書き込み失敗: {CONFIG_FILE}", exc_info=True)
        raise ConfigError(f"Cannot write config file: {e}") from e
    except Exception as e:
        logger.error(f"設定保存中に予期しないエラー: {e}", exc_info=True)
        raise ConfigError(f"Unexpected error saving config: {e}") from e


def calculate_file_hash(filepath):
    hash_md5 = hashlib.md5()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except FileNotFoundError as e:
        logger.error(f"ファイルが見つかりません: {filepath}", exc_info=True)
        raise FileHashError(f"File not found: {filepath}") from e
    except IOError as e:
        logger.error(f"ファイル読み込みエラー: {filepath}", exc_info=True)
        raise FileHashError(f"Cannot read file: {filepath}") from e
    except Exception as e:
        logger.error(f"ハッシュ計算中に予期しないエラー: {filepath}", exc_info=True)
        raise FileHashError(f"Unexpected error calculating hash: {e}") from e


def load_vectors():
    if os.path.exists(VECTOR_DATA_FILE):
        try:
            with open(VECTOR_DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info(f"ベクトルデータを読み込みました: {len(data)}件")
            return data
        except json.JSONDecodeError as e:
            logger.error(f"ベクトルファイルのJSON解析エラー: {VECTOR_DATA_FILE}", exc_info=True)
            raise VectorProcessingError(f"Invalid JSON in vector file: {e}") from e
        except IOError as e:
            logger.error(f"ベクトルファイル読み込みエラー: {VECTOR_DATA_FILE}", exc_info=True)
            raise VectorProcessingError(f"Cannot read vector file: {e}") from e
        except Exception as e:
            logger.error(f"ベクトル読み込み中に予期しないエラー: {e}", exc_info=True)
            raise VectorProcessingError(f"Unexpected error loading vectors: {e}") from e
    return {}


def save_vectors(vectors):
    try:
        os.makedirs(os.path.dirname(VECTOR_DATA_FILE), exist_ok=True)
        with open(VECTOR_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(vectors, f)
        logger.info(f"ベクトルデータを保存しました: {len(vectors)}件")
    except IOError as e:
        logger.error(f"ベクトルファイル書き込みエラー: {VECTOR_DATA_FILE}", exc_info=True)
        raise VectorProcessingError(f"Cannot write vector file: {e}") from e
    except Exception as e:
        logger.error(f"ベクトル保存中に予期しないエラー: {e}", exc_info=True)


def clear_vectors():
    """vectordata.json を空にする"""
    try:
        os.makedirs(os.path.dirname(VECTOR_DATA_FILE), exist_ok=True)
        with open(VECTOR_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)
        logger.info("ベクトルデータをクリアしました")
    except Exception as e:
        logger.error(f"ベクトルデータクリアエラー: {e}")


def clear_analysis_cache():
    """analysis_cache.json を空にする"""
    try:
        if os.path.exists(ANALYSIS_CACHE_FILE):
            with open(ANALYSIS_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump({}, f)
            logger.info("分析キャッシュをクリアしました")
    except Exception as e:
        logger.error(f"分析キャッシュクリアエラー: {e}")


def get_vector_data_info():
    """vectordata.json のファイルサイズと件数を返す"""
    if not os.path.exists(VECTOR_DATA_FILE):
        return 0, 0
    try:
        file_size = os.path.getsize(VECTOR_DATA_FILE)
        with open(VECTOR_DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return file_size, len(data)
    except Exception:
        try:
            return os.path.getsize(VECTOR_DATA_FILE), 0
        except Exception:
            return 0, 0


def _make_cache_key(folder, target_hash):
    return f"{folder}|{target_hash}"


def load_analysis_cache(folder, target_hash, current_file_count):
    """分析結果キャッシュを読み込む。無効ならNoneを返す"""
    if not os.path.exists(ANALYSIS_CACHE_FILE):
        return None
    try:
        with open(ANALYSIS_CACHE_FILE, "r", encoding="utf-8") as f:
            all_cache = json.load(f)
        key = _make_cache_key(folder, target_hash)
        entry = all_cache.get(key)
        if not entry:
            return None
        if entry.get("file_count") != current_file_count:
            logger.info(f"キャッシュ無効: ファイル数変更 ({entry.get('file_count')} -> {current_file_count})")
            return None
        results = [(r["file"], r["score"]) for r in entry["results"]]
        logger.info(f"分析キャッシュを読み込みました: {len(results)}件")
        return results
    except Exception as e:
        logger.warning(f"分析キャッシュ読み込みエラー: {e}")
        return None


def save_analysis_cache(folder, target_hash, results, file_count):
    """分析結果をキャッシュに保存する"""
    try:
        all_cache = {}
        if os.path.exists(ANALYSIS_CACHE_FILE):
            try:
                with open(ANALYSIS_CACHE_FILE, "r", encoding="utf-8") as f:
                    all_cache = json.load(f)
            except Exception:
                all_cache = {}

        from datetime import datetime
        key = _make_cache_key(folder, target_hash)
        all_cache[key] = {
            "timestamp": datetime.now().isoformat(),
            "file_count": file_count,
            "results": [{"file": path, "score": score} for path, score in results]
        }

        os.makedirs(os.path.dirname(ANALYSIS_CACHE_FILE), exist_ok=True)
        with open(ANALYSIS_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(all_cache, f, ensure_ascii=False)
        logger.info(f"分析キャッシュを保存しました: {len(results)}件")
    except Exception as e:
        logger.error(f"分析キャッシュ保存エラー: {e}")


# -------------------------------------------------------------------
import random
from lib.PicSorterGUILib import GetKoFolder, GetGazoFiles


class ImageDataManager():
    """画像データ保持クラス"""
    def __init__(self, def_folder):
        self.StartFolder = def_folder
        self.GazoFiles = []
        self.vectors_cache = {}

    def SetGazoFiles(self, GazoFiles, folder_path, include_subfolders=False):
        self.StartFolder = folder_path
        self.GazoFiles = GazoFiles

        if include_subfolders:
            self.GazoFiles = self._collect_all_images(folder_path)

        self.vectors_cache = load_vectors()

    def _collect_all_images(self, base_folder):
        all_images = []

        def collect_recursive(current_folder, base_path):
            try:
                items = os.listdir(current_folder)
                folders = GetKoFolder(items, current_folder)
                files = GetGazoFiles(items, current_folder)

                for f in files:
                    full_path = os.path.join(current_folder, f)
                    relative_path = os.path.relpath(full_path, base_path)
                    all_images.append(relative_path)

                for folder in folders:
                    subfolder_path = os.path.join(current_folder, folder)
                    collect_recursive(subfolder_path, base_path)
            except PermissionError:
                logger.warning(f"アクセス権限がありません: {current_folder}")
            except Exception as e:
                logger.warning(f"フォルダ読み込みエラー: {current_folder} - {e}")

        collect_recursive(base_folder, base_folder)
        logger.info(f"子フォルダを含めて{len(all_images)}件の画像を収集しました")
        return all_images

    def RandamGazoSet(self):
        if not self.GazoFiles:
            return None
        return random.choice(self.GazoFiles)

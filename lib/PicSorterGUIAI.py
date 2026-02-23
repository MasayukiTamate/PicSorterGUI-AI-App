'''
PicSorterGUI AI 複数モデル対応の画像ベクトル化ロジック
'''
from PIL import Image
import torch
from torchvision import models, transforms
import os
import threading
import sys
import itertools
from collections import OrderedDict
from .PicSorterGUIExceptions import AIModelError, ImageLoadError, VectorProcessingError
from .PicSorterGUILogger import LoggerManager
import time
from lib.PicSorterGUIData import load_vectors, save_vectors, calculate_file_hash
from lib.PicSorterGUILib import GetGazoFiles
from lib.PicSorterGUIExceptions import FileHashError
from lib.config_defaults import AI_MODELS, DEFAULT_AI_MODEL


logger = LoggerManager.get_logger(__name__)


def _get_torch_cache_dir():
    """torchvision の重みキャッシュディレクトリを取得"""
    try:
        from lib.PicSorterGUIState import get_app_state
        custom = get_app_state().model_cache_dir
        if custom:
            return os.path.join(custom, 'hub', 'checkpoints')
    except Exception:
        pass
    torch_home = os.environ.get('TORCH_HOME', os.path.join(os.path.expanduser('~'), '.cache', 'torch'))
    return os.path.join(torch_home, 'hub', 'checkpoints')


def get_model_cache_dir():
    """現在有効なモデルキャッシュディレクトリ（checkpoints 階層）を返す"""
    return _get_torch_cache_dir()


def apply_model_cache_dir(path=None):
    """保存済みのモデルキャッシュ先を TORCH_HOME 環境変数に適用する。
    path が None の場合は app_state から読む。空文字の場合は環境変数を削除してデフォルトに戻す。
    """
    if path is None:
        try:
            from lib.PicSorterGUIState import get_app_state
            path = get_app_state().model_cache_dir
        except Exception:
            path = ""
    if path:
        os.environ['TORCH_HOME'] = path
        logger.info(f"TORCH_HOME を設定: {path}")
    else:
        os.environ.pop('TORCH_HOME', None)
        logger.info("TORCH_HOME をデフォルトにリセット")


def move_model_files(old_dir, new_dir, progress_callback=None):
    """モデルの .pth ファイルを old_dir から new_dir に移動する。
    戻り値: (moved_list, failed_list)
    """
    import shutil
    moved = []
    failed = []
    try:
        os.makedirs(new_dir, exist_ok=True)
    except Exception as e:
        logger.error(f"移動先フォルダの作成に失敗: {new_dir} - {e}")
        return moved, [(None, str(e))]

    for key, info in AI_MODELS.items():
        weight_file = info.get("weight_file")
        if not weight_file:
            continue
        old_path = os.path.join(old_dir, weight_file)
        new_path = os.path.join(new_dir, weight_file)
        if not os.path.isfile(old_path):
            continue
        if os.path.isfile(new_path):
            logger.info(f"移動先に既に存在するためスキップ: {weight_file}")
            moved.append(weight_file)
            continue
        try:
            if progress_callback:
                progress_callback(f"移動中: {weight_file}")
            shutil.move(old_path, new_path)
            moved.append(weight_file)
            logger.info(f"モデルファイル移動完了: {weight_file}")
        except Exception as e:
            logger.error(f"モデルファイル移動失敗: {weight_file} - {e}")
            failed.append((weight_file, str(e)))

    return moved, failed


def check_model_cached(model_key):
    """指定モデルの重みがローカルにキャッシュされているか確認"""
    if model_key == "custom":
        from lib.PicSorterGUIState import get_app_state
        path = get_app_state().custom_model_path
        return bool(path and os.path.isfile(path))
    if model_key not in AI_MODELS:
        return False
    weight_file = AI_MODELS[model_key]["weight_file"]
    cache_dir = _get_torch_cache_dir()
    return os.path.exists(os.path.join(cache_dir, weight_file))


def download_model(model_key, progress_callback=None):
    """指定モデルの重みをダウンロードする"""
    if model_key == "custom":
        if progress_callback:
            progress_callback("カスタムモデルはファイルを直接選択してください")
        return False
    if model_key not in AI_MODELS:
        raise AIModelError(f"Unknown model: {model_key}")

    try:
        if progress_callback:
            progress_callback("モデルをダウンロード中...")

        if model_key == "mobilenet_v3_small":
            models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.DEFAULT)
        elif model_key == "mobilenet_v3_large":
            models.mobilenet_v3_large(weights=models.MobileNet_V3_Large_Weights.DEFAULT)
        elif model_key == "resnet50":
            models.resnet50(weights=models.ResNet50_Weights.DEFAULT)
        elif model_key == "efficientnet_b0":
            models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.DEFAULT)

        if progress_callback:
            progress_callback("ダウンロード完了")

        logger.info(f"モデルダウンロード完了: {model_key}")
        return True
    except Exception as e:
        logger.error(f"モデルダウンロードエラー: {model_key} - {e}")
        if progress_callback:
            progress_callback(f"エラー: {e}")
        return False


class VectorEngine:
    """複数モデル対応の画像ベクトル化クラス"""
    _instance = None
    _lock = threading.Lock()
    _current_model_key = None

    @classmethod
    def get_instance(cls, model_key=None):
        with cls._lock:
            if model_key and cls._current_model_key != model_key:
                cls._instance = None
                cls._current_model_key = model_key
            if cls._instance is None:
                cls._instance = cls(model_key=model_key or cls._current_model_key or DEFAULT_AI_MODEL)
        return cls._instance

    @classmethod
    def reset_instance(cls):
        with cls._lock:
            cls._instance = None
            cls._current_model_key = None

    def __init__(self, model_key=DEFAULT_AI_MODEL, debug_mode=False, cache_size=256):
        self.debug_mode = debug_mode
        self.cache_size = cache_size
        self.vector_cache = OrderedDict()
        self.model_key = model_key

        model_info = AI_MODELS.get(model_key)
        if not model_info:
            raise AIModelError(f"Unknown model: {model_key}")

        display_name = model_info['name']
        if model_key == "custom":
            from lib.PicSorterGUIState import get_app_state
            state = get_app_state()
            display_name = f"カスタム({os.path.basename(state.custom_model_path or '未設定')})"

        logger.info(f"AIモデル({display_name})の準備を開始...")

        try:
            self.model, self.preprocess = self._load_model(model_key)
            self.model.eval()

            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.model.to(self.device)

            torch.set_grad_enabled(False)

            self.available = True
            logger.info(f"AIモデル({display_name})の準備が完了しました")
        except Exception as e:
            logger.error(f"AIモデルの読み込みでエラー: {e}", exc_info=True)
            raise AIModelError(f"Failed to initialize AI model: {e}") from e

    def _load_model(self, model_key):
        """モデルキーに応じたモデルとプリプロセスを返す"""
        if model_key == "mobilenet_v3_small":
            weights = models.MobileNet_V3_Small_Weights.DEFAULT
            model = models.mobilenet_v3_small(weights=weights)
            model.classifier = torch.nn.Sequential(
                model.classifier[0],
                model.classifier[1],
                model.classifier[2],
                torch.nn.Identity()
            )
            return model, weights.transforms()

        elif model_key == "mobilenet_v3_large":
            weights = models.MobileNet_V3_Large_Weights.DEFAULT
            model = models.mobilenet_v3_large(weights=weights)
            model.classifier = torch.nn.Sequential(
                model.classifier[0],
                model.classifier[1],
                model.classifier[2],
                torch.nn.Identity()
            )
            return model, weights.transforms()

        elif model_key == "resnet50":
            weights = models.ResNet50_Weights.DEFAULT
            model = models.resnet50(weights=weights)
            model.fc = torch.nn.Identity()
            return model, weights.transforms()

        elif model_key == "efficientnet_b0":
            weights = models.EfficientNet_B0_Weights.DEFAULT
            model = models.efficientnet_b0(weights=weights)
            model.classifier = torch.nn.Identity()
            return model, weights.transforms()

        elif model_key == "custom":
            from lib.PicSorterGUIState import get_app_state
            state = get_app_state()
            arch = state.custom_model_arch
            path = state.custom_model_path

            if not path or not os.path.isfile(path):
                raise AIModelError(f"カスタムモデルファイルが見つかりません: {path}")

            # ベースアーキテクチャに合わせてモデル構造を構築
            if arch == "mobilenet_v3_small":
                base_weights = models.MobileNet_V3_Small_Weights.DEFAULT
                model = models.mobilenet_v3_small(weights=None)
                model.classifier = torch.nn.Sequential(
                    model.classifier[0], model.classifier[1],
                    model.classifier[2], torch.nn.Identity()
                )
                preprocess = base_weights.transforms()
            elif arch == "mobilenet_v3_large":
                base_weights = models.MobileNet_V3_Large_Weights.DEFAULT
                model = models.mobilenet_v3_large(weights=None)
                model.classifier = torch.nn.Sequential(
                    model.classifier[0], model.classifier[1],
                    model.classifier[2], torch.nn.Identity()
                )
                preprocess = base_weights.transforms()
            elif arch == "resnet50":
                base_weights = models.ResNet50_Weights.DEFAULT
                model = models.resnet50(weights=None)
                model.fc = torch.nn.Identity()
                preprocess = base_weights.transforms()
            elif arch == "efficientnet_b0":
                base_weights = models.EfficientNet_B0_Weights.DEFAULT
                model = models.efficientnet_b0(weights=None)
                model.classifier = torch.nn.Identity()
                preprocess = base_weights.transforms()
            else:
                raise AIModelError(f"未対応のベースアーキテクチャ: {arch}")

            # カスタム重みファイルを読み込む
            state_dict = torch.load(path, map_location="cpu", weights_only=True)
            # よくあるラッパー形式に対応
            if isinstance(state_dict, dict):
                for key in ("state_dict", "model", "model_state_dict", "net"):
                    if key in state_dict:
                        state_dict = state_dict[key]
                        break
            model.load_state_dict(state_dict, strict=False)
            logger.info(f"カスタムモデル読み込み完了: {path} (アーキテクチャ: {arch})")
            return model, preprocess

        else:
            raise AIModelError(f"Unsupported model: {model_key}")

    def check_available(self):
        return self.available

    def _get_cache_key(self, image_path):
        try:
            stat_info = os.stat(image_path)
            return f"{os.path.abspath(image_path)}_{stat_info.st_mtime}_{stat_info.st_size}"
        except:
            return os.path.abspath(image_path)

    def _get_from_cache(self, image_path):
        key = self._get_cache_key(image_path)
        if key in self.vector_cache:
            self.vector_cache.move_to_end(key)
            return self.vector_cache[key]
        return None

    def _add_to_cache(self, image_path, vector):
        key = self._get_cache_key(image_path)
        self.vector_cache[key] = vector

        if len(self.vector_cache) > self.cache_size:
            self.vector_cache.popitem(last=False)

    def clear_cache(self):
        self.vector_cache.clear()
        logger.info("ベクトルキャッシュをクリア")

    def get_cache_stats(self):
        return {
            "size": len(self.vector_cache),
            "max_size": self.cache_size
        }

    def get_image_feature(self, image_path):
        if not self.available:
            raise AIModelError("AI model is not available")

        cached_vec = self._get_from_cache(image_path)
        if cached_vec is not None:
            return cached_vec

        try:
            image = Image.open(image_path).convert("RGB")

            input_tensor = self.preprocess(image)
            input_batch = input_tensor.unsqueeze(0).to(self.device)

            with torch.no_grad():
                output = self.model(input_batch)

            feature_vector = output[0]

            norm = feature_vector.norm(p=2)
            if norm > 0:
                feature_vector = feature_vector / norm

            vec_list = feature_vector.tolist()

            self._add_to_cache(image_path, vec_list)

            return vec_list

        except FileNotFoundError as e:
            raise ImageLoadError(f"Image file not found: {image_path}") from e
        except IOError as e:
            raise ImageLoadError(f"Cannot read image file: {image_path}") from e
        except Exception as e:
            logger.error(f"ベクトル化処理中にエラー: {os.path.basename(image_path)}", exc_info=True)
            raise VectorProcessingError(f"Failed to vectorize image: {e}") from e

    def get_image_features_batch(self, image_paths):
        if not self.available:
            raise AIModelError("AI model is not available")

        if not image_paths:
            return []

        results = []
        batch_size = 8

        try:
            logger.info(f"バッチ処理開始: {len(image_paths)}個の画像")

            for batch_start in range(0, len(image_paths), batch_size):
                batch_end = min(batch_start + batch_size, len(image_paths))
                batch_paths = image_paths[batch_start:batch_end]

                images = []
                valid_paths = []

                for path in batch_paths:
                    try:
                        image = Image.open(path).convert("RGB")
                        images.append(image)
                        valid_paths.append(path)
                    except Exception as e:
                        logger.warning(f"画像読み込み失敗（スキップ）: {path} - {e}")
                        continue

                if not images:
                    continue

                input_tensors = [self.preprocess(img) for img in images]
                input_batch = torch.stack(input_tensors).to(self.device)

                with torch.no_grad():
                    outputs = self.model(input_batch)

                for i, (path, output) in enumerate(zip(valid_paths, outputs)):
                    feature_vector = output
                    norm = feature_vector.norm(p=2)
                    if norm > 0:
                        feature_vector = feature_vector / norm

                    vec_list = feature_vector.tolist()
                    results.append((path, vec_list))

            logger.info(f"バッチ処理完了: {len(results)}個のベクトルを生成")
            return results

        except Exception as e:
            logger.error(f"バッチ処理中にエラー: {e}", exc_info=True)
            raise VectorProcessingError(f"Failed to batch process images: {e}") from e

    def compare_features(self, vec1, vec2):
        try:
            if not vec1 or not vec2:
                raise VectorProcessingError("Cannot compare empty vectors")

            t1 = torch.tensor(vec1)
            t2 = torch.tensor(vec2)
            score = torch.nn.functional.cosine_similarity(t1.unsqueeze(0), t2.unsqueeze(0)).item()

            return score
        except VectorProcessingError:
            raise
        except Exception as e:
            logger.error(f"ベクトル比較中にエラー: {e}", exc_info=True)
            raise VectorProcessingError(f"Failed to compare features: {e}") from e

    def compare_features_batch(self, query_vec, candidate_vecs, threshold=0.5):
        try:
            if not query_vec or not candidate_vecs:
                return []

            t_query = torch.tensor(query_vec)
            t_candidates = torch.stack([torch.tensor(v) for v in candidate_vecs])

            scores = torch.nn.functional.cosine_similarity(
                t_query.unsqueeze(0),
                t_candidates
            )

            matches = []
            for idx, score in enumerate(scores):
                score_val = score.item()
                if score_val >= threshold:
                    matches.append((idx, score_val))

            matches.sort(key=lambda x: x[1], reverse=True)

            return matches

        except Exception as e:
            logger.error(f"バッチ比較処理中にエラー: {e}", exc_info=True)
            raise VectorProcessingError(f"Failed to batch compare features: {e}") from e


class VectorBatchProcessor(threading.Thread):
    """バックグラウンドでベクトル化を行うスレッドクラス。"""
    def __init__(self, folder_path, callback_progress=None, callback_finish=None):
        super().__init__()
        self.folder_path = folder_path
        self.callback_progress = callback_progress
        self.callback_finish = callback_finish
        self.daemon = True
        self.running = True

    def run(self):
        try:
            engine = VectorEngine.get_instance()
            if not engine.check_available():
                logger.error("AIモデルが利用できません")
                if self.callback_finish:
                    self.callback_finish("AIモデルが利用できません")
                return

            all_items = os.listdir(self.folder_path)
            files = GetGazoFiles(all_items, self.folder_path)
            total = len(files)

            try:
                vectors = load_vectors()
            except VectorProcessingError:
                vectors = {}

            updated_count = 0
            failed_count = 0

            logger.info(f"ベクトル更新開始: {total}ファイルをチェック")

            start_time = time.time()
            last_log_time = start_time

            for i, filename in enumerate(files):
                if not self.running:
                    logger.info("ベクトル化処理が中止されました")
                    break

                current_time = time.time()
                elapsed = current_time - start_time
                if elapsed > 600:
                    logger.warning("ベクトル化処理がタイムアウト (10分経過)")
                    if self.callback_finish:
                        self.callback_finish("タイムアウトにより停止しました")
                    break

                if current_time - last_log_time >= 60:
                    logger.info(f"ベクトル化処理中... {i}/{total} ({int(elapsed)}秒経過)")
                    last_log_time = current_time

                full_path = os.path.join(self.folder_path, filename)

                try:
                    file_hash = calculate_file_hash(full_path)
                except FileHashError:
                    logger.warning(f"ハッシュ計算失敗: {filename}")
                    failed_count += 1
                    continue

                if file_hash and file_hash not in vectors:
                    try:
                        vec = engine.get_image_feature(full_path)
                        if vec:
                            vectors[file_hash] = vec
                            updated_count += 1
                    except Exception as e:
                        logger.warning(f"ベクトル化失敗: {filename} - {e}")
                        failed_count += 1

                if self.callback_progress:
                    self.callback_progress(i + 1, total, filename)

                time.sleep(0.01)

            try:
                if updated_count > 0:
                    save_vectors(vectors)
            except VectorProcessingError as e:
                logger.error(f"ベクトルデータ保存失敗: {e}")
                if self.callback_finish:
                    self.callback_finish(f"ベクトル保存エラー: {e}")
                return

            if self.callback_finish:
                message = f"完了！ {updated_count}件のベクトルを新規追加しました。"
                if failed_count > 0:
                    message += f"({failed_count}件失敗)"
                self.callback_finish(message)

            logger.info(f"ベクトル更新完了: 追加{updated_count}件、失敗{failed_count}件")

        except Exception as e:
            logger.error(f"ベクトル化スレッド処理中にエラー: {e}", exc_info=True)
            if self.callback_finish:
                self.callback_finish(f"予期しないエラー: {e}")

    def stop(self):
        logger.info("ベクトル化処理停止要求")
        self.running = False

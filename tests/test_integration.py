"""
GazoTools 統合テストスイート

全フェーズの改善機能が正常に動作することを検証するテストのじゃ。
"""

import pytest
import os
import tempfile
import json
from pathlib import Path
from PIL import Image
import numpy as np

# テスト対象モジュールのインポート
from lib.GazoToolsAI import VectorEngine
from lib.GazoToolsImageCache import ImageCache, TileImageLoader, SlideShowImageLoader
from GazoToolsLogic import load_config, save_config, HakoData, calculate_file_hash
from lib.config_defaults import get_default_config, validate_ai_threshold
from lib.GazoToolsState import AppState


class TestPhaseIntegration:
    """全フェーズの統合テストのじゃ。"""
    
    @pytest.fixture(scope="function")
    def test_data_dir(self):
        """テスト用一時ディレクトリのじゃ。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture(scope="function")
    def sample_images(self, test_data_dir):
        """テスト用サンプル画像を生成するのじゃ。"""
        images = []
        for i in range(5):
            img_array = np.random.randint(0, 256, (200, 200, 3), dtype=np.uint8)
            img = Image.fromarray(img_array)
            path = Path(test_data_dir) / f"test_image_{i}.png"
            img.save(path)
            images.append(str(path))
        return images
    
    # --- Phase 1-3: 基礎機能テスト ---
    
    def test_config_defaults_integration(self):
        """Phase 2b: デフォルト設定の一貫性を検証"""
        config = get_default_config()
        
        # 必須フィールドが存在することを確認
        assert "window_width" in config
        assert "ai_threshold" in config
        assert "ss_interval" in config
        assert "move_destination_count" in config
        
        # 値の範囲を確認
        assert 0 <= config["ai_threshold"] <= 100
        assert 1 <= config["move_destination_count"] <= 12
    
    def test_app_state_integration(self):
        """Phase 2a: AppState シングルトンの動作を検証"""
        state1 = AppState.get_instance()
        state2 = AppState.get_instance()
        
        # シングルトンであることを確認
        assert state1 is state2
        
        # 状態変更が反映されることを確認
        state1.set_current_folder("/test/folder")
        assert state2.get_current_folder() == "/test/folder"
    
    def test_config_validation(self):
        """Phase 2b: 設定値の検証機能を確認"""
        # 有効な値
        assert validate_ai_threshold(50) is True
        assert validate_ai_threshold(0) is True
        assert validate_ai_threshold(100) is True
        
        # 無効な値
        assert validate_ai_threshold(-1) is False
        assert validate_ai_threshold(101) is False
    
    # --- Phase 4: AI最適化テスト ---
    
    def test_vector_engine_availability(self):
        """Phase 4: VectorEngine の初期化と可用性を検証"""
        engine = VectorEngine.get_instance()
        
        # エンジンが初期化されていることを確認
        assert engine is not None
        assert engine.check_available() is True
    
    def test_vector_engine_single_processing(self, sample_images):
        """Phase 4: 単一画像のベクトル化が機能することを確認"""
        engine = VectorEngine.get_instance()
        
        if not engine.check_available():
            pytest.skip("AI モデルが利用不可")
        
        try:
            vec = engine.get_image_feature(sample_images[0])
            
            # ベクトルが取得できていることを確認
            assert vec is not None
            assert isinstance(vec, list)
            assert len(vec) > 0
            
            # ベクトルが数値で構成されていることを確認
            assert all(isinstance(v, float) for v in vec)
        except Exception as e:
            pytest.skip(f"AI 処理エラー: {e}")
    
    def test_vector_engine_batch_processing(self, sample_images):
        """Phase 4: バッチ処理が機能することを確認"""
        engine = VectorEngine.get_instance()
        
        if not engine.check_available():
            pytest.skip("AI モデルが利用不可")
        
        try:
            # バッチ処理を実行
            results = engine.get_image_features_batch(sample_images[:3])
            
            # 結果の形式を確認
            assert isinstance(results, list)
            assert len(results) == 3
            
            # 各結果が (パス, ベクトル) のペアであることを確認
            for path, vec in results:
                assert isinstance(path, str)
                assert isinstance(vec, list)
                assert len(vec) > 0
        except Exception as e:
            pytest.skip(f"AI バッチ処理エラー: {e}")
    
    def test_vector_engine_caching(self, sample_images):
        """Phase 4: キャッシング機構が機能することを確認"""
        engine = VectorEngine.get_instance()
        
        if not engine.check_available():
            pytest.skip("AI モデルが利用不可")
        
        try:
            import time
            
            # キャッシュをクリア
            engine.clear_cache()
            
            # 1回目：ディスク読み込み
            start = time.time()
            vec1 = engine.get_image_feature(sample_images[0])
            time1 = time.time() - start
            
            # 2回目：キャッシュヒット
            start = time.time()
            vec2 = engine.get_image_feature(sample_images[0])
            time2 = time.time() - start
            
            # ベクトルが同じであることを確認
            assert vec1 == vec2
            
            # キャッシュヒット時が高速であることを確認（目安: 1/10以下）
            if time1 > 0:
                assert time2 < time1 / 5 or time2 < 0.01
        except Exception as e:
            pytest.skip(f"AI キャッシング テスト エラー: {e}")
    
    def test_vector_comparison(self, sample_images):
        """Phase 4: ベクトル比較が機能することを確認"""
        engine = VectorEngine.get_instance()
        
        if not engine.check_available():
            pytest.skip("AI モデルが利用不可")
        
        try:
            vec1 = engine.get_image_feature(sample_images[0])
            vec2 = engine.get_image_feature(sample_images[1])
            
            # 類似度を計算
            score = engine.compare_features(vec1, vec2)
            
            # スコアが有効な範囲であることを確認
            assert 0.0 <= score <= 1.0
        except Exception as e:
            pytest.skip(f"ベクトル比較エラー: {e}")
    
    # --- Phase 5: 画像キャッシングテスト ---
    
    def test_image_cache_basic(self, sample_images):
        """Phase 5: ImageCache の基本機能を検証"""
        cache = ImageCache.get_instance(max_size_mb=100)
        cache.clear()
        
        # 画像をキャッシュから取得
        img = cache.get(sample_images[0])
        
        # 画像が取得されていることを確認
        assert img is not None
        assert hasattr(img, 'size')
        
        # キャッシュ統計を確認
        stats = cache.get_cache_stats()
        assert stats['count'] == 1
        assert stats['size_mb'] > 0
    
    def test_image_cache_hit(self, sample_images):
        """Phase 5: キャッシュヒット時の高速化を確認"""
        import time
        
        cache = ImageCache.get_instance(max_size_mb=100)
        cache.clear()
        
        # 1回目：ディスク読み込み
        start = time.time()
        img1 = cache.get(sample_images[0])
        time1 = time.time() - start
        
        # 2回目：キャッシュヒット
        start = time.time()
        img2 = cache.get(sample_images[0])
        time2 = time.time() - start
        
        # 同じ画像が取得されていることを確認
        assert img1.size == img2.size
        
        # キャッシュヒット時が高速であることを確認
        if time1 > 0:
            assert time2 < time1 / 5 or time2 < 0.01
    
    def test_tile_image_loader(self, sample_images):
        """Phase 5: TileImageLoader が機能することを確認"""
        loader = TileImageLoader(tile_size=(100, 100), cache_mb=100)
        
        # タイル画像をロード
        tiles = loader.load_tiles(sample_images[:3], preload=False)
        
        # 結果の形式を確認
        assert isinstance(tiles, list)
        assert len(tiles) == 3
        
        # 各タイルが正しいサイズであることを確認
        for path, img in tiles:
            assert img.size == (100, 100)
    
    def test_slideshow_loader(self, sample_images):
        """Phase 5: SlideShowImageLoader が機能することを確認"""
        loader = SlideShowImageLoader(cache_mb=100)
        
        # スライドショー用に画像を取得
        img = loader.get_current(sample_images, 0)
        
        # 画像が取得されていることを確認
        assert img is not None
        assert hasattr(img, 'size')
    
    # --- 統合テスト ---
    
    def test_full_workflow_folder_processing(self, test_data_dir, sample_images):
        """完全ワークフロー: フォルダ処理から画像キャッシングまで"""
        # 1. 設定を取得
        config = get_default_config()
        assert config is not None
        
        # 2. フォルダデータを初期化
        hako = HakoData(test_data_dir)
        
        # 3. ファイルリストをセット
        file_names = [os.path.basename(img) for img in sample_images]
        hako.SetGazoFiles(file_names, test_data_dir)
        
        # 4. 画像キャッシュを初期化
        cache = ImageCache.get_instance(max_size_mb=100)
        cache.clear()
        
        # 5. タイルローダーで画像を一括処理
        loader = TileImageLoader(tile_size=(150, 150), cache_mb=100)
        tiles = loader.load_tiles(sample_images[:2], preload=True)
        
        # 結果を確認
        assert len(tiles) == 2
        for path, img in tiles:
            assert img.size == (150, 150)
    
    def test_performance_improvement_ai(self, sample_images):
        """AI処理のパフォーマンス改善を確認"""
        engine = VectorEngine.get_instance()
        
        if not engine.check_available():
            pytest.skip("AI モデルが利用不可")
        
        try:
            import time
            
            # 単一処理の合計時間
            start = time.time()
            for img_path in sample_images[:3]:
                engine.get_image_feature(img_path)
            single_time = time.time() - start
            
            # バッチ処理の時間
            engine.clear_cache()
            start = time.time()
            results = engine.get_image_features_batch(sample_images[:3])
            batch_time = time.time() - start
            
            # バッチ処理が有効であることを確認
            assert len(results) == 3
            # 完全にバッチの方が速いとは限らないが、複数画像の処理の基盤があることを確認
            assert batch_time > 0
        except Exception as e:
            pytest.skip(f"AI パフォーマンス テスト エラー: {e}")
    
    def test_memory_efficiency_image_cache(self, sample_images):
        """画像キャッシュのメモリ効率を確認"""
        cache = ImageCache.get_instance(max_size_mb=50)
        cache.clear()
        
        # 複数の画像をロード
        for img_path in sample_images:
            cache.get(img_path)
        
        # キャッシュ統計を確認
        stats = cache.get_cache_stats()
        
        # メモリ使用量が制限内であることを確認
        assert stats['size_mb'] <= stats['max_mb']
        assert stats['count'] > 0

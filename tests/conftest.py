'''
conftest.py - pytest の共通設定
作成日: 2026年01月04日
機能: テスト環境のセットアップと共通 fixture の定義
'''
import pytest
import os
import sys
import json
import tempfile
from pathlib import Path

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# テスト用ディレクトリ
TEST_DIR = Path(__file__).parent
TEMP_DIR = None


@pytest.fixture(scope="session")
def test_data_dir():
    """テストデータディレクトリを作成して返す"""
    global TEMP_DIR
    TEMP_DIR = tempfile.TemporaryDirectory()
    yield Path(TEMP_DIR.name)
    TEMP_DIR.cleanup()


@pytest.fixture
def temp_config_file(test_data_dir):
    """テスト用の一時設定ファイルを返す"""
    config_path = test_data_dir / "test_config.json"
    
    # デフォルト設定を書き込む
    default_config = {
        "last_folder": str(test_data_dir),
        "geometries": {},
        "settings": {
            "random_pos": False,
            "topmost": True,
            "show_folder": True,
            "show_file": True,
            "ss_mode": False,
            "ss_interval": 5,
            "ss_ai_mode": False,
            "ss_ai_threshold": 0.65,
            "move_dest_list": [""] * 12,
            "move_reg_idx": 0,
            "move_dest_count": 2,
            "cpu_low_color": "#e0ffe0",
            "cpu_high_color": "#ff8080",
        }
    }
    
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(default_config, f, indent=4)
    
    yield config_path
    
    # クリーンアップ
    if config_path.exists():
        config_path.unlink()


@pytest.fixture
def sample_image_paths(test_data_dir):
    """サンプル画像パスを返す"""
    images = []
    for i in range(3):
        img_path = test_data_dir / f"sample_{i}.txt"
        img_path.write_text(f"dummy image {i}")
        images.append(str(img_path))
    return images


@pytest.fixture
def sample_folder_paths(test_data_dir):
    """サンプルフォルダパスを返す"""
    folders = []
    for i in range(3):
        folder = test_data_dir / f"folder_{i}"
        folder.mkdir(exist_ok=True)
        folders.append(str(folder))
    return folders


@pytest.fixture(autouse=True)
def cleanup_logger():
    """テスト後にロガーを初期化"""
    yield
    # テスト後のクリーンアップ（必要に応じて）
    pass

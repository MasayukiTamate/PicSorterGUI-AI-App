'''
test_file_operations.py - ファイル操作のテスト
作成日: 2026年01月04日
対象: GazoToolsLogic.py の load_config, save_config
'''
import pytest
import os
import json
import tempfile
from pathlib import Path
from GazoToolsLogic import load_config, save_config, calculate_file_hash
from lib.GazoToolsExceptions import ConfigError


class TestLoadConfig:
    """load_config() 関数のテスト"""
    
    def test_load_config_default_values(self):
        """デフォルト設定が返されること"""
        config = load_config()
        
        assert isinstance(config, dict)
        assert "last_folder" in config
        assert "geometries" in config
        assert "settings" in config
    
    def test_load_config_settings_structure(self):
        """設定の構造が正しいこと"""
        config = load_config()
        settings = config["settings"]
        
        assert "random_pos" in settings
        assert "topmost" in settings
        assert "show_folder" in settings
        assert "show_file" in settings
        assert "ss_mode" in settings
        assert "ss_interval" in settings
        assert "ss_ai_threshold" in settings
        assert "move_dest_list" in settings
    
    def test_load_config_move_dest_list_length(self):
        """move_dest_list の長さが 12 であること"""
        config = load_config()
        
        assert len(config["settings"]["move_dest_list"]) == 12
    
    def test_load_config_returns_copy(self):
        """複数回呼び出しで独立した辞書を返すこと"""
        config1 = load_config()
        config2 = load_config()
        
        # 値は同じだが別のオブジェクト
        assert config1 is not config2
        assert config1 == config2


class TestSaveConfig:
    """save_config() 関数のテスト"""
    
    def test_save_config_creates_file(self):
        """設定ファイルが作成されること"""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_dir = os.getcwd()
            try:
                os.chdir(tmpdir)
                
                save_config(tmpdir)
                
                # ファイルが存在することを確認
                assert os.path.exists("config.json")
            finally:
                os.chdir(old_dir)
    
    def test_save_config_json_format(self):
        """設定ファイルが有効な JSON 形式であること"""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_dir = os.getcwd()
            try:
                os.chdir(tmpdir)
                
                save_config(tmpdir)
                
                with open("config.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                assert isinstance(data, dict)
                assert "last_folder" in data
            finally:
                os.chdir(old_dir)
    
    def test_save_config_preserves_folder_path(self):
        """フォルダパスが正しく保存されること"""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_dir = os.getcwd()
            try:
                os.chdir(tmpdir)
                
                test_path = "/test/path/to/folder"
                save_config(test_path)
                
                with open("config.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                assert data["last_folder"] == test_path
            finally:
                os.chdir(old_dir)
    
    def test_save_config_with_settings(self):
        """カスタム設定を保存できること"""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_dir = os.getcwd()
            try:
                os.chdir(tmpdir)
                
                test_settings = {
                    "ss_interval": 10,
                    "ss_mode": True,
                    "random_pos": True
                }
                
                save_config(tmpdir, settings=test_settings)
                
                with open("config.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # 設定が保存されたことを確認
                assert data["settings"]["ss_interval"] == 10
                assert data["settings"]["ss_mode"] is True
            finally:
                os.chdir(old_dir)


class TestCalculateFileHash:
    """calculate_file_hash() 関数のテスト"""
    
    def test_calculate_file_hash_returns_string(self, sample_image_paths):
        """ハッシュが文字列であること"""
        if sample_image_paths:
            hash_val = calculate_file_hash(sample_image_paths[0])
            
            assert isinstance(hash_val, str)
            assert len(hash_val) == 32  # MD5 のハッシュ長
    
    def test_calculate_file_hash_consistency(self, sample_image_paths):
        """同じファイルで同じハッシュが返されること"""
        if sample_image_paths:
            hash1 = calculate_file_hash(sample_image_paths[0])
            hash2 = calculate_file_hash(sample_image_paths[0])
            
            assert hash1 == hash2
    
    def test_calculate_file_hash_different_files(self, sample_image_paths):
        """異なるファイルで異なるハッシュが返されること"""
        if len(sample_image_paths) >= 2:
            hash1 = calculate_file_hash(sample_image_paths[0])
            hash2 = calculate_file_hash(sample_image_paths[1])
            
            assert hash1 != hash2
    
    def test_calculate_file_hash_nonexistent_file(self):
        """存在しないファイルの場合"""
        with pytest.raises(Exception):
            calculate_file_hash("/nonexistent/file/path.txt")


class TestConfigIntegration:
    """設定管理の統合テスト"""
    
    def test_load_save_cycle(self):
        """設定の保存と読み込みのサイクル"""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_dir = os.getcwd()
            try:
                os.chdir(tmpdir)
                
                # 設定を保存
                original_settings = {
                    "ss_interval": 15,
                    "ss_ai_threshold": 0.80,
                    "random_pos": True
                }
                save_config(tmpdir, settings=original_settings)
                
                # 設定を読み込む
                config = load_config()
                
                # 保存した設定が読み込まれたことを確認
                assert config["last_folder"] == tmpdir
                assert config["settings"]["ss_interval"] == 15
            finally:
                os.chdir(old_dir)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

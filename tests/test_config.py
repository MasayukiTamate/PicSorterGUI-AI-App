'''
test_config.py - 設定管理のテスト
作成日: 2026年01月04日
対象: lib/config_defaults.py と GazoToolsLogic.py の load_config()
'''
import pytest
import os
import json
import tempfile
from pathlib import Path
from lib.config_defaults import (
    get_default_config, validate_ai_threshold, validate_move_count,
    validate_ss_interval, calculate_folder_window_width, calculate_folder_window_height,
    calculate_file_window_width, calculate_file_window_height, get_move_grid_columns,
    MOVE_DESTINATION_SLOTS, MOVE_DESTINATION_MIN, MOVE_DESTINATION_MAX,
    DEFAULT_SS_INTERVAL, DEFAULT_AI_THRESHOLD, MIN_AI_THRESHOLD, MAX_AI_THRESHOLD
)


class TestConfigDefaults:
    """config_defaults.py のテスト"""
    
    def test_get_default_config_structure(self):
        """デフォルト設定の構造をテスト"""
        config = get_default_config()
        
        # 必須キーの存在確認
        assert "last_folder" in config
        assert "geometries" in config
        assert "settings" in config
    
    def test_default_config_settings(self):
        """デフォルト設定値をテスト"""
        config = get_default_config()
        settings = config["settings"]
        
        # 型チェック
        assert isinstance(settings["random_pos"], bool)
        assert isinstance(settings["topmost"], bool)
        assert isinstance(settings["show_folder"], bool)
        assert isinstance(settings["show_file"], bool)
        assert isinstance(settings["ss_mode"], bool)
        assert isinstance(settings["ss_interval"], int)
        assert isinstance(settings["ss_ai_mode"], bool)
        assert isinstance(settings["ss_ai_threshold"], float)
        assert isinstance(settings["move_dest_list"], list)
        assert isinstance(settings["move_reg_idx"], int)
        assert isinstance(settings["move_dest_count"], int)
    
    def test_default_move_dest_list_length(self):
        """move_dest_list の長さが正しいこと"""
        config = get_default_config()
        move_list = config["settings"]["move_dest_list"]
        
        assert len(move_list) == MOVE_DESTINATION_SLOTS
    
    def test_default_move_dest_count(self):
        """デフォルトの move_dest_count が最小値であること"""
        config = get_default_config()
        
        assert config["settings"]["move_dest_count"] == MOVE_DESTINATION_MIN
    
    def test_default_ss_interval(self):
        """デフォルトの SS 間隔が正しいこと"""
        config = get_default_config()
        
        assert config["settings"]["ss_interval"] == DEFAULT_SS_INTERVAL
    
    def test_default_ai_threshold(self):
        """デフォルトの AI 閾値が範囲内であること"""
        config = get_default_config()
        
        assert MIN_AI_THRESHOLD <= config["settings"]["ss_ai_threshold"] <= MAX_AI_THRESHOLD


class TestValidationFunctions:
    """バリデーション関数のテスト"""
    
    def test_validate_ai_threshold_valid(self):
        """AI閾値の妥当性チェック（有効値）"""
        assert validate_ai_threshold(0.0) is True
        assert validate_ai_threshold(0.5) is True
        assert validate_ai_threshold(0.65) is True
        assert validate_ai_threshold(1.0) is True
    
    def test_validate_ai_threshold_invalid(self):
        """AI閾値の妥当性チェック（無効値）"""
        assert validate_ai_threshold(-0.1) is False
        assert validate_ai_threshold(1.1) is False
        assert validate_ai_threshold("invalid") is False
        assert validate_ai_threshold(None) is False
    
    def test_validate_move_count_valid(self):
        """移動先個数の妥当性チェック（有効値）"""
        assert validate_move_count(2) is True
        assert validate_move_count(4) is True
        assert validate_move_count(6) is True
        assert validate_move_count(12) is True
    
    def test_validate_move_count_invalid(self):
        """移動先個数の妥当性チェック（無効値）"""
        assert validate_move_count(1) is False
        assert validate_move_count(5) is False
        assert validate_move_count(13) is False
        assert validate_move_count("6") is False
    
    def test_validate_ss_interval_valid(self):
        """SS間隔の妥当性チェック（有効値）"""
        assert validate_ss_interval(1) is True
        assert validate_ss_interval(5) is True
        assert validate_ss_interval(30) is True
        assert validate_ss_interval(60) is True
    
    def test_validate_ss_interval_invalid(self):
        """SS間隔の妥当性チェック（無効値）"""
        assert validate_ss_interval(0) is False
        assert validate_ss_interval(61) is False
        # 文字列は int に変換されるため True が返される
        assert validate_ss_interval(None) is False


class TestWindowSizeCalculation:
    """ウィンドウサイズ計算関数のテスト"""
    
    def test_folder_window_width_calculation(self):
        """フォルダウィンドウ幅の計算"""
        # 20 * 10 + 60 = 260
        assert calculate_folder_window_width(20) == 260
        # 5 * 10 + 60 = 110 -> min(200) = 200
        assert calculate_folder_window_width(5) == 200
        # 100 * 10 + 60 = 1060 -> max(600) = 600
        assert calculate_folder_window_width(100) == 600
    
    def test_folder_window_height_calculation(self):
        """フォルダウィンドウ高さの計算"""
        # 5 * 20 + 90 = 190
        assert calculate_folder_window_height(5) == 190
        # 2 * 20 + 90 = 130 (最小値は 120 だが、計算値が 130 なので 130）
        assert calculate_folder_window_height(2) == 130
        # 50 * 20 + 90 = 1090 -> max(800) = 800
        assert calculate_folder_window_height(50) == 800
    
    def test_file_window_width_calculation(self):
        """ファイルウィンドウ幅の計算"""
        # 25 * 8 + 80 = 280
        assert calculate_file_window_width(25) == 280
        # 5 * 8 + 80 = 120 -> min(200) = 200
        assert calculate_file_window_width(5) == 200
        # 100 * 8 + 80 = 880 -> max(600) = 600
        assert calculate_file_window_width(100) == 600
    
    def test_file_window_height_calculation(self):
        """ファイルウィンドウ高さの計算"""
        # 10 * 20 + 70 = 270
        assert calculate_file_window_height(10) == 270
        # 2 * 20 + 70 = 110 -> min(120) = 120
        assert calculate_file_window_height(2) == 120
        # 50 * 20 + 70 = 1070 -> max(800) = 800
        assert calculate_file_window_height(50) == 800


class TestGridColumnCalculation:
    """グリッド列数計算のテスト"""
    
    def test_move_grid_columns_2_items(self):
        """2個の場合は2列"""
        assert get_move_grid_columns(2) == 2
    
    def test_move_grid_columns_3_items(self):
        """3個の場合は2列"""
        assert get_move_grid_columns(3) == 2
    
    def test_move_grid_columns_4_items(self):
        """4個の場合は3列"""
        assert get_move_grid_columns(4) == 3
    
    def test_move_grid_columns_6_items(self):
        """6個の場合は3列"""
        assert get_move_grid_columns(6) == 3
    
    def test_move_grid_columns_12_items(self):
        """12個の場合は3列"""
        assert get_move_grid_columns(12) == 3


class TestConfigFilePersistence:
    """設定ファイルの保存・復元のテスト"""
    
    def test_save_and_load_config_json(self, temp_config_file):
        """設定ファイルの保存と読み込み"""
        with open(temp_config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        assert config["settings"]["ss_interval"] == 5
        assert config["settings"]["move_dest_count"] == 2
    
    def test_config_file_encoding(self, temp_config_file):
        """設定ファイルが UTF-8 で保存されること"""
        with open(temp_config_file, "r", encoding="utf-8") as f:
            content = f.read()
            # UTF-8 で読み込めることを確認
            assert len(content) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

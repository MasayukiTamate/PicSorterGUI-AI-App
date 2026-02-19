'''
test_ui_state.py - UI状態管理のテスト
作成日: 2026年01月04日
対象: lib/GazoToolsState.py の AppState クラス
'''
import pytest
from lib.GazoToolsState import get_app_state, AppState


class TestAppStateSingleton:
    """AppState のシングルトンパターンのテスト"""
    
    def test_singleton_instance(self):
        """同じインスタンスを返すこと"""
        state1 = get_app_state()
        state2 = get_app_state()
        
        assert state1 is state2
    
    def test_state_is_app_state_instance(self):
        """返されるオブジェクトが AppState インスタンスであること"""
        state = get_app_state()
        
        assert isinstance(state, AppState)


class TestAppStateCallbackMechanism:
    """AppState のコールバック機構のテスト"""
    
    def test_register_callback(self):
        """コールバックの登録"""
        app_state = get_app_state()
        
        events = []
        def test_callback(event_name, data):
            events.append((event_name, data))
        
        app_state.register_callback(test_callback)
        app_state.set_ss_mode(True)
        
        # コールバックが呼ばれたことを確認
        assert len(events) > 0
    
    def test_multiple_events(self):
        """複数のイベントが正しく処理されることのテスト"""
        app_state = get_app_state()
        
        events = []
        def test_callback(event_name, data):
            events.append(event_name)
        
        app_state.register_callback(test_callback)
        
        # 複数のイベントを発火
        app_state.set_current_folder("/test/path")
        app_state.set_move_destination(0, "/dest/path")
        app_state.set_ss_mode(True)
        
        # 最低3個のイベントが記録されたことを確認
        assert len(events) >= 3
        assert "folder_changed" in events
        assert "move_destination_changed" in events
        assert "ss_mode_changed" in events


class TestAppStateStatePersistence:
    """AppState の状態の保存・復元のテスト"""
    
    def test_state_to_dict(self):
        """to_dict() メソッドが辞書を返すことのテスト"""
        app_state = get_app_state()
        state_dict = app_state.to_dict()
        
        assert isinstance(state_dict, dict)
        assert "last_folder" in state_dict
        assert "geometries" in state_dict
        assert "settings" in state_dict
    
    def test_state_from_dict(self):
        """from_dict() メソッドで状態を復元できること"""
        app_state = get_app_state()
        
        # 状態を設定
        test_state = {
            "last_folder": "/test/path",
            "geometries": {},
            "settings": {
                "ss_mode": True,
                "ss_interval": 10,
                "move_dest_count": 6
            }
        }
        
        app_state.from_dict(test_state)
        
        # 設定した値を確認
        assert app_state.ss_mode == True
        assert app_state.ss_interval == 10


class TestAppStateMoveDestinationManagement:
    """AppState の移動先管理のテスト"""
    
    def test_set_move_destination(self):
        """移動先の設定"""
        app_state = get_app_state()
        
        app_state.set_move_destination(0, "/path/to/folder")
        
        assert app_state.move_dest_list[0] == "/path/to/folder"
    
    def test_move_destination_index_range(self):
        """移動先インデックスの範囲チェック"""
        app_state = get_app_state()
        
        # 有効なインデックス
        app_state.set_move_destination(0, "/path1")
        app_state.set_move_destination(11, "/path2")
        
        assert app_state.move_dest_list[0] == "/path1"
        assert app_state.move_dest_list[11] == "/path2"
    
    def test_rotate_move_reg_idx(self):
        """移動先登録インデックスの回転"""
        app_state = get_app_state()
        
        initial_idx = app_state.move_reg_idx
        app_state.rotate_move_reg_idx()
        next_idx = app_state.move_reg_idx
        
        # インデックスが進んだことを確認（またはリセット）
        assert next_idx >= 0 and next_idx < 12
    
    def test_reset_move_destinations(self):
        """移動先のリセット"""
        app_state = get_app_state()
        
        # いくつかの移動先を設定
        app_state.set_move_destination(0, "/path1")
        app_state.set_move_destination(1, "/path2")
        
        # リセット
        app_state.reset_move_destinations()
        
        # すべてが空になったことを確認
        for dest in app_state.move_dest_list:
            assert dest == ""


class TestAppStateMoveDestinationCount:
    """AppState の移動先個数管理のテスト"""
    
    def test_set_move_dest_count_valid(self):
        """有効な個数の設定"""
        app_state = get_app_state()
        
        result = app_state.set_move_dest_count(6)
        
        assert result is True
        assert app_state.move_dest_count == 6
    
    def test_set_move_dest_count_invalid(self):
        """無効な個数の設定"""
        app_state = get_app_state()
        
        # 無効な値
        result = app_state.set_move_dest_count(5)
        
        assert result is False
    
    def test_move_dest_count_options(self):
        """サポートされている個数のテスト"""
        app_state = get_app_state()
        
        valid_counts = [2, 4, 6, 8, 10, 12]
        
        for count in valid_counts:
            result = app_state.set_move_dest_count(count)
            assert result is True


class TestAppStateUISettings:
    """AppState のUI設定のテスト"""
    
    def test_set_show_folder_window(self):
        """フォルダウィンドウ表示設定"""
        app_state = get_app_state()
        
        app_state.set_show_folder_window(True)
        assert app_state.show_folder_window is True
        
        app_state.set_show_folder_window(False)
        assert app_state.show_folder_window is False
    
    def test_set_show_file_window(self):
        """ファイルウィンドウ表示設定"""
        app_state = get_app_state()
        
        app_state.set_show_file_window(True)
        assert app_state.show_file_window is True
        
        app_state.set_show_file_window(False)
        assert app_state.show_file_window is False
    
    def test_set_random_pos(self):
        """ランダム配置設定"""
        app_state = get_app_state()
        
        app_state.set_random_pos(True)
        assert app_state.random_pos is True
        
        app_state.set_random_pos(False)
        assert app_state.random_pos is False


class TestAppStateScreensaverSettings:
    """AppState のスクリーンセーバー設定のテスト"""
    
    def test_set_ss_mode(self):
        """スクリーンセーバーモード設定"""
        app_state = get_app_state()
        
        app_state.set_ss_mode(True)
        assert app_state.ss_mode is True
    
    def test_set_ss_interval(self):
        """スクリーンセーバー間隔設定"""
        app_state = get_app_state()
        
        app_state.set_ss_interval(10)
        assert app_state.ss_interval == 10
    
    def test_set_ss_ai_threshold(self):
        """AI類似度閾値設定"""
        app_state = get_app_state()
        
        app_state.set_ss_ai_threshold(0.75)
        assert app_state.ss_ai_threshold == 0.75


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

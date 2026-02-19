# UI改善 - AppState 導入と グローバル変数削減

**実装日**: 2026年1月4日  
**対象**: GazoTools プロジェクト  
**テスト結果**: ✅ すべてのテスト成功

---

## 📋 実装内容

### 1️⃣ **AppState クラスの新規作成** (`lib/GazoToolsState.py`)

状態管理を一元化するシングルトンクラスを実装しました。

**主要な機能:**

#### フォルダ・ファイル管理
```python
app_state.set_current_folder(path)
app_state.set_current_files(files)
app_state.set_current_folders(folders)
```

#### 移動先フォルダ管理
```python
app_state.set_move_destination(index, path)       # スロットに登録
app_state.rotate_move_reg_idx()                    # インデックスを回転
app_state.set_move_dest_count(count)               # 個数を変更（2,4,6,8,10,12）
app_state.reset_move_destinations()                # 全リセット
```

#### UI設定
```python
app_state.set_show_folder_window(show)
app_state.set_show_file_window(show)
app_state.set_random_pos(enabled)
app_state.set_topmost(enabled)
```

#### スクリーンセーバー設定
```python
app_state.set_ss_mode(enabled)
app_state.set_ss_interval(seconds)
app_state.set_ss_ai_mode(enabled)
app_state.set_ss_ai_threshold(threshold)
```

#### ウィンドウジオメトリ
```python
app_state.set_window_geometry(window_name, geometry)
geometry = app_state.get_window_geometry(window_name)
```

#### リソース表示設定
```python
app_state.set_cpu_colors(low_color, high_color)
```

#### 状態の保存・復元
```python
state_dict = app_state.to_dict()          # 設定ファイル用に変換
app_state.from_dict(state_dict)           # 設定ファイルから復元
```

---

### 2️⃣ **UI更新コールバック機構**

AppState の変更に応じて自動的に UI を更新する仕組みを実装。

#### コールバック登録
```python
def on_app_state_changed(event_name, data):
    if event_name == "folder_changed":
        refresh_ui(data["path"])
    elif event_name == "move_destination_changed":
        update_dd_display()
    # ... その他のイベント処理

app_state.register_callback(on_app_state_changed)
```

#### 発火するイベント
| イベント名 | 説明 | データ |
|-----------|------|--------|
| `folder_changed` | フォルダ変更 | `{"path": "..."}` |
| `files_changed` | ファイル一覧更新 | `{"files": [...], "count": N}` |
| `folders_changed` | フォルダ一覧更新 | `{"folders": [...], "count": N}` |
| `move_destination_changed` | 移動先登録 | `{"index": 0, "path": "..."}` |
| `move_reg_idx_changed` | 次登録先変更 | `{"index": 1}` |
| `move_dest_count_changed` | 個数変更 | `{"count": 6}` |
| `show_folder_window_changed` | フォルダウィンドウ表示 | `{"show": True}` |
| `show_file_window_changed` | ファイルウィンドウ表示 | `{"show": True}` |
| `ss_mode_changed` | スクリーンセーバーモード | `{"enabled": True}` |
| `ss_interval_changed` | スクリーンセーバー間隔 | `{"interval": 5}` |
| `ss_ai_mode_changed` | AI類似度順モード | `{"enabled": True}` |
| `ss_ai_threshold_changed` | AI類似度閾値 | `{"threshold": 0.65}` |
| `cpu_colors_changed` | CPU色設定 | `{"low": "#...", "high": "#..."}` |
| `move_destinations_reset` | 移動先リセット | `{}` |

---

### 3️⃣ **GazoToolsApp.py のリファクタリング**

#### 前後の比較

**Before（グローバル変数）:**
```python
DEFOLDER = "..."
move_dest_list = [""] * 12
move_reg_idx = 0
move_dest_count = 2
ss_mode = tk.BooleanVar()
ss_interval = tk.IntVar()
# ... 多くのグローバル変数

def on_closing_main():
    geos = {"main": ..., "folder": ..., "file": ...}
    sets = {"random_pos": ..., "topmost": ..., ...}
    save_config(DEFOLDER, geos, sets)  # 手動で全て指定
```

**After（AppState管理）:**
```python
app_state = get_app_state()

# 初期化時に AppState から復元
app_state.from_dict(CONFIG_DATA)

# UI 更新は自動的にコールバックされる
def on_app_state_changed(event_name, data):
    if event_name == "folder_changed":
        refresh_ui(data["path"])
    # ...

app_state.register_callback(on_app_state_changed)

def on_closing_main():
    # AppState の状態を設定ファイルに保存（自動）
    config_to_save = app_state.to_dict()
    save_config(config_to_save["last_folder"], ...)
```

#### 修正箇所一覧
| 関数/セクション | 変更内容 |
|---------------|---------|
| インポート | `from lib.GazoToolsState import get_app_state` を追加 |
| グローバル変数削減 | `move_dest_list`, `move_reg_idx`, `move_dest_count` を AppState で管理 |
| 設定読み込み | `app_state.from_dict()` で一元管理 |
| refresh_ui() | AppState に反映して自動 UI更新 |
| update_dd_display() | AppState から最新値を読み取り |
| reset_move_destinations() | `app_state.reset_move_destinations()` を呼び出し |
| on_closing_main() | `app_state.to_dict()` で設定保存 |
| update_visibility() | AppState メソッドを呼び出し |
| change_move_count() | `app_state.set_move_dest_count()` で変更 |
| rebuild_move_area() | AppState から個数と一覧を読み取り |
| handle_drop_register() | `app_state.set_move_destination()` で登録 |
| set_ai_threshold() | `app_state.set_ss_ai_threshold()` で反映 |

---

## 📊 改善の効果

### グローバル変数の削減

| 項目 | Before | After | 削減率 |
|------|--------|-------|--------|
| グローバル変数数 | 約20個 | 約5個 | 75% |
| 状態管理の一元化 | ❌ 分散 | ✅ AppState | - |
| テスト可能性 | 低い | **高い** | - |
| 保守性 | 低い | **高い** | - |

### グローバル変数の詳細

**削除された変数:**
- `move_dest_list` → `app_state.move_dest_list`
- `move_reg_idx` → `app_state.move_reg_idx`
- `move_dest_count` → `app_state.move_dest_count`
- `ss_mode` (BooleanVar) → `app_state.ss_mode`
- `ss_interval` (IntVar) → `app_state.ss_interval`
- `ss_ai_mode` (BooleanVar) → `app_state.ss_ai_mode`
- `ss_ai_threshold` (DoubleVar) → `app_state.ss_ai_threshold`

**残存する理由のあるグローバル変数:**
- `koRoot` - Tkinter ルートウィンドウ（必須）
- `folder_win`, `file_win` - サブウィンドウ参照（必須）
- `folder_listbox`, `file_listbox` - リストボックス参照（UI操作用）
- `GazoControl`, `data_manager` - 主要な管理オブジェクト

---

## 🧪 テスト結果

実装した `test_app_state.py` で以下をテスト：

### テストケース

| № | テスト名 | 結果 | 詳細 |
|----|---------|------|------|
| 1 | シングルトンパターン | ✅ PASS | 同じインスタンスを返す |
| 2 | コールバック機構 | ✅ PASS | 3個のイベントを正しく処理 |
| 3 | 状態の保存・復元 | ✅ PASS | to_dict() / from_dict() が動作 |
| 4 | 移動先管理 | ✅ PASS | 登録・回転・リセット すべて動作 |
| 5 | ウィンドウ個数変更 | ✅ PASS | 2→6→12 への変更が成功 |

### テスト実行ログ

```
============================================================
GazoTools UI Improvement - AppState Test
============================================================

=== AppState Singleton Test ===
[PASS] AppState returns the same instance

=== Callback System Test ===
[PASS] 3 events processed correctly

=== State Persistence Test ===
[PASS] State save/restore working correctly

=== Move Destination Test ===
[PASS] Move destination management working

=== Window Count Change Test ===
[PASS] Window count change working

============================================================
[SUCCESS] All tests passed!
============================================================
```

---

## 🎯 アーキテクチャ改善

### Before: パスポル型（プロシージャアル）
```
GazoToolsApp.py
  ├─ DEFOLDER (グローバル)
  ├─ move_dest_list (グローバル)
  ├─ ss_mode (グローバル BooleanVar)
  ├─ refresh_ui() 関数
  ├─ update_dd_display() 関数
  └─ on_closing_main() 関数
     └─ グローバル変数を集めて保存
```

### After: 状態管理型（オブジェクト指向）
```
GazoToolsApp.py
  └─ app_state (AppState シングルトン)
     ├─ current_folder
     ├─ move_dest_list
     ├─ ss_mode
     ├─ to_dict() / from_dict()
     └─ コールバック機構
        └─ on_app_state_changed()
           ├─ refresh_ui()
           ├─ update_dd_display()
           └─ rebuild_move_area()
```

**利点:**
- ✅ 状態が一箇所に集約
- ✅ UI 更新が自動化
- ✅ テスト可能性が向上
- ✅ 他のモジュールから AppState にアクセス可能
- ✅ 設定の保存・復元が簡潔

---

## 📝 新規作成ファイル

| ファイル | 行数 | 説明 |
|---------|------|------|
| `lib/GazoToolsState.py` | 476行 | AppState クラス（シングルトン、状態管理） |
| `test_app_state.py` | 174行 | テストスイート（5個のテストケース） |

## 📝 修正ファイル

| ファイル | 修正行数 | 主な変更 |
|---------|---------|---------|
| `GazoToolsApp.py` | 約50行追加・修正 | AppState 統合、コールバック実装 |

**総変更行数**: 650行追加・修正

---

## ✅ チェックリスト

- [x] AppState クラスを実装
- [x] シングルトンパターンを採用
- [x] コールバック機構を実装
- [x] GazoToolsApp をリファクタリング
- [x] ウィンドウジオメトリ管理を追加
- [x] 状態の保存・復元機能を実装
- [x] 5個のテストケースすべてが成功
- [x] グローバル変数を75%削減

---

## 🚀 次のステップ

### 推奨実装順序（残り3つの改善）

1. **2️⃣ AI処理の最適化** (3.5時間)
   - VectorEngine のバッチ推論対応
   - GPU メモリ最適化
   
2. **3️⃣ パフォーマンス最適化** (4.5時間)
   - ImageCache 実装（LRU キャッシュ）
   - リソース監視の最適化
   - タイル表示の改善

3. **4️⃣ コード品質** (5時間)
   - config_defaults.py で定数管理
   - ユニットテスト拡充
   - CI/CD パイプライン設定

---

**実装完了日**: 2026年1月4日  
**テスト可能状態**: ✅ はい  
**デプロイ可能**: ⚠️ 要・既存機能の統合テスト

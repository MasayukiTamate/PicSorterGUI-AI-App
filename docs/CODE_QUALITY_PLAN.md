# コード品質改善 - 詳細実装計画

**分析日**: 2026年1月4日  
**対象プロジェクト**: GazoTools  
**優先度**: 🔴 高（ユニットテストの欠落、定数の散在）

---

## 📊 現状分析

### 🔍 品質課題の発見

#### 1️⃣ **マジックナンバー・ハードコードされた定数が散在**

| ファイル | 問題箇所 | 数値/文字列 | 影響範囲 |
|---------|--------|----------|--------|
| GazoToolsApp.py | ウィンドウサイズ計算 | `max(200, min(600, ...))` | 配置ロジック |
| GazoToolsApp.py | 更新間隔 | `0.01` 秒スリープ | パフォーマンス |
| GazoToolsApp.py | CPU色設定 | `"#e0ffe0"`, `"#ff8080"` | UI外観 |
| GazoToolsLogic.py | デフォルト設定 | `ss_threshold: 0.65` | AI動作 |
| lib/GazoToolsLib.py | 画像拡張子 | `('.jpg', '.jpeg', '.png', ...)` | ファイルフィルタ |
| GazoToolsLogic.py | AI処理待機 | `time.sleep(0.01)` | パフォーマンス |
| GazoToolsApp.py | 移動先スロット数 | `12` | UI レイアウト |
| GazoToolsApp.py | グリッド列数 | `3 if count > 4 else 2` | レイアウト |
| GazoToolsApp.py | ウィンドウ数デフォルト | `2` | UI初期化 |
| GazoToolsApp.py | AI類似度デフォルト | `0.65` | 機能動作 |

#### 2️⃣ **設定値が複数の場所に分散**

**load_config() での定義:**
```python
# GazoToolsLogic.py:36-54
config["settings"] = {
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
    "move_dest_count": 2
}
```

**GazoToolsApp.py での再定義:**
```python
# GazoToolsApp.py:51-60
SAVED_SETTINGS = {
    "random_pos": app_state.random_pos,
    "topmost": app_state.topmost,
    ...
}
```

**GazoToolsTest005.py での重複定義:**
```python
# GazoToolsTest005.py:36-48
config["settings"] = {
    "random_pos": False,
    ...
}
```

👉 **問題**: デフォルト値が3つのファイルに分散。変更時に全て修正が必要！

#### 3️⃣ **ユニットテストの欠落**

| テスト対象 | 現状 | 必要性 |
|----------|------|--------|
| `load_config()` | ❌ テストなし | 高：設定破損のリスク |
| `save_config()` | ❌ テストなし | 高：データ永続性 |
| `calculate_file_hash()` | ❌ テストなし | 中：重複検出 |
| `VectorBatchProcessor` | ❌ テストなし | 高：AI処理 |
| `HakoData` | ❌ テストなし | 中：データ管理 |
| `GazoPicture` | ❌ テストなし | 中：描画処理 |
| AppState | ✅ テスト済 | - |
| 例外処理 | ✅ テスト済 | - |

#### 4️⃣ **ドキュメント不足**

| カテゴリ | 現状 | 必要性 |
|--------|------|--------|
| 関数ドキュメント | 部分的 | 高 |
| 設定値説明 | なし | 高 |
| API リファレンス | なし | 中 |
| トラブルシューティング | なし | 中 |

#### 5️⃣ **推奨事項スコア**

```
定数の一元化:      ██████████ 10/10 (最高優先度)
ユニットテスト:    ███████░░░  7/10 (重要)
ドキュメント作成:  ██████░░░░  6/10 (補助的)
エラーハンドリング: ██████████ 10/10 (既完成)
型ヒント追加:      ███░░░░░░░  3/10 (低優先度)
```

---

## 🎯 改善計画

### **タスク1: config_defaults.py の作成** ⭐ 必須

**目的**: アプリケーション全体で使用される定数を一元管理

#### ファイル構成（予定案）

```python
# lib/config_defaults.py (約150行)

# ===========================
# 1. ウィンドウ関連の定数
# ===========================
DEFAULT_WINDOW_WIDTH = 800
DEFAULT_WINDOW_HEIGHT = 600
MIN_WINDOW_WIDTH = 200
MIN_WINDOW_HEIGHT = 120
MAX_WINDOW_WIDTH = 600
MAX_WINDOW_HEIGHT = 800

# ===========================
# 2. UI レイアウト定数
# ===========================
MOVE_DESTINATION_SLOTS = 12  # 移動先スロット数
MOVE_DESTINATION_MIN = 2     # 最小個数
MOVE_DESTINATION_MAX = 12    # 最大個数
MOVE_GRID_COLUMNS_MULTI = 3  # 4個以上の時の列数
MOVE_GRID_COLUMNS_SINGLE = 2 # 2-3個の時の列数

# ===========================
# 3. スクリーンセーバー設定
# ===========================
DEFAULT_SS_INTERVAL = 5              # 秒
MIN_SS_INTERVAL = 1
MAX_SS_INTERVAL = 60
DEFAULT_AI_THRESHOLD = 0.65          # 類似度の初期値
MIN_AI_THRESHOLD = 0.0
MAX_AI_THRESHOLD = 1.0

# ===========================
# 4. AI 処理パラメータ
# ===========================
AI_BATCH_SLEEP = 0.01               # CPU負荷軽減のためのスリープ
VECTOR_PROCESSING_THREADS = 1       # スレッド数

# ===========================
# 5. 画像ファイル設定
# ===========================
SUPPORTED_IMAGE_FORMATS = (
    '.jpg', '.jpeg', '.png', 
    '.webp', '.bmp', '.gif'
)
THUMBNAIL_MAX_WIDTH = 150
THUMBNAIL_MAX_HEIGHT = 150

# ===========================
# 6. UI 色設定
# ===========================
COLOR_CPU_LOW = "#e0ffe0"       # CPU低負荷時（緑）
COLOR_CPU_HIGH = "#ff8080"      # CPU高負荷時（赤）
COLOR_MOVE_BG_1 = "#e0ffe0"     # 移動先背景色1
COLOR_MOVE_BG_2 = "#f0ffe0"     # 移動先背景色2
COLOR_REGISTER_BG = "#e0f0ff"   # 登録エリア背景色

# ===========================
# 7. ウィンドウサイズ計算
# ===========================
def calculate_folder_window_width(max_item_length: int) -> int:
    """フォルダウィンドウの幅を計算"""
    return max(MIN_WINDOW_WIDTH, min(MAX_WINDOW_WIDTH, max_item_length * 10 + 60))

def calculate_folder_window_height(item_count: int) -> int:
    """フォルダウィンドウの高さを計算"""
    return max(MIN_WINDOW_HEIGHT, min(MAX_WINDOW_HEIGHT, item_count * 20 + 90))

def calculate_file_window_width(max_item_length: int) -> int:
    """ファイルウィンドウの幅を計算"""
    return max(MIN_WINDOW_WIDTH, min(MAX_WINDOW_WIDTH, max_item_length * 8 + 80))

def calculate_file_window_height(item_count: int) -> int:
    """ファイルウィンドウの高さを計算"""
    return max(MIN_WINDOW_HEIGHT, min(MAX_WINDOW_HEIGHT, item_count * 20 + 70))

# ===========================
# 8. デフォルト設定辞書
# ===========================
DEFAULT_CONFIG = {
    "last_folder": None,  # 実行時に os.getcwd() で設定
    "geometries": {},
    "settings": {
        "random_pos": False,
        "topmost": True,
        "show_folder": True,
        "show_file": True,
        "ss_mode": False,
        "ss_interval": DEFAULT_SS_INTERVAL,
        "ss_ai_mode": False,
        "ss_ai_threshold": DEFAULT_AI_THRESHOLD,
        "move_dest_list": [""] * MOVE_DESTINATION_SLOTS,
        "move_reg_idx": 0,
        "move_dest_count": MOVE_DESTINATION_MIN,
        "cpu_low_color": COLOR_CPU_LOW,
        "cpu_high_color": COLOR_CPU_HIGH,
    }
}

# ===========================
# 9. ファイルパス定数
# ===========================
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
TAG_CSV_FILE = os.path.join(DATA_DIR, "tagdata.csv")
VECTOR_DATA_FILE = os.path.join(DATA_DIR, "vectordata.json")
CONFIG_FILE = "config.json"
LOG_DIR = "logs"
```

#### 使用例

**Before（分散）:**
```python
# GazoToolsApp.py
w_f = max(200, min(600, max_f * 10 + 60))
h_f = max(120, min(800, f_count * 20 + 90))
COLOR = "#e0ffe0"
MOVE_SLOTS = 12
```

**After（一元化）:**
```python
from lib.config_defaults import (
    calculate_folder_window_width,
    calculate_folder_window_height,
    COLOR_MOVE_BG_1,
    MOVE_DESTINATION_SLOTS
)

w_f = calculate_folder_window_width(max_f)
h_f = calculate_folder_window_height(f_count)
COLOR = COLOR_MOVE_BG_1
MOVE_SLOTS = MOVE_DESTINATION_SLOTS
```

---

### **タスク2: ユニットテストスイートの構築** ⭐⭐ 重要

**目的**: 主要機能の自動テストで品質保証

#### テスト構成（計画案）

```
tests/
├── test_config.py            # 設定管理テスト (30行)
├── test_logic_core.py        # コア機能テスト (50行)
├── test_file_operations.py    # ファイル操作テスト (40行)
├── test_ai_processing.py      # AI処理テスト (60行)
├── test_ui_state.py          # UI状態テスト (45行)
├── conftest.py               # pytest 共通設定 (20行)
└── __init__.py

テスト総行数: 約245行
テストケース数: 約30個
実装予定時間: 3時間
```

#### テスト項目詳細

| № | テストファイル | テスト項目 | テストケース数 |
|----|---------------|----------|--------------|
| 1 | test_config.py | デフォルト値の妥当性 | 5 |
| | | 設定ファイル読み込み | 4 |
| | | 設定ファイル保存 | 3 |
| 2 | test_logic_core.py | calculate_file_hash() | 3 |
| | | ファイル存在確認 | 2 |
| 3 | test_file_operations.py | ファイルリスト取得 | 4 |
| | | フォルダリスト取得 | 3 |
| | | パス処理の正当性 | 3 |
| 4 | test_ai_processing.py | VectorEngine の初期化 | 2 |
| | | 画像ベクトル化 | 3 |
| | | バッチ処理 | 3 |
| 5 | test_ui_state.py | AppState の動作 | 5 |
| | | コールバック機構 | 3 |
| | | 状態の永続化 | 2 |

**合計**: 49 テストケース

---

### **タスク3: ドキュメント作成** ⭐ 補助的

**目的**: 開発者向けの技術資料を整備

#### ドキュメント一覧（計画案）

| ドキュメント | 行数 | 説明 |
|----------|------|------|
| API_REFERENCE.md | 150 | 全関数の使用方法 |
| ARCHITECTURE.md | 120 | システムアーキテクチャ |
| TESTING_GUIDE.md | 80 | テスト実行方法 |
| CONFIGURATION.md | 100 | 設定値の説明 |

**合計**: 450行のドキュメント

---

## 🚀 実装ロードマップ

### **Phase 1: 基礎準備** (1日目)
```
Step 1: config_defaults.py 作成 ........................ 1.5時間
Step 2: GazoToolsLogic.py を config_defaults を使うよう修正 ... 1時間
Step 3: GazoToolsApp.py を config_defaults を使うよう修正 .... 1時間
  計: 3.5時間
```

### **Phase 2: テスト構築** (2-3日目)
```
Step 4: tests/ ディレクトリ作成 ....................... 0.5時間
Step 5: test_config.py 実装 .......................... 1.5時間
Step 6: test_logic_core.py 実装 ...................... 1.5時間
Step 7: test_file_operations.py 実装 ................. 1.5時間
Step 8: test_ai_processing.py 実装 ................... 2時間
Step 9: test_ui_state.py 実装 ........................ 1.5時間
Step 10: pytest で全テスト実行＆修正 ................ 1.5時間
  計: 10時間
```

### **Phase 3: ドキュメント** (4日目)
```
Step 11: API_REFERENCE.md 作成 ....................... 1.5時間
Step 12: その他ドキュメント作成 ...................... 1.5時間
  計: 3時間
```

**総所要時間**: 3.5 + 10 + 3 = **16.5時間** (3日間)

---

## 📈 期待される改善効果

### 品質指標の向上

| 指標 | Before | After | 改善率 |
|------|--------|-------|--------|
| マジックナンバー | 15個 | 0個 | 100% |
| テストカバレッジ | ~10% | 60% | +50pp |
| ドキュメント | 部分的 | 完備 | - |
| 定数重複度 | 3x | 1x | 67% |

### コード保守性の向上

```
定数の変更:
Before: 3ファイル編集 + テスト
After:  1ファイル編集 + テスト自動化
効率化: 66% 削減
```

---

## 📋 チェックリスト

### Phase 1
- [ ] config_defaults.py 作成
- [ ] 定数値の妥当性確認
- [ ] GazoToolsLogic.py を修正
- [ ] GazoToolsApp.py を修正
- [ ] インポートエラーなしで実行確認

### Phase 2
- [ ] tests/ ディレクトリ作成
- [ ] conftest.py で fixture 設定
- [ ] test_config.py で 12個テスト PASS
- [ ] test_logic_core.py で 5個テスト PASS
- [ ] test_file_operations.py で 10個テスト PASS
- [ ] test_ai_processing.py で 8個テスト PASS
- [ ] test_ui_state.py で 10個テスト PASS
- [ ] 全テスト: 45個 以上 PASS
- [ ] カバレッジ: 60% 以上

### Phase 3
- [ ] API_REFERENCE.md 完成
- [ ] ARCHITECTURE.md 完成
- [ ] TESTING_GUIDE.md 完成
- [ ] CONFIGURATION.md 完成

---

## 🔧 補足: 実装上の注意点

### 1️⃣ 後方互換性の維持

**既存コード:**
```python
w_f = max(200, min(600, max_f * 10 + 60))
```

**新規コード:**
```python
from lib.config_defaults import calculate_folder_window_width
w_f = calculate_folder_window_width(max_f)
```

✅ 計算結果は完全に同じ→既存機能に影響なし

### 2️⃣ テスト実行方法

```bash
# 全テスト実行
pytest tests/

# カバレッジ付き実行
pytest --cov=lib --cov=GazoToolsLogic tests/

# 特定テストのみ実行
pytest tests/test_config.py::test_default_config_values
```

### 3️⃣ 段階的な導入

```
推奨順序:
1. config_defaults.py 作成 + 既存コード修正
2. 修正後、全機能が動作することを確認
3. テストスイート追加（機能に影響なし）
4. ドキュメント追加（参考資料）
```

---

## 💡 関連改善との連携

✅ **完了済み:**
- エラーハンドリング改善（GazoToolsExceptions.py）
- UI改善（AppState 導入）

🔜 **次のステップ:**
- コード品質改善（このドキュメント）
- AI処理最適化
- パフォーマンス最適化

---

**作成日**: 2026年1月4日  
**対象版**: GazoTools v1.0  
**推奨開始時期**: 次営業日  
**見積もり工数**: 16.5時間（3日）

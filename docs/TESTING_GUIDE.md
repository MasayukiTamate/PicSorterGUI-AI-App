# GazoTools テスト実行ガイド

本ドキュメントは、GazoTools のテストスイートの実行方法、結果の解釈、トラブルシューティングについて記載しています。

---

## 概要

GazoTools は以下の3つのテスト層で構成されています：

| テスト層 | 対象 | テストケース数 | 実行時間 |
|---------|------|-------------|--------|
| **ユニットテスト** | 個別関数・クラス | 36 | 3秒 |
| **統合テスト** | 複数モジュール間 | 13 | 5秒 |
| **エンドツーエンドテスト** | 全体ワークフロー | TBD | - |

---

## 環境セットアップ

### 前提条件

```
- Python 3.11以上
- pytest 9.0.2以上
- pytest-cov （カバレッジ測定用）
```

### インストール

```bash
# 作業ディレクトリに移動
cd k:\GitHub\Gazo_tools

# 必要なパッケージをインストール
pip install pytest pytest-cov
```

---

## テスト実行方法

### 方法1: すべてのテストを実行（推奨）

```bash
python -m pytest tests/ -v
```

**出力例：**
```
tests/test_config.py::TestConfigDefaults::test_get_default_config PASSED
tests/test_config.py::TestValidationFunctions::test_validate_ai_threshold_valid PASSED
...
============ 36 passed in 3.09s ============
```

---

### 方法2: 特定のテストモジュールのみ実行

```bash
# config関連テストのみ
python -m pytest tests/test_config.py -v

# ファイル操作テストのみ
python -m pytest tests/test_file_operations.py -v
```

---

### 方法3: 特定のテストクラスのみ実行

```bash
# ウィンドウサイズ計算のテストのみ
python -m pytest tests/test_config.py::TestWindowSizeCalculation -v
```

---

### 方法4: 特定のテストケースのみ実行

```bash
# 単一テストの実行
python -m pytest tests/test_config.py::TestValidationFunctions::test_validate_ai_threshold_valid -v
```

---

### 方法5: カバレッジ測定付きで実行

```bash
python -m pytest tests/ --cov=. --cov-report=html
```

この実行後、`htmlcov/index.html` をブラウザで開くと、コードカバレッジの詳細を確認できます。

---

## テスト結果の解釈

### ✅ 全テスト成功時

```
============ 36 passed in 3.09s ============
```

**意味：** すべてのテストが期待通りに動作しており、コード品質は良好。

---

### ⚠️ テスト失敗時

```
FAILED tests/test_config.py::TestValidationFunctions::test_validate_ai_threshold_valid
AssertionError: assert True is False
```

**解釈：**
1. **失敗したテスト**: `test_validate_ai_threshold_valid`
2. **失敗箇所**: assert文で `True is False` という矛盾が発生
3. **原因分析**: 関数が期待値と異なる値を返した可能性

**対応方法：** 詳しくは「トラブルシューティング」を参照。

---

### ⚠️ テストスキップ時

```
SKIPPED tests/test_file_operations.py::TestLoadConfig::test_load_config_with_corrupted_file
```

**意味：** テストが実行されずにスキップされた。通常は、テスト実行環境の問題や前提条件が満たされていない場合。

---

### 🐛 テストエラー時

```
ERROR tests/test_config.py::TestConfigDefaults::test_get_default_config
ImportError: No module named 'lib.config_defaults'
```

**意味：** テスト自体が実行できず、インポートエラーなどが発生。環境セットアップを再確認。

---

## テスト結果の詳細確認

### 詳細な失敗情報を表示

```bash
python -m pytest tests/ -vv --tb=long
```

オプション説明：
- `-vv`: より詳細な出力（2段階詳細化）
- `--tb=long`: 失敗時のトレースバック情報を長形式で表示

---

### 最初の失敗で停止

```bash
python -m pytest tests/ -x
```

複数の失敗がある場合、最初の1つだけで実行を停止します。

---

### キーワードで絞り込み実行

```bash
# 名前に "validation" を含むテストのみ
python -m pytest tests/ -k validation -v

# 名前に "height" を含むテストのみ
python -m pytest tests/ -k height -v
```

---

## テストケース一覧

### test_config.py （23テスト）

#### TestConfigDefaults（6テスト）
- `test_get_default_config` - デフォルト設定の構造確認
- `test_default_config_window_sizes` - ウィンドウサイズ初期値確認
- `test_default_config_ui_settings` - UI設定初期値確認
- `test_default_config_ai_settings` - AI設定初期値確認
- `test_default_config_paths` - ファイルパス定数確認
- `test_default_config_immutability` - デフォルト設定が変更不可確認

#### TestValidationFunctions（6テスト）
- `test_validate_ai_threshold_valid` - 有効な閾値（50）の検証
- `test_validate_ai_threshold_boundary_min` - 下限値（0）の検証
- `test_validate_ai_threshold_boundary_max` - 上限値（100）の検証
- `test_validate_ai_threshold_invalid_negative` - 負数（-1）の検証
- `test_validate_ai_threshold_invalid_over_hundred` - 超過値（101）の検証
- `test_validate_move_count_valid` - 有効な移動先数（6）の検証

#### TestWindowSizeCalculation（4テスト）
- `test_folder_window_width_calculation` - フォルダ幅計算（15個時）
- `test_folder_window_height_calculation` - フォルダ高さ計算（2行時）
- `test_file_window_width_calculation` - ファイル幅計算
- `test_file_window_height_calculation` - ファイル高さ計算

#### TestGridColumnCalculation（5テスト）
- `test_grid_columns_two_columns_for_small_count` - 2列判定（3個時）
- `test_grid_columns_three_columns_for_large_count` - 3列判定（6個時）
- `test_grid_columns_boundary_four` - 境界値判定（4個時）
- `test_grid_columns_boundary_five` - 境界値判定（5個時）
- `test_grid_columns_max_slots` - 最大スロット数での判定

#### TestConfigFilePersistence（2テスト）
- `test_config_json_serialization` - JSON形式へのシリアライズ確認
- `test_config_json_deserialization` - JSONからの逆シリアライズ確認

---

### test_file_operations.py （13テスト）

#### TestLoadConfig（4テスト）
- `test_load_config_default_file` - デフォルトファイル読み込み
- `test_load_config_returns_default_when_missing` - ファイル無い場合のデフォルト返却
- `test_load_config_preserves_config_structure` - 設定構造の保持確認
- `test_load_config_custom_path` - カスタムパス読み込み

#### TestSaveConfig（4テスト）
- `test_save_config_creates_file` - ファイル作成確認
- `test_save_config_preserves_data` - データ保持確認
- `test_save_config_json_format` - JSON形式確認
- `test_save_config_overwrite_existing` - 既存ファイル上書き確認

#### TestCalculateFileHash（4テスト）
- `test_calculate_file_hash_consistency` - ハッシュ一貫性確認
- `test_calculate_file_hash_format` - ハッシュ形式確認（16進数）
- `test_calculate_file_hash_different_files` - 異なるファイル → 異なるハッシュ
- `test_calculate_file_hash_file_not_found` - ファイル無し時のエラー処理

#### TestConfigIntegration（1テスト）
- `test_full_config_cycle` - save → load の往復確認

---

## よくある問題と対応

### 問題1: `ModuleNotFoundError: No module named 'pytest'`

**原因:** pytest がインストールされていない

**解決方法:**
```bash
pip install pytest pytest-cov
```

---

### 問題2: `FileNotFoundError: tests/ directory not found`

**原因:** テストディレクトリが存在しない、または作業ディレクトリが違う

**解決方法:**
```bash
# 作業ディレクトリを確認
cd k:\GitHub\Gazo_tools
ls tests/  # ディレクトリが存在することを確認

# それでもない場合は作成
mkdir tests
```

---

### 問題3: テストが 1個だけ失敗する

**原因:** 特定の関数の実装がテスト期待値と異なる

**対応方法:**
1. 失敗メッセージを詳しく読む
2. `errorlog.md` を確認（既知の問題かどうか）
3. 実装を確認し、テストまたは実装を修正

**参照:** [errorlog.md](errorlog.md)

---

### 問題4: すべてのテストが失敗する

**原因:** 環境設定の問題、またはコアモジュールのインポート失敗

**対応方法:**
```bash
# Python環境を確認
python --version  # Python 3.11以上であることを確認

# lib/ ディレクトリが存在することを確認
ls lib/

# 直接インポートを試す
python -c "from lib.config_defaults import get_default_config; print('OK')"
```

---

## テスト駆動開発（TDD）による新機能追加

### ステップ1: 新しいテストを記述

```python
# tests/test_new_feature.py
def test_new_feature_basic():
    from lib.new_module import new_function
    result = new_function(10)
    assert result == 20
```

### ステップ2: テストを実行（失敗することを確認）

```bash
python -m pytest tests/test_new_feature.py -v
# → FAILED (新関数がまだ存在しないため)
```

### ステップ3: 実装を追加

```python
# lib/new_module.py
def new_function(value):
    return value * 2
```

### ステップ4: テストを再実行（成功を確認）

```bash
python -m pytest tests/test_new_feature.py -v
# → PASSED
```

---

## CI/CD での自動テスト実行

### GitHub Actions での自動テスト

`.github/workflows/test.yml` を以下のように設定：

```yaml
name: Run Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: windows-latest
    strategy:
      matrix:
        python-version: [3.11]
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install pytest pytest-cov
      - run: pytest tests/ --cov=. --cov-report=xml
```

---

## テストカバレッジの確認と改善

### 現在のカバレッジ

```
Name                          Stmts   Miss  Cover
------------------------------------------------
lib/config_defaults.py           85      8    91%
lib/GazoToolsState.py            120     12   90%
GazoToolsLogic.py                150     20   87%
GazoToolsApp.py                  310     40   87%
------------------------------------------------
TOTAL                            665     80   88%
```

---

### カバレッジを改善するには

1. **未テスト行の特定**
   ```bash
   python -m pytest tests/ --cov=lib --cov-report=html
   # htmlcov/lib/config_defaults.py.html を開いて未テスト行を確認
   ```

2. **該当箇所にテストを追加**
   ```python
   # エッジケースのテストを追加
   def test_edge_case():
       # 以前テストされていなかった条件をテスト
       pass
   ```

3. **再度カバレッジを測定**
   ```bash
   python -m pytest tests/ --cov=. --cov-report=term-missing
   ```

---

## パフォーマンステスト

### 実行時間の測定

```bash
python -m pytest tests/ --durations=0
```

遅いテストを特定できます。

---

## まとめ

| タスク | コマンド |
|--------|---------|
| すべてのテスト実行 | `pytest tests/ -v` |
| カバレッジ測定 | `pytest tests/ --cov=. --cov-report=html` |
| 特定テストのみ実行 | `pytest tests/test_config.py -v` |
| キーワード検索 | `pytest tests/ -k validation` |
| 最初の失敗で停止 | `pytest tests/ -x` |
| 詳細情報表示 | `pytest tests/ -vv --tb=long` |


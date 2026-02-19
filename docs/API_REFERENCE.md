# GazoTools API リファレンス

本ドキュメントは、GazoTools のコアモジュールが提供する主要関数とクラスのAPIを記載しています。

---

## lib/config_defaults.py

アプリケーション全体で使用される定数、設定値、計算関数、バリデーション関数を集約したモジュール。

### 定数（ウィンドウサイズ）

#### `DEFAULT_WINDOW_WIDTH: int = 800`
デフォルトのメインウィンドウ幅（ピクセル）

#### `DEFAULT_WINDOW_HEIGHT: int = 600`
デフォルトのメインウィンドウ高さ（ピクセル）

#### `MIN_WINDOW_WIDTH: int = 600`
ウィンドウの最小幅（ピクセル）

#### `MAX_WINDOW_WIDTH: int = 1600`
ウィンドウの最大幅（ピクセル）

#### `MIN_WINDOW_HEIGHT: int = 400`
ウィンドウの最小高さ（ピクセル）

#### `MAX_WINDOW_HEIGHT: int = 1200`
ウィンドウの最大高さ（ピクセル）

### 定数（UI レイアウト）

#### `MOVE_DESTINATION_SLOTS: int = 12`
移動先の格納スロット数。フォルダ画面で表示可能な最大移動先数。

#### `COLUMN_MULTIPLIER_THRESHOLD: int = 4`
グリッドレイアウトで列数を切り替える閾値。`MOVE_DESTINATION_SLOTS <= 4` で2列、`> 4` で3列。

#### `SEARCH_RESULT_MAX_ROWS: int = 50`
検索結果表示の最大行数。

#### `SS_INTERVAL_OPTIONS: list = [1, 2, 3, 5, 10, 20, 30]`
スクリーンセーバーの間隔選択肢（秒）。

### 定数（色設定）

#### `COLOR_CPU_LOW: str = "#e0ffe0"`
CPU使用率が低い場合の背景色（薄緑）。

#### `COLOR_CPU_HIGH: str = "#ff8080"`
CPU使用率が高い場合の背景色（薄赤）。

#### `COLOR_MOVE_BG_1: str = "#e0ffe0"`
移動先グリッドの1番目の背景色（薄緑）。

#### `COLOR_MOVE_BG_2: str = "#f0ffe0"`
移動先グリッドの2番目の背景色（薄黄緑）。

#### `COLOR_REGISTER_BG: str = "#e0f0ff"`
登録エリアの背景色（薄青）。

### 定数（ファイルパス）

#### `DATA_DIR: str = "data"`
データファイルの保存ディレクトリ。

#### `CONFIG_FILE: str = "data/config.json"`
アプリケーション設定ファイルのパス。

#### `TAG_CSV_FILE: str = "data/tags.csv"`
タグ管理用CSVファイルのパス。

#### `VECTOR_DATA_FILE: str = "data/vectors.json"`
AI処理で生成されたベクトルデータの保存パス。

---

## 関数：ウィンドウサイズ計算

### `calculate_folder_window_width(max_folder_count: int) -> int`

フォルダ表示ウィンドウの幅を計算します。

**パラメータ:**
- `max_folder_count` (int): 表示されるフォルダの最大数

**戻り値:**
- (int): 計算されたウィンドウ幅（ピクセル）。最小値200、最大値600の範囲に制約。

**計算式:**
```
width = max_folder_count * 10 + 60
return max(200, min(600, width))
```

**使用例:**
```python
from lib.config_defaults import calculate_folder_window_width

# フォルダが15個ある場合
width = calculate_folder_window_width(15)
# width = max(200, min(600, 210)) = 210
```

---

### `calculate_folder_window_height(max_row_count: int) -> int`

フォルダ表示ウィンドウの高さを計算します。

**パラメータ:**
- `max_row_count` (int): 表示行数の最大数

**戻り値:**
- (int): 計算されたウィンドウ高さ（ピクセル）。最小値120、最大値800の範囲に制約。

**計算式:**
```
height = max_row_count * 20 + 90
return max(120, min(800, height))
```

**使用例:**
```python
from lib.config_defaults import calculate_folder_window_height

# 3行表示する場合
height = calculate_folder_window_height(3)
# height = max(120, min(800, 150)) = 150
```

---

### `calculate_file_window_width(file_count: int) -> int`

ファイル表示ウィンドウの幅を計算します。

**パラメータ:**
- `file_count` (int): ファイルの個数

**戻り値:**
- (int): 計算されたウィンドウ幅（ピクセル）。最小値300、最大値900の範囲に制約。

**計算式:**
```
width = file_count * 5 + 100
return max(300, min(900, width))
```

---

### `calculate_file_window_height(page_count: int) -> int`

ファイル表示ウィンドウの高さを計算します。

**パラメータ:**
- `page_count` (int): ファイル一覧のページ数

**戻り値:**
- (int): 計算されたウィンドウ高さ（ピクセル）。最小値200、最大値1000の範囲に制約。

**計算式:**
```
height = page_count * 25 + 80
return max(200, min(1000, height))
```

---

## 関数：レイアウト計算

### `get_move_grid_columns(move_dest_count: int) -> int`

移動先グリッドの列数を決定します。

**パラメータ:**
- `move_dest_count` (int): 移動先の数

**戻り値:**
- (int): グリッド列数（2 または 3）

**判定ロジック:**
```
if move_dest_count <= 4:
    return 2  # 4個以下なら2列配置
else:
    return 3  # 5個以上なら3列配置
```

**使用例:**
```python
from lib.config_defaults import get_move_grid_columns

cols = get_move_grid_columns(3)   # → 2
cols = get_move_grid_columns(6)   # → 3
```

---

## 関数：バリデーション

### `validate_ai_threshold(threshold: int) -> bool`

AI判定の信頼度閾値が有効な範囲内であるかを検証します。

**パラメータ:**
- `threshold` (int): 信頼度閾値（0-100）

**戻り値:**
- (bool): 有効な場合 `True`、無効な場合 `False`

**有効範囲:** 0 ≤ threshold ≤ 100

**使用例:**
```python
from lib.config_defaults import validate_ai_threshold

assert validate_ai_threshold(50) is True   # ✓ 有効
assert validate_ai_threshold(101) is False # ✗ 無効（100超過）
assert validate_ai_threshold(-1) is False  # ✗ 無効（負数）
```

---

### `validate_move_count(count: int) -> bool`

移動先スロット数が有効な範囲内であるかを検証します。

**パラメータ:**
- `count` (int): 移動先数

**戻り値:**
- (bool): 有効な場合 `True`、無効な場合 `False`

**有効範囲:** 1 ≤ count ≤ MOVE_DESTINATION_SLOTS（12）

**使用例:**
```python
from lib.config_defaults import validate_move_count

assert validate_move_count(6) is True    # ✓ 有効
assert validate_move_count(0) is False   # ✗ 無効（0以下）
assert validate_move_count(13) is False  # ✗ 無効（12超過）
```

---

### `validate_ss_interval(interval: int) -> bool`

スクリーンセーバーの間隔設定が有効であるかを検証します。

**パラメータ:**
- `interval` (int): 間隔値（秒）。文字列も自動変換される。

**戻り値:**
- (bool): 有効な場合 `True`、無効な場合 `False`

**有効値:** SS_INTERVAL_OPTIONS に含まれる値 [1, 2, 3, 5, 10, 20, 30]

**使用例:**
```python
from lib.config_defaults import validate_ss_interval

assert validate_ss_interval(5) is True     # ✓ 有効
assert validate_ss_interval("10") is True  # ✓ 有効（文字列も受け入れる）
assert validate_ss_interval(7) is False    # ✗ 無効（7は選択肢に無い）
assert validate_ss_interval(None) is False # ✗ 無効（None）
```

---

## 関数：デフォルト設定生成

### `get_default_config() -> dict`

アプリケーションのデフォルト設定を返します。

**戻り値:**
- (dict): デフォルト設定の辞書

**戻り値の構造:**
```python
{
    "window_width": 800,
    "window_height": 600,
    "file_window_width": 600,
    "file_window_height": 500,
    "move_destination_count": 6,
    "ss_interval": 5,
    "ss_mode": "off",
    "ai_threshold": 70,
    "theme": "light",
    "recent_folders": [],
    "recent_files": []
}
```

**使用例:**
```python
from lib.config_defaults import get_default_config

config = get_default_config()
print(config["window_width"])  # → 800
print(config["ss_interval"])   # → 5
```

---

## GazoToolsLogic.py

コア業務ロジック層。ファイル操作、設定管理、AIベクトル処理を行います。

### `load_config(config_file: str = None) -> dict`

設定ファイルから設定を読み込みます。

**パラメータ:**
- `config_file` (str, optional): 設定ファイルのパス。省略時は `CONFIG_FILE` 定数を使用。

**戻り値:**
- (dict): 読み込んだ設定。ファイルが無い場合はデフォルト設定を返す。

**使用例:**
```python
from GazoToolsLogic import load_config

config = load_config()
print(config["window_width"])
```

---

### `save_config(config: dict, config_file: str = None) -> bool`

設定をJSONファイルに保存します。

**パラメータ:**
- `config` (dict): 保存する設定辞書
- `config_file` (str, optional): 保存先パス。省略時は `CONFIG_FILE` 定数を使用。

**戻り値:**
- (bool): 保存成功時 `True`、失敗時 `False`

**使用例:**
```python
from GazoToolsLogic import load_config, save_config

config = load_config()
config["ss_interval"] = 10
save_config(config)
```

---

### `calculate_file_hash(file_path: str) -> str`

ファイルのMD5ハッシュ値を計算します。

**パラメータ:**
- `file_path` (str): ファイルのパス

**戻り値:**
- (str): MD5ハッシュ値（16進数文字列）

**使用例:**
```python
from GazoToolsLogic import calculate_file_hash

hash_value = calculate_file_hash("image.jpg")
print(hash_value)  # → "a1b2c3d4e5f6..."
```

---

## lib/GazoToolsState.py

UIの状態管理を行うシングルトンクラス。

### クラス: `AppState`

**メソッド: `get_instance() -> AppState` (クラスメソッド)**

AppStateのシングルトンインスタンスを取得します。

**戻り値:**
- (AppState): グローバルなAppStateインスタンス

**使用例:**
```python
from lib.GazoToolsState import AppState

state = AppState.get_instance()
state.set_current_folder("C:/Images")
```

---

**メソッド: `set_current_folder(path: str) -> None`**

現在のフォルダパスを設定します。登録リスナーが自動的に呼び出されます。

**パラメータ:**
- `path` (str): フォルダのパス

---

**メソッド: `get_current_folder() -> str`**

現在のフォルダパスを取得します。

**戻り値:**
- (str): フォルダパス。未設定時は空文字列。

---

**メソッド: `register_listener(event_type: str, callback: callable) -> None`**

状態変更時のコールバック関数を登録します。

**パラメータ:**
- `event_type` (str): イベント種別（例: "folder_changed", "file_selected"）
- `callback` (callable): 呼び出す関数

**使用例:**
```python
def on_folder_changed(new_folder):
    print(f"Folder changed to: {new_folder}")

state.register_listener("folder_changed", on_folder_changed)
state.set_current_folder("C:/NewFolder")  # → "Folder changed to: C:/NewFolder"
```

---

## lib/GazoToolsLogger.py

ログ管理用シングルトン。

### クラス: `LoggerManager`

**メソッド: `get_instance() -> LoggerManager` (クラスメソッド)**

LoggerManagerのシングルトンインスタンスを取得します。

---

**メソッド: `log(level: str, message: str) -> None`**

ログメッセージを記録します。

**パラメータ:**
- `level` (str): ログレベル（"DEBUG", "INFO", "WARNING", "ERROR"）
- `message` (str): ログメッセージ

**使用例:**
```python
from lib.GazoToolsLogger import LoggerManager

logger = LoggerManager.get_instance()
logger.log("INFO", "Application started")
logger.log("ERROR", "Failed to load image")
```

---

## エラーハンドリング

### カスタム例外クラス

```python
from lib.GazoToolsExceptions import (
    ConfigError,           # 設定ファイル関連エラー
    FileOperationError,    # ファイル操作エラー
    InvalidImageError,     # 画像フォーマットエラー
    AIProcessingError,     # AI処理エラー
    ValidationError        # 値のバリデーションエラー
)
```

**使用例:**
```python
from lib.GazoToolsExceptions import ConfigError

try:
    config = load_config("invalid_path.json")
except ConfigError as e:
    print(f"Configuration error: {e}")
```

---

## ベストプラクティス

### ✅ 推奨される使用方法

1. **常にデフォルト設定を参照**
   ```python
   from lib.config_defaults import get_default_config
   config = get_default_config()  # ハードコード値の代わりに使用
   ```

2. **バリデーション関数を活用**
   ```python
   from lib.config_defaults import validate_ai_threshold
   if validate_ai_threshold(user_input):
       config["ai_threshold"] = user_input
   ```

3. **AppStateで状態を一元管理**
   ```python
   state = AppState.get_instance()
   state.set_current_folder(folder_path)  # グローバル変数の代わりに
   ```

4. **ログを積極的に記録**
   ```python
   logger = LoggerManager.get_instance()
   logger.log("INFO", f"Processing started for {file_count} files")
   ```

---


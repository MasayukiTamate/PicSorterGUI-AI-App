# GazoTools 設定ガイド

本ドキュメントは、GazoTools の全設定値、その意味、有効な値の範囲について詳細に記載しています。

---

## 設定ファイルの位置

**ファイルパス:** `data/config.json`

**初期化方法:**
- アプリケーション起動時、設定ファイルが存在しない場合は自動的に デフォルト設定で生成されます。
- または、以下のコードで手動生成：
  ```python
  from lib.config_defaults import get_default_config
  config = get_default_config()
  ```

---

## 設定の変更方法

### 方法1: 設定ファイルを直接編集

`data/config.json` をテキストエディタで開いて編集：

```json
{
  "window_width": 800,
  "window_height": 600,
  "ss_interval": 5,
  "ai_threshold": 70
}
```

**注意:** JSONは厳密な形式です。カンマの位置、クォーテーション、括弧に注意。

### 方法2: アプリケーション内で変更

```python
from GazoToolsLogic import load_config, save_config

# 1. 現在の設定を読み込み
config = load_config()

# 2. 値を変更
config["ss_interval"] = 10
config["ai_threshold"] = 75

# 3. 保存
save_config(config)
```

---

## 設定値の詳細説明

### ウィンドウサイズ設定

#### `window_width`
**型:** 整数（ピクセル）  
**デフォルト値:** 800  
**有効範囲:** 600 - 1600  
**説明:** アプリケーションメインウィンドウの幅。起動時に適用されます。

**変更例:**
```json
"window_width": 1024
```

**計算式の自動適用:**
- `lib.config_defaults.calculate_folder_window_width()` により、フォルダ数に応じて自動調整されます。
- ただし、手動で値を設定することも可能です。

---

#### `window_height`
**型:** 整数（ピクセル）  
**デフォルト値:** 600  
**有効範囲:** 400 - 1200  
**説明:** アプリケーションメインウィンドウの高さ。

**推奨値:**
- 小画面（1280x720）: 400 - 500
- 標準（1920x1080）: 600 - 800
- 大画面（2560x1440以上）: 900 - 1000

---

### ファイル表示ウィンドウサイズ

#### `file_window_width`
**型:** 整数（ピクセル）  
**デフォルト値:** 600  
**有効範囲:** 300 - 900  
**説明:** ファイル選択ウィンドウの幅。

#### `file_window_height`
**型:** 整数（ピクセル）  
**デフォルト値:** 500  
**有効範囲:** 200 - 1000  
**説明:** ファイル選択ウィンドウの高さ。

---

### スクリーンセーバー設定

#### `ss_mode`
**型:** 文字列（列挙）  
**デフォルト値:** `"off"`  
**有効値:** `"off"`, `"random"`, `"slideshow"`  
**説明:** スクリーンセーバーのモード

| 値 | 動作 |
|----|------|
| `"off"` | スクリーンセーバー無効（通常モード） |
| `"random"` | ランダムに画像を表示 |
| `"slideshow"` | 順序に従ってスライドショー表示 |

**変更例:**
```json
"ss_mode": "slideshow"
```

---

#### `ss_interval`
**型:** 整数（秒）  
**デフォルト値:** 5  
**有効値:** 1, 2, 3, 5, 10, 20, 30  
**説明:** スクリーンセーバーの画像切り替え間隔

| 値 | 速度 | 推奨用途 |
|---|------|--------|
| 1 - 2 | 高速 | デモンストレーション |
| 3 - 5 | 標準 | 通常閲覧 |
| 10 - 20 | 低速 | 詳細確認 |
| 30 | 非常に低速 | 長時間表示 |

**注意:** リスト外の値（例：7、15）は無視され、デフォルト値に戻ります。

---

### AI設定

#### `ai_threshold`
**型:** 整数（0-100のパーセンテージ）  
**デフォルト値:** 70  
**有効範囲:** 0 - 100  
**説明:** AIが画像を「対象」と判定するための信頼度閾値

| 値 | 感度 | 効果 |
|----|------|------|
| 0 - 30 | 非常に高（低い選別） | 誤検出が多いが、見落としが少ない |
| 40 - 60 | 高（バランス） | 汎用的で推奨 |
| 70 - 85 | 低（高い選別） | 誤検出が少ないが、見落としがある |
| 90 - 100 | 非常に低（厳密選別） | 確実な対象のみを検出 |

**変更例:**
```json
"ai_threshold": 50
```

**検証:**
```python
from lib.config_defaults import validate_ai_threshold

if validate_ai_threshold(75):
    config["ai_threshold"] = 75
    save_config(config)
```

---

### 移動先設定

#### `move_destination_count`
**型:** 整数  
**デフォルト値:** 6  
**有効範囲:** 1 - 12  
**説明:** 画像の移動先フォルダのスロット数

| 値 | グリッド配置 | 画面表示 |
|----|-----------|--------|
| 1 - 3 | 2列1行 | コンパクト |
| 4 - 6 | 2列複数行 | 標準 |
| 7 - 12 | 3列複数行 | ワイド |

**変更例:**
```json
"move_destination_count": 9
```

**制約:**
- 12を超える値は自動的に12に制限されます
- 0以下の値は拒否されます

---

### テーマ設定

#### `theme`
**型:** 文字列（列挙）  
**デフォルト値:** `"light"`  
**有効値:** `"light"`, `"dark"`（拡張可能）  
**説明:** UIの色スキーム

| テーマ | 背景 | テキスト | 推奨用途 |
|--------|------|--------|--------|
| `"light"` | 白系 | 黒系 | 昼間、通常環境 |
| `"dark"` | 黒系 | 白系 | 夜間、低光環境 |

**変更例:**
```json
"theme": "dark"
```

---

### 最近使用したアイテム

#### `recent_folders`
**型:** 文字列配列  
**デフォルト値:** `[]`（空）  
**説明:** 最近使用したフォルダのパスリスト

**例：**
```json
"recent_folders": [
  "C:\\Users\\MyName\\Pictures",
  "D:\\Images\\Archive",
  "E:\\PhotoGallery"
]
```

**自動更新:** フォルダを開くたびに、このリストが自動更新されます。

**最大保存数:** 10個（古い項目から削除）

---

#### `recent_files`
**型:** 文字列配列  
**デフォルト値:** `[]`（空）  
**説明:** 最近使用したファイルのパスリスト

**例：**
```json
"recent_files": [
  "C:\\Users\\MyName\\Pictures\\photo1.jpg",
  "C:\\Users\\MyName\\Pictures\\photo2.png",
  "D:\\Images\\archive.zip"
]
```

**自動更新:** ファイルを開くたびに更新。

**最大保存数:** 20個

---

## 完全な設定例

### シンプル設定（デフォルト）

```json
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

---

### カスタム設定（大画面 + AI厳密）

```json
{
  "window_width": 1400,
  "window_height": 900,
  "file_window_width": 800,
  "file_window_height": 700,
  "move_destination_count": 12,
  "ss_interval": 3,
  "ss_mode": "slideshow",
  "ai_threshold": 85,
  "theme": "dark",
  "recent_folders": [
    "C:\\Images\\Work"
  ],
  "recent_files": []
}
```

---

### カスタム設定（小画面 + 高感度AI）

```json
{
  "window_width": 600,
  "window_height": 450,
  "file_window_width": 400,
  "file_window_height": 350,
  "move_destination_count": 4,
  "ss_interval": 10,
  "ss_mode": "off",
  "ai_threshold": 40,
  "theme": "light",
  "recent_folders": [],
  "recent_files": []
}
```

---

## 環境別推奨設定

### 開発環境

```json
{
  "ai_threshold": 50,
  "ss_mode": "off",
  "theme": "light"
}
```

**理由:** AIテストの多様性確保、ログ出力の視認性重視

---

### 本番環境（一般ユーザー）

```json
{
  "window_width": 1024,
  "window_height": 768,
  "move_destination_count": 8,
  "ai_threshold": 70,
  "ss_mode": "slideshow",
  "ss_interval": 5,
  "theme": "light"
}
```

**理由:** バランスの取れた設定、安定動作

---

### 本番環境（大量処理）

```json
{
  "window_width": 1600,
  "window_height": 1000,
  "move_destination_count": 12,
  "ai_threshold": 75,
  "ss_mode": "random",
  "ss_interval": 2,
  "theme": "dark"
}
```

**理由:** 大画面対応、多数の移動先対応、効率的な処理

---

## 設定の検証とリセット

### 設定の検証

```python
from lib.config_defaults import (
    validate_ai_threshold,
    validate_move_count,
    validate_ss_interval
)
from GazoToolsLogic import load_config

config = load_config()

# 各設定値を検証
if not validate_ai_threshold(config["ai_threshold"]):
    print(f"Invalid AI threshold: {config['ai_threshold']}")

if not validate_move_count(config["move_destination_count"]):
    print(f"Invalid move count: {config['move_destination_count']}")

if not validate_ss_interval(config["ss_interval"]):
    print(f"Invalid SS interval: {config['ss_interval']}")
```

---

### 設定をリセット（デフォルトに戻す）

```python
from lib.config_defaults import get_default_config
from GazoToolsLogic import save_config

# デフォルト設定で上書き
config = get_default_config()
save_config(config)
print("Configuration reset to defaults")
```

---

## 設定のエクスポート・インポート

### 設定のバックアップ

```python
import shutil
from datetime import datetime

# バックアップファイルを作成
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
shutil.copy("data/config.json", f"data/config_backup_{timestamp}.json")
print(f"Backup created: data/config_backup_{timestamp}.json")
```

---

### 設定の復元

```python
import shutil

# バックアップから復元
shutil.copy("data/config_backup_20260104_143000.json", "data/config.json")
print("Configuration restored from backup")
```

---

## トラブルシューティング

### 問題: 設定ファイルが壊れている

**症状:** アプリ起動時に `json.JSONDecodeError` が発生

**対応方法:**
```python
# 1. バックアップがあれば復元
import shutil
shutil.copy("data/config_backup_latest.json", "data/config.json")

# 2. なければリセット
from lib.config_defaults import get_default_config
from GazoToolsLogic import save_config
config = get_default_config()
save_config(config)
```

---

### 問題: 設定が反映されない

**原因:** アプリが起動中に設定ファイルを編集した

**対応方法:**
1. アプリを完全に終了
2. `data/config.json` を編集
3. アプリを再起動

---

### 問題: 不正な値を入力してしまった

**例:** `ai_threshold` に 150 を入力

**対応方法:**
```python
from lib.config_defaults import validate_ai_threshold, get_default_config
from GazoToolsLogic import load_config, save_config

config = load_config()

# 検証して、不正値なら修正
if not validate_ai_threshold(config["ai_threshold"]):
    config["ai_threshold"] = get_default_config()["ai_threshold"]
    save_config(config)
    print("Invalid value corrected to default")
```

---

## 設定値の優先順位

GazoTools では、以下の優先順位で設定値が決定されます（上ほど優先）：

1. **コマンドライン引数** （例：`python GazoToolsApp.py --ai-threshold 80`）
2. **環境変数** （例：`GAZO_AI_THRESHOLD=80`）
3. **ユーザー設定ファイル** （`data/config.json`）
4. **デフォルト設定** （`lib/config_defaults.py`）

**使用例：**
```bash
# コマンドライン引数で一時的にAI閾値をオーバーライド
python GazoToolsApp.py --ai-threshold 90
```

---

## パフォーマンスへの影響

### 大きな影響がある設定

| 設定 | 値 | パフォーマンスへの影響 |
|------|-----|------------------|
| `move_destination_count` | 12 | 画面描画が重くなる可能性 |
| `ss_interval` | 1 - 2 | CPU使用率が高くなる |
| `ai_threshold` | 低い（高感度） | AI処理が多くなり時間増加 |
| `recent_files` | 多数 | 起動時間が長くなる |

### 最適化の提案

**遅い環境の場合:**
```json
{
  "move_destination_count": 6,
  "ss_interval": 10,
  "ai_threshold": 80,
  "recent_files": 10
}
```

**高速環境の場合:**
```json
{
  "move_destination_count": 12,
  "ss_interval": 1,
  "ai_threshold": 40,
  "recent_files": 50
}
```

---

---

## ベクトル表示設定 (vector_display)

AI 画像選択の根拠を「ベクトル解釈」で視覚化するための設定セクションです。

### 概要

自動再生で次の画像が選択された時、そのAI判断の根拠となる特徴ベクトルの値を
ユーザー理解できる形で表示します。

**デフォルト設定:**
```json
{
  "vector_display": {
    "enabled": true,
    "interpretation_mode": "labels",
    "show_color_features": true,
    "show_edge_features": true,
    "show_texture_features": true,
    "show_shape_features": true,
    "show_semantic_features": true,
    "max_dimensions_to_show": 10,
    "similarity_threshold": 0.05
  }
}
```

### 設定項目の詳細

#### `enabled` (boolean)
- **意味:** ベクトル解釈機能の有効・無効
- **値:** `true` / `false`
- **推奨:** `true` (機能を使いたい場合)
- **備考:** 無効にすると解釈処理がスキップされます

#### `interpretation_mode` (string)
- **意味:** ベクトル解釈の方法
- **値:** `"labels"` / `"shap"` / `"custom"`
- **推奨:** `"labels"` （最も理解しやすい）

**各モードの特徴:**

| モード | 説明 | 用途 |
|--------|------|------|
| `labels` | トップNの次元を取出し、各次元の意味を表示 | **推奨・初心者向け** 直感的に特徴を把握 |
| `shap` | 各次元の寄与度を計算して順序付け | **中級者向け** より科学的な分析 |
| `custom` | 将来的な拡張用（現在は`labels`と同じ） | 今後のカスタマイズに備える |

**例:** `"labels"` モードの出力
```
[LABELSモード]
  1. 赤色成分 (スコア: 12.5%)
  2. 対角線 (スコア: 10.2%)
  3. 風景 (スコア: 9.8%)
```

#### 特徴カテゴリの表示制御

以下の4つの設定で、ベクトルの各特徴カテゴリの表示をON/OFF制御できます：

##### `show_color_features` (boolean)
- **意味:** 色彩情報（赤・緑・青・明るさなど）を表示するか
- **値:** `true` / `false`
- **推奨:** `true`
- **無効にした場合:** 色彩関連の次元（0-250）は解釈対象から除外されます

##### `show_edge_features` (boolean)
- **意味:** エッジ・線特徴（水平線・垂直線・曲線など）を表示するか
- **値:** `true` / `false`
- **推奨:** `true`
- **無効にした場合:** エッジ関連の次元（251-450）は除外されます

##### `show_texture_features` (boolean)
- **意味:** テクスチャ・パターン特徴（滑らかさ・パターンなど）を表示するか
- **値:** `true` / `false`
- **推奨:** `true`
- **無効にした場合:** テクスチャ関連の次元（451-750）は除外されます

##### `show_shape_features` (boolean)
- **意味:** 形状特徴（円形・四角形・三角形など）を表示するか
- **値:** `true` / `false`
- **推奨:** `true`
- **無効にした場合:** 形状関連の次元（751-920）は除外されます

##### `show_semantic_features` (boolean)
- **意味:** セマンティック特徴（動物・建造物・風景など）を表示するか
- **値:** `true` / `false`
- **推奨:** `true`
- **無効にした場合:** セマンティック関連の次元（921-1023）は除外されます

#### `max_dimensions_to_show` (integer)
- **意味:** 解釈結果に表示する最大特徴数
- **値:** 1 ～ 50
- **推奨:** `10` （情報量と可読性のバランス）
- **範囲を超えた場合:** 最大値が自動的に制限されます

**値の効果:**
- `5`: コンパクト（top 5の主要な特徴のみ表示）
- `10`: バランス型（デフォルト）
- `20`: 詳細型（より多くの特徴情報を表示）

#### `similarity_threshold` (float)
- **意味:** 表示する特徴の最小スコア
- **値:** 0.0 ～ 1.0
- **推奨:** `0.05` （5% 以上のスコア）
- **用途:** ノイズフィルタリング

**値の効果:**
- `0.01`: 非常に多くの特徴を表示（ノイズが増加）
- `0.05`: バランス型（デフォルト、ノイズが少ない）
- `0.1`: 厳選型（最も重要な特徴のみ表示）

### 設定例

#### 例1: 色彩情報を重視したい場合
```json
{
  "vector_display": {
    "enabled": true,
    "interpretation_mode": "labels",
    "show_color_features": true,
    "show_edge_features": false,
    "show_texture_features": false,
    "show_shape_features": false,
    "show_semantic_features": false,
    "max_dimensions_to_show": 10,
    "similarity_threshold": 0.05
  }
}
```

#### 例2: より科学的な分析を行いたい場合
```json
{
  "vector_display": {
    "enabled": true,
    "interpretation_mode": "shap",
    "show_color_features": true,
    "show_edge_features": true,
    "show_texture_features": true,
    "show_shape_features": true,
    "show_semantic_features": true,
    "max_dimensions_to_show": 15,
    "similarity_threshold": 0.01
  }
}
```

#### 例3: 簡潔に表示したい場合
```json
{
  "vector_display": {
    "enabled": true,
    "interpretation_mode": "labels",
    "show_color_features": true,
    "show_edge_features": true,
    "show_texture_features": true,
    "show_shape_features": true,
    "show_semantic_features": true,
    "max_dimensions_to_show": 3,
    "similarity_threshold": 0.1
  }
}
```

### ベクトル解釈の仕組み

MobileNetV3は画像から 1024 次元のベクトルを抽出します。このモジュールは
これら1024個の数値を人間が理解できる情報に変換します：

```
[1024個の数値ベクトル]
     ↓
[VectorInterpreter が処理]
     ↓
[5つの意味カテゴリに分類]
  - 色彩 (0-250)
  - エッジ (251-450)
  - テクスチャ (451-750)
  - 形状 (751-920)
  - セマンティック (921-1023)
     ↓
[ユーザー理解できる説明に変換]
  例: 「赤色成分(12.5%) > 対角線(10.2%) > 風景(9.8%)」
```

---

## まとめ

| 用途 | 推奨設定 |
|------|--------|
| はじめる | デフォルト設定をそのまま使用 |
| 微調整 | `ai_threshold` と `ss_interval` から開始 |
| 大規模環境 | `move_destination_count` と `window_*` を増加 |
| トラブル | リセットして再スタート |


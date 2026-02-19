# エラーハンドリング改善 - 実装サマリー

**実装日**: 2026年1月4日  
**対象**: GazoTools プロジェクト

## 📋 実装内容

### 1. カスタム例外クラス定義 (`lib/GazoToolsExceptions.py` - 新規作成)

構造化された例外処理を実現するため、以下のカスタム例外クラスを定義しました：

```
GazoToolsError (基底例外)
├── ConfigError              (設定ファイル関連)
├── ImageLoadError           (画像読み込みエラー)
├── ImageProcessingError     (画像処理エラー)
├── FileHashError            (ハッシュ計算エラー)
├── TagManagementError       (タグ管理エラー)
├── AIModelError             (AIモデル関連)
├── VectorProcessingError    (ベクトル化処理)
├── FileOperationError       (ファイル操作)
├── FolderAccessError        (フォルダアクセス)
└── UIError                  (UI操作)
```

**利点:**
- エラーの種類を明確に区分
- キャッチ時に適切な処理を分岐可能
- 予期しないエラーと既知エラーを区別可能

---

### 2. ロギングシステム (`lib/GazoToolsLogger.py` - 新規作成)

統一されたロギング設定を管理するクラスを実装：

**LoggerManager クラスの機能:**
- ✅ コンソール出力（DEBUG/INFO/WARNING/ERROR）
- ✅ ファイル出力（`logs/error_YYYYMMDD.log`）
- ✅ デバッグモード切り替え機能
- ✅ シングルトンパターンによる一元管理

**ログレベル:**
```
DEBUG:   詳細なプログラム実行トレース
INFO:    重要なイベント（ファイル操作完了など）
WARNING: 予期しない但し続行可能な状況
ERROR:   エラー発生（例外情報付き）
```

**ログファイル出力:**
- 場所: `logs/error_YYYYMMDD.log`
- フォーマット: タイムスタンプ + モジュール名 + ログレベル + メッセージ + ファイル行番号
- 内容: WARNING 以上のレベルのみ（容量削減）

---

### 3. GazoToolsLogic.py の改善

#### 3-1. インポート追加
```python
from lib.GazoToolsExceptions import (
    ConfigError, ImageLoadError, FileHashError, ...
)
from lib.GazoToolsLogger import LoggerManager

logger = LoggerManager.get_logger(__name__)
```

#### 3-2. 関数別改善

| 関数名 | 改善内容 | 例外処理 |
|--------|---------|---------|
| `load_config()` | JSON解析エラー、IOエラーを詳細に捕捉 | ConfigError 発生 |
| `save_config()` | 書き込み失敗時にログ・例外発生 | ConfigError 発生 |
| `calculate_file_hash()` | ファイル不在・読み込みエラーを分岐 | FileHashError 発生 |
| `load_tags()` | CSV読み込みエラーを詳細に処理 | TagManagementError 発生 |
| `save_tags()` | ディレクトリ作成・書き込みエラー対応 | TagManagementError 発生 |
| `load_vectors()` | JSON解析エラーを分岐処理 | VectorProcessingError 発生 |
| `save_vectors()` | ベクトル保存失敗時の詳細ログ | VectorProcessingError 発生 |

#### 3-3. VectorBatchProcessor クラスの大幅改善

**Before:**
```python
def run(self):
    vectors = load_vectors()  # エラーが全て silent
    ...
    file_hash = calculate_file_hash(full_path)  # None を返す
    if file_hash:
        vec = engine.get_image_feature(full_path)  # None を返す
        if vec:
            vectors[file_hash] = vec
    ...
    save_vectors(vectors)  # 失敗を無視
```

**After:**
```python
def run(self):
    try:
        vectors = load_vectors()
    except VectorProcessingError as e:
        logger.warning(f"既存ベクトル読み込み失敗、新規作成します")
        vectors = {}
    
    updated_count = 0
    failed_count = 0
    
    for i, filename in enumerate(files):
        try:
            file_hash = calculate_file_hash(full_path)
        except FileHashError as e:
            logger.warning(f"ハッシュ計算失敗: {filename}")
            failed_count += 1
            continue
        
        try:
            vec = engine.get_image_feature(full_path)
            if vec:
                vectors[file_hash] = vec
                updated_count += 1
        except Exception as e:
            logger.warning(f"ベクトル化失敗: {filename} - {e}")
            failed_count += 1
    
    # 保存時にもエラーハンドリング
    try:
        if updated_count > 0:
            save_vectors(vectors)
    except VectorProcessingError as e:
        logger.error(f"ベクトルデータ保存失敗: {e}")
        if self.callback_finish:
            self.callback_finish(f"ベクトル保存エラー: {e}")
        return
    
    message = f"完了！ {updated_count}件の追加"
    if failed_count > 0:
        message += f"({failed_count}件失敗)"
    self.callback_finish(message)
```

**改善点:**
- ✅ 部分的なエラーでも処理を続行
- ✅ 失敗件数をトラッキング
- ✅ 詳細なログ出力
- ✅ ユーザーへの明確なフィードバック

---

### 4. GazoToolsAI.py の改善

#### 4-1. インポート追加
```python
from .GazoToolsExceptions import AIModelError, ImageLoadError, VectorProcessingError
from .GazoToolsLogger import LoggerManager

logger = LoggerManager.get_logger(__name__)
```

#### 4-2. VectorEngine クラスの改善

**__init__() メソッド:**
- GPU 自動検出機能追加
  ```python
  self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
  self.model.to(self.device)
  logger.debug(f"使用デバイス: {self.device}")
  ```
- デバッグモード対応（詳細ログ出力の制御）
- 例外をカスタム例外として発生

**get_image_feature() メソッド:**
- ✅ FileNotFoundError → ImageLoadError に変換
- ✅ IOError → ImageLoadError に変換
- ✅ その他の例外 → VectorProcessingError に変換
- ✅ 全て例外チェーン（from e）で原因を保持

**compare_features() メソッド:**
- ✅ 空ベクトルのチェック強化
- ✅ VectorProcessingError として例外発生
- ✅ デバッグモード時に詳細ログ出力

---

### 5. GazoToolsApp.py の改善

#### 5-1. ロギング初期化
```python
from lib.GazoToolsLogger import setup_logging, get_logger

setup_logging(debug_mode=False)  # 本番モード (True でデバッグモード)
logger = get_logger(__name__)
```

#### 5-2. 設定読み込みの改善
```python
try:
    CONFIG_DATA = load_config()
    logger.info(f"設定ファイル読み込み成功: {CONFIG_DATA.get('last_folder')}")
except Exception as e:
    logger.error(f"設定ファイル読み込み失敗: {e}")
    messagebox.showerror("エラー", f"設定ファイルの読み込みに失敗しました:\n{e}")
    CONFIG_DATA = { ... }  # デフォルト値を使用
```

#### 5-3. refresh_ui() 関数の改善
```python
try:
    all_items = os.listdir(DEFOLDER)
    folders = GetKoFolder(all_items, DEFOLDER)
    files = GetGazoFiles(all_items, DEFOLDER)
    logger.info(f"UI更新: {DEFOLDER} (フォルダ:{len(folders)}件, ファイル:{len(files)}件)")
except Exception as e:
    logger.error(f"再読み込みエラー: {e}", exc_info=True)
    messagebox.showerror("エラー", f"フォルダの読み込みに失敗しました:\n{e}")
    return
```

#### 5-4. execute_move() 関数の改善
```python
try:
    filename = os.path.basename(file_path)
    shutil.move(file_path, os.path.join(dest_folder, filename))
    logger.info(f"ファイル移動成功: {filename} -> {dest_folder}")
except FileNotFoundError as e:
    logger.error(f"ファイルが見つかりません: {file_path}")
    messagebox.showerror("エラー", f"ファイルが見つかりません: {filename}")
except PermissionError as e:
    logger.error(f"ファイル移動: 権限がありません: {file_path}")
    messagebox.showerror("エラー", f"ファイルを移動する権限がありません: {filename}")
except Exception as e:
    logger.error(f"ファイル移動エラー: {file_path} -> {dest_folder}", exc_info=True)
    messagebox.showerror("失敗", f"移動中にエラーが起きたのじゃ: {e}")
```

---

## 📊 改善の効果

### Before (改善前)
```python
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # 処理...
        except:  # ❌ 全てのエラーを無視
            pass
    return config

def calculate_file_hash(filepath):
    try:
        # 計算処理...
        return hash_value
    except:  # ❌ Noneを返すだけ
        return None
```

### After (改善後)
```python
def load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析エラー: {CONFIG_FILE}", exc_info=True)
        raise ConfigError(f"Invalid JSON: {e}") from e  # ✅ 具体的に報告
    except IOError as e:
        logger.error(f"読み込み失敗: {CONFIG_FILE}", exc_info=True)
        raise ConfigError(f"Cannot read file: {e}") from e  # ✅ 具体的に報告

def calculate_file_hash(filepath):
    try:
        # 計算処理...
        return hash_value
    except FileNotFoundError as e:
        logger.error(f"ファイル不在: {filepath}", exc_info=True)
        raise FileHashError(f"File not found: {filepath}") from e  # ✅ 具体的に報告
    except IOError as e:
        logger.error(f"読み込みエラー: {filepath}", exc_info=True)
        raise FileHashError(f"Cannot read file: {filepath}") from e  # ✅ 具体的に報告
```

**効果:**
- ✅ **エラーの可視化**: 何が起こったか、どこで起こったかが明確
- ✅ **デバッグ時間短縮**: スタックトレース + ログで原因特定が容易
- ✅ **ユーザー体験向上**: 意味のあるエラーメッセージを表示
- ✅ **保守性向上**: 同じエラータイプなら同じ処理で対応可能

---

## 🔧 デバッグモード設定

### デバッグモードを有効にする場合
```python
# GazoToolsApp.py 先頭付近
from lib.GazoToolsLogger import setup_logging

setup_logging(debug_mode=True)  # デバッグモード ON
```

**出力内容:**
```
[DEBUG] 手順1: モデルウェイトの設定を読み込むのじゃ
[DEBUG] 手順2: MobileNetV3_Smallモデルを構築するのじゃ
[DEBUG] 画像の前処理を行うのじゃ: (224, 224)
[DEBUG] ベクトル比較を開始するのじゃ
[DEBUG] ベクトル比較完了: 類似度スコア = 0.8543
```

### デバッグモードを無効にする場合（本番）
```python
setup_logging(debug_mode=False)  # デバッグモード OFF
```

**出力内容:**
```
[INFO] AIモデルの準備が全て正常に完了したのじゃ！
[INFO] 設定ファイル読み込み成功: K:/最強に最高に最強
[INFO] UI更新: K:/最強に最高に最強 (フォルダ:2件, ファイル:150件)
```

---

## 📁 新規作成ファイル

1. **lib/GazoToolsExceptions.py** (66行)
   - 10種類のカスタム例外クラス定義

2. **lib/GazoToolsLogger.py** (129行)
   - LoggerManager クラス
   - コンソール・ファイルハンドラ管理
   - デバッグモード制御

3. **test_error_handling.py** (87行)
   - エラーハンドリング改善の動作確認テスト

---

## 📝 修正ファイル一覧

| ファイル | 修正行数 | 主な改善 |
|---------|---------|---------|
| GazoToolsLogic.py | ~80行 | インポート追加、例外処理強化、エラーログ追加 |
| lib/GazoToolsAI.py | ~40行 | GPU検出、例外処理統一、デバッグモード対応 |
| GazoToolsApp.py | ~30行 | ロギング初期化、例外処理追加 |

**総変更行数**: 約150行追加・修正

---

## ✅ チェックリスト

- [x] カスタム例外クラスの定義
- [x] ロギング機構の実装
- [x] GazoToolsLogic.py の例外処理改善
- [x] GazoToolsAI.py のエラーハンドリング改善
- [x] GazoToolsApp.py への統合
- [x] テストスクリプトの作成

---

## 🚀 次のステップ（推奨）

1. **実際の使用テスト**: アプリケーションを起動して、logs/ フォルダにログが出力されることを確認
2. **デバッグモードテスト**: `setup_logging(debug_mode=True)` に変更して詳細ログを確認
3. **エラーシナリオテスト**: 意図的に設定ファイルを削除したり、不正な画像を選択してエラー処理を確認
4. **次の改善**: UI関連（グローバル変数削減）またはパフォーマンス最適化へ移行

---

**実装完了日**: 2026年1月4日  
**テスト可能状態**: ✅ はい

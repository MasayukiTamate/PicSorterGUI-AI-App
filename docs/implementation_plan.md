# Qwen2-VL-2B 導入計画 (CPU環境向け)

グラフィックボード(GPU)が無い環境で「Qwen」の画像認識およびタグ付け機能をアプリに組み込むための計画じゃ。
動作の軽快さと精度のバランスを考慮し、**Qwen2-VL-2B-Instruct** モデルを採用するのじゃ。

## User Review Required

> [!IMPORTANT]
> **実行速度について**: GPUが無いため、CPUでの実行となり、画像1枚の解析に数秒〜数十秒かかる可能性があるのじゃ。実用的な速度かどうかの検証が必要じゃ。

> [!NOTE]
> **ストレージ容量**: モデルのダウンロードに数GB(約5GB前後)のディスク容量が必要じゃ。

## Proposed Changes

### 1. 依存ライブラリのインストール
必要なPythonライブラリをインストールする手順を確認するのじゃ。
- `transformers`
- `qwen-vl-utils`
- `torch` (CPU版でも可)
- `accelerate`

### 2. プロトタイプ検証 (動作確認)
アプリに組み込む前に、単体で動作するテストスクリプトを作成し、速度と精度を確認するのじゃ。

#### [NEW] [test_qwen_local.py](file:///k:/GitHub/Gazo_tools/test_qwen_local.py)
- Qwen2-VL-2B モデルをロード
- 指定した画像を読み込み、タグ(キーワード)を生成させるプロンプトを送信
- 生成されたタグと実行時間を表示

### 3. アプリケーションへの組み込み
テストが良好であれば、アプリ内に機能を実装するのじゃ。

#### [NEW] [lib/QwenTagger.py](file:///k:/GitHub/Gazo_tools/lib/QwenTagger.py)
- シングルトンまたは静的クラスとしてモデルを管理（ロード時間を1回にするため）
- `generate_tags(image_path)` メソッドを提供
- 実行中はスレッドをブロックしないよう配慮

#### [MODIFY] [GazoToolsLogic.py](file:///k:/GitHub/Gazo_tools/GazoToolsLogic.py)
- 画像の右クリックメニューまたはツールバーに「AIタグ付け(Qwen)」機能を追加
- `QwenTagger` を呼び出し、結果を既存のタグシステム(CSV/Hash)に保存
- 処理中は「解析中...」のようなダイアログまたはステータス表示を行う（フリーズ防止のため別スレッド実行）

## Verification Plan

### Automated Tests
- なし (AIモデルの出力は毎回変わる可能性があるため、目視確認が主になる)

### Manual Verification
1. **単体テスト**:
   - コマンドラインで `python test_qwen_local.py` を実行。
   - エラーなくタグが出力されるか、処理時間が許容範囲か確認。
2. **アプリ統合テスト**:
   - アプリを起動し、画像を右クリック -> 「AIタグ付け」を選択。
   - UIがフリーズせずに処理が進むか確認。
   - 生成されたタグが正しく登録・保存されるか確認。

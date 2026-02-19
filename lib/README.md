# lib/ - コアライブラリ

GazoToolsのビジネスロジック・データ処理・AI機能を提供するモジュール群です。

## モジュール一覧

| ファイル | 役割 |
|:---|:---|
| `GazoToolsAI.py` | AI エンジン。MobileNetV3 Small による画像ベクトル化・類似度比較 |
| `GazoToolsData.py` | データ I/O。設定・タグ・評価・ベクトルの JSON 読み書き |
| `GazoToolsState.py` | アプリケーション状態管理（シングルトン）。イベントコールバック機構 |
| `GazoToolsGUI.py` | 再利用可能な GUI コンポーネント（スプラッシュ、類似画像ダイアログ、ベクトルウィンドウ等） |
| `GazoToolsImageCache.py` | LRU 画像キャッシュ（最大256MB）とタイル画像ローダー |
| `GazoToolsLib.py` | ファイル操作ユーティリティ（フォルダ取得、画像ファイルフィルタリング） |
| `GazoToolsBasicLib.py` | 低レベルヘルパー（ウィンドウサイズ変換、カラーブレンド） |
| `GazoToolsVectorInterpreter.py` | ベクトル解釈。1024次元ベクトルを色彩・エッジ・テクスチャ等のカテゴリに変換 |
| `GazoToolsLogger.py` | 構造化ロギング |
| `GazoToolsExceptions.py` | カスタム例外クラス（10種類） |
| `GazoToolsUI.py` | UI 関連ユーティリティ |
| `config_defaults.py` | 定数・デフォルト値の一元管理（マジックナンバー排除） |

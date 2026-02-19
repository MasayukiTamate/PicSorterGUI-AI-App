# tests/ - テストスイート

GazoToolsの自動テストを格納するフォルダです。pytest で実行します。

## テストファイル

| ファイル | テスト対象 |
|:---|:---|
| `test_config.py` | 設定ファイルの読み書き・バリデーション |
| `test_file_operations.py` | ファイル操作（移動・ハッシュ計算・パス処理） |
| `test_ui_state.py` | AppState の状態管理・イベントコールバック |
| `test_integration.py` | モジュール間の統合テスト |
| `conftest.py` | テスト共通フィクスチャ |

## 実行方法

```bash
pytest tests/
```

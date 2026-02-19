'''
PicSorterGUI用カスタム例外クラス定義
'''


class PicSorterGUIError(Exception):
    """PicSorterGUI基底例外クラス"""
    pass


class ConfigError(PicSorterGUIError):
    """設定ファイル関連のエラー"""
    pass


class ImageLoadError(PicSorterGUIError):
    """画像読み込みエラー"""
    pass


class ImageProcessingError(PicSorterGUIError):
    """画像処理エラー（リサイズ、表示など）"""
    pass


class FileHashError(PicSorterGUIError):
    """ファイルハッシュ計算エラー"""
    pass


class AIModelError(PicSorterGUIError):
    """AIモデル関連のエラー"""
    pass


class VectorProcessingError(PicSorterGUIError):
    """ベクトル化処理エラー"""
    pass


class FileOperationError(PicSorterGUIError):
    """ファイル移動・削除などのエラー"""
    pass


class FolderAccessError(PicSorterGUIError):
    """フォルダアクセスエラー"""
    pass


class UIError(PicSorterGUIError):
    """UI操作関連のエラー"""
    pass

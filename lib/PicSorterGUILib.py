'''
PicSorterGUI ファイル・フォルダユーティリティ
'''
print("PicSorterGUILib.py loaded!")
import os


def GetKoFolder(files, base_path):
    '''
    指定したパス(base_path)内のfilesリストから、子フォルダのみを抽出して返す
    '''
    folder = []
    for f in files:
        if not str(f).startswith("."):
            full_path = os.path.join(base_path, f)
            if os.path.isdir(full_path):
                folder.append(f)

    return folder


def GetGazoFiles(folder, base_path):
    '''
    フォルダ内のファイルリストから画像ファイルのみを抽出して返す。
    '''
    Files = []
    valid_extensions = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif')

    for f in folder:
        if str(f).lower().endswith(valid_extensions):
            Files.append(f)

    return Files

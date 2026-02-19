import PyInstaller.__main__
import shutil
import os
import sys

# アプリ名
APP_NAME = "PicSorterGUI"
SCRIPT_NAME = "PicSorterGUIApp.py"

print("Building PicSorterGUI Executable...")

# PyInstaller の実行
try:
    import tkinterdnd2
    tkdnd_path = os.path.join(os.path.dirname(tkinterdnd2.__file__), 'tkdnd')
    add_data_option = f'--add-data={tkdnd_path}{os.pathsep}tkinterdnd2/tkdnd'
except ImportError:
    tkdnd_path = ""
    add_data_option = ""
    print("Warning: tkinterdnd2 not found. D&D features might not work.")

PyInstaller.__main__.run([
    SCRIPT_NAME,
    '--name=%s' % APP_NAME,
    '--onedir',        # 1つのディレクトリにまとめる
    '--noconsole',     # コンソール画面を出さない
    '--clean',         # キャッシュクリア
    '-y',              # 出力ディレクトリを自動上書き
    '--icon=PicClass.ico', # アイコン設定
    add_data_option,   # tkinterdnd2のデータを追加

    '--exclude-module=PicSorterGUILogic',  # ロジックを除外
    '--exclude-module=lib',
    '--hidden-import=ctypes.wintypes',
    '--hidden-import=torch',
    '--hidden-import=torchvision',
    '--hidden-import=torchvision.models',
    '--hidden-import=torchvision.transforms',
    '--hidden-import=tkinter',
    '--hidden-import=tkinter.ttk',
    '--hidden-import=tkinter.messagebox',
    '--hidden-import=tkinter.filedialog',
    '--hidden-import=send2trash',
])

# ビルド後のディレクトリ
dist_dir = os.path.join('dist', APP_NAME)

if not os.path.exists(dist_dir):
    print("Error: Build failed, dist directory not found.")
    sys.exit(1)

# ロジックファイルとlibフォルダをコピー
print("Copying external logic files to dist folder...")

# PicClass.ico（ウィンドウアイコン用）
try:
    shutil.copy('PicClass.ico', dist_dir)
    print(" - Copied PicClass.ico")
except Exception as e:
    print(f"Error copying PicClass.ico: {e}")

# PicSorterGUILogic.py
try:
    shutil.copy('PicSorterGUILogic.py', dist_dir)
    print(" - Copied PicSorterGUILogic.py")
except Exception as e:
    print(f"Error copying PicSorterGUILogic.py: {e}")

# libフォルダ
lib_dest = os.path.join(dist_dir, 'lib')
try:
    if os.path.exists(lib_dest):
        shutil.rmtree(lib_dest)
    shutil.copytree('lib', lib_dest)
    print(" - Copied lib folder")
except Exception as e:
    print(f"Error copying lib folder: {e}")

# 不要な__pycache__を削除
for root, dirs, files in os.walk(lib_dest):
    for d in dirs:
        if d == "__pycache__":
            shutil.rmtree(os.path.join(root, d))
            print(f" - Removed __pycache__ from {root}")

print("-" * 30)
print(f"Build complete! Executable is in: {os.path.abspath(dist_dir)}")
print("Run PicSorterGUI.exe to start.")
print("-" * 30)

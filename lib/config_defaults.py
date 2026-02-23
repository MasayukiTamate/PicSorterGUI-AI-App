'''
PicSorterGUI グローバル設定定数管理
'''
import os

# ===========================
# 1. ウィンドウサイズ関連の定数
# ===========================
DEFAULT_WINDOW_WIDTH = 600
DEFAULT_WINDOW_HEIGHT = 600

MIN_WINDOW_WIDTH = 200
MIN_WINDOW_HEIGHT = 120
MAX_WINDOW_WIDTH = 600
MAX_WINDOW_HEIGHT = 800

FOLDER_WINDOW_CHAR_MULTIPLIER = 10
FOLDER_WINDOW_HEIGHT_MULTIPLIER = 20
FOLDER_WINDOW_HEIGHT_OFFSET = 90
FOLDER_WINDOW_WIDTH_OFFSET = 60

FILE_WINDOW_CHAR_MULTIPLIER = 8
FILE_WINDOW_HEIGHT_MULTIPLIER = 20
FILE_WINDOW_HEIGHT_OFFSET = 70
FILE_WINDOW_WIDTH_OFFSET = 80

WINDOW_SPACING = 10
SCREEN_MARGIN = 40


# ===========================
# 2. UI レイアウト定数
# ===========================
MOVE_DESTINATION_SLOTS = 12
MOVE_DESTINATION_MIN = 2
MOVE_DESTINATION_MAX = 12
MOVE_DESTINATION_OPTIONS = [2, 4, 6, 8, 10, 12]

MOVE_GRID_COLUMNS_MULTI = 3
MOVE_GRID_COLUMNS_SINGLE = 2


# ===========================
# 3. AI 処理パラメータ
# ===========================
DEFAULT_AI_THRESHOLD = 0.65
MIN_AI_THRESHOLD = 0.0
MAX_AI_THRESHOLD = 1.0

AI_BATCH_SLEEP = 0.01
VECTOR_PROCESSING_TIMEOUT = 300

DEFAULT_AI_MODEL = "mobilenet_v3_small"

AI_MODELS = {
    "mobilenet_v3_small": {
        "name": "MobileNetV3-Small",
        "description": "軽量・高速（推奨）",
        "vector_dim": 1024,
        "weight_file": "mobilenet_v3_small-047dcff4.pth",
    },
    "mobilenet_v3_large": {
        "name": "MobileNetV3-Large",
        "description": "バランス型",
        "vector_dim": 960,
        "weight_file": "mobilenet_v3_large-8738ca79.pth",
    },
    "resnet50": {
        "name": "ResNet-50",
        "description": "高精度・重い",
        "vector_dim": 2048,
        "weight_file": "resnet50-11ad3fa6.pth",
    },
    "efficientnet_b0": {
        "name": "EfficientNet-B0",
        "description": "高効率",
        "vector_dim": 1280,
        "weight_file": "efficientnet_b0_rwightman-7f5810bc.pth",
    },
    "custom": {
        "name": "カスタムモデル (.pth)",
        "description": "注意！　自分で理解できる人が選択してください。\n自分でダウンロードした重みファイルを使用",
        "vector_dim": None,
        "weight_file": None,
    },
}


# ===========================
# 4. 画像ファイル設定
# ===========================
SUPPORTED_IMAGE_FORMATS = (
    '.jpg', '.jpeg', '.png',
    '.webp', '.bmp', '.gif'
)

THUMBNAIL_MAX_WIDTH = 150
THUMBNAIL_MAX_HEIGHT = 150
IMAGE_QUALITY_JPEG = 85

DEFAULT_IMAGE_MIN_WIDTH = 100
DEFAULT_IMAGE_MIN_HEIGHT = 100
DEFAULT_IMAGE_MAX_WIDTH = 0
DEFAULT_IMAGE_MAX_HEIGHT = 0

MIN_IMAGE_SIZE_LIMIT = 50
MAX_IMAGE_SIZE_LIMIT = 10000


# ===========================
# 5. UI 色設定
# ===========================
COLOR_MOVE_BG_1 = "#e0ffe0"
COLOR_MOVE_BG_2 = "#f0ffe0"

COLOR_REGISTER_BG = "#e0f0ff"
COLOR_STATUS_FG = "#000000"


# ===========================
# 6. ファイルパス定数
# ===========================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
VECTOR_DATA_FILE = os.path.join(DATA_DIR, "vectordata.json")
ANALYSIS_CACHE_FILE = os.path.join(DATA_DIR, "analysis_cache.json")
CONFIG_FILE = "config.json"
LOG_DIR = "logs"


# ===========================
# 7. デフォルト設定辞書
# ===========================
def get_default_config():
    return {
        "last_folder": os.getcwd(),
        "geometries": {
            "main": "",
            "folder": "",
            "file": ""
        },
        "settings": {
            "topmost": True,
            "show_folder": False,
            "move_dest_list": [""] * MOVE_DESTINATION_SLOTS,
            "move_reg_idx": 0,
            "move_dest_count": MOVE_DESTINATION_MIN,
            "ai_model": DEFAULT_AI_MODEL,
            "reference_folders": [],
            "custom_model_path": "",
            "custom_model_arch": "mobilenet_v3_small",
            "model_cache_dir": "",
        },
    }


# ===========================
# 8. ウィンドウサイズ計算関数
# ===========================
def calculate_folder_window_width(max_item_length: int) -> int:
    calculated = max_item_length * FOLDER_WINDOW_CHAR_MULTIPLIER + FOLDER_WINDOW_WIDTH_OFFSET
    return max(MIN_WINDOW_WIDTH, min(MAX_WINDOW_WIDTH, calculated))


def calculate_folder_window_height(item_count: int) -> int:
    calculated = item_count * FOLDER_WINDOW_HEIGHT_MULTIPLIER + FOLDER_WINDOW_HEIGHT_OFFSET
    return max(MIN_WINDOW_HEIGHT, min(MAX_WINDOW_HEIGHT, calculated))


def calculate_file_window_width(max_item_length: int) -> int:
    calculated = max_item_length * FILE_WINDOW_CHAR_MULTIPLIER + FILE_WINDOW_WIDTH_OFFSET
    return max(MIN_WINDOW_WIDTH, min(MAX_WINDOW_WIDTH, calculated))


def calculate_file_window_height(item_count: int) -> int:
    calculated = item_count * FILE_WINDOW_HEIGHT_MULTIPLIER + FILE_WINDOW_HEIGHT_OFFSET
    return max(MIN_WINDOW_HEIGHT, min(MAX_WINDOW_HEIGHT, calculated))


def get_move_grid_columns(move_count: int) -> int:
    if move_count <= 3:
        return MOVE_GRID_COLUMNS_SINGLE
    else:
        return MOVE_GRID_COLUMNS_MULTI


def validate_ai_threshold(value: float) -> bool:
    try:
        return MIN_AI_THRESHOLD <= float(value) <= MAX_AI_THRESHOLD
    except (ValueError, TypeError):
        return False


def validate_move_count(count: int) -> bool:
    return count in MOVE_DESTINATION_OPTIONS


# ===========================
# 9. ログ設定
# ===========================
LOG_LEVEL_DEBUG = "DEBUG"
LOG_LEVEL_INFO = "INFO"
LOG_LEVEL_WARNING = "WARNING"
LOG_LEVEL_ERROR = "ERROR"

DEFAULT_LOG_LEVEL = LOG_LEVEL_INFO
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


# ===========================
# 10. メール通知設定
# ===========================
DEFAULT_SMTP_SERVER = "smtp.gmail.com"
DEFAULT_SMTP_PORT = 587
DEFAULT_SENDER_EMAIL = ""
DEFAULT_SENDER_PASSWORD = ""
DEFAULT_RECIPIENT_EMAIL = "tamaya2473616@gmail.com"
DEFAULT_ENABLE_EMAIL_LOGGING = False

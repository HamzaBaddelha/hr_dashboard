from pathlib import Path
import os
import tempfile


APP_NAME = "Luxury Vehicle HR Analytics"
COMPANY_NAME = "Luxury Vehicle"

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = Path(tempfile.gettempdir()) / "lv_hr_dashboard"
DB_PATH = DATA_DIR / "app.db"
APP_ICON = str(BASE_DIR / "src" / "public" / "assets" / "hiring.png")
COMPANY_LOGO_PATH = BASE_DIR / "src" / "public" / "assets" / "company_logo.png"

MIN_PASSWORD_LENGTH = 8
VALID_ROLES = {"admin", "hr_user", "viewer"}

DEFAULT_ADMIN_USERNAME = os.getenv("LV_ADMIN_USERNAME", "admin")
DEFAULT_ADMIN_PASSWORD = os.getenv("LV_ADMIN_PASSWORD", "changeme123!")
DEFAULT_ADMIN_FULL_NAME = os.getenv("LV_ADMIN_FULL_NAME", "System Administrator")

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
# Load environment variables from backend/.env or root .env
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR.parent / ".env")
load_dotenv()
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
MEDIA_DIR = DATA_DIR / "media"
DB_PATH = DATA_DIR / "learning_system.db"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")

# Database Configurations
MONGODB_URL = os.getenv("MONGODB_URL", "")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "learning_system")

# Authentication & JWT Configurations
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "textiq_secure_jwt_secret_token_adaptive_2026_xyz")
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_HOURS = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_HOURS", "24"))
JWT_REMEMBER_ME_EXPIRE_DAYS = int(os.getenv("JWT_REMEMBER_ME_EXPIRE_DAYS", "30"))

# App Configurations
APP_TITLE = "AI-Powered Multilingual Textbook Summarization and Adaptive Learning System"
APP_VERSION = "1.0.0"
DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")

# Gemini Quota & Rate-Limit Circuit Breaker
import time
_GEMINI_QUOTA_EXHAUSTED_UNTIL = 0.0

FAST_GEMINI_MODELS = [
    "gemini-3-flash-preview",
    "gemini-3.1-flash-lite",
    "gemini-3.8-flash"
]

def is_gemini_available() -> bool:
    """Returns True if GEMINI_API_KEY is configured and not rate-limited by 429 quota exhaustion."""
    global _GEMINI_QUOTA_EXHAUSTED_UNTIL
    if not GEMINI_API_KEY:
        return False
    if time.time() < _GEMINI_QUOTA_EXHAUSTED_UNTIL:
        return False
    return True

def mark_gemini_quota_exhausted(duration_seconds: float = 120.0):
    """Temporarily marks Gemini as quota-exhausted so requests fall back instantly without network retry lag."""
    global _GEMINI_QUOTA_EXHAUSTED_UNTIL
    _GEMINI_QUOTA_EXHAUSTED_UNTIL = time.time() + duration_seconds

def get_gemini_client():
    """Returns an optimized google-genai Client with tight timeouts and single-attempt retries to avoid 30s+ 503 hangs."""
    if not is_gemini_available():
        return None
    try:
        from google import genai
        from google.genai import types
        return genai.Client(
            api_key=GEMINI_API_KEY,
            http_options=types.HttpOptions(
                timeout=12000,
                retry_options=types.HttpRetryOptions(attempts=1)
            )
        )
    except Exception as e:
        print(f"Failed to create Gemini client: {e}")
        return None

# Sarvam AI Translation Circuit Breaker
_SARVAM_RATE_LIMITED_UNTIL = 0.0

def is_sarvam_available() -> bool:
    """Returns True if SARVAM_API_KEY is configured and not in rate-limit cooldown."""
    global _SARVAM_RATE_LIMITED_UNTIL
    if not SARVAM_API_KEY:
        return False
    if time.time() < _SARVAM_RATE_LIMITED_UNTIL:
        return False
    return True

def mark_sarvam_rate_limited(duration_seconds: float = 120.0):
    """Temporarily marks Sarvam as in cooldown upon 429/5xx error."""
    global _SARVAM_RATE_LIMITED_UNTIL
    _SARVAM_RATE_LIMITED_UNTIL = time.time() + duration_seconds


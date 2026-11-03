import logging
import os
import secrets
from pathlib import Path

# Load KEY=VALUE pairs from <project>/.env without overriding variables already set.
_env_file = Path(__file__).resolve().parent.parent / ".env"
if _env_file.exists():
    for _line in _env_file.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _key, _value = _line.split("=", 1)
            os.environ.setdefault(_key.strip(), _value.strip())

# Example: mysql+pymysql://root:your_password@localhost:3306/unicart?charset=utf8mb4
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://root:@localhost:3306/unicart?charset=utf8mb4",
)

UNPAID_ORDER_TIMEOUT_MINUTES = 15      # BR-04
FLAT_SHIPPING_FEE = 30000              # BR-06
FREE_SHIPPING_THRESHOLD = 500000       # BR-06
EXPIRY_SWEEP_SECONDS = int(os.getenv("EXPIRY_SWEEP_SECONDS", "30"))
RETURN_WINDOW_DAYS = int(os.getenv("RETURN_WINDOW_DAYS", "7"))      # demo return policy used by the chatbot (docs/CHATBOT.md)

# --- API security (NFR-03, NFR-04, NFR-06)
JWT_SECRET = os.getenv("JWT_SECRET", "")
if not JWT_SECRET:
    JWT_SECRET = secrets.token_urlsafe(48)
    logging.getLogger("unicart").warning(
        "JWT_SECRET is not set: using a random secret, all logins are lost on restart. Set it in .env.")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))
# Shared secret that partner systems (payment gateway, carrier, supplier) send in the X-Partner-Secret header.
PARTNER_SECRET = os.getenv("PARTNER_SECRET", "") or secrets.token_urlsafe(24)
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
                if o.strip()]

# --- AI search through the Google Gemini API (free tier). Without a key, search falls back to keywords (NFR-12).
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_TEXT_MODEL = os.getenv("GEMINI_TEXT_MODEL", "gemini-flash-lite-latest")      # image understanding + speech-to-text
GEMINI_FALLBACK_MODEL = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-3.5-flash-lite")
GEMINI_EMBED_MODEL = os.getenv("GEMINI_EMBED_MODEL", "gemini-embedding-001")
GEMINI_EMBED_DIM = int(os.getenv("GEMINI_EMBED_DIM", "768"))
AI_QUERY_TIMEOUT = float(os.getenv("AI_QUERY_TIMEOUT", "2.0"))          # NFR-12: fall back to keywords within 2 s
AI_GENERATE_TIMEOUT = float(os.getenv("AI_GENERATE_TIMEOUT", "12"))

# --- Shopping assistant (chatbot). The free Gemini tier measured 7-17 s per call, and an answer that uses a tool needs
# two calls, so chat has its own limits: per call, and in total (then the rule engine answers instead).
CHAT_CALL_TIMEOUT = float(os.getenv("CHAT_CALL_TIMEOUT", "25"))
CHAT_TIMEOUT = float(os.getenv("CHAT_TIMEOUT", "50"))
CHAT_FAST_PATH_WORDS = int(os.getenv("CHAT_FAST_PATH_WORDS", "12"))   # short FAQ-style messages skip the model

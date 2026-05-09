import json
import os

from dotenv import load_dotenv

load_dotenv()


REQUIRED_CHANNELS = [
    {
        "chat_id": "@dashpartner_news",
        "title": "Подписаться на Dash News",
        "url": "https://t.me/reysldevblog",
    },
    {
        "chat_id": "@dashpartner_updates",
        "title": "Подписаться на Dash Updates",
        "url": "https://t.me/SSticSS",
    },
]

DEFAULT_HTTP_HOST = os.getenv("HTTP_HOST", "0.0.0.0")
DEFAULT_HTTP_PORT = int(os.getenv("HTTP_PORT", "8080"))

PARTNER_STORE_PATH = os.getenv("PARTNER_STORE_PATH", "data/partner_store.json")
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/dashpartner.sqlite3")
PARTNER_BOT_USERNAME = os.getenv("PARTNER_BOT_USERNAME")
CHAT_SUBSCRIPTION_REWARD = float(os.getenv("CHAT_SUBSCRIPTION_REWARD", "0.8"))

TGRASS_OFFERS_URL = os.getenv("TGRASS_OFFERS_URL", "https://tgrass.space/offers")
TGRASS_CHECK_URL = os.getenv("TGRASS_CHECK_URL", "https://tgrass.space/check")
TGRASS_AUTH_KEY = os.getenv("TGRASS_AUTH_KEY") or os.getenv("TG_RASS_API_KEY")


def load_tg_rass_demo_tasks() -> list[dict]:
    raw_value = os.getenv("TG_RASS_DEMO_TASKS") or os.getenv("TGRASS_DEMO_TASKS")
    if not raw_value:
        return []

    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError:
        return []

    return parsed if isinstance(parsed, list) else []


# Admin configuration
ADMIN_IDS = [1723065839, 7975675184]

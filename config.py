"""
MyTarot WhatsApp Bot — Global Configuration
=============================================
Single source of truth for all pricing, limits, API keys, and tier definitions.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ================= Networking =================
PUBLIC_URL = os.getenv("PUBLIC_URL", "web-production-f1268.up.railway.app")
BASE_URL = f"https://{PUBLIC_URL}"

# ================= API Keys =================
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")
CLAUDE_MODEL = "claude-3-5-haiku-20241022"

STRIPE_API_KEY = os.getenv("STRIPE_API_KEY", "sk_test_xxx")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_xxx")

WA_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
WA_PHONE_ID = os.getenv("PHONE_NUMBER_ID", "")
WA_VERIFY_TOKEN = os.getenv("WA_VERIFY_TOKEN", "my_tarot_verify_secret")
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "super_secret_admin_key_123")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///mytarot.db")

# ================= Tier Definitions =================
TIERS = {
    "free": {
        "daily_draws": 1,
        "max_birthdays": 1,
        "curve_months_visible": 0,  # sees shape only, no scores
        "curve_blur": True,
        "share_watermark": True,
        "real_card_spreads": ["single"],  # only single card if they own physical deck
        "push_weekly": False,
        "push_daily": False,
        "price_usd": 0,
        "price_myr": 0,
    },
    "pro": {
        "daily_draws": 5,
        "max_birthdays": 2,
        "curve_months_visible": 12,
        "curve_blur": False,
        "share_watermark": False,
        "real_card_spreads": ["single", "three_card", "five_element", "celtic_cross"],
        "push_weekly": True,
        "push_daily": False,
        "price_usd": 9.99,
        "price_myr": 45,
        "deck_reward_months": 6,  # cumulative months to earn free deck
    },
    "agent": {
        "daily_draws": 25,
        "max_birthdays": 999,  # unlimited
        "curve_months_visible": 12,
        "curve_blur": False,
        "share_watermark": False,
        "real_card_spreads": ["single", "three_card", "five_element", "celtic_cross"],
        "push_weekly": True,
        "push_daily": False,
        "price_usd": 25,
        "price_myr": 99,
        "deck_reward_months": 3,
    },
    "affiliate": {
        "daily_draws": 60,
        "max_birthdays": 999,
        "curve_months_visible": 12,
        "curve_blur": False,
        "share_watermark": False,
        "real_card_spreads": ["single", "three_card", "five_element", "celtic_cross"],
        "push_weekly": True,
        "push_daily": True,
        "price_usd": 66,
        "price_myr": 266,
        "deck_reward_months": 0,  # instant on first month
        "referral_commission": 0.10,  # 10%
        "min_withdrawal_usd": 25,
    },
}

# Tier ordering for permission checks
TIER_ORDER = {"free": 0, "pro": 1, "agent": 2, "affiliate": 3}

# ================= Birthday Rules =================
BIRTHDAY_FREE_EDITS = 2          # first 2 edits are free
BIRTHDAY_EDIT_COOLDOWN_DAYS = 60  # after free edits, 60-day cooldown per edit

# ================= Categories =================
CATEGORIES = {
    "1": {"id": "love", "emoji": "💌", "label_zh": "爱情", "label_en": "Love", "label_ms": "Cinta"},
    "2": {"id": "career", "emoji": "💼", "label_zh": "事业", "label_en": "Career", "label_ms": "Kerjaya"},
    "3": {"id": "study", "emoji": "🎓", "label_zh": "学业", "label_en": "Studies", "label_ms": "Pelajaran"},
    "4": {"id": "other", "emoji": "🌀", "label_zh": "其他", "label_en": "Other", "label_ms": "Lain-lain"},
}

# Category modifiers for fortune scoring
CATEGORY_MODIFIERS = {
    "love":   {"cups": 1.3, "wands": 1.0, "swords": 0.8, "pentacles": 0.9, "major": 1.0},
    "career": {"cups": 0.8, "wands": 1.2, "swords": 1.0, "pentacles": 1.3, "major": 1.0},
    "study":  {"cups": 0.9, "wands": 1.1, "swords": 1.3, "pentacles": 1.0, "major": 1.0},
    "other":  {"cups": 1.0, "wands": 1.0, "swords": 1.0, "pentacles": 1.0, "major": 1.0},
}

# ================= Stripe Product IDs (to be filled after creation) =================
STRIPE_PRODUCTS = {
    "pro_monthly_usd": os.getenv("STRIPE_PRO_USD", ""),
    "pro_monthly_myr": os.getenv("STRIPE_PRO_MYR", ""),
    "agent_monthly_usd": os.getenv("STRIPE_AGENT_USD", ""),
    "agent_monthly_myr": os.getenv("STRIPE_AGENT_MYR", ""),
    "affiliate_monthly_usd": os.getenv("STRIPE_AFFILIATE_USD", ""),
    "affiliate_monthly_myr": os.getenv("STRIPE_AFFILIATE_MYR", ""),
    "deck_onetime_myr": os.getenv("STRIPE_DECK_MYR", ""),
}

# ================= Paths =================
TAROT_METADATA_PATH = os.getenv("TAROT_METADATA_PATH", "tarot-assets/tarot_metadata.json")
ORACLE_FLAVORS_PATH = os.getenv("ORACLE_FLAVORS_PATH", "tarot-assets/oracle_flavors.json")
CARD_SCORES_PATH = os.getenv("CARD_SCORES_PATH", "data/card_scores.json")
CARD_IMAGES_PATH = os.getenv("CARD_IMAGES_PATH", "tarot-assets/whatsapp-ready/")

# ================= WhatsApp =================
WA_API_URL = f"https://graph.facebook.com/v18.0/{WA_PHONE_ID}/messages"
WA_HEADERS = {
    "Authorization": f"Bearer {WA_TOKEN}",
    "Content-Type": "application/json",
}

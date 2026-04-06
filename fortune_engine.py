"""
MyTarot — Fortune Engine
==========================
Deterministic 12-month fortune curve generator.

Algorithm:
  1. Hash(user_phone + birthday + category + year) → seed
  2. Seed → pick 12 cards (one per month), each with orientation
  3. Apply category modifier to each card's base score
  4. Smooth the curve with weighted moving average
  5. Return monthly scores + assigned cards
"""

import hashlib
import json
import random
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from config import CATEGORY_MODIFIERS, CARD_SCORES_PATH


# Load card scores once at import
with open(CARD_SCORES_PATH, 'r', encoding='utf-8') as f:
    CARD_SCORES = json.load(f)

CARD_IDS = list(CARD_SCORES.keys())


def _make_seed(phone: str, birthday: str, category: str, year: int,
               gender: str = "unknown", lucky_number: int = 0,
               birth_hour: str = None) -> int:
    """Deterministic seed from user identity + context + profile."""
    hour_part = birth_hour if birth_hour else "X"
    raw = f"{phone}|{birthday}|{gender}|{lucky_number}|{hour_part}|{category}|{year}"
    return int(hashlib.sha256(raw.encode()).hexdigest(), 16)


def generate_yearly_fortune(phone: str, birthday: str, category: str,
                            start_date: datetime = None,
                            gender: str = "unknown", lucky_number: int = 0,
                            birth_hour: str = None) -> dict:
    """
    Generate a rolling 12-month fortune curve.

    Args:
        phone: User's WhatsApp phone number
        birthday: User's birthday string (YYYY-MM-DD)
        category: One of 'love', 'career', 'study', 'other'
        start_date: Starting month (default: current month)
        gender: User's gender ('male', 'female', 'unknown')
        lucky_number: User's chosen lucky number (1-99, default 0)
        birth_hour: Optional birth hour string (e.g. '08:30', '辰时')

    Returns:
        {
            "months": [
                {
                    "month": "2026-04",
                    "label": "Apr 2026",
                    "card_id": "19_the_sun",
                    "orientation": "upright",
                    "raw_score": 95,
                    "modified_score": 95.0,
                    "smoothed_score": 82.3
                },
                ...  (12 months)
            ],
            "peak_month": {"month": "2026-04", "score": 95.0},
            "valley_month": {"month": "2026-08", "score": 28.5},
            "yearly_average": 62.1,
            "seed": 123456789
        }
    """
    if start_date is None:
        start_date = datetime.now().replace(day=1)
    else:
        start_date = start_date.replace(day=1)

    year = start_date.year
    seed = _make_seed(phone, birthday, category, year,
                      gender, lucky_number, birth_hour)

    rng = random.Random(seed)

    # Pick 12 unique cards for the year
    selected_cards = rng.sample(CARD_IDS, 12)

    # Get category modifier map
    cat_mod = CATEGORY_MODIFIERS.get(category, CATEGORY_MODIFIERS["other"])

    months = []
    for i in range(12):
        month_date = start_date + relativedelta(months=i)
        card_id = selected_cards[i]
        card_data = CARD_SCORES[card_id]

        # 60% upright, 40% reversed
        orientation = "upright" if rng.random() < 0.6 else "reversed"
        raw_score = card_data[orientation]

        # Apply category modifier based on suit
        suit = card_data["suit"]
        modifier = cat_mod.get(suit, 1.0)
        modified_score = round(raw_score * modifier, 1)

        # Clamp to 0-100
        modified_score = max(0, min(100, modified_score))

        months.append({
            "month": month_date.strftime("%Y-%m"),
            "label": month_date.strftime("%b %Y"),
            "card_id": card_id,
            "orientation": orientation,
            "raw_score": raw_score,
            "modified_score": modified_score,
        })

    # Smooth the curve (weighted moving average, window=3)
    scores = [m["modified_score"] for m in months]
    smoothed = _smooth_curve(scores)
    for i, m in enumerate(months):
        m["smoothed_score"] = smoothed[i]

    # Find peak and valley
    peak = max(months, key=lambda m: m["smoothed_score"])
    valley = min(months, key=lambda m: m["smoothed_score"])
    avg = round(sum(m["smoothed_score"] for m in months) / 12, 1)

    return {
        "months": months,
        "peak_month": {"month": peak["month"], "score": peak["smoothed_score"]},
        "valley_month": {"month": valley["month"], "score": valley["smoothed_score"]},
        "yearly_average": avg,
        "seed": seed % (10**12),  # truncate for display
    }


def _smooth_curve(scores: list, window: int = 3) -> list:
    """Weighted moving average smoothing. Edges use smaller windows."""
    n = len(scores)
    smoothed = []
    weights = [0.2, 0.6, 0.2]  # center-heavy

    for i in range(n):
        if i == 0:
            val = scores[0] * 0.7 + scores[1] * 0.3
        elif i == n - 1:
            val = scores[n-2] * 0.3 + scores[n-1] * 0.7
        else:
            val = (scores[i-1] * weights[0] +
                   scores[i] * weights[1] +
                   scores[i+1] * weights[2])
        smoothed.append(round(val, 1))

    return smoothed


def get_monthly_guardian_card(phone: str, birthday: str,
                              month: str = None) -> dict:
    """
    Get the 'Guardian Card' for a specific month.
    This is the card assigned to that month in the yearly fortune.

    Args:
        phone: User phone
        birthday: User birthday
        month: Month string like '2026-04', defaults to current month
    """
    if month is None:
        month = datetime.now().strftime("%Y-%m")

    year = int(month.split("-")[0])
    start = datetime(year, 1, 1)

    # Generate for 'other' category to get the general guardian
    fortune = generate_yearly_fortune(phone, birthday, "other", start)

    for m in fortune["months"]:
        if m["month"] == month:
            return {
                "month": month,
                "card_id": m["card_id"],
                "orientation": m["orientation"],
                "score": m["smoothed_score"],
            }

    return None


def draw_single_card(phone: str, category: str) -> dict:
    """
    Draw a single card for a one-time reading.
    Uses current timestamp + phone as seed for pseudo-randomness
    that still allows reproducibility within the same second.
    """
    now = datetime.now()
    seed_str = f"{phone}|{category}|{now.strftime('%Y%m%d%H%M%S')}"
    seed = int(hashlib.sha256(seed_str.encode()).hexdigest(), 16)
    rng = random.Random(seed)

    card_id = rng.choice(CARD_IDS)
    orientation = "upright" if rng.random() < 0.6 else "reversed"

    return {
        "card_id": card_id,
        "orientation": orientation,
        "score": CARD_SCORES[card_id][orientation],
        "timestamp": now.isoformat(),
    }

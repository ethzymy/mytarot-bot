"""
MyTarot — Real Card Mode
===========================
Physical card interaction engine.
User inputs card numbers from their physical deck → system generates AI reading.

Spreads:
  - single:       1 card  (Free + card, Pro+)
  - three_card:   3 cards (Pro+)
  - five_element:  5 cards (Pro+)
  - celtic_cross: 10 cards (Pro+)
"""

import json
from config import TIERS, CARD_SCORES_PATH
from db import get_db, P
from subscription_mgr import get_user_tier

with open(CARD_SCORES_PATH, 'r', encoding='utf-8') as f:
    _ALL_CARDS = json.load(f)

CARD_IDS = list(_ALL_CARDS.keys())
TOTAL_CARDS = len(CARD_IDS)

SPREAD_DEFINITIONS = {
    "single": {
        "name_zh": "单牌解读",
        "name_en": "Single Card",
        "name_ms": "Kad Tunggal",
        "card_count": 1,
        "positions": ["核心启示"],
        "positions_en": ["Core Insight"],
    },
    "three_card": {
        "name_zh": "三牌阵（过去·现在·未来）",
        "name_en": "Three Card Spread",
        "name_ms": "Tiga Kad",
        "card_count": 3,
        "positions": ["过去", "现在", "未来"],
        "positions_en": ["Past", "Present", "Future"],
    },
    "five_element": {
        "name_zh": "五元素牌阵",
        "name_en": "Five Element Spread",
        "name_ms": "Lima Elemen",
        "card_count": 5,
        "positions": ["现状", "挑战", "过去影响", "未来趋势", "潜力/结果"],
        "positions_en": ["Current", "Challenge", "Past Influence", "Future Trend", "Potential"],
    },
    "celtic_cross": {
        "name_zh": "凯尔特十字牌阵",
        "name_en": "Celtic Cross",
        "name_ms": "Salib Celtic",
        "card_count": 10,
        "positions": [
            "核心问题", "障碍/交叉", "根源", "过去", "可能性",
            "近未来", "你的态度", "外在环境", "希望与恐惧", "最终结果"
        ],
        "positions_en": [
            "Core Issue", "Crossing", "Root", "Past", "Potential",
            "Near Future", "Your Attitude", "Environment", "Hopes & Fears", "Outcome"
        ],
    },
}


def check_real_card_access(phone: str) -> dict:
    """
    Check if user has physical card access and which spreads they can use.

    Returns:
        {"has_card": bool, "available_spreads": list}
    """
    with get_db() as conn:
        c = conn.cursor()
        c.execute(f"SELECT card_activated FROM users WHERE phone = {P}", (phone,))
        row = c.fetchone()

        if not row:
            return {"has_card": False, "available_spreads": []}

        activated = row[0] if isinstance(row, tuple) else row["card_activated"]
        if not activated:
            return {"has_card": False, "available_spreads": []}

    tier = get_user_tier(phone)
    allowed = TIERS.get(tier, TIERS["free"])["real_card_spreads"]

    return {
        "has_card": True,
        "available_spreads": allowed,
    }


def parse_card_input(raw_input: str) -> dict:
    """
    Parse user's card number input.

    Accepted formats:
        "15"          → single card #15
        "15 正"       → card #15 upright
        "15 逆"       → card #15 reversed
        "3, 15, 42"   → three cards
        "3 15 42"     → three cards (space-separated)

    Returns:
        {"valid": bool, "cards": list, "error": str}
    """
    raw = raw_input.strip()

    # Detect orientation markers
    has_orientation = any(x in raw for x in ["正", "逆", "up", "rev", "U", "R"])

    # Split by comma, space, or Chinese comma
    parts = raw.replace("，", ",").replace("、", ",").split(",")
    if len(parts) == 1:
        parts = raw.split()

    cards = []
    for part in parts:
        part = part.strip()
        if not part:
            continue

        # Extract orientation
        orientation = "upright"  # default
        for marker in ["逆", "rev", "R"]:
            if marker in part:
                orientation = "reversed"
                part = part.replace(marker, "").strip()
                break
        for marker in ["正", "up", "U"]:
            if marker in part:
                orientation = "upright"
                part = part.replace(marker, "").strip()
                break

        # Parse number
        try:
            num = int(part)
        except ValueError:
            return {"valid": False, "cards": [],
                    "error": f"无法识别数字: '{part}'。请输入卡牌编号 (0-77)。"}

        if num < 0 or num >= TOTAL_CARDS:
            return {"valid": False, "cards": [],
                    "error": f"编号 {num} 超出范围。有效范围: 0-{TOTAL_CARDS-1}。"}

        card_id = CARD_IDS[num]
        cards.append({
            "number": num,
            "card_id": card_id,
            "orientation": orientation,
        })

    if not cards:
        return {"valid": False, "cards": [],
                "error": "未能识别任何卡牌编号。请输入数字，如: 15 或 3,15,42"}

    return {"valid": True, "cards": cards, "error": None}


def validate_spread(cards: list, spread_type: str) -> dict:
    """
    Validate that the card count matches the spread requirement.

    Returns:
        {"valid": bool, "spread": dict, "error": str}
    """
    spread = SPREAD_DEFINITIONS.get(spread_type)
    if not spread:
        return {"valid": False, "spread": None,
                "error": f"未知牌阵类型: {spread_type}"}

    expected = spread["card_count"]
    actual = len(cards)

    if actual != expected:
        return {"valid": False, "spread": spread,
                "error": f"{spread['name_zh']}需要 {expected} 张牌，你输入了 {actual} 张。"}

    # Check for duplicates
    card_ids = [c["card_id"] for c in cards]
    if len(set(card_ids)) != len(card_ids):
        return {"valid": False, "spread": spread,
                "error": "检测到重复的卡牌编号，每张牌只能出现一次。"}

    return {"valid": True, "spread": spread, "error": None}


def prepare_reading_context(cards: list, spread_type: str,
                            category: str) -> dict:
    """
    Prepare the structured context for AI reading generation.

    Returns a dict ready to be passed to ai_reading.py's prompt template.
    """
    spread = SPREAD_DEFINITIONS[spread_type]

    positions = []
    for i, card in enumerate(cards):
        position_name = spread["positions"][i] if i < len(spread["positions"]) else f"位置{i+1}"
        positions.append({
            "position": position_name,
            "card_id": card["card_id"],
            "card_name": card["card_id"].split("_", 1)[1].replace("_", " ").title(),
            "orientation": card["orientation"],
            "score": _ALL_CARDS[card["card_id"]][card["orientation"]],
        })

    return {
        "spread_type": spread_type,
        "spread_name": spread["name_zh"],
        "category": category,
        "positions": positions,
        "card_count": len(cards),
        "mode": "real_card",
    }

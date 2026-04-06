"""
MyTarot — AI Reading Generator
=================================
Generates tarot readings using Claude 3.5 Haiku.
Includes prompt templates for all reading types and the
Oracle Lens/Sensory Seed system for千人千面 variation.
"""

import json
import random
import hashlib
from datetime import datetime

import anthropic

from config import CLAUDE_API_KEY, CLAUDE_MODEL, TAROT_METADATA_PATH, ORACLE_FLAVORS_PATH

# Load metadata
with open(TAROT_METADATA_PATH, 'r', encoding='utf-8') as f:
    CARD_METADATA = json.load(f)

with open(ORACLE_FLAVORS_PATH, 'r', encoding='utf-8') as f:
    ORACLE_FLAVORS = json.load(f)

SENSORY_SEEDS = ORACLE_FLAVORS.get("sensory_seeds", [])
ORACLE_LENSES = ORACLE_FLAVORS.get("oracle_lenses", [])

client = anthropic.Anthropic(api_key=CLAUDE_API_KEY) if CLAUDE_API_KEY else None

# ================= Prompt Templates =================

SYSTEM_PROMPT_CAT = """你是「灵猫 Oracle」— 一只拥有九条命的神秘塔罗灵猫。
你用古老而灵动的猫系口吻解读塔罗牌，语气兼具神秘感与亲和力。

你的解读风格：
- 以猫的感官（视觉、嗅觉、听觉、触觉）引入解读
- 使用「喵呜」「灵猫感应」「猫的直觉」等语气词
- 解读内容要有深度，融合塔罗传统含义与猫系隐喻
- 结尾给出一句简短有力的行动建议

重要规则：
- 不要复述用户的问题
- 直接进入解读
- 使用「你」称呼用户
- 所有解读末尾加一行：「✨ 本服务仅供娱乐目的参考」"""


def _pick_flavor(phone: str) -> dict:
    """Select a unique Oracle Lens + Sensory Seed combo based on phone+time."""
    seed_str = f"{phone}|{datetime.now().strftime('%Y%m%d%H%M')}"
    seed = int(hashlib.sha256(seed_str.encode()).hexdigest(), 16)
    rng = random.Random(seed)

    lens = rng.choice(ORACLE_LENSES) if ORACLE_LENSES else "Manifest"
    sensory = rng.choice(SENSORY_SEEDS) if SENSORY_SEEDS else "moonlight"

    return {"lens": lens, "sensory_seed": sensory}


def generate_single_reading(card_id: str, orientation: str,
                             category: str, phone: str,
                             is_pro: bool = False,
                             language: str = "zh") -> str:
    """
    Generate a single-card reading.

    Free users: ~50 words (truncated)
    Pro+ users: ~300 words (full)
    """
    card_meta = CARD_METADATA.get(card_id, {})
    card_name = card_meta.get("name", card_id)
    card_energy = card_meta.get("cat_energy", "")
    keywords = card_meta.get("core_keywords", [])

    flavor = _pick_flavor(phone)
    word_limit = 300 if is_pro else 50

    category_labels = {
        "love": "爱情", "career": "事业",
        "study": "学业", "other": "综合运势"
    }
    cat_label = category_labels.get(category, "综合运势")

    user_prompt = f"""请为以下塔罗抽牌结果进行解读：

牌面：{card_name}（{'正位' if orientation == 'upright' else '逆位'}）
领域：{cat_label}
猫能量：{card_energy}
核心关键词：{', '.join(keywords)}

风格要求：
- Oracle Lens（解读视角）：{flavor['lens']}
- Sensory Seed（感官线索）：{flavor['sensory_seed']}
- 将以上两个元素自然融入你的解读中，不要直接提及它们的名称

字数限制：{word_limit}字以内
语言：{'中文' if language == 'zh' else 'English' if language == 'en' else 'Bahasa Melayu'}"""

    if not client:
        # Fallback when no API key configured
        return _generate_fallback(card_name, orientation, cat_label, keywords, word_limit)

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=500 if is_pro else 150,
        system=SYSTEM_PROMPT_CAT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    return response.content[0].text


def generate_spread_reading(reading_context: dict,
                             phone: str, language: str = "zh") -> str:
    """
    Generate a multi-card spread reading (three_card, celtic_cross, etc.)
    Used by Real Card Mode.
    """
    positions = reading_context["positions"]
    spread_name = reading_context["spread_name"]
    category = reading_context["category"]
    flavor = _pick_flavor(phone)

    category_labels = {
        "love": "爱情", "career": "事业",
        "study": "学业", "other": "综合运势"
    }
    cat_label = category_labels.get(category, "综合运势")

    # Build position descriptions
    pos_text = ""
    for p in positions:
        card_meta = CARD_METADATA.get(p["card_id"], {})
        ori = "正位" if p["orientation"] == "upright" else "逆位"
        pos_text += f"\n位置「{p['position']}」: {card_meta.get('name', p['card_id'])}（{ori}）"
        pos_text += f"\n  关键词: {', '.join(card_meta.get('core_keywords', []))}"
        pos_text += f"\n  猫能量: {card_meta.get('cat_energy', '')}\n"

    user_prompt = f"""请对以下{spread_name}进行完整解读：

领域：{cat_label}
牌阵：{spread_name}（共{len(positions)}张牌）
{pos_text}

风格要求：
- Oracle Lens：{flavor['lens']}
- Sensory Seed：{flavor['sensory_seed']}
- 将以上元素自然融入解读

解读结构：
1. 总览：一句话概括整个牌阵的信息（30字以内）
2. 逐位解读：每个位置的含义与相互关系
3. 综合建议：结合所有牌面给出3条具体行动建议
4. 行动指南：最重要的一件事

字数限制：800字以内
语言：{'中文' if language == 'zh' else 'English' if language == 'en' else 'Bahasa Melayu'}"""

    if not client:
        return _generate_fallback_spread(positions, spread_name, cat_label)

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1200,
        system=SYSTEM_PROMPT_CAT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    return response.content[0].text


def generate_fortune_summary(months_data: list, category: str,
                              phone: str, language: str = "zh") -> str:
    """Generate a narrative summary of the 12-month fortune curve."""
    peak = max(months_data, key=lambda m: m["smoothed_score"])
    valley = min(months_data, key=lambda m: m["smoothed_score"])

    category_labels = {
        "love": "爱情", "career": "事业",
        "study": "学业", "other": "综合运势"
    }
    cat_label = category_labels.get(category, "综合运势")

    user_prompt = f"""请为以下12个月运势曲线写一段总结性解读：

领域：{cat_label}
运势高峰：{peak['label']}（{peak['smoothed_score']}分，牌面：{peak['card_id']}）
运势低谷：{valley['label']}（{valley['smoothed_score']}分，牌面：{valley['card_id']}）

逐月概览：
{chr(10).join(f"  {m['label']}: {m['smoothed_score']}分 ({m['card_id']}, {m['orientation']})" for m in months_data)}

请写出：
1. 整体运势走向（50字）
2. 高峰月的机遇提示（30字）
3. 低谷月的避险建议（30字）
4. 一句总结性金句

字数限制：200字以内"""

    if not client:
        return f"🐱 {cat_label}运势总览\n\n高峰月：{peak['label']}（{peak['smoothed_score']}分）\n低谷月：{valley['label']}（{valley['smoothed_score']}分）\n\n✨ 本服务仅供娱乐目的参考"

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=400,
        system=SYSTEM_PROMPT_CAT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    return response.content[0].text


def _generate_fallback(card_name, orientation, category, keywords, word_limit):
    """Offline fallback when no API key is available."""
    ori = "正位" if orientation == "upright" else "逆位"
    kw = "、".join(keywords[:3]) if keywords else "未知能量"
    return (
        f"🐱 灵猫感应到【{card_name}】（{ori}）的能量...\n\n"
        f"在{category}领域，{kw}的力量正在涌动。\n\n"
        f"{'这股能量预示着积极的变化。' if orientation == 'upright' else '需要注意内在的平衡。'}\n\n"
        f"✨ 本服务仅供娱乐目的参考\n"
        f"💡 开启深度解读获取完整分析"
    )


def _generate_fallback_spread(positions, spread_name, category):
    """Offline fallback for multi-card spread readings."""
    lines = [f"🐱 {spread_name} — {category}解读\n"]
    for p in positions:
        card_meta = CARD_METADATA.get(p["card_id"], {})
        ori = "正位" if p["orientation"] == "upright" else "逆位"
        lines.append(f"📌 {p['position']}: {card_meta.get('name', p['card_id'])}（{ori}）")
    lines.append("\n✨ 本服务仅供娱乐目的参考")
    return "\n".join(lines)

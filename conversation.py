"""
MyTarot — Conversation State Machine
=======================================
Main WhatsApp webhook handler and dialog flow controller.
Refactored from whatsapp_stripe_poc.py into a modular architecture.
"""

import os
import json
import re
import requests
import stripe
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()

from config import (
    STRIPE_API_KEY, STRIPE_WEBHOOK_SECRET,
    WA_API_URL, WA_HEADERS, WA_VERIFY_TOKEN, CATEGORIES, TIERS,
    CARD_IMAGES_PATH,
)
from db import get_db, P, init_db
from subscription_mgr import (
    get_or_create_user, check_daily_draws, record_draw,
    create_checkout_session, get_user_tier,
    handle_subscription_created, handle_invoice_paid, handle_subscription_cancelled,
)
from fortune_engine import generate_yearly_fortune, draw_single_card
from ai_reading import generate_single_reading
from referral_manager import validate_referral_code, generate_referral_code
from real_card_mode import (
    check_real_card_access, parse_card_input, validate_spread,
    prepare_reading_context, SPREAD_DEFINITIONS,
)
import messages as msg
from admin_routes import admin_bp

stripe.api_key = STRIPE_API_KEY
app = Flask(__name__)
app.register_blueprint(admin_bp)

# Session cache (backed by DB, this is just for fast in-memory state)
SESSIONS = {}


# ================= WhatsApp Helpers =================

def send_text(to, text):
    payload = {
        "messaging_product": "whatsapp", "to": to,
        "type": "text", "text": {"body": text}
    }
    requests.post(WA_API_URL, headers=WA_HEADERS, json=payload)


def send_image(to, image_url, caption):
    payload = {
        "messaging_product": "whatsapp", "to": to,
        "type": "image", "image": {"link": image_url, "caption": caption}
    }
    requests.post(WA_API_URL, headers=WA_HEADERS, json=payload)


# ================= Language Detection =================

def detect_language(text):
    """Simple heuristic language detection from first message."""
    text_lower = text.lower()
    malay_words = ["hai", "saya", "nak", "boleh", "terima", "kasih", "selamat"]
    chinese_chars = any('\u4e00' <= c <= '\u9fff' for c in text)

    if chinese_chars or any(w in text_lower for w in ["你好", "嗨", "开始"]):
        return "zh"
    if any(w in text_lower for w in malay_words):
        return "ms"
    return "en"


# ================= State Machine =================

def get_session(phone):
    if phone not in SESSIONS:
        user = get_or_create_user(phone)
        SESSIONS[phone] = {
            "state": "START",
            "language": user.get("language", "zh"),
            "category": None,
            "tier": user.get("tier", "free"),
        }
    return SESSIONS[phone]


def process_message(phone, text):
    """Main entry point for processing a user message."""
    text = text.strip()
    text_lower = text.lower()
    session = get_session(phone)
    lang = session["language"]

    # Global commands (work from any state)
    if text_lower in ["hi", "hello", "你好", "嗨", "hai", "menu", "菜单"]:
        session["language"] = detect_language(text)
        lang = session["language"]
        session["tier"] = get_user_tier(phone)

        user = get_or_create_user(phone, lang)

        # Check if onboarding is needed (first-time user)
        if not user.get("onboarding_done"):
            send_text(phone, msg.onboarding_birthday(lang))
            session["state"] = "ONBOARD_BIRTHDAY"
            return

        # Returning user — go straight to category
        session["state"] = "AWAITING_CATEGORY"
        send_text(phone, msg.welcome(lang))
        return

    if text_lower in ["订阅", "subscribe", "langgan", "plan", "计划"]:
        send_text(phone, msg.subscription_menu(lang))
        session["state"] = "AWAITING_SUB_CHOICE"
        return

    if text_lower in ["激活", "activate", "pin"]:
        send_text(phone, msg.pin_prompt(lang))
        session["state"] = "AWAITING_PIN"
        return

    # ---- State-specific handling ----

    state = session["state"]

    # === CATEGORY SELECTION ===
    if state == "AWAITING_CATEGORY":
        if text in CATEGORIES:
            cat = CATEGORIES[text]
            session["category"] = cat["id"]
            label = cat[f"label_{lang}"] if f"label_{lang}" in cat else cat["label_zh"]
            send_text(phone, msg.category_selected(f"{cat['emoji']} {label}", lang))
            session["state"] = "AWAITING_SERVICE"
        else:
            send_text(phone, msg.invalid_input(lang))
        return

    # === SERVICE SELECTION ===
    if state == "AWAITING_SERVICE":
        category = session.get("category", "other")

        # Draw a card
        if any(w in text_lower for w in ["抽卡", "draw", "cabut", "抽"]):
            draw_status = check_daily_draws(phone)
            if not draw_status["allowed"]:
                send_text(phone, msg.draw_limit_reached(0, 0, lang))
                return

            cat_label = category
            send_text(phone, msg.preparing_draw(cat_label, lang))

            card = draw_single_card(phone, category)
            record_draw(phone)

            is_pro = session["tier"] != "free"
            reading = generate_single_reading(
                card["card_id"], card["orientation"],
                category, phone, is_pro=is_pro, language=lang
            )

            # Send card image
            image_filename = f"{card['card_id']}_whatsapp.png"
            # TODO: Replace with actual CDN URL
            image_url = f"https://tarot.ethzy.my/cards/{image_filename}"

            ori_label = "正位 Upright" if card["orientation"] == "upright" else "逆位 Reversed"
            caption = f"🌕 {card['card_id'].split('_', 1)[1].replace('_', ' ').title()} ({ori_label})\n\n{reading}"

            send_image(phone, image_url, caption)

            remaining = draw_status["remaining"] - 1
            if remaining > 0:
                send_text(phone, f"📊 今日剩余抽卡次数: {remaining}/{draw_status['limit']}")

            session["state"] = "AWAITING_SERVICE"
            return

        # Fortune curve
        if any(w in text_lower for w in ["运势", "fortune", "nasib", "曲线"]):
            if session["tier"] == "free":
                send_text(phone, "📈 运势曲线功能需要 Pro 以上订阅。\n回复【订阅】查看计划。")
                return

            # Need birthday first
            with get_db() as conn:
                c = conn.cursor()
                c.execute(f"SELECT birthdays FROM users WHERE phone = {P}", (phone,))
                row = c.fetchone()
                bdays = json.loads(row[0] if isinstance(row, tuple) else row["birthdays"]) if row else []

            if not bdays:
                send_text(phone, "🎂 请先设置生日。\n格式：1990-05-15")
                session["state"] = "AWAITING_BIRTHDAY"
                return

            birthday = bdays[0] if isinstance(bdays[0], str) else bdays[0].get("date", "2000-01-01")

            # Fetch profile for personalized fortune
            with get_db() as conn:
                c = conn.cursor()
                c.execute(f"SELECT gender, lucky_number, birth_hour FROM users WHERE phone = {P}", (phone,))
                profile = c.fetchone()
                if profile:
                    g = profile[0] if isinstance(profile, tuple) else profile["gender"]
                    ln = profile[1] if isinstance(profile, tuple) else profile["lucky_number"]
                    bh = profile[2] if isinstance(profile, tuple) else profile["birth_hour"]
                else:
                    g, ln, bh = "unknown", 0, None

            fortune = generate_yearly_fortune(phone, birthday, category,
                                              gender=g, lucky_number=ln,
                                              birth_hour=bh)

            # TODO: Generate and send curve image via curve_renderer.py
            summary_lines = [f"📈 *12个月{category}运势*\n"]
            for m in fortune["months"]:
                bar = "█" * int(m["smoothed_score"] / 10) + "░" * (10 - int(m["smoothed_score"] / 10))
                summary_lines.append(f"{m['label']}: {bar} {m['smoothed_score']:.0f}")

            summary_lines.append(f"\n🔝 高峰: {fortune['peak_month']['month']} ({fortune['peak_month']['score']:.0f})")
            summary_lines.append(f"📉 低谷: {fortune['valley_month']['month']} ({fortune['valley_month']['score']:.0f})")

            send_text(phone, "\n".join(summary_lines))
            session["state"] = "AWAITING_SERVICE"
            return

        # Real Card Mode
        if any(w in text_lower for w in ["实体牌", "real card", "kad fizikal", "实体"]):
            access = check_real_card_access(phone)
            if not access["has_card"]:
                send_text(phone, msg.pin_prompt(lang))
                session["state"] = "AWAITING_PIN"
                return

            send_text(phone, msg.real_card_spread_menu(access["available_spreads"], lang))
            session["state"] = "AWAITING_SPREAD_CHOICE"
            return

        send_text(phone, msg.invalid_input(lang))
        return

    # === ONBOARDING: BIRTHDAY ===
    if state == "ONBOARD_BIRTHDAY":
        match = re.match(r'(\d{4})-(\d{1,2})-(\d{1,2})', text)
        if match:
            birthday = f"{match.group(1)}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"
            with get_db() as conn:
                c = conn.cursor()
                bdays = json.dumps([{"date": birthday, "label": "自己"}])
                c.execute(f"UPDATE users SET birthdays = {P}, updated_at = datetime('now') WHERE phone = {P}",
                          (bdays, phone))
            send_text(phone, msg.onboarding_birth_hour(lang))
            session["state"] = "ONBOARD_BIRTH_HOUR"
        else:
            send_text(phone, "❌ 格式不正确。请输入：YYYY-MM-DD（如 1990-05-15）")
        return

    # === ONBOARDING: BIRTH HOUR (optional) ===
    if state == "ONBOARD_BIRTH_HOUR":
        if text_lower in ["跳过", "skip", "langkau"]:
            # No birth hour — proceed to gender
            send_text(phone, msg.onboarding_gender(lang))
            session["state"] = "ONBOARD_GENDER"
            return

        # Validate time format (HH:MM) or Chinese hour names
        chinese_hours = {
            "子": "23:00", "丑": "01:00", "寅": "03:00", "卯": "05:00",
            "辰": "07:00", "巳": "09:00", "午": "11:00", "未": "13:00",
            "申": "15:00", "酉": "17:00", "戌": "19:00", "亥": "21:00",
        }

        birth_hour = None
        # Check Chinese hour name (single char or with 时)
        for ch, hh in chinese_hours.items():
            if ch in text:
                birth_hour = hh
                break

        if not birth_hour:
            time_match = re.match(r'(\d{1,2})[:\s.时](\d{0,2})', text)
            if time_match:
                h = int(time_match.group(1))
                m = int(time_match.group(2)) if time_match.group(2) else 0
                if 0 <= h <= 23 and 0 <= m <= 59:
                    birth_hour = f"{h:02d}:{m:02d}"

        if birth_hour:
            with get_db() as conn:
                c = conn.cursor()
                c.execute(f"UPDATE users SET birth_hour = {P} WHERE phone = {P}",
                          (birth_hour, phone))
            send_text(phone, msg.onboarding_gender(lang))
            session["state"] = "ONBOARD_GENDER"
        else:
            send_text(phone, "❌ 无法识别时间格式。请输入 HH:MM（如 08:30）或回复【跳过】。")
        return

    # === ONBOARDING: GENDER ===
    if state == "ONBOARD_GENDER":
        gender_map = {"1": "male", "2": "female", "3": "unknown"}
        if text in gender_map:
            with get_db() as conn:
                c = conn.cursor()
                c.execute(f"UPDATE users SET gender = {P} WHERE phone = {P}",
                          (gender_map[text], phone))
            send_text(phone, msg.onboarding_lucky_number(lang))
            session["state"] = "ONBOARD_LUCKY_NUM"
        else:
            send_text(phone, msg.invalid_input(lang))
        return

    # === ONBOARDING: LUCKY NUMBER ===
    if state == "ONBOARD_LUCKY_NUM":
        try:
            num = int(text)
            if 1 <= num <= 99:
                with get_db() as conn:
                    c = conn.cursor()
                    c.execute(f"UPDATE users SET lucky_number = {P}, onboarding_done = 1 WHERE phone = {P}",
                              (num, phone))
                send_text(phone, msg.onboarding_complete(lang))
                session["state"] = "AWAITING_CATEGORY"
            else:
                send_text(phone, "⚠️ 请输入 1 到 99 之间的数字。")
        except ValueError:
            send_text(phone, "⚠️ 请输入一个数字（1-99）。")
        return

    # === BIRTHDAY INPUT (for fortune, outside onboarding) ===
    if state == "AWAITING_BIRTHDAY":
        match = re.match(r'(\d{4})-(\d{1,2})-(\d{1,2})', text)
        if match:
            birthday = f"{match.group(1)}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"
            with get_db() as conn:
                c = conn.cursor()
                bdays = json.dumps([{"date": birthday, "label": "自己"}])
                c.execute(f"UPDATE users SET birthdays = {P}, updated_at = datetime('now') WHERE phone = {P}",
                          (bdays, phone))
            send_text(phone, f"✅ 生日已设置: {birthday}\n\n回复【运势】查看运势曲线。")
            session["state"] = "AWAITING_SERVICE"
        else:
            send_text(phone, "❌ 格式不正确。请输入：YYYY-MM-DD（如 1990-05-15）")
        return

    # === PIN ACTIVATION ===
    if state == "AWAITING_PIN":
        if text_lower in ["取消", "cancel", "batal"]:
            session["state"] = "AWAITING_SERVICE"
            send_text(phone, msg.return_to_menu(lang))
            return

        from pin_manager import activate_pin
        result = activate_pin(text, phone)
        send_text(phone, result["message"])

        if result["success"]:
            with get_db() as conn:
                c = conn.cursor()
                c.execute(f"UPDATE users SET card_activated = 1 WHERE phone = {P}", (phone,))
            session["state"] = "AWAITING_SERVICE"
        return

    # === SUBSCRIPTION CHOICE ===
    if state == "AWAITING_SUB_CHOICE":
        tier_map = {"1": "pro", "2": "agent", "3": "affiliate"}
        if text in tier_map:
            chosen_tier = tier_map[text]
            session["pending_tier"] = chosen_tier
            send_text(phone, msg.referral_prompt(lang))
            session["state"] = "AWAITING_REFERRAL"
        else:
            send_text(phone, msg.invalid_input(lang))
        return

    # === REFERRAL CODE INPUT ===
    if state == "AWAITING_REFERRAL":
        referral_code = None
        if text_lower not in ["跳过", "skip", "langkau"]:
            result = validate_referral_code(text, phone)
            send_text(phone, result["message"])
            if not result["valid"]:
                return
            referral_code = text.upper().strip()

        tier = session.get("pending_tier", "pro")
        checkout_url = create_checkout_session(phone, tier, referral_code)

        if checkout_url:
            send_text(phone, f"💳 点击链接完成订阅：\n{checkout_url}")
        else:
            send_text(phone, "⚠️ 支付链接生成失败，请稍后重试。")

        session["state"] = "AWAITING_SERVICE"
        return

    # === REAL CARD: SPREAD SELECTION ===
    if state == "AWAITING_SPREAD_CHOICE":
        spread_map = {"1": "single", "2": "three_card", "3": "five_element", "4": "celtic_cross"}
        if text in spread_map:
            spread = spread_map[text]
            session["spread_type"] = spread
            card_count = SPREAD_DEFINITIONS[spread]["card_count"]
            send_text(phone, msg.real_card_input_prompt(card_count, lang))
            session["state"] = "AWAITING_CARD_INPUT"
        else:
            send_text(phone, msg.invalid_input(lang))
        return

    # === REAL CARD: CARD NUMBER INPUT ===
    if state == "AWAITING_CARD_INPUT":
        if text_lower in ["对照表", "list", "senarai"]:
            # Send card number reference (first 22 Major Arcana as sample)
            ref = "📋 *卡牌编号对照表*\n\n*大阿卡纳 (0-21):*\n"
            ref += "0=愚者 1=魔术师 2=女祭司\n3=皇后 4=皇帝 5=教皇\n"
            ref += "6=恋人 7=战车 8=力量\n9=隐者 10=命运之轮 11=正义\n"
            ref += "12=倒吊人 13=死神 14=节制\n15=恶魔 16=塔 17=星星\n"
            ref += "18=月亮 19=太阳 20=审判 21=世界\n\n"
            ref += "*小阿卡纳 (22-77):*\n"
            ref += "权杖: 22-35 | 圣杯: 36-49\n宝剑: 50-63 | 星币: 64-77\n\n"
            ref += "完整列表: tarot.ethzy.my/card-list"
            send_text(phone, ref)
            return

        parsed = parse_card_input(text)
        if not parsed["valid"]:
            send_text(phone, f"❌ {parsed['error']}")
            return

        spread_type = session.get("spread_type", "single")
        validation = validate_spread(parsed["cards"], spread_type)
        if not validation["valid"]:
            send_text(phone, f"❌ {validation['error']}")
            return

        category = session.get("category", "other")
        context = prepare_reading_context(parsed["cards"], spread_type, category)

        send_text(phone, "🔮 灵猫正在解读你的牌面，请稍候...")

        from ai_reading import generate_spread_reading
        reading = generate_spread_reading(context, phone, lang)
        send_text(phone, reading)

        # Log the reading
        with get_db() as conn:
            c = conn.cursor()
            c.execute(f"""
                INSERT INTO readings (phone, reading_type, category, cards, reading_text, mode)
                VALUES ({P}, {P}, {P}, {P}, {P}, 'real_card')
            """, (phone, spread_type, category, json.dumps(parsed["cards"]), reading))

        record_draw(phone)
        session["state"] = "AWAITING_SERVICE"
        return

    # Default: unrecognized
    send_text(phone, msg.return_to_menu(lang))


# ================= Flask Routes =================

@app.route('/whatsapp', methods=['GET'])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == WA_VERIFY_TOKEN:
        return challenge, 200
    return "Forbidden", 403


@app.route('/whatsapp', methods=['POST'])
def webhook():
    body = request.get_json()
    try:
        entry = body['entry'][0]['changes'][0]['value']
        if 'messages' not in entry:
            return jsonify({"status": "ok"}), 200

        msg_data = entry['messages'][0]
        phone = msg_data['from']
        text = msg_data.get('text', {}).get('body', '').strip()

        if text:
            process_message(phone, text)

    except Exception as e:
        print(f"[ERROR] {e}")

    return jsonify({"status": "ok"}), 200


@app.route('/stripe', methods=['POST'])
def stripe_webhook():
    payload = request.data
    sig = request.headers.get('Stripe-Signature')

    try:
        event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.error.SignatureVerificationError):
        return 'Invalid', 400

    if event['type'] == 'checkout.session.completed':
        handle_subscription_created(event['data'])
    elif event['type'] == 'invoice.paid':
        handle_invoice_paid(event['data'])
    elif event['type'] == 'customer.subscription.deleted':
        handle_subscription_cancelled(event['data'])

    return jsonify(success=True)


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "service": "mytarot-bot"})


if __name__ == '__main__':
    print("🐱 MyTarot Bot starting...")
    app.run(port=5000, debug=True, use_reloader=False)

"""
MyTarot — Conversation State Machine
=======================================
Main WhatsApp webhook handler and dialog flow controller.
"""

import os
import json
import re
import requests
import stripe
import time
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

# Session cache (backed by DB)
SESSIONS = {}

# Shortcut for multi-lang display
def _t(zh, en, ms, lang="zh"):
    return {"zh": zh, "en": en, "ms": ms}.get(lang, zh)

# ================= WhatsApp Helpers =================

def send_text(to, text):
    print(f"[DEBUG] Sending text to {to}: {text[:50]}...")
    payload = {
        "messaging_product": "whatsapp", "to": to,
        "type": "text", "text": {"body": text}
    }
    response = requests.post(WA_API_URL, headers=WA_HEADERS, json=payload)
    print(f"[DEBUG] WhatsApp API Response: {response.status_code} - {response.text}")

def send_image(to, image_url, caption):
    print(f"[DEBUG] Sending image to {to}: {image_url}")
    payload = {
        "messaging_product": "whatsapp", "to": to,
        "type": "image", "image": {"link": image_url, "caption": caption}
    }
    response = requests.post(WA_API_URL, headers=WA_HEADERS, json=payload)
    print(f"[DEBUG] WhatsApp API Response: {response.status_code} - {response.text}")

# ================= Language Detection =================

def detect_language(text):
    text_lower = text.lower()
    malay_words = ["hai", "saya", "nak", "boleh", "terima", "kasih", "selamat"]
    chinese_chars = any('\u4e00' <= c <= '\u9fff' for c in text)
    if chinese_chars or any(w in text_lower for w in ["你好", "嗨", "开始"]): return "zh"
    if any(w in text_lower for w in malay_words): return "ms"
    return "en"

# ================= State Machine =================

def get_session(phone):
    """Fetch session from memory, or fallback to DB persistence."""
    if phone not in SESSIONS:
        user = get_or_create_user(phone)
        cur_state = user.get("current_state") or "START"
        try:
            state_data = json.loads(user.get("state_data") or "{}")
        except:
            state_data = {}
        
        SESSIONS[phone] = {
            "state": cur_state,
            "language": user.get("language") or "zh",
            "category": None,
            "tier": user.get("tier") or "free",
            "data": state_data
        }
        print(f"[DEBUG] Session LOADED for {phone}: State={cur_state}")
    return SESSIONS[phone]

def save_session(phone, session):
    """Persist session state and temporary data to DB."""
    try:
        with get_db() as conn:
            c = conn.cursor()
            state_json = json.dumps(session.get("data", {}))
            ts_func = "NOW()" if os.getenv("DATABASE_URL", "").startswith("postgres") else "datetime('now')"
            sql = f"UPDATE users SET current_state = {P}, state_data = {P}, updated_at = {ts_func} WHERE phone = {P}"
            c.execute(sql, (session["state"], state_json, phone))
        print(f"[DEBUG] Session SAVED for {phone}: State={session['state']}")
    except Exception as e:
        print(f"[ERROR] Session SAVE FAILED for {phone}: {e}")

def process_message(phone, text):
    """Main entry point for processing a user message."""
    text = text.strip()
    text_lower = text.lower()
    session = get_session(phone)
    lang = session["language"]

    # Global commands
    if text_lower in ["hi", "hello", "你好", "嗨", "hai", "menu", "菜单"]:
        session["language"] = detect_language(text)
        lang = session["language"]
        session["tier"] = get_user_tier(phone)
        user = get_or_create_user(phone, lang)

        if not user.get("onboarding_done") or session["state"] == "START":
            card_back_url = "https://tarot.ethzy.my/assets/card_back_whatsapp.jpg"
            send_image(phone, card_back_url, msg.onboarding_birthday(lang))
            session["state"] = "ONBOARD_BIRTHDAY"
            save_session(phone, session)
            return

        session["state"] = "AWAITING_CATEGORY"
        save_session(phone, session)
        send_text(phone, msg.welcome(lang))
        return

    if text_lower in ["订阅", "subscribe", "plan", "计划"]:
        send_text(phone, msg.subscription_menu(lang))
        session["state"] = "AWAITING_SUB_CHOICE"
        save_session(phone, session)
        return

    if text_lower in ["激活", "activate", "pin"]:
        send_text(phone, msg.pin_prompt(lang))
        session["state"] = "AWAITING_PIN"
        save_session(phone, session)
        return

    if text_lower in ["资料", "profile", "my", "me", "status"]:
        user = get_or_create_user(phone)
        try:
            profile_msg = msg.profile_display(user, lang)
        except:
            profile_msg = f"👤 Profile: {phone}\nTier: {user.get('tier', 'free').upper()}"
        send_text(phone, profile_msg)
        return

    # ---- State-specific handling ----
    state = session["state"]

    if state == "ONBOARD_BIRTHDAY":
        match = re.match(r'(\d{4})-(\d{1,2})-(\d{1,2})', text)
        if match:
            birthday = f"{match.group(1)}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"
            with get_db() as conn:
                c = conn.cursor()
                bdays = json.dumps([{"date": birthday, "label": "自己"}])
                ts_func = "NOW()" if os.getenv("DATABASE_URL", "").startswith("postgres") else "datetime('now')"
                sql = f"UPDATE users SET birthdays = {P}, updated_at = {ts_func} WHERE phone = {P}"
                c.execute(sql, (bdays, phone))
            send_text(phone, msg.onboarding_birth_hour(lang))
            session["state"] = "ONBOARD_BIRTH_HOUR"; save_session(phone, session)
        else:
            send_text(phone, "❌ 格式不正确。请输入：YYYY-MM-DD（如 1990-05-15）")
        return

    if state == "ONBOARD_BIRTH_HOUR":
        if text_lower in ["跳过", "skip", "langkau"]:
            send_text(phone, msg.onboarding_gender(lang))
            session["state"] = "ONBOARD_GENDER"; save_session(phone, session); return
        birth_hour = None
        chinese_hours = {"子":"23:00","丑":"01:00","寅":"03:00","卯":"05:00","辰":"07:00","巳":"09:00","午":"11:00","未":"13:00","申":"15:00","酉":"17:00","戌":"19:00","亥":"21:00"}
        for ch, hh in chinese_hours.items():
            if ch in text: birth_hour = hh; break
        if not birth_hour:
            time_match = re.match(r'(\d{1,2})[:\s.时](\d{0,2})', text)
            if time_match:
                h = int(time_match.group(1))
                m = int(time_match.group(2)) if time_match.group(2) else 0
                if 0 <= h <= 23 and 0 <= m <= 59: birth_hour = f"{h:02d}:{m:02d}"
        if birth_hour:
            with get_db() as conn:
                c = conn.cursor()
                ts_func = "NOW()" if os.getenv("DATABASE_URL", "").startswith("postgres") else "datetime('now')"
                sql = f"UPDATE users SET birth_hour = {P}, updated_at = {ts_func} WHERE phone = {P}"
                c.execute(sql, (birth_hour, phone))
            send_text(phone, msg.onboarding_gender(lang))
            session["state"] = "ONBOARD_GENDER"; save_session(phone, session)
        else:
            send_text(phone, "❌ 无法识别。请输入 HH:MM 或回复【跳过】。")
        return

    if state == "ONBOARD_GENDER":
        gender = None
        if text in ["1", "2", "3"]: gender = {"1": "male", "2": "female", "3": "unknown"}[text]
        elif text_lower.startswith("m"): gender = "male"
        elif text_lower.startswith("f"): gender = "female"
        elif text_lower.startswith("o") or text_lower.startswith("p"): gender = "unknown"
        if gender:
            with get_db() as conn:
                c = conn.cursor()
                ts_func = "NOW()" if os.getenv("DATABASE_URL", "").startswith("postgres") else "datetime('now')"
                sql = f"UPDATE users SET gender = {P}, updated_at = {ts_func} WHERE phone = {P}"
                c.execute(sql, (gender, phone))
            send_text(phone, msg.onboarding_lucky_number(lang))
            session["state"] = "ONBOARD_LUCKY_NUM"; save_session(phone, session)
        else:
            send_text(phone, msg.invalid_input(lang))
        return

    if state == "ONBOARD_LUCKY_NUM":
        num_match = re.search(r'\d+', text)
        if num_match:
            val = int(num_match.group())
            if 1 <= val <= 999:
                with get_db() as conn:
                    c = conn.cursor()
                    ts_func = "NOW()" if os.getenv("DATABASE_URL", "").startswith("postgres") else "datetime('now')"
                    done_val = "TRUE" if os.getenv("DATABASE_URL", "").startswith("postgres") else "1"
                    sql = f"UPDATE users SET lucky_number = {P}, onboarding_done = {done_val}, updated_at = {ts_func} WHERE phone = {P}"
                    c.execute(sql, (val, phone))
                send_text(phone, msg.onboarding_complete(lang))
                session["state"] = "AWAITING_CATEGORY"; save_session(phone, session)
                return
        send_text(phone, "⚠️ 请输入 1 到 999 之间的数字。")
        return

    if state == "AWAITING_CATEGORY":
        if text in CATEGORIES:
            cat = CATEGORIES[text]
            session["category"] = cat["id"]
            label = cat[f"label_{lang}"] if f"label_{lang}" in cat else cat["label_zh"]
            send_text(phone, msg.category_selected(f"{cat['emoji']} {label}", lang))
            card_back_url = "https://tarot.ethzy.my/assets/card_back_whatsapp.jpg"
            caption = _t("✅ 洗牌完毕，牌列已就绪。", "✅ Deck ready.", "✅ Dek sedia.", lang)
            send_image(phone, card_back_url, caption)
            session["state"] = "AWAITING_SERVICE"; save_session(phone, session)
        else:
            send_text(phone, msg.invalid_input(lang))
        return

    if state == "AWAITING_SERVICE":
        category = session.get("category", "other")
        if any(w in text_lower for w in ["抽卡", "draw", "cabut", "抽"]):
            draw_status = check_daily_draws(phone)
            if not draw_status["allowed"]: send_text(phone, msg.draw_limit_reached(0, 0, lang)); return
            send_text(phone, msg.preparing_draw(category, lang))
            card = draw_single_card(phone, category); record_draw(phone)
            reading = generate_single_reading(card["card_id"], card["orientation"], category, phone, is_pro=(session["tier"] != "free"), language=lang)
            send_image(phone, f"https://tarot.ethzy.my/cards/{card['card_id']}_whatsapp.png", f"🌕 {card['card_id']}\n\n{reading}")
            time.sleep(1.5); send_image(phone, "https://tarot.ethzy.my/assets/card_back_whatsapp.jpg", msg.post_draw_hook(lang))
            return
        if any(w in text_lower for w in ["运势", "fortune", "nasib"]):
            if session["tier"] == "free": send_text(phone, "📈 请先回复【订阅】。"); return
            user = get_or_create_user(phone); bdays = json.loads(user["birthdays"]) if user.get("birthdays") else []
            if not bdays: send_text(phone, "🎂 请先设置生日。"); return
            birthday = bdays[0].get("date") if isinstance(bdays[0], dict) else bdays[0]
            fortune = generate_yearly_fortune(phone, birthday, category, gender=user.get("gender"), lucky_number=user.get("lucky_number"), birth_hour=user.get("birth_hour"))
            summary = [f"📈 *12个月运势*\n"]
            for m in fortune["months"]: summary.append(f"{m['label']}: {'█' * int(m['smoothed_score']/10)} {m['smoothed_score']:.0f}")
            send_text(phone, "\n".join(summary)); return
        if any(w in text_lower for w in ["实体", "real card"]):
            access = check_real_card_access(phone)
            if not access["has_card"]: session["state"] = "AWAITING_PIN"; save_session(phone, session); send_text(phone, msg.pin_prompt(lang)); return
            send_text(phone, msg.real_card_spread_menu(access["available_spreads"], lang))
            session["state"] = "AWAITING_SPREAD_CHOICE"; save_session(phone, session); return

    if state == "AWAITING_PIN":
        if text_lower in ["取消", "cancel"]: session["state"] = "AWAITING_SERVICE"; save_session(phone, session); return
        from pin_manager import activate_pin
        res = activate_pin(text, phone); send_text(phone, res["message"])
        if res["success"]: session["state"]="AWAITING_SERVICE"; save_session(phone, session)
        return

    send_text(phone, msg.return_to_menu(lang))


@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        if mode == 'subscribe' and token == WA_VERIFY_TOKEN: return challenge, 200
        return 'Forbidden', 403

    body = request.get_json()
    print(f"[DEBUG] Raw Webhook Body: {json.dumps(body)}")
    try:
        if not body.get('entry') or not body['entry'][0].get('changes'): return jsonify({"status": "ignored"}), 200
        entry = body['entry'][0]['changes'][0]['value']
        if 'messages' not in entry: return jsonify({"status": "ok"}), 200
        msg_data = entry['messages'][0]; phone = msg_data['from']
        text = msg_data.get('text', {}).get('body', '').strip()
        print(f"[DEBUG] Processing msg from {phone}: {text}")
        if text: process_message(phone, text)
    except Exception as e:
        print(f"[ERROR] Webhook Crash: {e}")
    return jsonify({"status": "ok"}), 200

@app.route('/stripe', methods=['POST'])
def stripe_webhook():
    payload = request.data; sig = request.headers.get('Stripe-Signature')
    try:
        event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
        if event['type'] == 'checkout.session.completed': handle_subscription_created(event['data'])
        elif event['type'] == 'invoice.paid': handle_invoice_paid(event['data'])
        elif event['type'] == 'customer.subscription.deleted': handle_subscription_cancelled(event['data'])
    except: pass
    return jsonify(success=True)

@app.route('/health', methods=['GET'])
def health(): return jsonify({"status": "ok", "service": "mytarot-bot"})

if __name__ == '__main__':
    init_db()
    app.run(port=5000, debug=True, use_reloader=False)

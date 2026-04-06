"""Full stack verification: import every module and run key checks."""
import sys

print("=== Import Tests ===")
try:
    from config import TIERS, CATEGORIES, TIER_ORDER
    print(f"  config.py      OK ({len(TIERS)} tiers, {len(CATEGORIES)} categories)")
except Exception as e:
    print(f"  config.py      FAIL: {e}")
    sys.exit(1)

try:
    from db import get_db, P
    print(f"  db.py          OK (placeholder: {P})")
except Exception as e:
    print(f"  db.py          FAIL: {e}")
    sys.exit(1)

try:
    import json
    scores = json.load(open("data/card_scores.json"))
    print(f"  card_scores    OK ({len(scores)} cards)")
except Exception as e:
    print(f"  card_scores    FAIL: {e}")
    sys.exit(1)

try:
    from fortune_engine import generate_yearly_fortune, draw_single_card
    f = generate_yearly_fortune("test", "2000-01-01", "career")
    assert len(f["months"]) == 12
    f2 = generate_yearly_fortune("test", "2000-01-01", "career")
    assert f["months"][0]["card_id"] == f2["months"][0]["card_id"], "Determinism broken"

    # Profile uniqueness: same birthday, different profile = different fortune
    fa = generate_yearly_fortune("test", "2000-01-01", "career", gender="male", lucky_number=42)
    fb = generate_yearly_fortune("test", "2000-01-01", "career", gender="female", lucky_number=77)
    differs = any(fa["months"][i]["card_id"] != fb["months"][i]["card_id"] for i in range(12))
    assert differs, "Different profiles should produce different curves"
    print(f"  fortune_engine OK (12 months, deterministic, profile-unique)")
except Exception as e:
    print(f"  fortune_engine FAIL: {e}")
    sys.exit(1)

try:
    from subscription_mgr import get_or_create_user, check_daily_draws, record_draw
    user = get_or_create_user("test_phone_123", "zh")
    assert user["tier"] == "free"
    status = check_daily_draws("test_phone_123")
    assert status["allowed"] == True
    record_draw("test_phone_123")
    status2 = check_daily_draws("test_phone_123")
    assert status2["used"] == 1
    print(f"  subscription   OK (user create, draw tracking)")
except Exception as e:
    print(f"  subscription   FAIL: {e}")
    sys.exit(1)

try:
    from referral_manager import generate_referral_code, validate_referral_code
    print(f"  referral       OK (imports clean)")
except Exception as e:
    print(f"  referral       FAIL: {e}")
    sys.exit(1)

try:
    from pin_manager import generate_pins, activate_pin
    pins = generate_pins(3, "TEST-VERIFY")
    assert len(pins) == 3
    result = activate_pin(pins[0], "test_phone_123")
    assert result["success"] == True
    result2 = activate_pin(pins[0], "other_phone_999")
    assert result2["success"] == False
    print(f"  pin_manager    OK (generate, activate, security)")
except Exception as e:
    print(f"  pin_manager    FAIL: {e}")
    sys.exit(1)

try:
    from real_card_mode import parse_card_input, validate_spread, check_real_card_access
    parsed = parse_card_input("15, 42, 7")
    assert parsed["valid"] and len(parsed["cards"]) == 3
    v = validate_spread(parsed["cards"], "three_card")
    assert v["valid"]
    print(f"  real_card_mode OK (parse, validate)")
except Exception as e:
    print(f"  real_card_mode FAIL: {e}")
    sys.exit(1)

try:
    from ai_reading import generate_single_reading
    # Test offline fallback (no API key)
    reading = generate_single_reading("19_the_sun", "upright", "love", "test", False, "zh")
    assert "灵猫" in reading or "太阳" in reading or "Sun" in reading
    print(f"  ai_reading     OK (fallback mode)")
except Exception as e:
    print(f"  ai_reading     FAIL: {e}")
    sys.exit(1)

try:
    import messages as msg
    w = msg.welcome("zh")
    assert "My Tarot" in w
    w_en = msg.welcome("en")
    assert "Welcome" in w_en
    w_ms = msg.welcome("ms")
    assert "Selamat" in w_ms
    # Onboarding messages
    ob = msg.onboarding_birthday("zh")
    assert "出生" in ob
    og = msg.onboarding_gender("en")
    assert "Male" in og
    ol = msg.onboarding_lucky_number("ms")
    assert "Nombor" in ol
    oc = msg.onboarding_complete("zh")
    assert "命运档案" in oc
    print(f"  messages       OK (zh, en, ms + onboarding)")
except Exception as e:
    print(f"  messages       FAIL: {e}")
    sys.exit(1)

try:
    from conversation import app
    print(f"  conversation   OK (Flask app created)")
except Exception as e:
    print(f"  conversation   FAIL: {e}")
    sys.exit(1)

print("\n✅ ALL MODULES VERIFIED — Full stack is operational!")

# Cleanup test data
import os
if os.path.exists("mytarot.db"):
    os.remove("mytarot.db")
    print("  Cleaned up test database.")

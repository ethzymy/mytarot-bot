"""
MyTarot — Subscription Manager
================================
Handles tier management, Stripe integration, daily usage tracking,
and subscription lifecycle (create, upgrade, cancel, webhook).
"""

import stripe
from datetime import datetime, date

from config import TIERS, TIER_ORDER, STRIPE_API_KEY, STRIPE_PRODUCTS
from db import get_db, P
from referral_manager import add_commission

stripe.api_key = STRIPE_API_KEY


def get_or_create_user(phone: str, language: str = "zh") -> dict:
    """Get existing user or create a new free-tier user."""
    with get_db() as conn:
        c = conn.cursor()
        c.execute(f"SELECT * FROM users WHERE phone = {P}", (phone,))
        row = c.fetchone()

        if row:
            if isinstance(row, tuple):
                cols = ["phone", "tier", "birthdays", "birthday_edits",
                        "last_bday_edit", "language", "birth_hour",
                        "gender", "lucky_number", "onboarding_done",
                        "referral_code", "referred_by", "card_activated",
                        "theme", "created_at", "updated_at"]
                return dict(zip(cols, row))
            return dict(row)

        c.execute(f"""
            INSERT INTO users (phone, language) VALUES ({P}, {P})
        """, (phone, language))

    return {
        "phone": phone, "tier": "free", "birthdays": "[]",
        "birthday_edits": 0, "language": language,
        "birth_hour": None, "gender": "unknown",
        "lucky_number": 0, "onboarding_done": False,
        "referral_code": None, "referred_by": None,
        "card_activated": False, "theme": "cat",
    }


def get_user_tier(phone: str) -> str:
    """Get the user's current tier."""
    with get_db() as conn:
        c = conn.cursor()
        c.execute(f"SELECT tier FROM users WHERE phone = {P}", (phone,))
        row = c.fetchone()
        if row:
            return row[0] if isinstance(row, tuple) else row["tier"]
    return "free"


def has_permission(phone: str, min_tier: str) -> bool:
    """Check if user's tier is >= min_tier."""
    user_tier = get_user_tier(phone)
    return TIER_ORDER.get(user_tier, 0) >= TIER_ORDER.get(min_tier, 0)


def check_daily_draws(phone: str) -> dict:
    """
    Check if user has draws remaining today.

    Returns:
        {"allowed": bool, "used": int, "limit": int, "remaining": int}
    """
    tier = get_user_tier(phone)
    limit = TIERS[tier]["daily_draws"]
    today = date.today().isoformat()

    with get_db() as conn:
        c = conn.cursor()
        c.execute(f"SELECT draw_count FROM daily_usage WHERE phone = {P} AND date = {P}",
                  (phone, today))
        row = c.fetchone()
        used = (row[0] if isinstance(row, tuple) else row["draw_count"]) if row else 0

    return {
        "allowed": used < limit,
        "used": used,
        "limit": limit,
        "remaining": max(0, limit - used),
    }


def record_draw(phone: str):
    """Increment today's draw count by 1."""
    today = date.today().isoformat()

    with get_db() as conn:
        c = conn.cursor()
        c.execute(f"SELECT draw_count FROM daily_usage WHERE phone = {P} AND date = {P}",
                  (phone, today))
        if c.fetchone():
            c.execute(f"UPDATE daily_usage SET draw_count = draw_count + 1 WHERE phone = {P} AND date = {P}",
                      (phone, today))
        else:
            c.execute(f"INSERT INTO daily_usage (phone, date, draw_count) VALUES ({P}, {P}, 1)",
                      (phone, today))


def create_checkout_session(phone: str, tier: str, referral_code: str = None,
                            currency: str = "myr") -> str:
    """
    Create a Stripe Checkout session for subscription.

    Returns: Checkout URL string
    """
    price_key = f"{tier}_monthly_{currency}"
    price_id = STRIPE_PRODUCTS.get(price_key)

    if not price_id:
        return None

    metadata = {"phone": phone, "tier": tier}
    if referral_code:
        metadata["referral_code"] = referral_code

    session = stripe.checkout.Session.create(
        mode="subscription",
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        client_reference_id=phone,
        metadata=metadata,
        success_url=f"https://tarot.ethzy.my/success?phone={phone}",
        cancel_url=f"https://tarot.ethzy.my/cancel?phone={phone}",
    )

    return session.url


def create_deck_checkout(phone: str) -> str:
    """Create a one-time payment checkout for physical deck purchase."""
    price_id = STRIPE_PRODUCTS.get("deck_onetime_myr")
    if not price_id:
        return None

    session = stripe.checkout.Session.create(
        mode="payment",
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        client_reference_id=phone,
        metadata={"phone": phone, "product": "physical_deck"},
        success_url=f"https://tarot.ethzy.my/deck-success?phone={phone}",
        cancel_url=f"https://tarot.ethzy.my/cancel?phone={phone}",
    )

    return session.url


def handle_subscription_created(event_data: dict):
    """
    Handle Stripe checkout.session.completed for subscriptions.
    Called from the webhook handler.
    """
    session = event_data["object"]
    phone = session.get("client_reference_id")
    metadata = session.get("metadata", {})
    tier = metadata.get("tier", "pro")
    stripe_sub_id = session.get("subscription")
    referral_code = metadata.get("referral_code")

    if not phone:
        return

    with get_db() as conn:
        c = conn.cursor()

        # Update user tier
        c.execute(f"UPDATE users SET tier = {P}, updated_at = {P} WHERE phone = {P}",
                  (tier, datetime.now().isoformat(), phone))

        # Create subscription record
        c.execute(f"""
            INSERT INTO subscriptions (phone, tier, stripe_sub_id, consecutive_months)
            VALUES ({P}, {P}, {P}, 1)
        """, (phone, tier, stripe_sub_id))

    # Handle referral if a code was provided
    if referral_code:
        from referral_manager import validate_referral_code, record_referral
        result = validate_referral_code(referral_code, phone)
        if result["valid"]:
            record_referral(result["referrer_phone"], phone)


def handle_invoice_paid(event_data: dict):
    """
    Handle invoice.paid for recurring subscription payments.
    This is where we track consecutive months and trigger commissions.
    """
    invoice = event_data["object"]
    stripe_sub_id = invoice.get("subscription")
    amount_paid = invoice.get("amount_paid", 0) / 100  # cents → dollars
    event_id = event_data.get("id", "")

    if not stripe_sub_id:
        return

    with get_db() as conn:
        c = conn.cursor()

        # Find the subscription
        c.execute(f"SELECT phone, tier, consecutive_months FROM subscriptions WHERE stripe_sub_id = {P} AND status = 'active'",
                  (stripe_sub_id,))
        row = c.fetchone()
        if not row:
            return

        phone = row[0] if isinstance(row, tuple) else row["phone"]
        tier = row[1] if isinstance(row, tuple) else row["tier"]
        months = row[2] if isinstance(row, tuple) else row["consecutive_months"]

        # Increment consecutive months
        c.execute(f"UPDATE subscriptions SET consecutive_months = consecutive_months + 1 WHERE stripe_sub_id = {P}",
                  (stripe_sub_id,))

        # Check if referred → trigger commission
        c.execute(f"SELECT referred_by FROM users WHERE phone = {P}", (phone,))
        ref_row = c.fetchone()
        referred_by = (ref_row[0] if isinstance(ref_row, tuple) else ref_row["referred_by"]) if ref_row else None

        if referred_by:
            # Convert amount to MYR for commission calculation
            add_commission(referred_by, phone, amount_paid, event_id)

        # Check deck reward eligibility
        tier_config = TIERS.get(tier, {})
        reward_months = tier_config.get("deck_reward_months", 0)
        if reward_months > 0 and (months + 1) >= reward_months:
            c.execute(f"SELECT deck_redeemed FROM subscriptions WHERE stripe_sub_id = {P}",
                      (stripe_sub_id,))
            dr = c.fetchone()
            redeemed = (dr[0] if isinstance(dr, tuple) else dr["deck_redeemed"]) if dr else False
            if not redeemed:
                c.execute(f"UPDATE subscriptions SET deck_redeemed = 1 WHERE stripe_sub_id = {P}",
                          (stripe_sub_id,))
                # TODO: Send WhatsApp notification about free deck eligibility


def handle_subscription_cancelled(event_data: dict):
    """Handle customer.subscription.deleted — mark subscription as cancelled."""
    sub = event_data["object"]
    stripe_sub_id = sub.get("id")

    if not stripe_sub_id:
        return

    with get_db() as conn:
        c = conn.cursor()

        c.execute(f"SELECT phone FROM subscriptions WHERE stripe_sub_id = {P}", (stripe_sub_id,))
        row = c.fetchone()
        if not row:
            return

        phone = row[0] if isinstance(row, tuple) else row["phone"]

        c.execute(f"""
            UPDATE subscriptions SET status = 'cancelled', cancelled_at = {P}
            WHERE stripe_sub_id = {P}
        """, (datetime.now().isoformat(), stripe_sub_id))

        # Downgrade user to free
        c.execute(f"UPDATE users SET tier = 'free', updated_at = {P} WHERE phone = {P}",
                  (datetime.now().isoformat(), phone))

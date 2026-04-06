"""
MyTarot — Referral Manager
============================
Handles referral code generation, validation, commission tracking,
and balance management for the Affiliate tier.

Only Affiliate users get referral codes and earn commissions.
"""

import secrets
from datetime import datetime

from db import get_db, P


SAFE_CHARS = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
COMMISSION_RATE = 0.10


def generate_referral_code(phone: str, custom_name: str = None) -> dict:
    """
    Create a referral code for an Affiliate user.

    Args:
        phone: Affiliate's WhatsApp number
        custom_name: Optional custom suffix (e.g. "KEAN" → REF-KEAN)

    Returns:
        {"success": bool, "code": str, "message": str}
    """
    with get_db() as conn:
        c = conn.cursor()

        # Check if user already has a code
        c.execute(f"SELECT referral_code FROM users WHERE phone = {P}", (phone,))
        row = c.fetchone()
        if row and (row[0] if isinstance(row, tuple) else row["referral_code"]):
            existing = row[0] if isinstance(row, tuple) else row["referral_code"]
            return {"success": True, "code": existing,
                    "message": f"您已有推荐码：{existing}"}

        # Generate code
        if custom_name:
            code = f"REF-{custom_name.upper().strip()[:12]}"
            c.execute(f"SELECT referral_code FROM users WHERE referral_code = {P}", (code,))
            if c.fetchone():
                return {"success": False, "code": None,
                        "message": f"推荐码 {code} 已被使用，请换一个名称。"}
        else:
            for _ in range(50):
                suffix = ''.join(secrets.choice(SAFE_CHARS) for _ in range(6))
                code = f"REF-{suffix}"
                c.execute(f"SELECT referral_code FROM users WHERE referral_code = {P}", (code,))
                if not c.fetchone():
                    break

        c.execute(f"UPDATE users SET referral_code = {P}, updated_at = {P} WHERE phone = {P}",
                  (code, datetime.now().isoformat(), phone))

    return {"success": True, "code": code,
            "message": f"🎉 推荐码已生成：*{code}*\n分享给朋友，他们订阅时输入即可！"}


def validate_referral_code(code: str, user_phone: str) -> dict:
    """
    Validate a referral code during subscription signup.

    Args:
        code: The referral code entered (e.g. "REF-KEAN")
        user_phone: The new subscriber's phone (to prevent self-referral)

    Returns:
        {"valid": bool, "referrer_phone": str or None, "message": str}
    """
    code = code.upper().strip()
    if not code.startswith("REF-"):
        code = f"REF-{code}"

    with get_db() as conn:
        c = conn.cursor()
        c.execute(f"SELECT phone, tier FROM users WHERE referral_code = {P}", (code,))
        row = c.fetchone()

        if not row:
            return {"valid": False, "referrer_phone": None,
                    "message": "❌ 无效的推荐码，请检查后重试。"}

        referrer_phone = row[0] if isinstance(row, tuple) else row["phone"]
        referrer_tier = row[1] if isinstance(row, tuple) else row["tier"]

        if referrer_phone == user_phone:
            return {"valid": False, "referrer_phone": None,
                    "message": "❌ 不能使用自己的推荐码。"}

        if referrer_tier != "affiliate":
            return {"valid": False, "referrer_phone": None,
                    "message": "❌ 该推荐码的用户不是 Affiliate，无法使用。"}

    return {"valid": True, "referrer_phone": referrer_phone,
            "message": f"✅ 推荐码有效！"}


def record_referral(referrer_phone: str, referred_phone: str):
    """Record the referral relationship in the users table."""
    with get_db() as conn:
        c = conn.cursor()
        c.execute(f"UPDATE users SET referred_by = {P}, updated_at = {P} WHERE phone = {P}",
                  (referrer_phone, datetime.now().isoformat(), referred_phone))


def add_commission(referrer_phone: str, referred_phone: str,
                   payment_amount: float, stripe_event_id: str) -> dict:
    """
    Record a commission when a referred user makes a payment.
    Called from Stripe webhook handler.

    Args:
        referrer_phone: The affiliate who referred this user
        referred_phone: The user who paid
        payment_amount: Amount paid in MYR
        stripe_event_id: Stripe event ID for idempotency

    Returns:
        {"success": bool, "commission": float}
    """
    commission = round(payment_amount * COMMISSION_RATE, 2)

    with get_db() as conn:
        c = conn.cursor()

        # Idempotency: skip if this event was already processed
        c.execute(f"SELECT id FROM referral_commissions WHERE stripe_event_id = {P}",
                  (stripe_event_id,))
        if c.fetchone():
            return {"success": True, "commission": 0, "note": "duplicate event"}

        c.execute(f"""
            INSERT INTO referral_commissions
            (referrer_phone, referred_phone, payment_amount, commission, stripe_event_id)
            VALUES ({P}, {P}, {P}, {P}, {P})
        """, (referrer_phone, referred_phone, payment_amount, commission, stripe_event_id))

    return {"success": True, "commission": commission}


def get_affiliate_balance(phone: str) -> dict:
    """Get an affiliate's commission summary."""
    with get_db() as conn:
        c = conn.cursor()

        c.execute(f"""
            SELECT
                COALESCE(SUM(CASE WHEN status = 'pending' THEN commission ELSE 0 END), 0),
                COALESCE(SUM(CASE WHEN status = 'settled' THEN commission ELSE 0 END), 0),
                COUNT(DISTINCT referred_phone)
            FROM referral_commissions
            WHERE referrer_phone = {P}
        """, (phone,))

        row = c.fetchone()
        pending = row[0]
        settled = row[1]
        referral_count = row[2]

    return {
        "pending_balance": float(pending),
        "total_settled": float(settled),
        "total_referrals": referral_count,
    }


def get_pending_settlements(min_amount: float = 25.0) -> list:
    """Admin: get all affiliates with pending balance >= min_amount."""
    with get_db() as conn:
        c = conn.cursor()
        c.execute(f"""
            SELECT referrer_phone,
                   SUM(commission) as total_pending,
                   COUNT(*) as txn_count
            FROM referral_commissions
            WHERE status = 'pending'
            GROUP BY referrer_phone
            HAVING SUM(commission) >= {P}
            ORDER BY total_pending DESC
        """, (min_amount,))

        results = []
        for row in c.fetchall():
            results.append({
                "phone": row[0],
                "pending": float(row[1]),
                "transactions": row[2],
            })

    return results


def settle_commission(referrer_phone: str, settle_up_to: str = None) -> dict:
    """
    Admin: mark all pending commissions for a referrer as settled.

    Args:
        referrer_phone: The affiliate to settle
        settle_up_to: Optional ISO date string. Only settle commissions before this date.
    """
    now = datetime.now().isoformat()

    with get_db() as conn:
        c = conn.cursor()

        if settle_up_to:
            c.execute(f"""
                UPDATE referral_commissions
                SET status = 'settled', settled_at = {P}
                WHERE referrer_phone = {P} AND status = 'pending' AND payment_date <= {P}
            """, (now, referrer_phone, settle_up_to))
        else:
            c.execute(f"""
                UPDATE referral_commissions
                SET status = 'settled', settled_at = {P}
                WHERE referrer_phone = {P} AND status = 'pending'
            """, (now, referrer_phone))

        affected = c.rowcount

    return {"settled_count": affected, "settled_at": now}


def get_referral_tree(referrer_phone: str) -> list:
    """Admin: get all users referred by a specific affiliate."""
    with get_db() as conn:
        c = conn.cursor()
        c.execute(f"""
            SELECT u.phone, u.tier, u.created_at,
                   s.status as sub_status,
                   COALESCE(SUM(rc.commission), 0) as total_commission
            FROM users u
            LEFT JOIN subscriptions s ON u.phone = s.phone AND s.status = 'active'
            LEFT JOIN referral_commissions rc ON rc.referred_phone = u.phone
                                             AND rc.referrer_phone = {P}
            WHERE u.referred_by = {P}
            GROUP BY u.phone, u.tier, u.created_at, s.status
            ORDER BY u.created_at DESC
        """, (referrer_phone, referrer_phone))

        results = []
        for row in c.fetchall():
            results.append({
                "phone": row[0],
                "tier": row[1],
                "joined": row[2],
                "subscription_status": row[3] or "inactive",
                "total_commission": float(row[4]),
            })

    return results

"""
MyTarot PIN Manager — Physical Card Activation
=================================================
Migrated from standalone version to use shared db.py module.
"""

import secrets
import csv
from datetime import datetime

from db import get_db, P

SAFE_CHARS = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"


def generate_pins(quantity: int, batch_id: str = None) -> list:
    if batch_id is None:
        batch_id = f"BATCH-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    with get_db() as conn:
        c = conn.cursor()
        generated = []
        for _ in range(quantity * 10):
            if len(generated) >= quantity:
                break
            code = ''.join(secrets.choice(SAFE_CHARS) for _ in range(4))
            pin = f"MT-{code}"
            c.execute(f"SELECT pin FROM activation_pins WHERE pin = {P}", (pin,))
            if not c.fetchone():
                c.execute(f"INSERT INTO activation_pins (pin, batch_id) VALUES ({P}, {P})",
                          (pin, batch_id))
                generated.append(pin)

    return generated


def activate_pin(pin: str, phone: str) -> dict:
    pin = pin.upper().strip().replace(" ", "")
    if not pin.startswith("MT-"):
        pin = f"MT-{pin}"

    with get_db() as conn:
        c = conn.cursor()
        c.execute(f"SELECT status, bound_phone FROM activation_pins WHERE pin = {P}", (pin,))
        row = c.fetchone()

        if not row:
            return {"success": False, "message": "❌ 无效的激活码。\n格式：MT-XXXX", "error_code": "INVALID"}

        status = row[0] if isinstance(row, tuple) else row["status"]
        bound = row[1] if isinstance(row, tuple) else row["bound_phone"]

        if status == "activated" and bound != phone:
            return {"success": False, "message": "⚠️ 此激活码已被其他账号使用。", "error_code": "ALREADY_USED"}

        if status == "activated" and bound == phone:
            return {"success": True, "message": "✅ 卡牌已激活！回复【实体牌】进入 Real Card Mode 🃏", "error_code": "ALREADY_ACTIVATED"}

        c.execute(f"""
            UPDATE activation_pins SET status = 'activated', bound_phone = {P}, activated_at = {P}
            WHERE pin = {P}
        """, (phone, datetime.now().isoformat(), pin))

    return {
        "success": True,
        "message": f"🎉 *卡牌激活成功！*\n\n📌 PIN: {pin}\n📱 绑定号码: {phone}\n\n✨ Real Card Mode 已解锁！\n回复【实体牌】开始 🃏"
    }


def has_real_card_access(phone: str) -> bool:
    with get_db() as conn:
        c = conn.cursor()
        c.execute(f"SELECT COUNT(*) FROM activation_pins WHERE bound_phone = {P} AND status = 'activated'", (phone,))
        return c.fetchone()[0] > 0


def export_pins_to_csv(batch_id: str, output_path: str = None) -> str:
    if output_path is None:
        output_path = f"pins_{batch_id}.csv"

    with get_db() as conn:
        c = conn.cursor()
        c.execute(f"SELECT pin FROM activation_pins WHERE batch_id = {P} ORDER BY rowid", (batch_id,))
        pins = c.fetchall()

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["序号", "PIN码", "批次"])
        for i, row in enumerate(pins, 1):
            writer.writerow([i, row[0], batch_id])

    return output_path


def get_batch_stats(batch_id: str = None) -> dict:
    with get_db() as conn:
        c = conn.cursor()
        if batch_id:
            c.execute(f"SELECT COUNT(*) FROM activation_pins WHERE batch_id = {P}", (batch_id,))
            total = c.fetchone()[0]
            c.execute(f"SELECT COUNT(*) FROM activation_pins WHERE batch_id = {P} AND status = 'activated'", (batch_id,))
            activated = c.fetchone()[0]
        else:
            c.execute("SELECT COUNT(*) FROM activation_pins")
            total = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM activation_pins WHERE status = 'activated'")
            activated = c.fetchone()[0]

    return {
        "batch_id": batch_id or "ALL", "total": total,
        "activated": activated, "unused": total - activated,
        "activation_rate": f"{(activated/total*100):.1f}%" if total > 0 else "N/A"
    }

"""
MyTarot — Database Layer
==========================
Handles connection pooling and schema initialization.
Supports SQLite (dev) and PostgreSQL via Supabase (prod)
based on DATABASE_URL format.
"""

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///mytarot.db")

# Detect database type from URL
IS_POSTGRES = DATABASE_URL.startswith("postgres")

if IS_POSTGRES:
    import psycopg2
    import psycopg2.pool
    _pool = None
else:
    _sqlite_path = DATABASE_URL.replace("sqlite:///", "")


def _get_pg_pool():
    global _pool
    if _pool is None:
        _pool = psycopg2.pool.ThreadedConnectionPool(1, 10, DATABASE_URL)
    return _pool


@contextmanager
def get_db():
    """Yield a database connection. Auto-commits on success, rolls back on error."""
    if IS_POSTGRES:
        pool = _get_pg_pool()
        conn = pool.getconn()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            pool.putconn(conn)
    else:
        conn = sqlite3.connect(_sqlite_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def _placeholder(n=1):
    """Return the correct placeholder syntax for the current DB."""
    return "%s" if IS_POSTGRES else "?"


P = _placeholder()  # Use db.P in queries for parameterized values


def init_db():
    """Create all tables if they don't exist."""

    # SQLite-compatible CREATE TABLE statements
    # PostgreSQL equivalents use SERIAL and TIMESTAMP WITH TIME ZONE
    if IS_POSTGRES:
        _init_postgres()
    else:
        _init_sqlite()
    print("[DB] Schema initialized")


def _init_sqlite():
    with get_db() as conn:
        c = conn.cursor()

        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                phone           TEXT PRIMARY KEY,
                tier            TEXT DEFAULT 'free',
                birthdays       TEXT DEFAULT '[]',
                birthday_edits  INTEGER DEFAULT 0,
                last_bday_edit  TEXT,
                language        TEXT DEFAULT 'zh',
                birth_hour      TEXT,
                gender          TEXT DEFAULT 'unknown',
                lucky_number    INTEGER DEFAULT 0,
                onboarding_done INTEGER DEFAULT 0,
                referral_code   TEXT UNIQUE,
                referred_by     TEXT,
                card_activated  INTEGER DEFAULT 0,
                theme           TEXT DEFAULT 'cat',
                created_at      TEXT DEFAULT (datetime('now')),
                updated_at      TEXT DEFAULT (datetime('now'))
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                phone           TEXT REFERENCES users(phone),
                tier            TEXT NOT NULL,
                stripe_sub_id   TEXT,
                status          TEXT DEFAULT 'active',
                started_at      TEXT DEFAULT (datetime('now')),
                cancelled_at    TEXT,
                consecutive_months INTEGER DEFAULT 0,
                deck_redeemed   INTEGER DEFAULT 0
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS referral_commissions (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_phone  TEXT REFERENCES users(phone),
                referred_phone  TEXT REFERENCES users(phone),
                payment_amount  REAL,
                commission      REAL,
                status          TEXT DEFAULT 'pending',
                payment_date    TEXT DEFAULT (datetime('now')),
                settled_at      TEXT,
                stripe_event_id TEXT UNIQUE
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS activation_pins (
                pin             TEXT PRIMARY KEY,
                batch_id        TEXT NOT NULL,
                status          TEXT DEFAULT 'unused',
                bound_phone     TEXT,
                activated_at    TEXT,
                created_at      TEXT DEFAULT (datetime('now'))
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS readings (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                phone           TEXT REFERENCES users(phone),
                reading_type    TEXT,
                category        TEXT,
                cards           TEXT,
                reading_text    TEXT,
                mode            TEXT DEFAULT 'online',
                created_at      TEXT DEFAULT (datetime('now'))
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS daily_usage (
                phone           TEXT,
                date            TEXT,
                draw_count      INTEGER DEFAULT 0,
                birthday_inputs INTEGER DEFAULT 0,
                PRIMARY KEY (phone, date)
            )
        """)

        # Indexes
        c.execute("CREATE INDEX IF NOT EXISTS idx_users_referral ON users(referral_code)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_users_referred ON users(referred_by)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_commissions_referrer ON referral_commissions(referrer_phone, status)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_readings_phone ON readings(phone)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_subs_phone ON subscriptions(phone, status)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_pins_phone ON activation_pins(bound_phone)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_usage_phone ON daily_usage(phone, date)")


def _init_postgres():
    with get_db() as conn:
        c = conn.cursor()

        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                phone           TEXT PRIMARY KEY,
                tier            TEXT DEFAULT 'free',
                birthdays       JSONB DEFAULT '[]',
                birthday_edits  INTEGER DEFAULT 0,
                last_bday_edit  TIMESTAMP,
                language        TEXT DEFAULT 'zh',
                birth_hour      TEXT,
                gender          TEXT DEFAULT 'unknown',
                lucky_number    INTEGER DEFAULT 0,
                onboarding_done BOOLEAN DEFAULT FALSE,
                referral_code   TEXT UNIQUE,
                referred_by     TEXT,
                card_activated  BOOLEAN DEFAULT FALSE,
                theme           TEXT DEFAULT 'cat',
                created_at      TIMESTAMP DEFAULT NOW(),
                updated_at      TIMESTAMP DEFAULT NOW()
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id              SERIAL PRIMARY KEY,
                phone           TEXT REFERENCES users(phone),
                tier            TEXT NOT NULL,
                stripe_sub_id   TEXT,
                status          TEXT DEFAULT 'active',
                started_at      TIMESTAMP DEFAULT NOW(),
                cancelled_at    TIMESTAMP,
                consecutive_months INTEGER DEFAULT 0,
                deck_redeemed   BOOLEAN DEFAULT FALSE
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS referral_commissions (
                id              SERIAL PRIMARY KEY,
                referrer_phone  TEXT REFERENCES users(phone),
                referred_phone  TEXT REFERENCES users(phone),
                payment_amount  DECIMAL(10,2),
                commission      DECIMAL(10,2),
                status          TEXT DEFAULT 'pending',
                payment_date    TIMESTAMP DEFAULT NOW(),
                settled_at      TIMESTAMP,
                stripe_event_id TEXT UNIQUE
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS activation_pins (
                pin             TEXT PRIMARY KEY,
                batch_id        TEXT NOT NULL,
                status          TEXT DEFAULT 'unused',
                bound_phone     TEXT,
                activated_at    TIMESTAMP,
                created_at      TIMESTAMP DEFAULT NOW()
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS readings (
                id              SERIAL PRIMARY KEY,
                phone           TEXT REFERENCES users(phone),
                reading_type    TEXT,
                category        TEXT,
                cards           JSONB,
                reading_text    TEXT,
                mode            TEXT DEFAULT 'online',
                created_at      TIMESTAMP DEFAULT NOW()
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS daily_usage (
                phone           TEXT,
                date            DATE,
                draw_count      INTEGER DEFAULT 0,
                birthday_inputs INTEGER DEFAULT 0,
                PRIMARY KEY (phone, date)
            )
        """)

        c.execute("CREATE INDEX IF NOT EXISTS idx_users_referral ON users(referral_code)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_users_referred ON users(referred_by)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_commissions_referrer ON referral_commissions(referrer_phone, status)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_readings_phone ON readings(phone)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_subs_phone ON subscriptions(phone, status)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_pins_phone ON activation_pins(bound_phone)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_usage_phone ON daily_usage(phone, date)")


# Auto-init on import
init_db()

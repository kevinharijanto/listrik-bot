"""SQLite storage layer for Listrik Bot."""

import sqlite3
import os
from datetime import datetime, timedelta


class Storage:
    def __init__(self, db_path="data/listrik.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self._get_conn()
        c = conn.cursor()

        c.execute("""
            CREATE TABLE IF NOT EXISTS power_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                voltage REAL,
                current REAL,
                power REAL
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS topups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                kwh_added REAL,
                balance_after REAL
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS balance (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                current_kwh REAL DEFAULT 0,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        c.execute("INSERT OR IGNORE INTO balance (id, current_kwh) VALUES (1, 0)")

        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_readings_timestamp 
            ON power_readings(timestamp)
        """)

        conn.commit()
        conn.close()

    # ======================== POWER READINGS ========================

    def save_reading(self, voltage, current, power):
        """Save a power reading."""
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO power_readings (timestamp, voltage, current, power) VALUES (?, ?, ?, ?)",
            (datetime.now().isoformat(), voltage, current, power),
        )
        conn.commit()
        conn.close()

    def get_latest_reading(self):
        """Get the most recent power reading."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM power_readings ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    def get_daily_usage(self, days=7):
        """Calculate average kWh/day over the last N days."""
        conn = self._get_conn()
        since = (datetime.now() - timedelta(days=days)).isoformat()

        rows = conn.execute(
            "SELECT timestamp, power FROM power_readings WHERE timestamp >= ? ORDER BY timestamp ASC",
            (since,),
        ).fetchall()
        conn.close()

        if len(rows) < 2:
            return 0.0

        total_kwh = 0.0
        for i in range(1, len(rows)):
            t0 = datetime.fromisoformat(rows[i - 1]["timestamp"])
            t1 = datetime.fromisoformat(rows[i]["timestamp"])
            dt_hours = (t1 - t0).total_seconds() / 3600.0
            dt_hours = min(dt_hours, 5.0 / 60.0)

            avg_power = (rows[i - 1]["power"] + rows[i]["power"]) / 2.0
            total_kwh += avg_power * dt_hours / 1000.0

        first_ts = datetime.fromisoformat(rows[0]["timestamp"])
        last_ts = datetime.fromisoformat(rows[-1]["timestamp"])
        actual_days = (last_ts - first_ts).total_seconds() / 86400.0

        if actual_days < 0.01:
            return 0.0

        return total_kwh / actual_days

    def get_hourly_usage_today(self):
        """Get kWh usage per hour for today."""
        conn = self._get_conn()
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        rows = conn.execute(
            "SELECT timestamp, power FROM power_readings WHERE timestamp >= ? ORDER BY timestamp ASC",
            (today_start.isoformat(),),
        ).fetchall()
        conn.close()

        if len(rows) < 2:
            return {}

        hourly = {}
        for i in range(1, len(rows)):
            t0 = datetime.fromisoformat(rows[i - 1]["timestamp"])
            t1 = datetime.fromisoformat(rows[i]["timestamp"])
            hour = t1.hour
            dt_hours = (t1 - t0).total_seconds() / 3600.0
            dt_hours = min(dt_hours, 5.0 / 60.0)

            avg_power = (rows[i - 1]["power"] + rows[i]["power"]) / 2.0
            kwh = avg_power * dt_hours / 1000.0

            hourly[hour] = hourly.get(hour, 0.0) + kwh

        return hourly

    def get_monthly_usage(self, year, month):
        """Get total kWh for a specific month."""
        conn = self._get_conn()
        start = datetime(year, month, 1).isoformat()
        if month == 12:
            end = datetime(year + 1, 1, 1).isoformat()
        else:
            end = datetime(year, month + 1, 1).isoformat()

        rows = conn.execute(
            "SELECT timestamp, power FROM power_readings WHERE timestamp >= ? AND timestamp < ? ORDER BY timestamp ASC",
            (start, end),
        ).fetchall()
        conn.close()

        if len(rows) < 2:
            return 0.0

        total_kwh = 0.0
        for i in range(1, len(rows)):
            t0 = datetime.fromisoformat(rows[i - 1]["timestamp"])
            t1 = datetime.fromisoformat(rows[i]["timestamp"])
            dt_hours = (t1 - t0).total_seconds() / 3600.0
            dt_hours = min(dt_hours, 5.0 / 60.0)

            avg_power = (rows[i - 1]["power"] + rows[i]["power"]) / 2.0
            total_kwh += avg_power * dt_hours / 1000.0

        return total_kwh

    def get_monthly_summary(self, months=6):
        """Get usage summary for the last N months."""
        now = datetime.now()
        summary = []
        for i in range(months):
            year = now.year
            month = now.month - i
            while month <= 0:
                month += 12
                year -= 1
            kwh = self.get_monthly_usage(year, month)
            summary.append({"year": year, "month": month, "kwh": kwh})
        return summary

    # ======================== BALANCE ========================

    def get_balance(self):
        """Get current kWh balance."""
        conn = self._get_conn()
        row = conn.execute("SELECT current_kwh, last_updated FROM balance WHERE id = 1").fetchone()
        conn.close()
        return {
            "current_kwh": row["current_kwh"] if row else 0.0,
            "last_updated": row["last_updated"] if row else None,
        }

    def set_balance(self, kwh):
        """Manually set the kWh balance."""
        conn = self._get_conn()
        conn.execute(
            "UPDATE balance SET current_kwh = ?, last_updated = ? WHERE id = 1",
            (kwh, datetime.now().isoformat()),
        )
        conn.commit()
        conn.close()

    def deduct_usage(self, kwh):
        """Subtract kWh from balance. Returns new balance."""
        conn = self._get_conn()
        conn.execute(
            "UPDATE balance SET current_kwh = MAX(0, current_kwh - ?), last_updated = ? WHERE id = 1",
            (kwh, datetime.now().isoformat()),
        )
        conn.commit()
        row = conn.execute("SELECT current_kwh FROM balance WHERE id = 1").fetchone()
        conn.close()
        return row["current_kwh"]

    # ======================== TOP-UPS ========================

    def add_topup(self, kwh):
        """Record a token top-up. Returns new balance."""
        conn = self._get_conn()
        conn.execute(
            "UPDATE balance SET current_kwh = current_kwh + ?, last_updated = ? WHERE id = 1",
            (kwh, datetime.now().isoformat()),
        )
        row = conn.execute("SELECT current_kwh FROM balance WHERE id = 1").fetchone()
        new_balance = row["current_kwh"]
        conn.execute(
            "INSERT INTO topups (timestamp, kwh_added, balance_after) VALUES (?, ?, ?)",
            (datetime.now().isoformat(), kwh, new_balance),
        )
        conn.commit()
        conn.close()
        return new_balance

    def get_topup_history(self, limit=10):
        """Get recent top-up history."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM topups ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # ======================== STATS ========================

    def get_reading_count(self):
        """Get total number of readings."""
        conn = self._get_conn()
        row = conn.execute("SELECT COUNT(*) as cnt FROM power_readings").fetchone()
        conn.close()
        return row["cnt"]

    def get_first_reading_date(self):
        """Get the timestamp of the first reading."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT timestamp FROM power_readings ORDER BY timestamp ASC LIMIT 1"
        ).fetchone()
        conn.close()
        return row["timestamp"] if row else None

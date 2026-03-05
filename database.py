# database.py
from __future__ import annotations
import sqlite3
from typing import List, Tuple, Optional, Dict, Any

DB = "sensor.db"


def init_db() -> None:
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    # database.py (inside init_db)
    cur.execute("""
                CREATE TABLE IF NOT EXISTS template_meta
                (
                    template_id
                    INTEGER
                    PRIMARY
                    KEY,
                    name
                    TEXT
                    NOT
                    NULL,
                    unit
                    TEXT,
                    scale
                    REAL
                    DEFAULT
                    1.0
                )
                """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS measurements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts DATETIME DEFAULT CURRENT_TIMESTAMP,
        device_id TEXT NOT NULL,
        code INTEGER NOT NULL,
        value REAL NOT NULL,
        flag INTEGER
    )
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_measurements_device_code_ts
    ON measurements(device_id, code, ts)
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts DATETIME DEFAULT CURRENT_TIMESTAMP,
        device_id TEXT NOT NULL,
        template_id INTEGER NOT NULL
    )
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_templates_device_ts
    ON templates(device_id, ts)
    """)

    conn.commit()
    conn.close()


def insert_measurement(device_id: str, code: int, value: float, flag: int | None = None) -> None:
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO measurements(device_id, code, value, flag) VALUES (?, ?, ?, ?)",
        (device_id, code, value, flag),
    )
    conn.commit()
    conn.close()


def replace_templates(device_id: str, template_ids: List[int]) -> None:
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("DELETE FROM templates WHERE device_id = ?", (device_id,))
    cur.executemany(
        "INSERT INTO templates(device_id, template_id) VALUES (?, ?)",
        [(device_id, t) for t in template_ids],
    )
    conn.commit()
    conn.close()


def get_latest_measurements(limit: int = 50) -> List[Tuple]:
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("""
    SELECT ts, device_id, code, value, flag
    FROM measurements
    ORDER BY id DESC
    LIMIT ?
    """, (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_latest_by_code(device_id: str) -> List[Tuple]:
    """
    Return latest row per code for a device.
    """
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("""
    SELECT m1.ts, m1.device_id, m1.code, m1.value, m1.flag
    FROM measurements m1
    JOIN (
        SELECT code, MAX(id) AS max_id
        FROM measurements
        WHERE device_id = ?
        GROUP BY code
    ) m2
    ON m1.id = m2.max_id
    ORDER BY m1.code ASC
    """, (device_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_devices() -> List[str]:
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT device_id FROM measurements ORDER BY device_id")
    rows = [r[0] for r in cur.fetchall()]
    conn.close()
    return rows
def upsert_template_meta(rows):
    # rows: list of (template_id, name, unit, scale)
    import sqlite3
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.executemany("""
    INSERT INTO template_meta (template_id, name, unit, scale)
    VALUES (?, ?, ?, ?)
    ON CONFLICT(template_id) DO UPDATE SET
      name=excluded.name,
      unit=excluded.unit,
      scale=excluded.scale
    """, rows)
    conn.commit()
    conn.close()

def get_template_meta_map():
    import sqlite3
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT template_id, name, unit, scale FROM template_meta")
    rows = cur.fetchall()
    conn.close()
    return {tid: {"name": n, "unit": u, "scale": s} for tid, n, u, s in rows}
def get_templates_for_device(device_id: str) -> List[int]:
    """
    Return template_id list for this device in the same order as received in 1001.
    We rely on AUTOINCREMENT 'id' to preserve insertion order in replace_templates().
    """
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("""
        SELECT template_id
        FROM templates
        WHERE device_id = ?
        ORDER BY id ASC
    """, (device_id,))
    rows = [r[0] for r in cur.fetchall()]
    conn.close()
    return rows
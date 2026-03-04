import sqlite3

DB = "sensor.db"

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS sensor_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device TEXT,
        temperature REAL,
        humidity REAL,
        ph REAL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()


def insert_data(device, temperature, humidity, ph):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute(
        "INSERT INTO sensor_data (device,temperature,humidity,ph) VALUES (?,?,?,?)",
        (device, temperature, humidity, ph),
    )

    conn.commit()
    conn.close()


def get_latest():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    SELECT device,temperature,humidity,ph,timestamp
    FROM sensor_data
    ORDER BY id DESC
    LIMIT 20
    """)

    rows = c.fetchall()
    conn.close()

    return rows
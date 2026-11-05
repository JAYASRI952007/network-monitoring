import sqlite3
from datetime import datetime
import config
def init_db():
    """
    Creates the database and tables if they don't already exist.
    Safe to call every time the app starts.
    """
    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS status_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_name TEXT NOT NULL,
            ip TEXT NOT NULL,
            status TEXT NOT NULL,
            response_time_ms REAL,
            packet_loss_percent REAL,
            checked_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_name TEXT NOT NULL,
            ip TEXT NOT NULL,
            went_down_at TEXT NOT NULL,
            recovered_at TEXT,
            duration_seconds REAL
        )
    """)

    conn.commit()
    conn.close()
def log_status(device_name, ip, status, response_time_ms, packet_loss_percent):
    """
    Inserts one row into status_log for every monitoring check.
    """
    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO status_log (device_name, ip, status, response_time_ms, packet_loss_percent, checked_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (device_name, ip, status, response_time_ms, packet_loss_percent, datetime.now().isoformat()))

    conn.commit()
    conn.close()

def open_incident(device_name, ip):
    """
    Called when a device transitions from UP to DOWN.
    Creates a new incident row with no recovery time yet.
    """
    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO incidents (device_name, ip, went_down_at, recovered_at, duration_seconds)
        VALUES (?, ?, ?, NULL, NULL)
    """, (device_name, ip, datetime.now().isoformat()))

    conn.commit()
    conn.close()


def close_incident(device_name, ip):
    """
    Called when a device transitions from DOWN back to UP.
    Finds the most recent open incident for this device and fills in recovery info.
    """
    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, went_down_at FROM incidents
        WHERE device_name = ? AND ip = ? AND recovered_at IS NULL
        ORDER BY id DESC LIMIT 1
    """, (device_name, ip))

    row = cursor.fetchone()
    if row:
        incident_id, went_down_at = row
        recovered_at = datetime.now()
        duration = (recovered_at - datetime.fromisoformat(went_down_at)).total_seconds()

        cursor.execute("""
            UPDATE incidents
            SET recovered_at = ?, duration_seconds = ?
            WHERE id = ?
        """, (recovered_at.isoformat(), duration, incident_id))

    conn.commit()
    conn.close()
    
if __name__ == "__main__":
    init_db()
    log_status("Test Device", "1.2.3.4", "UP", 25.5, 0.0)
    open_incident("Test Device 2", "5.6.7.8")
    print("Database initialized and test rows inserted. Check monitor.db")
import sqlite3
import os
import shutil
import uuid
from datetime import datetime

DB_FILE = "storage.db"
INCOMING_DIR = "incoming_logs"
ARCHIVE_DIR = "raw_archive"

def get_conn():
    os.makedirs(INCOMING_DIR, exist_ok=True)
    os.makedirs(ARCHIVE_DIR, exist_ok=True)

    conn = sqlite3.connect(DB_FILE, check_same_thread=False, timeout=20)
    conn.execute("PRAGMA journal_mode=WAL;")

    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS log_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                log_id TEXT,
                source TEXT,
                event_type TEXT,
                event_time TEXT,
                details TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS normalized_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uuid TEXT,
                ts TEXT,
                source TEXT,
                raw TEXT,
                ocsf_class TEXT,
                fields TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS unknown_dlq (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uuid TEXT,
                ts TEXT,
                source TEXT,
                raw TEXT,
                status TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS failed_dlq (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uuid TEXT,
                ts TEXT,
                source TEXT,
                raw TEXT,
                reason TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS draft_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_id TEXT,
                source TEXT,
                regex TEXT,
                mapping TEXT,
                ocsf_class TEXT,
                status TEXT,
                created_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS approved_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_id TEXT,
                source TEXT,
                regex TEXT,
                mapping TEXT,
                ocsf_class TEXT,
                approved_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ingestion_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                log_uuid TEXT,
                message TEXT,
                ts TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ai_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                log_uuid TEXT,
                message TEXT,
                ts TEXT
            )
        """)
        
        # Migration: Add 'raw' column to normalized_logs if it doesn't exist
        try:
            conn.execute("ALTER TABLE normalized_logs ADD COLUMN raw TEXT")
        except sqlite3.OperationalError:
            pass # Column already exists
            
    return conn

def log_ingestion_activity(conn, log_uuid, message):
    ts = datetime.now().isoformat()
    with conn:
        conn.execute("INSERT INTO ingestion_activity (log_uuid, message, ts) VALUES (?, ?, ?)", (log_uuid, message, ts))

def log_ai_activity(conn, log_uuid, message):
    ts = datetime.now().isoformat()
    with conn:
        conn.execute("INSERT INTO ai_activity (log_uuid, message, ts) VALUES (?, ?, ?)", (log_uuid, message, ts))

def log_event(conn, log_id, source, event_type, details=""):
    event_time = datetime.now().isoformat()
    
    with conn:
        conn.execute(
            "INSERT INTO log_events (log_id, source, event_type, event_time, details) VALUES (?, ?, ?, ?, ?)",
            (log_id, source, event_type, event_time, details)
        )

def archive_raw(source_file, log_id):
    filename = os.path.basename(source_file)
    archive_name = f"{log_id}_{filename}"
    destination = os.path.join(ARCHIVE_DIR, archive_name)
    
    shutil.copy2(source_file, destination)
    return destination

def archive_raw_text(raw_text, log_id):
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    archive_name = f"{log_id}_raw.log"
    destination = os.path.join(ARCHIVE_DIR, archive_name)
    with open(destination, "w", encoding="utf-8") as f:
        f.write(raw_text)
    return destination

def process_logs():
    conn = get_conn()
    new_events = []

    for filename in os.listdir(INCOMING_DIR):
        source_file = os.path.join(INCOMING_DIR, filename)
        
        if not os.path.isfile(source_file):
            continue

        # Generate a new UUID for every new file
        log_id = str(uuid.uuid4())
        source = "incoming_logs"

        # RECEIVED
        log_event(conn, log_id, source, "RECEIVED", f"Log received: {filename}")
        new_events.append((log_id, "RECEIVED", filename))

        # ARCHIVE ORIGINAL
        archive_path = archive_raw(source_file, log_id)

        # ARCHIVED
        log_event(conn, log_id, source, "ARCHIVED", f"Original log preserved at {archive_path}")
        new_events.append((log_id, "ARCHIVED", archive_path))

        # Remove from incoming queue
        os.remove(source_file)

        print(f"New log stored: {filename}")
        print(f"UUID: {log_id}\n")

    conn.close()
    return new_events

if __name__ == "__main__":
    events = process_logs()
    
    if not events:
        print("No new logs to process.")
    else:
        print("\nNEW LOG EVENTS\n")
        for event in events:
            print(event)
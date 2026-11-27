import json
import sqlite3
import os
from datetime import datetime

class StateIO:
    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.state_db = os.path.join(base_dir, "state.db")
        self.event_log = os.path.join(base_dir, "event_log.jsonl")
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.state_db) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS state (key TEXT PRIMARY KEY, value TEXT, timestamp TEXT)")

    def save_state(self, key, value):
        with sqlite3.connect(self.state_db) as conn:
            conn.execute("INSERT OR REPLACE INTO state VALUES (?, ?, ?)", 
                         (key, json.dumps(value), datetime.utcnow().isoformat()))

    def load_state(self, key):
        with sqlite3.connect(self.state_db) as conn:
            row = conn.execute("SELECT value FROM state WHERE key=?", (key,)).fetchone()
            return json.loads(row[0]) if row else None

    def log_event(self, event_type, data):
        with open(self.event_log, "a") as f:
            f.write(json.dumps({"timestamp": datetime.utcnow().isoformat(), "type": event_type, "data": data}) + "\n")

import sqlite3

DB_NAME = "requests.db"

def initialize_database():
    """Initializes the SQLite database with the requests table."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_body TEXT NOT NULL,
        summary TEXT,
        response TEXT,
        processed_at TIMESTAMP DEFAULT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()
    print(f"Database '{DB_NAME}' initialized successfully with 'requests' table.")

if __name__ == "__main__":
    initialize_database()

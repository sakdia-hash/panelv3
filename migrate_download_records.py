import sqlite3
from datetime import datetime

def migrate_records():
    try:
        conn = sqlite3.connect('sql_app.db')
        cursor = conn.cursor()
        
        # Create download_records table
        print("Creating download_records table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS download_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            start_date DATE,
            end_date DATE,
            count INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(employee_id) REFERENCES employees(id)
        )
        """)
        
        # Optional: Migrate existing total_downloads to a record (so data isn't "lost" from view)
        # We'll assign it to today's date for simplicity
        print("Migrating legacy data...")
        cursor.execute("SELECT id, total_downloads FROM employees WHERE total_downloads > 0")
        rows = cursor.fetchall()
        today = datetime.now().date().isoformat()
        
        for emp_id, total in rows:
            cursor.execute("""
            INSERT INTO download_records (employee_id, start_date, end_date, count)
            VALUES (?, ?, ?, ?)
            """, (emp_id, today, today, total))
            
        conn.commit()
        print("Migration successful.")
        conn.close()
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate_records()

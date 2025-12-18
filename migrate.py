import sqlite3

def migrate():
    try:
        conn = sqlite3.connect('sql_app.db')
        cursor = conn.cursor()
        
        # Check if column exists
        cursor.execute("PRAGMA table_info(employees)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'account_quota' not in columns:
            print("Migrating: Adding account_quota to employees...")
            cursor.execute("ALTER TABLE employees ADD COLUMN account_quota INTEGER DEFAULT 0")
            conn.commit()
            print("Migration successful: account_quota added.")
        else:
            print("Column account_quota already exists.")
            
        conn.close()
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate()

import sqlite3

def migrate_downloads():
    try:
        conn = sqlite3.connect('sql_app.db')
        cursor = conn.cursor()
        
        # Check if column exists
        cursor.execute("PRAGMA table_info(employees)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'total_downloads' not in columns:
            print("Migrating: Adding total_downloads to employees...")
            cursor.execute("ALTER TABLE employees ADD COLUMN total_downloads INTEGER DEFAULT 0")
            conn.commit()
            print("Migration successful.")
        else:
            print("Column total_downloads already exists.")
            
        conn.close()
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate_downloads()

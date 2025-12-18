import sqlite3

def migrate():
    try:
        conn = sqlite3.connect("sql_app.db")
        cursor = conn.cursor()
        
        # Check if column exists
        cursor.execute("PRAGMA table_info(employees)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if "visible_password" not in columns:
            print("Adding visible_password column...")
            cursor.execute("ALTER TABLE employees ADD COLUMN visible_password TEXT DEFAULT ''")
            conn.commit()
            print("Migration successful.")
        else:
            print("Column already exists.")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    migrate()

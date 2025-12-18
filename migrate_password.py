import sqlite3

def migrate_password():
    try:
        conn = sqlite3.connect('sql_app.db')
        cursor = conn.cursor()
        
        # Check if column exists
        cursor.execute("PRAGMA table_info(instagram_accounts)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'password' not in columns:
            print("Migrating: Adding password to instagram_accounts...")
            cursor.execute("ALTER TABLE instagram_accounts ADD COLUMN password VARCHAR")
            conn.commit()
            print("Migration successful: password added.")
        else:
            print("Column password already exists.")
            
        conn.close()
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate_password()

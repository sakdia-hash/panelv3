import sqlite3

def cleanup():
    try:
        conn = sqlite3.connect('sql_app.db')
        cursor = conn.cursor()
        
        print("Checking for orphaned users...")
        
        # Find users with role 'employee' who don't have an entry in 'employees' table
        query = """
        SELECT id, username FROM users 
        WHERE role = 'employee' 
        AND id NOT IN (SELECT user_id FROM employees)
        """
        
        cursor.execute(query)
        orphans = cursor.fetchall()
        
        if orphans:
            print(f"Found {len(orphans)} orphaned users: {[o[1] for o in orphans]}")
            ids_to_delete = [o[0] for o in orphans]
            
            # Delete them
            cursor.executemany("DELETE FROM users WHERE id = ?", [(i,) for i in ids_to_delete])
            conn.commit()
            print("Orphaned users deleted successfully.")
        else:
            print("No orphaned users found. System is clean.")
            
        conn.close()
    except Exception as e:
        print(f"Cleanup failed: {e}")

if __name__ == "__main__":
    cleanup()

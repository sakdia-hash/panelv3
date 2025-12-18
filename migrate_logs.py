from database import SessionLocal, engine
import models
from sqlalchemy import text

# Drop and recreate audit_logs to ensure schema update
try:
    with engine.connect() as con:
        # Check if table exists (optional, but dropping is harsh if we wanted to keep logs. 
        # Since it's new, drop is fine. If it didn't exist, ignore error.)
        con.execute(text("DROP TABLE IF EXISTS audit_logs"))
        print("Dropped audit_logs table (if it existed).")
except Exception as e:
    print(e)
    
models.Base.metadata.create_all(bind=engine)

print("Tables ensured. audit_logs created.")

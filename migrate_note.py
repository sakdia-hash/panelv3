from database import SessionLocal, engine
import models
from sqlalchemy import text

# Drop and recreate admin_notes to ensure schema update
try:
    with engine.connect() as con:
        con.execute(text("DROP TABLE IF EXISTS admin_notes"))
        print("Dropped admin_notes table.")
except Exception as e:
    print(e)
    
models.Base.metadata.create_all(bind=engine)

print("Tables ensured. admin_notes recreated.")

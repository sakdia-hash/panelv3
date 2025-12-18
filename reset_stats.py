from database import SessionLocal, engine
import models
from sqlalchemy import text

db = SessionLocal()

try:
    # Delete all download records
    num_downloads = db.query(models.DownloadRecord).delete()
    print(f"Deleted {num_downloads} download records.")

    # Delete all daily reports
    num_reports = db.query(models.DailyReport).delete()
    print(f"Deleted {num_reports} daily reports.")

    # Reset auto-increment counters (sqlite specific) if needed, but not strictly necessary for functionality.
    
    db.commit()
    print("Statistics data reset successfully.")

except Exception as e:
    print(f"Error: {e}")
    db.rollback()
finally:
    db.close()

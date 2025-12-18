
from .database import SessionLocal, engine, Base
from . import models
from .auth import get_password_hash
import os
from dotenv import load_dotenv

load_dotenv()

def seed_db():
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    # Check if admin exists
    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
    
    existing_admin = db.query(models.User).filter(models.User.username == admin_username).first()
    
    if not existing_admin:
        print(f"Creating admin user: {admin_username}")
        hashed_password = get_password_hash(admin_password)
        admin_user = models.User(
            username=admin_username,
            password_hash=hashed_password,
            role="admin"
        )
        db.add(admin_user)
        db.commit()
    else:
        print("Admin user already exists. Resetting password...")
        hashed_password = get_password_hash(admin_password)
        existing_admin.password_hash = hashed_password
        db.commit()
        print(f"Admin password reset to: {admin_password}")
        
    db.close()

if __name__ == "__main__":
    seed_db()

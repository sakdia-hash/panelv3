
from database import SessionLocal
import models
from auth import verify_password, get_password_hash

db = SessionLocal()
user = db.query(models.User).filter(models.User.username == "admin").first()

if not user:
    print("❌ Admin user NOT FOUND in database!")
else:
    print(f"✅ Admin user FOUND. Role: {user.role}")
    print(f"Stored Hash: {user.password_hash}")
    
    test_pass = "admin123"
    is_valid = verify_password(test_pass, user.password_hash)
    
    if is_valid:
        print(f"✅ Password '{test_pass}' is MATCHING!")
    else:
        print(f"❌ Password '{test_pass}' is NOT MATCHING!")
        
        # Force update to be sure
        print("🔄 Force updating password to 'admin123'...")
        new_hash = get_password_hash("admin123")
        user.password_hash = new_hash
        db.commit()
        print("✅ Password updated. Try logging in again.")

db.close()

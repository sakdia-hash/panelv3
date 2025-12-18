from database import SessionLocal
import models
import sys

def debug_list():
    db = SessionLocal()
    try:
        print("Querying employees...")
        emps = db.query(models.Employee).all()
        print(f"Found {len(emps)} employees.")
        
        for e in emps:
            print(f"Checking Employee ID: {e.id}")
            print(f" - Full Name: {e.full_name}")
            
            # Check User
            try:
                u = e.user
                print(f" - User: {u}")
                if u:
                    print(f" - Username: {u.username}")
                else:
                    print(" - User object is None")
            except Exception as ex:
                print(f" !!! Error accessing user: {ex}")

            # Check Quota
            try:
                q = e.account_quota
                print(f" - Quota: {q}")
            except Exception as ex:
                print(f" !!! Error accessing quota: {ex}")

            # Check Assigned Accounts
            try:
                accs = e.assigned_accounts
                print(f" - Assigned Accounts Type: {type(accs)}")
                print(f" - Count: {len(accs)}")
            except Exception as ex:
                print(f" !!! Error accessing assigned_accounts: {ex}")

    except Exception as e:
        print(f"CRITICAL FAILURE: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    debug_list()

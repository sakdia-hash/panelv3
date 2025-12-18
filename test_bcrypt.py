
try:
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    print(f"Hash: {pwd_context.hash('test')}")
    print("Passlib bcrypt OK")
except Exception as e:
    print(f"Passlib Error: {e}")

try:
    import bcrypt
    print("Bcrypt import OK")
    hashed = bcrypt.hashpw(b"test", bcrypt.gensalt())
    print(f"Bcrypt native: {hashed}")
except Exception as e:
    print(f"Bcrypt native Error: {e}")

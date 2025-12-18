from .database import engine
from . import models

def migrate():
    print("Running migrations...")
    models.Base.metadata.create_all(bind=engine)
    print("Migrations complete.")

if __name__ == "__main__":
    migrate()

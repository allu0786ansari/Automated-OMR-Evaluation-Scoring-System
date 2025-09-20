# backend/init_db.py
"""
Utility script to create all tables in the MySQL database.
Run: python backend/init_db.py
"""
from backend.db.session import engine, Base
from backend.db import models  # import models so metadata is registered


def init_db():
    print("Creating all tables in the database...")
    Base.metadata.create_all(bind=engine)
    print("✅ Done! Tables created.")


if __name__ == "__main__":
    init_db()

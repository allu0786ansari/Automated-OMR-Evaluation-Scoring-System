from .session import engine, Base, SessionLocal
from . import models
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def init_db():
    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Create default admin user if not exists
    db = SessionLocal()
    admin_user = db.query(models.User).filter(models.User.username == "admin").first()

    if not admin_user:
        hashed_pw = pwd_context.hash("admin")
        admin = models.User(username="admin", hashed_password=hashed_pw, role="admin")
        db.add(admin)
        db.commit()
        print("✅ Default admin user created (username=admin, password=admin)")
    else:
        print("ℹ️ Admin user already exists")

    db.close()

if __name__ == "__main__":
    init_db()

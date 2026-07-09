from sqlalchemy.orm import Session
from app.db.models.user import User
from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.db.versioning import live_filter, mark_created

class UserRepository:
    def get_db(self) -> Session:
        return SessionLocal()

    def get_user_by_email(self, email: str) -> User | None:
        db = self.get_db()
        try:
            return db.query(User).filter(User.email == email, *live_filter(User)).first()
        finally:
            db.close()

    def get_user_by_id(self, user_id: int) -> User | None:
        db = self.get_db()
        try:
            return db.query(User).filter(User.id == user_id, *live_filter(User)).first()
        finally:
            db.close()

    def has_any_users(self) -> bool:
        db = self.get_db()
        try:
            return db.query(User).filter(*live_filter(User)).first() is not None
        finally:
            db.close()

    def create_user(
        self,
        email: str,
        password: str,
        full_name: str = None,
        role: str = None,
        is_superuser: bool = False,
        audit_user=None,
    ) -> User:
        db = self.get_db()
        try:
            hashed_password = get_password_hash(password)
            db_user = User(
                email=email,
                role=role,
                hashed_password=hashed_password,
                full_name=full_name,
                is_active=True,
                is_superuser=is_superuser,
            )
            mark_created(db_user, audit_user)
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
            return db_user
        finally:
            db.close()


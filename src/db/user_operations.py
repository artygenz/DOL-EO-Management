from sqlalchemy.orm import Session
from src.models.user import User
from src.core.auth import hash_password, verify_password
from typing import Optional

def create_user_with_password(
    db: Session,
    name: str,
    email: str,
    password: str,
    role: str = "executor",
    org_role: Optional[str] = None
) -> User:
    """Create a new user with hashed password"""
    hashed_password = hash_password(password)
    
    user = User(
        name=name,
        email=email,
        password_hash=hashed_password,
        role=role,
        org_role=org_role
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Authenticate a user with email and password"""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None
    
    if not verify_password(password, user.password_hash):
        return None
    
    return user

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email"""
    return db.query(User).filter(User.email == email).first()

def update_user_password(db: Session, user_id: str, new_password: str) -> bool:
    """Update user password"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    
    user.password_hash = hash_password(new_password)
    db.commit()
    return True

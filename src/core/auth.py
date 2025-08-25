import jwt
import bcrypt
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from src.core.settings import settings

# JWT Configuration
SECRET_KEY = settings.JWT_SECRET or "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def hash_token(token: str) -> str:
    """Create a hash of the token for blacklisting"""
    return hashlib.sha256(token.encode()).hexdigest()

def verify_token(token: str) -> Optional[dict]:
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None

def blacklist_token(token: str, user_id: str) -> bool:
    """Add a token to the blacklist"""
    try:
        from src.db.session import SessionLocal
        from src.models.token_blacklist import TokenBlacklist
        
        # Decode token to get expiration
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        expires_at = datetime.fromtimestamp(payload.get("exp", 0))
        
        # Create blacklist entry
        db = SessionLocal()
        blacklist_entry = TokenBlacklist(
            token_hash=hash_token(token),
            user_id=user_id,
            expires_at=expires_at
        )
        db.add(blacklist_entry)
        db.commit()
        db.close()
        return True
    except Exception as e:
        print(f"Error blacklisting token: {e}")
        return False

def is_token_blacklisted(token: str) -> bool:
    """Check if a token is blacklisted"""
    try:
        from src.db.session import SessionLocal
        from src.models.token_blacklist import TokenBlacklist
        
        token_hash = hash_token(token)
        db = SessionLocal()
        
        # Check if token is blacklisted
        blacklisted = db.query(TokenBlacklist).filter(
            TokenBlacklist.token_hash == token_hash
        ).first()
        
        db.close()
        return blacklisted is not None
    except Exception as e:
        print(f"Error checking token blacklist: {e}")
        return False

import re
import secrets
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple
from config import (
    JWT_SECRET_KEY, 
    JWT_ALGORITHM, 
    JWT_ACCESS_TOKEN_EXPIRE_HOURS, 
    JWT_REMEMBER_ME_EXPIRE_DAYS
)

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
VALID_ORG_TYPES = {"College", "University", "School", "Company", "Other"}
VALID_LANGUAGES = {"en", "ta"}

def hash_password(plain_password: str) -> str:
    """Hashes a plain-text password securely using bcrypt with auto-generated salt."""
    if not plain_password:
        raise ValueError("Password cannot be empty")
    salt = bcrypt.gensalt(rounds=12)
    hashed_bytes = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed_bytes.decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies that a plain password matches the bcrypt hashed password."""
    if not plain_password or not hashed_password:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception as e:
        print(f"[AuthService] Password verification error: {e}")
        return False

def create_access_token(user_id: str, email: str, name: str, remember_me: bool = False) -> Tuple[str, datetime]:
    """Generates a cryptographically signed JWT access token."""
    now = datetime.now(timezone.utc)
    if remember_me:
        expires_delta = timedelta(days=JWT_REMEMBER_ME_EXPIRE_DAYS)
    else:
        expires_delta = timedelta(hours=JWT_ACCESS_TOKEN_EXPIRE_HOURS)
    
    expire = now + expires_delta
    payload = {
        "sub": user_id,
        "email": email,
        "name": name,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp())
    }
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token, expire

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decodes and cryptographically validates a JWT access token."""
    if not token:
        return None
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        print("[AuthService] Token expired")
        return None
    except jwt.PyJWTError as e:
        print(f"[AuthService] Invalid token: {e}")
        return None

def validate_registration_input(
    name: str,
    email: str,
    password: str,
    confirm_password: Optional[str] = None,
    org_type: Optional[str] = "College",
    preferred_language: Optional[str] = "en"
) -> Tuple[bool, Optional[str]]:
    """Validates registration input fields according to system constraints."""
    if not name or len(name.strip()) < 2:
        return False, "Full name must be at least 2 characters long."
    
    if not email or not EMAIL_REGEX.match(email.strip()):
        return False, "Please enter a valid email address (e.g., student@college.edu)."
    
    if not password or len(password) < 6:
        return False, "Password must be at least 6 characters long."
    
    if confirm_password is not None and password != confirm_password:
        return False, "Passwords do not match. Please verify your confirm password."
    
    if org_type and org_type not in VALID_ORG_TYPES:
        return False, f"Invalid organization type '{org_type}'. Must be one of: {', '.join(sorted(VALID_ORG_TYPES))}."
    
    if preferred_language and preferred_language not in VALID_LANGUAGES:
        return False, f"Invalid preferred language '{preferred_language}'. Must be 'en' (English) or 'ta' (Tamil)."
    
    return True, None

def generate_password_reset_token() -> str:
    """Generates a secure random 6-character alphanumeric reset code."""
    # We generate a user-friendly 6-digit verification code
    return "".join(secrets.choice("0123456789") for _ in range(6))

"""
Security Module - ISO 27001 Compliant Authentication
PT BESTPROFIT FUTURES SURABAYA
"""

import os, re, secrets, logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Tuple
from passlib.context import CryptContext
from jose import jwt

# ============================================
# PASSWORD HASHING
# ============================================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# ============================================
# JWT CONFIGURATION
# ============================================
JWT_SECRET = os.getenv("JWT_SECRET", secrets.token_urlsafe(64))
JWT_ALGORITHM = "HS256"

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=1))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

def create_temp_token(username: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=10)
    return jwt.encode(
        {"sub": username, "exp": expire, "type": "temp", "requires_password_change": True},
        JWT_SECRET, algorithm=JWT_ALGORITHM
    )

def decode_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

# ============================================
# PASSWORD POLICY
# ============================================
def validate_password_strength(password: str, username: str = None) -> Tuple[bool, str]:
    errors = []
    if len(password) < 8: errors.append("Password minimal 8 karakter")
    if not re.search(r"[A-Z]", password): errors.append("Harus mengandung huruf besar (A-Z)")
    if not re.search(r"[a-z]", password): errors.append("Harus mengandung huruf kecil (a-z)")
    if not re.search(r"[0-9]", password): errors.append("Harus mengandung angka (0-9)")
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", password): errors.append("Harus mengandung karakter spesial")
    if username and username.lower() in password.lower(): errors.append("Password tidak boleh mengandung username")
    return (len(errors) == 0, "; ".join(errors))

def get_password_strength_score(password: str) -> dict:
    length = len(password)
    score = 0
    if length >= 8: score += 20
    if length >= 12: score += 15
    if re.search(r"[A-Z]", password): score += 15
    if re.search(r"[a-z]", password): score += 10
    if re.search(r"[0-9]", password): score += 15
    if re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", password): score += 15
    return {
        "score": min(score, 100),
        "level": "weak" if score < 40 else "medium" if score < 70 else "strong",
        "checks": {
            "length_8": length >= 8,
            "length_12": length >= 12,
            "has_uppercase": bool(re.search(r"[A-Z]", password)),
            "has_lowercase": bool(re.search(r"[a-z]", password)),
            "has_number": bool(re.search(r"[0-9]", password)),
            "has_special": bool(re.search(r"[!@#$%^&*]", password)),
        }
    }

# ============================================
# BRUTE-FORCE PROTECTION
# ============================================
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15

def is_account_locked(locked_until: Optional[datetime]) -> bool:
    if not locked_until: return False
    return locked_until > datetime.utcnow()

def increment_failed_attempts(failed_count: int, locked_until: Optional[datetime]) -> Tuple[int, Optional[datetime]]:
    new_count = failed_count + 1
    new_locked = locked_until
    if new_count >= MAX_FAILED_ATTEMPTS:
        new_locked = datetime.utcnow() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
    return new_count, new_locked

# ============================================
# AUDIT LOGGING (minimal)
# ============================================
audit_logger = logging.getLogger("security_audit")
audit_logger.setLevel(logging.INFO)
# Console only untuk Docker
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(message)s'))
audit_logger.addHandler(console_handler)

def log_security_event(event_type: str, username: str, details: dict = None):
    extra = ""
    if details: extra = " | " + " | ".join(f"{k}={v}" for k, v in details.items())
    audit_logger.info(f"{event_type} | user={username}{extra}")

# ============================================
# SEED ADMIN
# ============================================
def generate_secure_password(length: int = 16) -> str:
    uppercase = secrets.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    lowercase = secrets.choice("abcdefghijklmnopqrstuvwxyz")
    digit = secrets.choice("0123456789")
    special = secrets.choice("!@#$%^&*")
    all_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*"
    remaining = ''.join(secrets.choice(all_chars) for _ in range(length - 4))
    password = list(uppercase + lowercase + digit + special + remaining)
    secrets.SystemRandom().shuffle(password)
    return ''.join(password)

"""
Authentication Routes - Login, Change Password, User Management
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, validator
from datetime import datetime, timedelta
from typing import Optional
import os

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

JWT_SECRET = os.getenv("JWT_SECRET", "K4r40k3JWTS3cr3tK3yV3ryL0ngStr1ng2024!@#$")
JWT_ALGORITHM = "HS256"

# ============================================
# MODELS
# ============================================

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str
    confirm_password: str

    @validator('new_password')
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password minimal 8 karakter')
        return v

    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Konfirmasi password tidak cocok')
        return v

# ============================================
# HELPERS
# ============================================

def verify_password_local(plain: str, hashed: str) -> bool:
    """Verify password hash"""
    try:
        import hashlib
        salt, h = hashed.split("$", 1)
        return hashlib.sha256(f"{salt}{plain}".encode()).hexdigest() == h
    except:
        return False

def get_password_hash_local(password: str) -> str:
    """Hash password"""
    import hashlib, secrets
    salt = secrets.token_hex(16)
    h = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return f"{salt}${h}"

async def get_current_user(authorization: Optional[str] = Header(None)):
    """
    Dependency: Extract current user from JWT token
    """
    from jose import jwt, JWTError
    
    if not authorization:
        raise HTTPException(status_code=401, detail="Token tidak ditemukan")
    
    try:
        token = authorization.replace("Bearer ", "")
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Token tidak valid")
        return username
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token tidak valid")

# ============================================
# ENDPOINTS
# ============================================

@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: str = Depends(get_current_user)
):
    """
    Ganti password user yang sedang login
    """
    from main import async_session, User
    
    async with async_session() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(User).where(User.username == current_user)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User tidak ditemukan")
        
        # Verifikasi password lama
        if not verify_password_local(request.old_password, user.password_hash):
            raise HTTPException(status_code=400, detail="Password lama tidak sesuai")
        
        # Cek konfirmasi
        if request.new_password != request.confirm_password:
            raise HTTPException(status_code=400, detail="Password baru tidak cocok")
        
        # Update password
        user.password_hash = get_password_hash_local(request.new_password)
        await session.commit()
        
        return {
            "message": "Password berhasil diubah",
            "username": current_user,
            "timestamp": datetime.utcnow().isoformat()
        }

@router.get("/me")
async def get_profile(current_user: str = Depends(get_current_user)):
    """
    Dapatkan profil user yang sedang login
    """
    from main import async_session, User
    from sqlalchemy import select
    
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.username == current_user)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User tidak ditemukan")
        
        return {
            "username": user.username,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None
        }

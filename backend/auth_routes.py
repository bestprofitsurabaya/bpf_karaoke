from pathlib import Path
"""
Authentication Routes - ISO 27001 Production Ready
PT BESTPROFIT FUTURES SURABAYA
"""

from fastapi import APIRouter, HTTPException, Depends, Header, Request
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional
import json

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# Import security module
from security import (
    hash_password, verify_password, create_access_token, create_temp_token,
    decode_token, validate_password_strength, get_password_strength_score,
    is_account_locked, increment_failed_attempts,
    MAX_FAILED_ATTEMPTS, LOCKOUT_DURATION_MINUTES,
    log_security_event
)

# ============================================
# MODELS
# ============================================

class LoginRequest(BaseModel):
    username: str
    password: str

class ChangePasswordRequest(BaseModel):
    old_password: str = None  # Optional: not required for first-time change
    new_password: str
    confirm_password: str

class ForceChangePasswordRequest(BaseModel):
    new_password: str
    confirm_password: str

# ============================================
# HELPERS
# ============================================

async def get_current_user(authorization: Optional[str] = Header(None)) -> str:
    """Extract username dari JWT token"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Token tidak ditemukan")
    
    token = authorization.replace("Bearer ", "").replace("bearer ", "").strip()
    
    if not token or token in ("null", "undefined"):
        raise HTTPException(status_code=401, detail="Token tidak valid")
    
    try:
        payload = decode_token(token)
        
        # Cek token type: temp token hanya untuk change password
        token_type = payload.get("type", "access")
        if token_type == "temp":
            # Temp token valid, tapi hanya untuk endpoint tertentu
            pass
        
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Token tidak valid")
        
        return username
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Session expired: {str(e)}")

async def get_admin_user(authorization: Optional[str] = Header(None)) -> str:
    """Extract user & verify admin role"""
    username = await get_current_user(authorization)
    
    from main import async_session, User
    from sqlalchemy import select
    
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.username == username, User.is_active == True)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=401, detail="User tidak ditemukan")
        
        if user.role != "admin":
            raise HTTPException(status_code=403, detail="Akses ditolak: memerlukan role admin")
        
        return username

# ============================================
# LOGIN ENDPOINT (ISO 27001 A.9.4.2)
# ============================================

@router.post("/login")
async def login(request: LoginRequest, req: Request = None):
    """
    Login dengan brute-force protection & force password change detection.
    ISO 27001 A.9.4.2: Protection against brute-force attacks
    """
    from main import async_session, User
    from sqlalchemy import select
    
    client_ip = req.client.host if req else "unknown"
    
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.username == request.username)
        )
        user = result.scalar_one_or_none()
        
        # User tidak ditemukan → generic error (cegah username enumeration)
        if not user:
            log_security_event("LOGIN_FAILED", request.username, {"reason": "user_not_found", "ip": client_ip})
            raise HTTPException(status_code=401, detail="Username atau password salah")
        
        # Check account lock (ISO 27001 A.9.4.2)
        if is_account_locked(user.locked_until):
            remaining = (user.locked_until - datetime.utcnow()).seconds // 60
            log_security_event("LOGIN_BLOCKED", request.username, {"reason": "account_locked", "ip": client_ip})
            raise HTTPException(
                status_code=423,  # 423 Locked
                detail=f"Akun terkunci. Silakan coba lagi dalam {remaining} menit."
            )
        
        # Verify password
        if not verify_password(request.password, user.password_hash):
            # Increment failed attempts (ISO 27001 A.9.4.2)
            new_attempts, new_locked = increment_failed_attempts(
                user.failed_login_attempts, user.locked_until
            )
            user.failed_login_attempts = new_attempts
            user.locked_until = new_locked
            await session.commit()
            
            if new_locked:
                log_security_event("ACCOUNT_LOCKED", request.username, {
                    "attempts": new_attempts, "ip": client_ip,
                    "locked_until": new_locked.isoformat()
                })
            
            log_security_event("LOGIN_FAILED", request.username, {
                "reason": "wrong_password", 
                "attempt": new_attempts,
                "ip": client_ip
            })
            
            raise HTTPException(status_code=401, detail="Username atau password salah")
        
        # Login sukses → reset failed attempts
        user.failed_login_attempts = 0
        user.locked_until = None
        await session.commit()
        
        log_security_event("LOGIN_SUCCESS", request.username, {"ip": client_ip})
        
        # Check force password change (ISO 27001 A.9.2.4)
        if user.requires_password_change:
            temp_token = create_temp_token(user.username)
            log_security_event("FORCE_PASSWORD_CHANGE", request.username, {"ip": client_ip})
            return {
                "status": "requires_password_change",
                "temp_token": temp_token,
                "message": "Anda harus mengganti password sebelum melanjutkan.",
                "user": {"username": user.username, "role": user.role}
            }
        
        # Normal login → return access token
        access_token = create_access_token(data={"sub": user.username, "role": user.role})
        
        return {
            "status": "success",
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "username": user.username,
                "role": user.role,
                "last_password_change": user.last_password_change.isoformat() if user.last_password_change else None
            }
        }

# ============================================
# FORCE CHANGE PASSWORD (ISO 27001 A.9.2.4)
# ============================================

@router.post("/force-change-password")
async def force_change_password(
    request: ForceChangePasswordRequest,
    current_user: str = Depends(get_current_user)
):
    """
    Endpoint khusus untuk first-time password change.
    Hanya menerima temp_token dari response login.
    ISO 27001 A.9.2.4: Enforce password change on first login
    """
    from main import async_session, User
    from sqlalchemy import select
    
    # Validate password complexity
    is_valid, error_msg = validate_password_strength(request.new_password, current_user)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    # Validate confirmation
    if request.new_password != request.confirm_password:
        raise HTTPException(status_code=400, detail="Password baru tidak cocok")
    
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.username == current_user)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User tidak ditemukan")
        
        # Check password history (tidak boleh sama dengan 3 password terakhir)
        if user.password_history:
            try:
                old_hashes = json.loads(user.password_history) if isinstance(user.password_history, str) else user.password_history
                for old_hash in old_hashes[:3]:
                    if verify_password(request.new_password, old_hash):
                        raise HTTPException(
                            status_code=400, 
                            detail="Password tidak boleh sama dengan 3 password terakhir"
                        )
            except json.JSONDecodeError:
                pass
        
        # Update password history
        history = []
        if user.password_history:
            try:
                history = json.loads(user.password_history) if isinstance(user.password_history, str) else user.password_history
            except:
                history = []
        history.insert(0, user.password_hash)  # Simpan hash lama
        history = history[:5]  # Maksimal 5 password history
        
        # Update password
        user.password_hash = hash_password(request.new_password)
        user.requires_password_change = False
        user.password_history = json.dumps(history)
        user.last_password_change = datetime.utcnow()
        user.failed_login_attempts = 0
        user.locked_until = None
        await session.commit()
        
        log_security_event("PASSWORD_CHANGED", current_user, {"type": "force_change"})
        
        # Issue full access token
        access_token = create_access_token(data={"sub": user.username, "role": user.role})
        
        return {
            "status": "success",
            "access_token": access_token,
            "token_type": "bearer",
            "message": "Password berhasil diubah! Selamat datang.",
            "user": {"username": user.username, "role": user.role}
        }

# ============================================
# CHANGE PASSWORD (Normal)
# ============================================

@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: str = Depends(get_current_user)
):
    """Ganti password untuk user yang sudah pernah login"""
    from main import async_session, User
    from sqlalchemy import select
    
    # Validate password complexity
    is_valid, error_msg = validate_password_strength(request.new_password, current_user)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    if request.new_password != request.confirm_password:
        raise HTTPException(status_code=400, detail="Password baru tidak cocok")
    
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.username == current_user, User.is_active == True)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User tidak ditemukan")
        
        # Verifikasi password lama (kecuali untuk force change)
        if user.requires_password_change:
            # Force change scenario - no old password needed
            pass
        elif not verify_password(request.old_password, user.password_hash):
            raise HTTPException(status_code=401, detail="Password lama tidak sesuai")
        
        # Update password
        history = []
        if user.password_history:
            try:
                history = json.loads(user.password_history) if isinstance(user.password_history, str) else user.password_history
            except:
                history = []
        history.insert(0, user.password_hash)
        history = history[:5]
        
        user.password_hash = hash_password(request.new_password)
        user.requires_password_change = False
        user.password_history = json.dumps(history)
        user.last_password_change = datetime.utcnow()
        await session.commit()
        
        log_security_event("PASSWORD_CHANGED", current_user, {"type": "normal_change"})
        
        return {
            "message": "Password berhasil diubah!",
            "username": current_user,
            "timestamp": datetime.utcnow().isoformat()
        }

# ============================================
# PASSWORD STRENGTH CHECK
# ============================================

@router.post("/check-password-strength")
async def check_password_strength(request: ForceChangePasswordRequest):
    """Check password strength without saving"""
    score = get_password_strength_score(request.new_password)
    is_valid, error_msg = validate_password_strength(request.new_password)
    
    return {
        "is_valid": is_valid,
        "score": score,
        "errors": error_msg if not is_valid else None
    }

# ============================================
# PROFILE
# ============================================

@router.get("/me")
async def get_profile(current_user: str = Depends(get_admin_user)):
    """Get current admin profile"""
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
            "requires_password_change": user.requires_password_change,
            "failed_login_attempts": user.failed_login_attempts,
            "last_password_change": user.last_password_change.isoformat() if user.last_password_change else None,
            "created_at": user.created_at.isoformat() if user.created_at else None
        }

#!/usr/bin/env python3
"""
Admin Seeder Script - ISO 27001 Compliant
Generate secure random password for initial admin account.
Run: python seed_admin.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import asyncio
import secrets
from datetime import datetime
from security import hash_password, generate_secure_password, validate_password_strength
from sqlalchemy import select
from main import async_session, User, engine, Base

async def seed_admin():
    """Create admin account with secure random password"""
    
    # Generate secure password
    password = generate_secure_password(16)
    
    # Verify password meets complexity requirements
    is_valid, errors = validate_password_strength(password, "admin")
    if not is_valid:
        print(f"❌ Generated password doesn't meet requirements: {errors}")
        print("   Regenerating...")
        return await seed_admin()
    
    # Hash password
    hashed = hash_password(password)
    
    async with async_session() as session:
        # Check if admin already exists
        result = await session.execute(
            select(User).where(User.username == "admin")
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            # Update existing admin password
            existing.password_hash = hashed
            existing.requires_password_change = True
            existing.failed_login_attempts = 0
            existing.locked_until = None
            existing.last_password_change = datetime.utcnow()
            await session.commit()
            print("🔄 Admin account UPDATED with new secure password.")
        else:
            # Create new admin
            admin = User(
                username="admin",
                password_hash=hashed,
                role="admin",
                is_active=True,
                requires_password_change=True,
                last_password_change=datetime.utcnow()
            )
            session.add(admin)
            await session.commit()
            print("✅ Admin account CREATED with secure password.")
    
    # Print credentials
    print("")
    print("=" * 60)
    print("  🔐 ADMIN CREDENTIALS (ISO 27001 Compliant)")
    print("=" * 60)
    print(f"  Username : admin")
    print(f"  Password : {password}")
    print("")
    print("  ⚠️  IMPORTANT:")
    print("  1. Copy password ini dan simpan di tempat aman")
    print("  2. Password hanya ditampilkan SEKALI INI")
    print("  3. Anda WAJIB mengganti password saat login pertama")
    print("  4. Jangan bagikan password ini ke siapa pun")
    print("=" * 60)
    print("")
    
    return password

if __name__ == "__main__":
    asyncio.run(seed_admin())

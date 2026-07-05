#!/usr/bin/env python3
"""Run once to create the initial admin user: python scripts/seed_admin.py"""
import asyncio
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User


async def main() -> None:
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        admin = User(
            id=uuid.uuid4(),
            name="Admin",
            phone="+972500000000",
            password_hash=hash_password("admin123"),
            role="admin",
        )
        session.add(admin)
        await session.commit()
        print("Admin created: phone=+972500000000 password=admin123")
        print("IMPORTANT: Change the password after first login!")


asyncio.run(main())

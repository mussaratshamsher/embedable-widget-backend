"""Script 2: Test user registration and count."""
import asyncio
import os
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy.future import select
from app.db.database import AsyncSessionLocal, Base, engine
from app.models.user import User
from app.core.security import hash_password


async def main():
    print("=== Script 2: User Test ===")
    try:
        # Ensure tables exist
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with AsyncSessionLocal() as db:
            # Count existing users
            result = await db.execute(select(User))
            existing = result.scalars().all()
            count_before = len(existing)
            print(f"User count before: {count_before}")

            # Create a test user
            test_email = f"script_test_{uuid.uuid4().hex[:8]}@example.com"
            user = User(
                id=uuid.uuid4(),
                email=test_email,
                hashed_password=hash_password("scriptpass123"),
                first_name="Script",
                last_name="Test",
                is_active=True,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            print(f"Created user: {user.email} (id={user.id})")

            # Count after
            result = await db.execute(select(User))
            all_users = result.scalars().all()
            count_after = len(all_users)
            print(f"User count after: {count_after}")

            if count_after == count_before + 1:
                print("SUCCESS: User count increased by 1.")
            else:
                print(f"FAILED: Expected count {count_before + 1}, got {count_after}.")
                sys.exit(1)

    except Exception as e:
        print(f"FAILED: {type(e).__name__}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

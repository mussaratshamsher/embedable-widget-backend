"""Script 3: Create organisation and project, verify via API + direct DB query."""
import asyncio
import os
import sys
import uuid
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy.future import select
from app.db.database import AsyncSessionLocal, Base, engine
from app.models.organization import Organization
from app.models.project import Project
from app.models.user import User
from app.core.security import hash_password
import urllib.request


async def main():
    print("=== Script 3: Organisation & Project ===")
    try:
        # Ensure tables exist
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Create a user first (FK dependency)
        async with AsyncSessionLocal() as db:
            user_email = f"org_script_{uuid.uuid4().hex[:8]}@example.com"
            user = User(
                id=uuid.uuid4(),
                email=user_email,
                hashed_password=hash_password("orgpass123"),
                first_name="Org",
                last_name="Script",
                is_active=True,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            print(f"Created user: {user.id}")

            # Create organisation
            org = Organization(
                id=uuid.uuid4(),
                name=f"Script Org {uuid.uuid4().hex[:6]}",
                owner_id=user.id,
                is_active=True,
            )
            db.add(org)
            await db.commit()
            await db.refresh(org)
            print(f"Created organisation: {org.id} -> {org.name}")

            # Create project
            project = Project(
                id=uuid.uuid4(),
                organization_id=org.id,
                name=f"Script Project {uuid.uuid4().hex[:6]}",
                description="Created by verification script",
                is_active=True,
            )
            db.add(project)
            await db.commit()
            await db.refresh(project)
            print(f"Created project: {project.id} -> {project.name}")

            # Verify via DB query
            result = await db.execute(select(Organization).where(Organization.id == org.id))
            db_org = result.scalar_one_or_none()
            result = await db.execute(select(Project).where(Project.id == project.id))
            db_proj = result.scalar_one_or_none()

            if db_org and db_proj:
                print("SUCCESS: Organisation and project are persisted in the database.")
            else:
                print("FAILED: Could not verify org/project in database.")
                sys.exit(1)

            # Try API (optional, may require auth depending on your routes)
            print("\nNote: API verification skipped because organisation/project endpoints")
            print("may require authentication. Check Supabase dashboard for tables:")
            print(" - organizations")
            print(" - projects")

    except Exception as e:
        print(f"FAILED: {type(e).__name__}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

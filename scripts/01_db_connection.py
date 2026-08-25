"""Script 1: Test database connection and basic query."""
import asyncio
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import text
from app.db.database import engine


async def main():
    print("=== Script 1: Database Connection ===")
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT NOW()"))
            row = result.fetchone()
            timestamp = row[0] if row else None
            print(f"SUCCESS: Database connected. Current DB time: {timestamp}")
    except Exception as e:
        print(f"FAILED: {type(e).__name__}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

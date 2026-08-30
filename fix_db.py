import asyncio
import sys
import os
sys.path.insert(0, '.')
from app.db.database import engine
from sqlalchemy import text

async def main():
    try:
        async with engine.begin() as conn:
            await conn.execute(text("ALTER TABLE projects ADD COLUMN IF NOT EXISTS allowed_domains JSON DEFAULT '[]'"))
            await conn.execute(text("ALTER TABLE projects ADD COLUMN IF NOT EXISTS theme_color VARCHAR(255)"))
            await conn.execute(text("ALTER TABLE projects ADD COLUMN IF NOT EXISTS is_banned BOOLEAN DEFAULT FALSE"))
            await conn.execute(text("ALTER TABLE projects ADD COLUMN IF NOT EXISTS ban_reason TEXT"))
        print('Columns added successfully')
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await engine.dispose()

if __name__ == '__main__':
    asyncio.run(main())

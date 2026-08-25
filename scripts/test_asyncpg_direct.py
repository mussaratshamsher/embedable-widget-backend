import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL").replace("postgresql+asyncpg://", "postgresql://")

async def main():
    import asyncpg
    print("Testing asyncpg with statement_cache_size=0...")
    try:
        conn = await asyncpg.connect(DATABASE_URL, statement_cache_size=0)
        row = await conn.fetchrow("SELECT NOW()")
        print(f"SUCCESS: {row[0]}")
        await conn.close()
    except Exception as e:
        print(f"FAILED: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(main())

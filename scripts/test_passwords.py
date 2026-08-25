import asyncio
import os
from dotenv import load_dotenv
import asyncpg

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL").replace("postgresql+asyncpg://", "postgresql://")

async def main():
    print("Testing with current .env password...")
    try:
        conn = await asyncpg.connect(DATABASE_URL, statement_cache_size=0)
        row = await conn.fetchrow("SELECT NOW()")
        print(f"SUCCESS: {row[0]}")
        await conn.close()
    except Exception as e:
        print(f"FAILED: {type(e).__name__}: {e}")

    # Try old password
    old_url = DATABASE_URL.replace("leadforge%401122", "yashfa%401122")
    print("\nTesting with OLD password (yashfa@1122)...")
    try:
        conn = await asyncpg.connect(old_url, statement_cache_size=0)
        row = await conn.fetchrow("SELECT NOW()")
        print(f"SUCCESS: {row[0]}")
        await conn.close()
    except Exception as e:
        print(f"FAILED: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

async def main():
    print("Single engine test with statement_cache_size=0")
    try:
        engine = create_async_engine(
            DATABASE_URL,
            echo=False,
            future=True,
            connect_args={"statement_cache_size": 0},
            pool_size=1,
            max_overflow=0,
        )
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT NOW()"))
            row = result.fetchone()
            print(f"SUCCESS: {row[0]}")
        await engine.dispose()
    except Exception as e:
        print(f"FAILED: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(main())

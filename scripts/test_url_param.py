import asyncio
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url

load_dotenv()

base_url = os.getenv("DATABASE_URL")

# Add prepared_statement_cache_size=0 to URL
if "?" in base_url:
    url_str = base_url + "&prepared_statement_cache_size=0"
else:
    url_str = base_url + "?prepared_statement_cache_size=0"

parsed = make_url(url_str)

async def main():
    print(f"Testing URL: {parsed}")
    try:
        engine = create_async_engine(parsed, echo=False, future=True)
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT NOW()"))
            row = result.fetchone()
            print(f"SUCCESS: {row[0]}")
        await engine.dispose()
    except Exception as e:
        print(f"FAILED: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(main())

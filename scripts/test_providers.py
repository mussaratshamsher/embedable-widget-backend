import asyncio
import sys
import os

# Add parent directory to path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.llm.groq_provider import GroqProvider
from app.services.llm.gemini_provider import GeminiProvider
from app.services.llm.factory import LLMFactory

async def test_providers():
    print("Testing Groq Provider...")
    groq = GroqProvider()
    try:
        response = await groq.generate_response(
            messages=[{"role": "user", "content": "Say hello!"}],
            max_tokens=20
        )
        print(f"Groq Response: {response}")
    except Exception as e:
        print(f"Groq Error: {e}")

    print("\nTesting Gemini Provider...")
    gemini = GeminiProvider()
    try:
        response = await gemini.generate_response(
            messages=[{"role": "user", "content": "Say hello!"}],
            max_tokens=20
        )
        print(f"Gemini Response: {response}")
    except Exception as e:
        print(f"Gemini Error: {e}")

    print("\nTesting Factory with Fallback (Simulating Groq Failure by changing model)...")
    factory = LLMFactory()
    # Force Groq to fail
    factory.primary_provider.model = "invalid-model-name-to-force-404"
    try:
        response = await factory.get_response_with_fallback(
            messages=[{"role": "user", "content": "Say hello to the factory!"}],
            max_tokens=20
        )
        print(f"Factory Response (Should be from Gemini): {response}")
    except Exception as e:
        print(f"Factory Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_providers())

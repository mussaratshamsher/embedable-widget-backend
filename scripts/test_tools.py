import asyncio
import sys
import os

# Add parent directory to path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.llm.service import LLMService

async def test_tools():
    service = LLMService()
    
    print("Test 1: Search Tool")
    history_search = [{"role": "user", "content": "Search the web for the latest news on AI."}]
    response_search = await service.get_ai_response(
        conversation_history=history_search,
        enabled_tools=["search_web", "book_meeting", "sync_crm"]
    )
    print(f"Response: {response_search}\n")
    
    print("Test 2: Calendar Tool")
    history_calendar = [{"role": "user", "content": "I want to book a meeting for tomorrow at 2pm. My email is test@example.com."}]
    response_calendar = await service.get_ai_response(
        conversation_history=history_calendar,
        enabled_tools=["search_web", "book_meeting", "sync_crm"]
    )
    print(f"Response: {response_calendar}\n")

if __name__ == "__main__":
    asyncio.run(test_tools())

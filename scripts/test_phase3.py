import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import AsyncSessionLocal
from app.models.project import Project, ProjectStatus
from app.models.organization import Organization
from app.services.llm.service import LLMService

async def setup_test_data():
    async with AsyncSessionLocal() as db:
        # Create a test organization
        org = Organization(
            name="Test Org Phase 3",
            slug="test-org-phase-3",
        )
        db.add(org)
        await db.commit()
        await db.refresh(org)
        
        # Create Project A: Groq + Search Tool
        project_a = Project(
            organization_id=org.id,
            name="Project A - Groq Search",
            website_url="https://project-a.com",
            status=ProjectStatus.ACTIVE,
            api_key="sk_test_project_a",
            primary_llm="groq",
            enabled_tools=["search_web"]
        )
        db.add(project_a)
        
        # Create Project B: Gemini + Calendar Tool
        project_b = Project(
            organization_id=org.id,
            name="Project B - Gemini Calendar",
            website_url="https://project-b.com",
            status=ProjectStatus.ACTIVE,
            api_key="sk_test_project_b",
            primary_llm="gemini", # Testing Gemini Fallback or if they fix their key
            enabled_tools=["book_meeting"]
        )
        db.add(project_b)
        
        await db.commit()
        await db.refresh(project_a)
        await db.refresh(project_b)
        
        return project_a, project_b

async def test_dynamic_routing():
    project_a, project_b = await setup_test_data()
    
    print(f"--- Testing Project A ({project_a.name}) ---")
    print(f"Primary LLM: {project_a.primary_llm}, Tools: {project_a.enabled_tools}")
    
    llm_service_a = LLMService(primary_llm=project_a.primary_llm)
    history_a = [{"role": "user", "content": "Search the web for news on AI."}]
    
    print("Sending prompt to Project A (should trigger search_web on Groq)...")
    response_a = await llm_service_a.get_ai_response(
        conversation_history=history_a,
        enabled_tools=project_a.enabled_tools
    )
    print(f"Project A Response: {response_a}\n")
    
    print(f"--- Testing Project B ({project_b.name}) ---")
    print(f"Primary LLM: {project_b.primary_llm}, Tools: {project_b.enabled_tools}")
    
    llm_service_b = LLMService(primary_llm=project_b.primary_llm)
    history_b = [{"role": "user", "content": "Book a meeting for tomorrow at 3pm."}]
    
    print("Sending prompt to Project B (should trigger book_meeting on Gemini fallback to Groq)...")
    response_b = await llm_service_b.get_ai_response(
        conversation_history=history_b,
        enabled_tools=project_b.enabled_tools
    )
    print(f"Project B Response: {response_b}\n")

if __name__ == "__main__":
    asyncio.run(test_dynamic_routing())

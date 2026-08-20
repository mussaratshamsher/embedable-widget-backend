"""Integration tests for widget and conversation endpoints."""
import pytest
from httpx import AsyncClient
from uuid import UUID


@pytest.mark.asyncio
async def test_create_widget_session(async_client: AsyncClient):
    """Test creating a widget session."""
    # First create a project with API key
    # Register and login user
    reg_response = await async_client.post(
        "/api/auth/register",
        json={
            "email": "widget@example.com",
            "password": "testpassword123",
        },
    )
    token = reg_response.json()["access_token"]
    
    # Create organization
    org_response = await async_client.post(
        "/api/organizations",
        json={
            "name": "Widget Test Org",
            "slug": "widget-test-org",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    org_id = org_response.json()["id"]
    
    # Create project
    proj_response = await async_client.post(
        "/api/projects",
        json={
            "name": "Test Project",
            "website_url": "https://example.com",
        },
        params={"organization_id": org_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    project = proj_response.json()
    api_key = project["api_key"]
    
    # Create widget session
    session_response = await async_client.post(
        "/api/widget/session",
        json={
            "project_api_key": api_key,
            "visitor_identifier": "test_visitor_123",
        },
    )
    
    assert session_response.status_code == 201
    data = session_response.json()
    assert "visitor_id" in data
    assert "visitor_identifier" in data
    assert "conversation_id" in data
    assert data["visitor_identifier"] == "test_visitor_123"


@pytest.mark.asyncio
async def test_widget_session_invalid_api_key(async_client: AsyncClient):
    """Test widget session with invalid API key."""
    response = await async_client.post(
        "/api/widget/session",
        json={
            "project_api_key": "invalid_key",
            "visitor_identifier": "test_visitor",
        },
    )
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_send_message_to_conversation(async_client: AsyncClient):
    """Test sending a message to a conversation."""
    # Create project and session
    reg_response = await async_client.post(
        "/api/auth/register",
        json={
            "email": "message@example.com",
            "password": "testpassword123",
        },
    )
    token = reg_response.json()["access_token"]
    
    org_response = await async_client.post(
        "/api/organizations",
        json={
            "name": "Message Test Org",
            "slug": "message-test-org",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    org_id = org_response.json()["id"]
    
    proj_response = await async_client.post(
        "/api/projects",
        json={
            "name": "Message Project",
            "website_url": "https://example.com",
        },
        params={"organization_id": org_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    api_key = proj_response.json()["api_key"]
    
    # Create session
    session_response = await async_client.post(
        "/api/widget/session",
        json={
            "project_api_key": api_key,
            "visitor_identifier": "message_visitor",
        },
    )
    conversation_id = session_response.json()["conversation_id"]
    
    # Send message
    msg_response = await async_client.post(
        f"/api/widget/conversations/{conversation_id}/messages",
        json={"content": "Hello, how can you help?"},
        params={"project_api_key": api_key},
    )
    
    assert msg_response.status_code == 201
    msg_data = msg_response.json()
    assert msg_data["role"] == "user"
    assert msg_data["content"] == "Hello, how can you help?"


@pytest.mark.asyncio
async def test_get_conversation_messages(async_client: AsyncClient):
    """Test retrieving conversation messages."""
    # Create project and session
    reg_response = await async_client.post(
        "/api/auth/register",
        json={
            "email": "retrieve@example.com",
            "password": "testpassword123",
        },
    )
    token = reg_response.json()["access_token"]
    
    org_response = await async_client.post(
        "/api/organizations",
        json={
            "name": "Retrieve Test Org",
            "slug": "retrieve-test-org",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    org_id = org_response.json()["id"]
    
    proj_response = await async_client.post(
        "/api/projects",
        json={
            "name": "Retrieve Project",
            "website_url": "https://example.com",
        },
        params={"organization_id": org_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    api_key = proj_response.json()["api_key"]
    
    # Create session
    session_response = await async_client.post(
        "/api/widget/session",
        json={
            "project_api_key": api_key,
            "visitor_identifier": "retrieve_visitor",
        },
    )
    conversation_id = session_response.json()["conversation_id"]
    
    # Send multiple messages
    await async_client.post(
        f"/api/widget/conversations/{conversation_id}/messages",
        json={"content": "First message"},
        params={"project_api_key": api_key},
    )
    
    await async_client.post(
        f"/api/widget/conversations/{conversation_id}/messages",
        json={"content": "Second message"},
        params={"project_api_key": api_key},
    )
    
    # Retrieve messages
    msg_response = await async_client.get(
        f"/api/widget/conversations/{conversation_id}/messages",
        params={"project_api_key": api_key},
    )
    
    assert msg_response.status_code == 200
    messages = msg_response.json()
    assert len(messages) == 2
    assert messages[0]["content"] == "First message"
    assert messages[1]["content"] == "Second message"


@pytest.mark.asyncio
async def test_list_conversations_authenticated(async_client: AsyncClient):
    """Test listing conversations as authenticated user."""
    # Create project
    reg_response = await async_client.post(
        "/api/auth/register",
        json={
            "email": "list@example.com",
            "password": "testpassword123",
        },
    )
    token = reg_response.json()["access_token"]
    
    org_response = await async_client.post(
        "/api/organizations",
        json={
            "name": "List Test Org",
            "slug": "list-test-org",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    org_id = org_response.json()["id"]
    
    proj_response = await async_client.post(
        "/api/projects",
        json={
            "name": "List Project",
            "website_url": "https://example.com",
        },
        params={"organization_id": org_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    project_id = proj_response.json()["id"]
    api_key = proj_response.json()["api_key"]
    
    # Create sessions
    await async_client.post(
        "/api/widget/session",
        json={
            "project_api_key": api_key,
            "visitor_identifier": "visitor_1",
        },
    )
    
    await async_client.post(
        "/api/widget/session",
        json={
            "project_api_key": api_key,
            "visitor_identifier": "visitor_2",
        },
    )
    
    # List conversations as authenticated user
    conv_response = await async_client.get(
        "/api/conversations",
        params={"project_id": project_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert conv_response.status_code == 200
    conversations = conv_response.json()
    assert len(conversations) == 2

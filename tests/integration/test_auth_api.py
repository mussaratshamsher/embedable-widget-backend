"""Integration tests for authentication endpoints."""
import pytest
from httpx import AsyncClient
import json


@pytest.mark.asyncio
async def test_register_new_user(async_client: AsyncClient):
    """Test user registration."""
    response = await async_client.post(
        "/api/auth/register",
        json={
            "email": "test@example.com",
            "password": "testpassword123",
            "first_name": "Test",
            "last_name": "User",
        },
    )
    
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "test@example.com"
    assert data["user"]["first_name"] == "Test"


@pytest.mark.asyncio
async def test_register_duplicate_email(async_client: AsyncClient):
    """Test registration with duplicate email."""
    # Register first user
    await async_client.post(
        "/api/auth/register",
        json={
            "email": "duplicate@example.com",
            "password": "testpassword123",
        },
    )
    
    # Try to register with same email
    response = await async_client.post(
        "/api/auth/register",
        json={
            "email": "duplicate@example.com",
            "password": "differentpassword123",
        },
    )
    
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login_success(async_client: AsyncClient):
    """Test successful login."""
    # Register user
    await async_client.post(
        "/api/auth/register",
        json={
            "email": "login@example.com",
            "password": "testpassword123",
        },
    )
    
    # Login
    response = await async_client.post(
        "/api/auth/login",
        json={
            "email": "login@example.com",
            "password": "testpassword123",
        },
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "login@example.com"


@pytest.mark.asyncio
async def test_login_invalid_password(async_client: AsyncClient):
    """Test login with invalid password."""
    # Register user
    await async_client.post(
        "/api/auth/register",
        json={
            "email": "password@example.com",
            "password": "correctpassword123",
        },
    )
    
    # Try to login with wrong password
    response = await async_client.post(
        "/api/auth/login",
        json={
            "email": "password@example.com",
            "password": "wrongpassword123",
        },
    )
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(async_client: AsyncClient):
    """Test login with nonexistent user."""
    response = await async_client.post(
        "/api/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "anypassword123",
        },
    )
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user(async_client: AsyncClient):
    """Test getting current user info."""
    # Register and login
    login_response = await async_client.post(
        "/api/auth/register",
        json={
            "email": "current@example.com",
            "password": "testpassword123",
            "first_name": "Current",
            "last_name": "User",
        },
    )
    token = login_response.json()["access_token"]
    
    # Get current user
    response = await async_client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "current@example.com"
    assert data["first_name"] == "Current"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_get_current_user_without_token(async_client: AsyncClient):
    """Test accessing protected endpoint without token."""
    response = await async_client.get("/api/auth/me")
    
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_logout(async_client: AsyncClient):
    """Test logout endpoint."""
    # Register and login
    login_response = await async_client.post(
        "/api/auth/register",
        json={
            "email": "logout@example.com",
            "password": "testpassword123",
        },
    )
    token = login_response.json()["access_token"]
    
    # Logout
    response = await async_client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert response.status_code == 200
    assert "logged out" in response.json()["message"].lower()

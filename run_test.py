import asyncio, httpx

BASE_URL = "http://127.0.0.1:8000"

async def main():
    async with httpx.AsyncClient() as client:
        # Register (ignore conflict)
        reg = {
            "email": "auto_user@example.com",
            "password": "StrongPass!123",
            "first_name": "Auto",
            "last_name": "User"
        }
        try:
            r = await client.post(f"{BASE_URL}/api/auth/register", json=reg)
            r.raise_for_status()
            print("Registered user")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 409:
                print("User already exists, proceeding")
            else:
                print("Register failed", e)
                return
        # Login
        login = {"email": reg["email"], "password": reg["password"]}
        r = await client.post(f"{BASE_URL}/api/auth/login", json=login)
        r.raise_for_status()
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("🔑 Got token")
        # Create organization
        org = {"name": "AutoOrg", "slug": "auto-org", "description": "Demo org"}
        r = await client.post(f"{BASE_URL}/api/organizations", json=org, headers=headers)
        r.raise_for_status()
        org_res = r.json()
        print("🏢 Org created", org_res["id"], org_res["slug"])
        # Create project
        proj = {
            "name": "AutoProject",
            "website_url": "https://example.com",
            "description": "Demo project",
            "business_type": "SaaS",
            "ai_instructions": "You are an assistant",
            "welcome_message": "Welcome!"
        }
        r = await client.post(f"{BASE_URL}/api/projects?organization_id={org_res['id']}", json=proj, headers=headers)
        r.raise_for_status()
        proj_res = r.json()
        print("📦 Project created, API key", proj_res["api_key"], "ID", proj_res["id"])

if __name__ == "__main__":
    asyncio.run(main())

"""CRM Sync tool."""
from typing import Any, Dict
from app.services.tools.base import BaseTool


class CRMTool(BaseTool):
    """Tool for pushing lead data to a CRM."""
    
    name = "sync_crm"
    description = "Push a qualified lead's data to the external CRM system."
    
    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Lead name"
                },
                "email": {
                    "type": "string",
                    "description": "Lead email"
                },
                "company": {
                    "type": "string",
                    "description": "Lead company"
                }
            },
            "required": ["name", "email"]
        }
        
    async def execute(self, name: str, email: str, company: str = "Unknown", **kwargs) -> Any:
        # Mocking a successful CRM post
        return f"Lead '{name}' ({email}) from {company} successfully synced to CRM."

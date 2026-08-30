"""Calendar booking tool."""
from typing import Any, Dict
from app.services.tools.base import BaseTool


class CalendarTool(BaseTool):
    """Tool for checking availability and booking meetings."""
    
    name = "book_meeting"
    description = "Book a meeting or schedule a time on the calendar."
    
    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "The date for the meeting (YYYY-MM-DD)."
                },
                "time": {
                    "type": "string",
                    "description": "The time for the meeting (e.g. 14:00)."
                },
                "email": {
                    "type": "string",
                    "description": "The user's email address to send the invite."
                }
            },
            "required": ["date", "time", "email"]
        }
        
    async def execute(self, date: str, time: str, email: str, **kwargs) -> Any:
        # Mocking a successful booking
        return f"Successfully booked a meeting on {date} at {time}. A calendar invite has been sent to {email}."

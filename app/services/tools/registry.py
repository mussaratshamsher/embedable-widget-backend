"""Tool registry to manage and execute available tools."""
from typing import Dict, Type
from app.services.tools.base import BaseTool
from app.services.tools.search_tool import SearchTool
from app.services.tools.calendar_tool import CalendarTool
from app.services.tools.crm_tool import CRMTool

# Available tools
AVAILABLE_TOOLS: Dict[str, Type[BaseTool]] = {
    SearchTool.name: SearchTool,
    CalendarTool.name: CalendarTool,
    CRMTool.name: CRMTool,
}

def get_tool(tool_name: str) -> BaseTool:
    """Get a tool instance by name."""
    if tool_name not in AVAILABLE_TOOLS:
        raise ValueError(f"Tool {tool_name} not found")
    return AVAILABLE_TOOLS[tool_name]()

def get_all_tools() -> list[BaseTool]:
    """Get all available tool instances."""
    return [tool() for tool in AVAILABLE_TOOLS.values()]

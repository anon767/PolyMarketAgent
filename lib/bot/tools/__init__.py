"""Trading bot tools - dynamically loaded."""
import inspect
from typing import List, Dict, Any
from .base import BaseTool

# Import all tool modules
from . import funds, traders, markets, trading, research


def get_all_tools() -> List[BaseTool]:
    """Get all tool instances."""
    tools = []
    
    # Get all tool classes from imported modules
    for module in [funds, traders, markets, trading, research]:
        for name, obj in inspect.getmembers(module):
            if (inspect.isclass(obj) and 
                issubclass(obj, BaseTool) and 
                obj is not BaseTool):
                tools.append(obj())
    
    return tools


def get_tools_dict() -> List[Dict[str, Any]]:
    """Get tools in OpenAI function calling format."""
    return [tool.to_dict() for tool in get_all_tools()]


# Export for backward compatibility
TOOLS = get_tools_dict()

__all__ = ['BaseTool', 'get_all_tools', 'get_tools_dict', 'TOOLS']

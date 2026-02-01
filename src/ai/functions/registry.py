"""
Function Registry for AI Function Calling
Manages available functions that AI can invoke
"""
import logging
from typing import Dict, Any, Callable

logger = logging.getLogger(__name__)


class FunctionRegistry:
    """Registry for AI-callable functions"""
    
    def __init__(self):
        self.functions: Dict[str, Dict[str, Any]] = {}
    
    def register(self, name: str, func: Callable, schema: Dict[str, Any]):
        """
        Register a function that AI can call
        
        Args:
            name: Function name
            func: Callable function
            schema: OpenAI function schema (description, parameters)
        """
        self.functions[name] = {
            'callable': func,
            'schema': schema
        }
        logger.debug(f"Registered function: {name}")
    
    def get_openai_tools(self) -> list:
        """
        Get functions in OpenAI tools format
        
        Returns:
            List of tool definitions for OpenAI API
        """
        return [
            {
                'type': 'function',
                'function': {
                    'name': name,
                    'description': f['schema']['description'],
                    'parameters': f['schema']['parameters']
                }
            }
            for name, f in self.functions.items()
        ]
    
    async def execute(self, name: str, arguments: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """
        Execute a registered function
        
        Args:
            name: Function name
            arguments: Function arguments
            context: Bot context
            
        Returns:
            Function result as dictionary
        """
        if name not in self.functions:
            logger.error(f"Function not found: {name}")
            return {'error': f'Function {name} not found'}
        
        try:
            func = self.functions[name]['callable']
            # Check if function is async
            import asyncio
            if asyncio.iscoroutinefunction(func):
                result = await func(context, **arguments)
            else:
                result = func(context, **arguments)
            logger.info(f"✓ Function executed: {name} with args {arguments}")
            return result
        except Exception as e:
            logger.error(f"Function execution error: {name} - {e}", exc_info=True)
            return {'error': str(e)}


# Global registry instance
_registry = None


def get_function_registry() -> FunctionRegistry:
    """Get or create global function registry"""
    global _registry
    if _registry is None:
        _registry = FunctionRegistry()
        _register_default_functions(_registry)
    return _registry


def _register_default_functions(registry: FunctionRegistry):
    """Register default system functions"""
    from . import statistics, notes, search, tags, archives, commands
    
    # Register all default functions
    statistics.register(registry)
    notes.register(registry)
    search.register(registry)
    tags.register(registry)
    archives.register(registry)
    commands.register(registry)
    
    logger.info(f"Registered {len(registry.functions)} default functions")

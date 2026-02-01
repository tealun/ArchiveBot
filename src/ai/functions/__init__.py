"""
AI Function Calling Module
Provides callable functions for AI to query system data
"""

from .registry import FunctionRegistry, get_function_registry

__all__ = ['FunctionRegistry', 'get_function_registry']

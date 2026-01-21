"""
Base storage provider interface
"""

from abc import ABC, abstractmethod
from typing import Optional, Any


class BaseStorage(ABC):
    """
    Base class for storage providers
    """
    
    @abstractmethod
    async def store(self, file_data: Any, metadata: dict) -> Optional[str]:
        """
        Store file
        
        Args:
            file_data: File data to store
            metadata: File metadata
            
        Returns:
            Storage path/ID or None if failed
        """
        pass
    
    @abstractmethod
    async def retrieve(self, storage_path: str) -> Optional[Any]:
        """
        Retrieve file
        
        Args:
            storage_path: Storage path/ID
            
        Returns:
            File data or None if not found
        """
        pass
    
    @abstractmethod
    async def delete(self, storage_path: str) -> bool:
        """
        Delete file
        
        Args:
            storage_path: Storage path/ID
            
        Returns:
            True if deleted, False otherwise
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if storage is available
        
        Returns:
            True if available, False otherwise
        """
        pass

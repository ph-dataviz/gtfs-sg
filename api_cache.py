"""Cache LTA DataMall API responses to JSON files."""

import json
import os
from datetime import datetime
from typing import List, Dict, Any


class APICache:
    """Cache for storing and loading API responses."""

    def __init__(self, cache_dir: str = "api_cache"):
        """Initialize the API cache.

        Args:
            cache_dir: Directory to store cached API responses
        """
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def _get_cache_filepath(self, cache_name: str) -> str:
        """Get the filepath for a cache file.

        Args:
            cache_name: Name of the cache (e.g., 'bus_stops')

        Returns:
            Full path to the cache file
        """
        return os.path.join(self.cache_dir, f"{cache_name}.json")

    def save(self, cache_name: str, data: List[Dict[str, Any]]) -> str:
        """Save data to cache file.

        Args:
            cache_name: Name of the cache (e.g., 'bus_stops')
            data: Data to cache

        Returns:
            Path to the saved cache file
        """
        filepath = self._get_cache_filepath(cache_name)

        cache_data = {
            "timestamp": datetime.now().isoformat(),
            "record_count": len(data),
            "data": data
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)

        print(f"  Saved {len(data)} records to {filepath}")
        return filepath

    def load(self, cache_name: str) -> List[Dict[str, Any]]:
        """Load data from cache file.

        Args:
            cache_name: Name of the cache (e.g., 'bus_stops')

        Returns:
            Cached data, or None if cache doesn't exist

        Raises:
            FileNotFoundError: If cache file doesn't exist
        """
        filepath = self._get_cache_filepath(cache_name)

        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Cache file not found: {filepath}")

        with open(filepath, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)

        print(f"  Loaded {cache_data['record_count']} records from {filepath}")
        print(f"  Cache timestamp: {cache_data['timestamp']}")

        return cache_data['data']

    def exists(self, cache_name: str) -> bool:
        """Check if a cache file exists.

        Args:
            cache_name: Name of the cache

        Returns:
            True if cache exists, False otherwise
        """
        filepath = self._get_cache_filepath(cache_name)
        return os.path.exists(filepath)

    def get_cache_info(self, cache_name: str) -> Dict[str, Any]:
        """Get information about a cache file.

        Args:
            cache_name: Name of the cache

        Returns:
            Dictionary with cache information (timestamp, record_count, file_size)

        Raises:
            FileNotFoundError: If cache file doesn't exist
        """
        filepath = self._get_cache_filepath(cache_name)

        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Cache file not found: {filepath}")

        with open(filepath, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)

        file_size = os.path.getsize(filepath)

        return {
            "cache_name": cache_name,
            "filepath": filepath,
            "timestamp": cache_data['timestamp'],
            "record_count": cache_data['record_count'],
            "file_size_bytes": file_size,
            "file_size_mb": round(file_size / (1024 * 1024), 2)
        }

    def list_caches(self) -> List[str]:
        """List all available caches.

        Returns:
            List of cache names
        """
        if not os.path.exists(self.cache_dir):
            return []

        cache_files = [f for f in os.listdir(self.cache_dir) if f.endswith('.json')]
        return [f.replace('.json', '') for f in cache_files]

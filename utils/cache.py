"""
Cache utility module for storing and retrieving LLM results.

This module provides functionality to cache LLM responses based on context strings,
reducing API calls and improving performance.
"""

import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

# Default cache directory
DEFAULT_CACHE_DIR = Path("cache/llm_results")


class CacheManager(Generic[T]):
    """
    Generic cache manager for storing and retrieving typed results.

    Args:
        cache_dir: Directory where cache files will be stored
        result_type: Pydantic model class for the cached data
    """

    def __init__(self, cache_dir: Path | str, result_type: type[T]):
        self.cache_dir = Path(cache_dir)
        self.result_type = result_type
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_key(self, context: str) -> str:
        """
        Generate a cache key based on the context string.

        Args:
            context: Context string to hash

        Returns:
            SHA256 hash of the context
        """
        return hashlib.sha256(context.encode("utf-8")).hexdigest()

    def _get_cache_path(self, context: str) -> Path:
        """
        Get the cache file path for a given context.

        Args:
            context: Context string

        Returns:
            Path to the cache file
        """
        cache_key = self._get_cache_key(context)
        return self.cache_dir / f"{cache_key}.json"

    def load(self, context: str) -> list[T] | None:
        """
        Load cached results from disk.

        Args:
            context: Context string to look up

        Returns:
            List of result objects if cache exists, None otherwise
        """
        cache_path = self._get_cache_path(context)

        if not cache_path.exists():
            return None

        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [self.result_type(**item) for item in data["results"]]
        except (json.JSONDecodeError, KeyError, FileNotFoundError, TypeError) as e:
            print(f"Error loading cache from {cache_path}: {e}")
            return None

    def save(self, context: str, results: list[T]) -> None:
        """
        Save results to cache.

        Args:
            context: Context string (used as cache key)
            results: List of result objects to cache
        """
        cache_path = self._get_cache_path(context)

        try:
            data = {
                "context": context,
                "cache_key": self._get_cache_key(context),
                "results": [r.model_dump() for r in results],
            }

            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            print(f"✓ Cache saved: {cache_path.name}")
        except Exception as e:
            print(f"✗ Error saving cache to {cache_path}: {e}")

    def clear(self, context: str | None = None) -> None:
        """
        Clear cached results.

        Args:
            context: Specific context to clear. If None, clears all cache files.
        """
        if context is not None:
            # Clear specific cache entry
            cache_path = self._get_cache_path(context)
            if cache_path.exists():
                cache_path.unlink()
                print(f"✓ Cleared cache: {cache_path.name}")
        else:
            # Clear all cache files
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
            print(f"✓ Cleared all cache files in {self.cache_dir}")

    def exists(self, context: str) -> bool:
        """
        Check if a cache entry exists for the given context.

        Args:
            context: Context string to check

        Returns:
            True if cache exists, False otherwise
        """
        return self._get_cache_path(context).exists()

    def get_cache_info(self, context: str) -> dict[str, Any] | None:
        """
        Get metadata about a cached entry.

        Args:
            context: Context string

        Returns:
            Dictionary with cache metadata or None if not found
        """
        cache_path = self._get_cache_path(context)

        if not cache_path.exists():
            return None

        try:
            stat = cache_path.stat()
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            return {
                "cache_key": self._get_cache_key(context),
                "path": str(cache_path),
                "size_bytes": stat.st_size,
                "modified": stat.st_mtime,
                "num_results": len(data.get("results", [])),
            }
        except Exception as e:
            print(f"Error reading cache info: {e}")
            return None


def with_cache(
    cache_manager: CacheManager[T],
    context_getter: Callable[..., str],
    use_cache: bool = True,
) -> Callable:
    """
    Decorator to add caching to a function that returns list[T].

    Args:
        cache_manager: CacheManager instance to use
        context_getter: Function to extract context string from function arguments
        use_cache: Whether to enable caching

    Returns:
        Decorated function with caching

    Example:
        >>> cache = CacheManager(Path("cache"), Replacement)
        >>> @with_cache(cache, lambda strings, context, **kw: context)
        >>> def get_data(strings: list[str], context: str) -> list[Replacement]:
        >>>     # ... expensive operation
        >>>     return results
    """

    def decorator(func: Callable[..., list[T]]) -> Callable[..., list[T]]:
        def wrapper(*args: Any, **kwargs: Any) -> list[T]:
            if not use_cache:
                return func(*args, **kwargs)

            # Get context from arguments
            context = context_getter(*args, **kwargs)

            # Try to load from cache
            cached = cache_manager.load(context)
            if cached is not None:
                print(f"✓ Loaded {len(cached)} items from cache")
                return cached

            # Cache miss - call original function
            print("○ Cache miss - executing function...")
            result = func(*args, **kwargs)

            # Save to cache
            cache_manager.save(context, result)

            return result

        return wrapper

    return decorator

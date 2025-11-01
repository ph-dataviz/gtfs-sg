#!/usr/bin/env python3
"""Utility script to inspect cached API responses."""

import sys
from api_cache import APICache


def main():
    """Display information about cached API responses."""
    cache = APICache()

    print("=" * 60)
    print("LTA DataMall API Cache Inspector")
    print("=" * 60)

    cache_names = cache.list_caches()

    if not cache_names:
        print("\n❌ No cached data found.")
        print(f"\nRun the following command to create cache:")
        print("  python build_gtfs.py --save-cache")
        sys.exit(1)

    print(f"\n✅ Found {len(cache_names)} cached datasets:\n")

    total_size_bytes = 0

    for cache_name in sorted(cache_names):
        try:
            info = cache.get_cache_info(cache_name)
            print(f"📦 {cache_name}")
            print(f"   File: {info['filepath']}")
            print(f"   Records: {info['record_count']:,}")
            print(f"   Size: {info['file_size_mb']} MB")
            print(f"   Timestamp: {info['timestamp']}")
            print()

            total_size_bytes += info['file_size_bytes']

        except Exception as e:
            print(f"⚠️  Error reading {cache_name}: {e}")
            print()

    total_size_mb = round(total_size_bytes / (1024 * 1024), 2)
    print("=" * 60)
    print(f"Total cache size: {total_size_mb} MB")
    print("=" * 60)

    print("\n💡 Usage:")
    print("  - Generate GTFS from cache: python build_gtfs.py --use-cache")
    print("  - Refresh cache: python build_gtfs.py --save-cache")


if __name__ == "__main__":
    main()

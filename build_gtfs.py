#!/usr/bin/env python3
"""Main script to build GTFS feed from LTA DataMall API."""

import sys
import argparse
from lta_api_client import LTADataMallClient
from gtfs_generator import GTFSGenerator
import config


def main():
    """Main function to build GTFS feed."""
    parser = argparse.ArgumentParser(
        description="Build GTFS feed from LTA DataMall API"
    )
    parser.add_argument(
        "--output-dir",
        default=config.GTFS_OUTPUT_DIR,
        help=f"Output directory for GTFS files (default: {config.GTFS_OUTPUT_DIR})"
    )
    parser.add_argument(
        "--api-key",
        default=config.LTA_API_KEY,
        help="LTA DataMall API key (default: from config.py)"
    )
    parser.add_argument(
        "--save-cache",
        action="store_true",
        help="Save API responses to cache files for future use"
    )
    parser.add_argument(
        "--use-cache",
        action="store_true",
        help="Load data from cache instead of making API calls"
    )
    parser.add_argument(
        "--cache-dir",
        default="api_cache",
        help="Directory for cached API responses (default: api_cache)"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate the generated GTFS feed after creation"
    )
    parser.add_argument(
        "--run-canonical-validator",
        action="store_true",
        help="Run the canonical validator (requires Java and validator jar)"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("LTA DataMall to GTFS Feed Builder")
    print("=" * 60)
    print(f"API Key: {args.api_key[:3]}..." if args.api_key else "No API key provided")
    print(f"Output Directory: {args.output_dir}")
    if args.use_cache:
        print(f"Mode: Loading from cache ({args.cache_dir})")
    elif args.save_cache:
        print(f"Mode: Fetching from API and saving to cache ({args.cache_dir})")
    else:
        print("Mode: Fetching from API (no caching)")
    print("=" * 60)

    try:
        # Initialize client
        client = LTADataMallClient(
            api_key=args.api_key,
            use_cache=args.use_cache,
            cache_dir=args.cache_dir
        )

        # Fetch data from LTA DataMall API or cache
        if args.use_cache:
            print("\n💾 Loading data from cache...")
        else:
            print("\n📡 Fetching data from LTA DataMall API...")

        bus_stops = client.get_bus_stops(save_cache=args.save_cache)
        bus_services = client.get_bus_services(save_cache=args.save_cache)
        bus_routes = client.get_bus_routes(save_cache=args.save_cache)

        # Load train data from static files
        print("\n🚆 Loading train data from static files...")
        train_stations = client.get_train_stations()
        train_lines = client.get_train_lines()
        train_routes = client.get_train_routes()

        # Validate data
        if not bus_stops:
            print("❌ Error: No bus stops data retrieved")
            sys.exit(1)
        if not bus_services:
            print("❌ Error: No bus services data retrieved")
            sys.exit(1)
        if not bus_routes:
            print("❌ Error: No bus routes data retrieved")
            sys.exit(1)

        print(f"\n✅ Data loading complete:")
        print(f"   - Bus Stops: {len(bus_stops)}")
        print(f"   - Bus Services: {len(bus_services)}")
        print(f"   - Bus Routes: {len(bus_routes)}")
        print(f"   - Train Stations: {len(train_stations)}")
        print(f"   - Train Lines: {len(train_lines)}")
        print(f"   - Train Route Stops: {len(train_routes)}")

        # Generate GTFS feed with both bus and train data
        generator = GTFSGenerator(output_dir=args.output_dir)
        generator.generate_gtfs_feed(
            bus_stops, bus_services, bus_routes,
            train_stations, train_lines, train_routes
        )

        print("\n✅ GTFS feed generation completed successfully!")
        print(f"\n📁 GTFS files are available in: {args.output_dir}")
        print("\nGenerated GTFS files:")
        print("  - agency.txt")
        print("  - stops.txt")
        print("  - routes.txt")
        print("  - trips.txt")
        print("  - stop_times.txt")
        print("  - calendar.txt")
        print("  - feed_info.txt")

        # Validate the GTFS feed if requested
        if args.validate or args.run_canonical_validator:
            from gtfs_validator import GTFSValidator

            print("\n" + "=" * 60)
            print("VALIDATING GTFS FEED")
            print("=" * 60)

            validator = GTFSValidator(args.output_dir)

            # Basic validation
            if not validator.validate_structure():
                print("\n❌ Basic structure validation failed")
                sys.exit(1)

            # gtfs-kit validation
            validator.validate_with_gtfs_kit()

            # Canonical validator
            canonical_passed = True
            if args.run_canonical_validator:
                canonical_passed = validator.run_canonical_validator(country_code="sg")

            # Print summary and check for errors
            validation_passed = validator.print_summary()

            # Exit with error if validation failed
            if not validation_passed:
                print("\n❌ GTFS validation failed with errors")
                sys.exit(1)

            if args.run_canonical_validator and not canonical_passed:
                print("\n❌ Canonical validation failed")
                sys.exit(1)

            print("\n✅ All validation checks passed!")
            print("\n💡 For comprehensive validation, use the canonical validator:")
            print("   python gtfs_validator.py gtfs_output --download-validator")
            print("   python gtfs_validator.py gtfs_output --run-canonical")

    except KeyboardInterrupt:
        print("\n\n⚠️  Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

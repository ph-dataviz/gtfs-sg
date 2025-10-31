#!/usr/bin/env python3
"""GTFS feed validator using gtfs-kit and optional canonical validator."""

import os
import sys
import subprocess
import zipfile
from pathlib import Path
from typing import Dict, List, Any, Optional
import requests


class GTFSValidator:
    """Validator for GTFS feeds."""

    def __init__(self, gtfs_path: str):
        """Initialize the validator.

        Args:
            gtfs_path: Path to GTFS directory or zip file
        """
        self.gtfs_path = Path(gtfs_path)
        self.validation_results = {
            "basic_checks": [],
            "warnings": [],
            "errors": [],
            "info": []
        }

    def validate_structure(self) -> bool:
        """Validate basic GTFS structure.

        Returns:
            True if basic structure is valid
        """
        print("\n🔍 Validating GTFS structure...")

        required_files = [
            "agency.txt",
            "stops.txt",
            "routes.txt",
            "trips.txt",
            "stop_times.txt"
        ]

        optional_files = [
            "calendar.txt",
            "calendar_dates.txt",
            "feed_info.txt",
            "shapes.txt",
            "frequencies.txt",
            "transfers.txt",
            "pathways.txt",
            "levels.txt",
            "translations.txt",
            "attributions.txt"
        ]

        # Check if directory exists
        if not self.gtfs_path.exists():
            self._add_error(f"GTFS path does not exist: {self.gtfs_path}")
            return False

        # Get list of files in directory
        if self.gtfs_path.is_dir():
            files = [f.name for f in self.gtfs_path.glob("*.txt")]
        else:
            self._add_error("GTFS path must be a directory")
            return False

        # Check required files
        missing_required = []
        for required_file in required_files:
            if required_file not in files:
                missing_required.append(required_file)

        if missing_required:
            for file in missing_required:
                self._add_error(f"Missing required file: {file}")
            return False

        self._add_info(f"✅ All {len(required_files)} required files present")

        # Check optional files
        present_optional = [f for f in optional_files if f in files]
        if present_optional:
            self._add_info(f"📄 Found {len(present_optional)} optional files: {', '.join(present_optional)}")

        return True

    def validate_with_gtfs_kit(self) -> Dict[str, Any]:
        """Validate using gtfs-kit library.

        Returns:
            Dictionary with validation results
        """
        print("\n🔍 Validating with gtfs-kit...")

        try:
            import gtfs_kit as gk

            # Read the feed
            feed = gk.read_feed(str(self.gtfs_path), dist_units="km")

            results = {
                "feed_loaded": True,
                "statistics": {},
                "issues": []
            }

            # Get basic statistics
            results["statistics"] = {
                "agencies": len(feed.agency) if feed.agency is not None else 0,
                "stops": len(feed.stops) if feed.stops is not None else 0,
                "routes": len(feed.routes) if feed.routes is not None else 0,
                "trips": len(feed.trips) if feed.trips is not None else 0,
                "stop_times": len(feed.stop_times) if feed.stop_times is not None else 0,
            }

            print(f"  Agencies: {results['statistics']['agencies']}")
            print(f"  Stops: {results['statistics']['stops']}")
            print(f"  Routes: {results['statistics']['routes']}")
            print(f"  Trips: {results['statistics']['trips']}")
            print(f"  Stop Times: {results['statistics']['stop_times']}")

            # Check for common issues
            self._check_gtfs_kit_issues(feed, results)

            return results

        except Exception as e:
            self._add_error(f"Error validating with gtfs-kit: {e}")
            return {"feed_loaded": False, "error": str(e)}

    def _check_gtfs_kit_issues(self, feed, results: Dict):
        """Check for common issues using gtfs-kit.

        Args:
            feed: gtfs-kit Feed object
            results: Dictionary to store results
        """
        # Check for stops without coordinates
        if feed.stops is not None:
            invalid_coords = feed.stops[
                (feed.stops["stop_lat"].isna()) |
                (feed.stops["stop_lon"].isna())
            ]
            if len(invalid_coords) > 0:
                msg = f"Found {len(invalid_coords)} stops with missing coordinates"
                self._add_warning(msg)
                results["issues"].append(msg)

        # Check for trips without stop_times
        if feed.trips is not None and feed.stop_times is not None:
            trip_ids_with_stops = set(feed.stop_times["trip_id"].unique())
            trip_ids_all = set(feed.trips["trip_id"].unique())
            trips_without_stops = trip_ids_all - trip_ids_with_stops

            if trips_without_stops:
                msg = f"Found {len(trips_without_stops)} trips without stop_times"
                self._add_warning(msg)
                results["issues"].append(msg)

        # Check for routes without trips
        if feed.routes is not None and feed.trips is not None:
            route_ids_with_trips = set(feed.trips["route_id"].unique())
            route_ids_all = set(feed.routes["route_id"].unique())
            routes_without_trips = route_ids_all - route_ids_with_trips

            if routes_without_trips:
                msg = f"Found {len(routes_without_trips)} routes without trips"
                self._add_warning(msg)
                results["issues"].append(msg)

        if not results["issues"]:
            self._add_info("✅ No major issues found with gtfs-kit analysis")

    def run_canonical_validator(
        self,
        validator_jar: Optional[str] = None,
        country_code: str = "sg",
        output_dir: str = "validation_output"
    ) -> bool:
        """Run the canonical MobilityData GTFS validator.

        Args:
            validator_jar: Path to gtfs-validator CLI jar file
            country_code: Two-letter country code (ISO 3166-1 alpha-2)
            output_dir: Output directory for validation results

        Returns:
            True if validation succeeded
        """
        print("\n🔍 Running canonical GTFS validator...")

        # Check if validator jar exists
        if validator_jar is None:
            validator_jar = "gtfs-validator.jar"

        if not os.path.exists(validator_jar):
            print(f"\n⚠️  Validator jar not found: {validator_jar}")
            print("\n💡 To download the canonical validator:")
            print("   1. Visit: https://github.com/MobilityData/gtfs-validator/releases")
            print("   2. Download the latest gtfs-validator-X.X.X-cli.jar")
            print("   3. Save it as 'gtfs-validator.jar' in this directory")
            print("\n   Or use the web validator at: https://gtfs-validator.mobilitydata.org/")
            return False

        # Check if Java is installed
        try:
            result = subprocess.run(
                ["java", "-version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                print("⚠️  Java not found. Please install Java 17 or higher.")
                return False
        except Exception as e:
            print(f"⚠️  Error checking Java: {e}")
            return False

        # Zip the GTFS directory if it's not already zipped
        gtfs_zip = self.gtfs_path
        temp_zip = False

        if self.gtfs_path.is_dir():
            gtfs_zip = Path("temp_gtfs.zip")
            print(f"  Creating temporary zip file: {gtfs_zip}")
            self._create_zip(self.gtfs_path, gtfs_zip)
            temp_zip = True

        # Run the validator
        try:
            os.makedirs(output_dir, exist_ok=True)

            cmd = [
                "java",
                "-jar",
                validator_jar,
                "-i",
                str(gtfs_zip),
                "-o",
                output_dir,
                "-c",
                country_code
            ]

            print(f"  Running: {' '.join(cmd)}")
            print(f"  Output will be saved to: {output_dir}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes
            )

            if result.returncode == 0:
                print("\n✅ Canonical validation completed successfully!")
                print(f"\n📄 Validation report: {output_dir}/report.html")
                self._add_info("Canonical validation passed")
                return True
            else:
                print(f"\n⚠️  Validation completed with issues")
                print(f"📄 See detailed report: {output_dir}/report.html")
                if result.stderr:
                    print(f"Error output: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            print("\n⚠️  Validation timed out after 5 minutes")
            return False
        except Exception as e:
            print(f"\n❌ Error running validator: {e}")
            return False
        finally:
            # Clean up temporary zip
            if temp_zip and gtfs_zip.exists():
                gtfs_zip.unlink()

    def _create_zip(self, source_dir: Path, output_zip: Path):
        """Create a zip file from a directory.

        Args:
            source_dir: Source directory
            output_zip: Output zip file path
        """
        with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in source_dir.glob("*.txt"):
                zipf.write(file, file.name)

    def download_canonical_validator(
        self,
        output_path: str = "gtfs-validator.jar",
        version: str = "latest"
    ) -> bool:
        """Download the canonical GTFS validator jar.

        Args:
            output_path: Where to save the jar file
            version: Version to download ('latest' or specific version like 'v5.0.1')

        Returns:
            True if download succeeded
        """
        print(f"\n📥 Downloading canonical GTFS validator ({version})...")

        if version == "latest":
            # Get latest release from GitHub API
            try:
                api_url = "https://api.github.com/repos/MobilityData/gtfs-validator/releases/latest"
                response = requests.get(api_url, timeout=10)
                response.raise_for_status()
                release_data = response.json()

                # Find the CLI jar asset
                jar_asset = None
                for asset in release_data.get("assets", []):
                    if asset["name"].endswith("-cli.jar"):
                        jar_asset = asset
                        break

                if not jar_asset:
                    print("❌ Could not find CLI jar in latest release")
                    return False

                download_url = jar_asset["browser_download_url"]
                print(f"  Downloading from: {download_url}")

                # Download the jar
                response = requests.get(download_url, stream=True, timeout=60)
                response.raise_for_status()

                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0

                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                percent = (downloaded / total_size) * 100
                                print(f"\r  Progress: {percent:.1f}%", end="", flush=True)

                print(f"\n✅ Downloaded successfully: {output_path}")
                print(f"   Size: {downloaded / (1024*1024):.1f} MB")
                return True

            except Exception as e:
                print(f"\n❌ Error downloading validator: {e}")
                return False
        else:
            print("⚠️  Specific version download not yet implemented")
            print("   Please download manually from:")
            print("   https://github.com/MobilityData/gtfs-validator/releases")
            return False

    def _add_error(self, message: str):
        """Add an error to validation results."""
        self.validation_results["errors"].append(message)
        print(f"  ❌ ERROR: {message}")

    def _add_warning(self, message: str):
        """Add a warning to validation results."""
        self.validation_results["warnings"].append(message)
        print(f"  ⚠️  WARNING: {message}")

    def _add_info(self, message: str):
        """Add info to validation results."""
        self.validation_results["info"].append(message)
        print(f"  ℹ️  {message}")

    def print_summary(self):
        """Print validation summary."""
        print("\n" + "=" * 60)
        print("VALIDATION SUMMARY")
        print("=" * 60)
        print(f"Errors: {len(self.validation_results['errors'])}")
        print(f"Warnings: {len(self.validation_results['warnings'])}")
        print(f"Info: {len(self.validation_results['info'])}")

        if self.validation_results["errors"]:
            print("\n❌ ERRORS:")
            for error in self.validation_results["errors"]:
                print(f"  - {error}")

        if self.validation_results["warnings"]:
            print("\n⚠️  WARNINGS:")
            for warning in self.validation_results["warnings"]:
                print(f"  - {warning}")

        print("=" * 60)

        return len(self.validation_results["errors"]) == 0


def main():
    """Main function for command-line usage."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate GTFS feed"
    )
    parser.add_argument(
        "gtfs_path",
        help="Path to GTFS directory"
    )
    parser.add_argument(
        "--download-validator",
        action="store_true",
        help="Download the canonical GTFS validator"
    )
    parser.add_argument(
        "--run-canonical",
        action="store_true",
        help="Run the canonical validator (requires Java and validator jar)"
    )
    parser.add_argument(
        "--validator-jar",
        default="gtfs-validator.jar",
        help="Path to gtfs-validator jar file"
    )
    parser.add_argument(
        "--country",
        default="sg",
        help="Two-letter country code (default: sg)"
    )

    args = parser.parse_args()

    validator = GTFSValidator(args.gtfs_path)

    # Download validator if requested
    if args.download_validator:
        validator.download_canonical_validator(args.validator_jar)
        return

    # Run validation
    print("=" * 60)
    print("GTFS FEED VALIDATION")
    print("=" * 60)

    # Basic structure validation
    if not validator.validate_structure():
        print("\n❌ Basic structure validation failed")
        sys.exit(1)

    # gtfs-kit validation
    validator.validate_with_gtfs_kit()

    # Canonical validator (if requested)
    if args.run_canonical:
        validator.run_canonical_validator(
            validator_jar=args.validator_jar,
            country_code=args.country
        )

    # Print summary
    success = validator.print_summary()

    if success:
        print("\n✅ Validation passed!")
        sys.exit(0)
    else:
        print("\n❌ Validation failed with errors")
        sys.exit(1)


if __name__ == "__main__":
    main()

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a GTFS (General Transit Feed Specification) feed builder for Singapore's public transport system. It combines:
- **Bus data** from the LTA (Land Transport Authority) DataMall API
- **Train data** (MRT/LRT) from LTA static shapefiles and manual route data

The system generates a production-ready, validated GTFS feed covering Singapore's entire public transit network.

**Key accomplishment**: Combined bus+train feed is production-ready with successful validation.

## Architecture

### Data Flow Pipeline

```
Bus: LTA DataMall API → API Client (with caching) → GTFS Generator → Validation → Output
Train: Static Files → Data Loader → GTFS Generator → Validation → Output
```

1. **LTA API Client** (`lta_api_client.py`):
   - Handles paginated API calls ($skip parameter, 500 records per page) with optional JSON caching
   - Loads train data from static CSV files (`static_data/`)
2. **GTFS Generator** (`gtfs_generator.py`):
   - Transforms LTA data to GTFS format with critical fixes applied
   - Merges bus and train data into unified GTFS feed
3. **Validator** (`gtfs_validator.py`): Multi-level validation (basic structure, gtfs-kit, canonical MobilityData validator)

### Critical Implementation Details

**Distance-based Time Calculations** (gtfs_generator.py:26-46, 192-241):
- Uses Haversine formula to calculate great-circle distances between stops
- Average bus speed: 25 km/h (realistic for urban Singapore)
- Minimum 1 minute between consecutive stops
- This fixed 210 "fast_travel" validation warnings

**Route Deduplication** (gtfs_generator.py:112-122):
- LTA API returns routes twice (once per direction)
- We deduplicate using set() to ensure unique route_id values
- Direction is handled via `direction_id` in trips.txt
- Fixed critical duplicate_key ERROR that prevented feed from loading

**Direction Mapping** (gtfs_generator.py:183-184):
- LTA uses direction values 1, 2
- GTFS spec requires direction_id values 0, 1
- Mapping: `gtfs_direction_id = 0 if direction == 1 else 1`
- Fixed 177 unexpected_enum_value warnings

**Stop Coordinates Cache** (gtfs_generator.py:24, 86-89):
- Cached in `self.stop_coordinates` dict during stops.txt generation
- Used for distance calculations in stop_times.txt generation
- Critical for performance (avoids repeated lookups)

### API Caching System

The caching system (`api_cache.py`, `lta_api_client.py`) is essential for development:

- **Cache structure**: JSON files with metadata (timestamp, record_count) + data array
- **Total size**: ~9.6 MB (bus_routes.json is largest at 8.4 MB)
- **Performance**: Reduces generation time from 2-3 minutes → 5 seconds
- **Usage**: Always use `--use-cache` for development unless you need fresh data

## Development Commands

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variable (or add to .env)
export LTA_API_KEY="your_api_key_here"
```

### Generate GTFS Feed

**From cache (fastest, for development):**
```bash
python build_gtfs.py --use-cache --validate
```

**From API (creates fresh cache):**
```bash
python build_gtfs.py --save-cache --validate
```

**From API without caching:**
```bash
python build_gtfs.py
```

### Validation

**Quick validation (gtfs-kit):**
```bash
python build_gtfs.py --use-cache --validate
```

**Comprehensive validation (requires Java 21):**
```bash
# Download validator once (creates gtfs-validator-7.1.0-cli.jar)
python gtfs_validator.py gtfs_output --download-validator

# Run canonical validation
python gtfs_validator.py gtfs_output --run-canonical --validator-jar gtfs-validator-7.1.0-cli.jar --country sg
```

**Standalone validation:**
```bash
python gtfs_validator.py gtfs_output
```

### Inspect Cache
```bash
python inspect_cache.py
```

Shows cache statistics, timestamps, file sizes.

## GitHub Actions Workflow

Automated nightly builds run at 4:00 AM Singapore Time (20:00 UTC):

- **Workflow file**: `.github/workflows/nightly-gtfs-build.yml`
- **Setup**: Requires `LTA_API_KEY` in GitHub Secrets
- **Output**: GTFS feed ZIP, validation reports, feed statistics
- **Auto-commit**: Can optionally commit updated feeds (currently enabled in .gitignore comments)
- **Weekly releases**: Creates GitHub release every Sunday

**Manual trigger:**
```bash
gh workflow run nightly-gtfs-build.yml
```

See `GITHUB_ACTIONS_SETUP.md` for detailed configuration.

## Configuration

All configuration is in `config.py`:

- **API endpoints**: Uses HTTPS (not HTTP) - critical fix
- **API key**: Loaded from `LTA_API_KEY` environment variable
- **GTFS metadata**: Agency name, URL, timezone (Asia/Singapore)
- **Pagination**: 500 records per page

## Validation Status

**Current status**: Production Ready (Grade A+)

**Validation results** (from validation_output/report.json):
- Errors: 0
- Warnings: 2 (cosmetic only)
  - mixed_case_recommended_field (6 occurrences) - actual LTA stop names
  - same_name_and_description_for_stop (4 occurrences) - limited LTA metadata

**All critical fixes documented in**:
- `FIXES_APPLIED.md` - GTFS compliance fixes
- `VALIDATION_EXIT_CODE_FIX.md` - Exit code handling for CI/CD

### Exit Code Behavior (P1 Fix - 2025-10-31)

**CRITICAL**: Validation scripts now properly fail with exit code 1 when errors are detected.

The canonical validator (gtfs_validator.py:260-302) now:
1. Parses `report.json` to check for ERROR-level notices
2. Returns `False` when errors are found (not just when Java process fails)
3. Properly fails builds in CI/CD pipelines

Both `build_gtfs.py` and `gtfs_validator.py` now:
- Check return values from validation methods
- Exit with `sys.exit(1)` when validation fails
- Display clear error messages before exiting

This ensures GitHub Actions and other automation properly detect validation failures.

## Key Files

- `config.py`: Configuration (API keys, endpoints, GTFS metadata)
- `lta_api_client.py`: API client with pagination and caching
- `api_cache.py`: Cache management (save/load JSON)
- `gtfs_generator.py`: Core GTFS generation logic with all validation fixes
- `gtfs_validator.py`: Multi-level validation wrapper
- `build_gtfs.py`: Main orchestration script with CLI
- `inspect_cache.py`: Cache inspection utility

## Common Development Scenarios

### Adding New GTFS Fields

1. Modify appropriate method in `gtfs_generator.py` (e.g., `generate_stops_txt`)
2. Update CSV headers and row data
3. Test with `--use-cache --validate`
4. Run canonical validator to ensure GTFS compliance

### Updating Time Calculations

Time calculations are in `generate_trips_and_stop_times` (gtfs_generator.py:192-244):
- Modify `average_speed_kmh` for different speeds
- Adjust `dwell_time_minutes` for stop dwell time
- Keep minimum 1 minute between stops

### Debugging Validation Issues

1. Run canonical validator: `python gtfs_validator.py gtfs_output --run-canonical --country sg`
2. Open `validation_output/report.html` in browser
3. Check `validation_output/report.json` for machine-readable results
4. Reference `VALIDATION_GUIDE.md` for common issues

### Updating API Data

When LTA API structure changes:
1. Delete old cache: `rm -rf api_cache/`
2. Regenerate: `python build_gtfs.py --save-cache`
3. Check for errors in data transformation
4. Validate: `python gtfs_validator.py gtfs_output --run-canonical`

## Important Context

### Why Caching is Essential
- LTA API is paginated (500 records/page)
- Total records: 5,175 stops + 580 services + 26,121 routes
- Without cache: ~2-3 minutes with rate limiting
- With cache: ~5 seconds

### Why Distance Calculations Matter
- Initial implementation used fixed 2-minute intervals
- Created impossible speeds (465 km/h recorded)
- Now uses Haversine formula with realistic 25 km/h average
- Critical for GTFS compliance and usable routing

### Why Route Deduplication is Critical
- LTA returns same route twice (one per direction)
- GTFS spec requires unique route_id
- Without fix: Feed won't load in transit apps (ERROR level)
- Direction handled via direction_id field in trips.txt

### Contact Information Fix
Feed requires contact information for maintainability:
- Email: `feedback@lta.gov.sg`
- URL: `https://www.lta.gov.sg/content/ltagov/en/contact_us.html`

## Environment Setup

API key can be set via:
1. Environment variable: `export LTA_API_KEY="key"`
2. `.env` file (gitignored)
3. Command line: `--api-key "key"`

**Never commit API keys to repository.**

## Train Data Integration

**NEW**: The feed now includes Singapore's MRT/LRT train network alongside buses.

### Train Data Sources
- **Station locations**: LTA shapefile (`TrainStation_Aug2025.zip`)
- **Station codes**: Manual mapping from Wikipedia/official sources
- **Route sequences**: Manually created based on official line maps
- **Line definitions**: 12 lines (NSL, EWL, CG, NEL, CCL, DTL, TEL, BP, SW, SE, PW, PE)

### Train Files
- `generate_train_data.py`: Generates train CSV files
- `create_station_mapping.py`: Creates station code mapping
- `static_data/train_stations.csv`: 282 stations with coordinates
- `static_data/train_lines.csv`: 12 train lines with colors
- `static_data/train_routes.csv`: 222 station stops
- `static_data/station_code_mapping.csv`: 220 code-to-name mappings

### Train Parameters
- **Average speed**: 40 km/h (vs 25 km/h for buses)
- **Dwell time**: 0.5 minutes (vs 1 minute for buses)
- **Service start**: 05:00 (vs 06:00 for buses)
- **Route type**: 1 (Subway/Metro) in GTFS

See `TRAIN_INTEGRATION.md` for complete documentation.

## Documentation

- `README.md`: User-facing usage guide
- `TRAIN_INTEGRATION.md`: Train data integration documentation
- `VALIDATION_GUIDE.md`: Comprehensive validation documentation
- `FIXES_APPLIED.md`: Detailed documentation of all validation fixes
- `GITHUB_ACTIONS_SETUP.md`: GitHub Actions configuration guide
- `SUMMARY.md`: Project implementation summary

## Output

Generated GTFS files in `gtfs_output/`:
- `agency.txt` (1 agency: LTA)
- `stops.txt` (5,457 stops: 5,175 bus + 282 train)
- `routes.txt` (592 routes: 580 bus + 12 train lines)
- `trips.txt` (781 trips: 757 bus + 24 train)
- `stop_times.txt` (26,565 stop times with realistic travel times)
- `calendar.txt` (1 year validity, daily service)
- `feed_info.txt` (with contact information)

Total feed size: ~1.5 MB (buses + trains)

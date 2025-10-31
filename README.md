# Singapore GTFS Feed Builder

Build a GTFS (General Transit Feed Specification) feed for Singapore's public bus system using the LTA DataMall API.

## Overview

This tool fetches real-time bus data from Singapore's Land Transport Authority (LTA) DataMall API and converts it into a standardized GTFS feed format that can be used with various transit applications and mapping services.

## Features

- Fetches all bus stops, routes, and services from LTA DataMall API
- Generates complete GTFS feed with the following files:
  - `agency.txt` - Transit agency information
  - `stops.txt` - Bus stop locations and details
  - `routes.txt` - Bus route information
  - `trips.txt` - Individual trips for each route
  - `stop_times.txt` - Stop sequences and timing for each trip
  - `calendar.txt` - Service calendar
  - `feed_info.txt` - Feed metadata

## Requirements

- Python 3.7+
- LTA DataMall API key (get one at https://datamall.lta.gov.sg)

## Installation

1. Clone or download this repository

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure your API key in `config.py`:
```python
LTA_API_KEY = "your_api_key_here"
```

## Usage

### Basic Usage

Run the script to generate the GTFS feed:

```bash
python build_gtfs.py
```

This will:
1. Fetch all bus stops, services, and routes from LTA DataMall API
2. Generate GTFS files in the `gtfs_output/` directory

### Advanced Usage

Specify custom output directory:
```bash
python build_gtfs.py --output-dir my_gtfs_feed
```

Specify API key via command line:
```bash
python build_gtfs.py --api-key YOUR_API_KEY
```

### API Response Caching

To avoid making repeated API calls (which can be slow), you can save API responses to cache files:

**Save API responses to cache** (first run):
```bash
python build_gtfs.py --save-cache
```

This will:
1. Fetch data from the LTA DataMall API
2. Save responses to JSON files in `api_cache/` directory
3. Generate the GTFS feed

**Load from cache** (subsequent runs):
```bash
python build_gtfs.py --use-cache
```

This will:
1. Load data from cached JSON files (much faster!)
2. Generate the GTFS feed without making API calls
3. No API key required when using cache

**Cache files:**
- `api_cache/bus_stops.json` (954 KB)
- `api_cache/bus_services.json` (243 KB)
- `api_cache/bus_routes.json` (8.4 MB)

Benefits of caching:
- 🚀 **Fast**: Load data in seconds instead of minutes
- 💾 **Offline**: Work without internet connection
- 🔑 **No API key needed**: Use cached data without authentication
- 💰 **API rate limits**: Avoid hitting API rate limits during development

**Inspect cached data:**
```bash
python inspect_cache.py
```

This will show details about cached files including record counts, file sizes, and timestamps.

### Using Virtual Environment

It's recommended to use a virtual environment:

```bash
# Activate the virtual environment
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt

# Run the script
python build_gtfs.py
```

## Automated Builds (GitHub Actions)

This project includes a GitHub Actions workflow for automated nightly GTFS feed generation.

### Features

- 🕐 **Scheduled Runs**: Automatically builds GTFS feed every night at 4:00 AM Singapore Time
- ✅ **Automatic Validation**: Runs canonical GTFS validator on every build
- 📦 **Artifacts**: Saves generated feeds and validation reports
- 🔄 **Auto-commit**: Optionally commits updated feeds to repository
- 📋 **Weekly Releases**: Creates GitHub releases every Sunday

### Setup

See [GITHUB_ACTIONS_SETUP.md](GITHUB_ACTIONS_SETUP.md) for complete setup instructions.

**Quick setup:**
1. Add `LTA_API_KEY` to repository secrets
2. Enable GitHub Actions in repository settings
3. Workflow runs automatically every night at 4am SGT

**Manual trigger:**
```bash
# Via GitHub CLI
gh workflow run nightly-gtfs-build.yml

# Or use GitHub UI: Actions → Nightly GTFS Feed Generation → Run workflow
```

### Workflow Output

Each run produces:
- ✅ GTFS feed ZIP file (`gtfs-sg-YYYYMMDD.zip`)
- ✅ Validation report (HTML and JSON)
- ✅ Feed statistics
- ✅ Error checking (fails if validation errors found)

## GTFS Validation

The project includes comprehensive GTFS validation tools to ensure feed quality.

### Quick Validation

Validate during feed generation:
```bash
python build_gtfs.py --use-cache --validate
```

This performs:
- ✅ Structure validation (checks for required files)
- ✅ Data validation using gtfs-kit (checks for common issues)
- ✅ Statistics reporting

### Standalone Validation

Validate an existing GTFS feed:
```bash
python gtfs_validator.py gtfs_output
```

### Canonical Validator (Comprehensive)

For the most thorough validation, use the MobilityData canonical GTFS validator:

**1. Download the validator:**
```bash
python gtfs_validator.py gtfs_output --download-validator
```

This downloads the official Java-based validator (~50 MB).

**2. Run comprehensive validation:**
```bash
python gtfs_validator.py gtfs_output --run-canonical --country sg
```

Requirements:
- Java 17 or higher installed
- Generates detailed HTML report in `validation_output/`

**Alternative: Web Validator**

You can also use the online validator:
1. Zip your GTFS feed: `cd gtfs_output && zip -r ../gtfs.zip *.txt`
2. Visit: https://gtfs-validator.mobilitydata.org/
3. Upload the zip file for validation

### Validation Checks

The validation performs these checks:

**Basic Structure:**
- Required files present (agency.txt, stops.txt, routes.txt, trips.txt, stop_times.txt)
- Optional files detection

**Data Quality (gtfs-kit):**
- Stops with missing coordinates
- Trips without stop_times
- Routes without trips
- Feed statistics and counts

**Comprehensive (Canonical Validator):**
- Full GTFS specification compliance
- Semantic validation
- Best practices checks
- Country-specific rules

## Configuration

Edit `config.py` to customize:

- `LTA_API_KEY` - Your LTA DataMall API key
- `GTFS_OUTPUT_DIR` - Output directory for GTFS files
- `AGENCY_NAME` - Transit agency name
- `AGENCY_URL` - Agency website URL
- `AGENCY_TIMEZONE` - Timezone (default: Asia/Singapore)

## Output

The generated GTFS feed will be saved in the `gtfs_output/` directory (or your specified output directory). You can:

- Zip the contents for use with transit apps
- Import into tools like QGIS for visualization
- Use with routing engines like OpenTripPlanner
- Validate using the GTFS validator

## Project Structure

```
gtfs-sg/
├── .github/
│   └── workflows/
│       └── nightly-gtfs-build.yml  # GitHub Actions workflow
├── build_gtfs.py                   # Main build script
├── lta_api_client.py               # LTA DataMall API client with caching
├── gtfs_generator.py               # GTFS file generator
├── gtfs_validator.py               # GTFS feed validator
├── api_cache.py                    # API response caching module
├── inspect_cache.py                # Cache inspection utility
├── config.py                       # Configuration
├── requirements.txt                # Python dependencies (includes gtfs-kit)
├── README.md                       # This file
├── GITHUB_ACTIONS_SETUP.md        # GitHub Actions setup guide
├── VALIDATION_GUIDE.md            # Validation documentation
├── FIXES_APPLIED.md               # Validation fixes documentation
├── api_cache/                     # Cached API responses
├── gtfs_output/                   # Generated GTFS files
└── validation_output/             # Validation reports
```

## Notes

- The LTA DataMall API has rate limits; the script includes delays to respect these limits
- Stop times are currently estimated based on average travel times between stops
- For production use, you may want to integrate real-time schedule data

## API Reference

This tool uses the following LTA DataMall API endpoints:

- **Bus Stops**: Returns all bus stops with coordinates
- **Bus Services**: Returns all bus services with operator info
- **Bus Routes**: Returns route details with stop sequences

## License

This project is for educational and personal use. Please ensure you comply with LTA DataMall's terms of service when using their API.

## Contributing

Feel free to submit issues or pull requests to improve this tool.

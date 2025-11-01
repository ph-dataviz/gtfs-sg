"""Configuration for LTA DataMall API and GTFS generation."""

import os

# LTA DataMall API Configuration
LTA_API_KEY = os.getenv("LTA_API_KEY")
LTA_BASE_URL = "https://datamall2.mytransport.sg/ltaodataservice"

# API Endpoints
ENDPOINTS = {
    "bus_stops": f"{LTA_BASE_URL}/BusStops",
    "bus_services": f"{LTA_BASE_URL}/BusServices",
    "bus_routes": f"{LTA_BASE_URL}/BusRoutes"
}

# GTFS Configuration
GTFS_OUTPUT_DIR = "gtfs_output"
AGENCY_NAME = "Land Transport Authority"
AGENCY_URL = "https://www.lta.gov.sg"
AGENCY_TIMEZONE = "Asia/Singapore"
AGENCY_LANG = "en"

# Pagination
RECORDS_PER_PAGE = 500

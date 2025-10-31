"""Generate GTFS feed from LTA DataMall data."""

import os
import csv
import math
from typing import List, Dict, Any, Tuple
from datetime import datetime, date
import config


class GTFSGenerator:
    """Generator for GTFS feed files from LTA DataMall data."""

    def __init__(self, output_dir: str = None):
        """Initialize the GTFS generator.

        Args:
            output_dir: Directory to output GTFS files. Defaults to config.GTFS_OUTPUT_DIR
        """
        self.output_dir = output_dir or config.GTFS_OUTPUT_DIR
        os.makedirs(self.output_dir, exist_ok=True)

        # Cache for stop coordinates lookup
        self.stop_coordinates = {}

    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in kilometers using Haversine formula.

        Args:
            lat1, lon1: Coordinates of first point
            lat2, lon2: Coordinates of second point

        Returns:
            Distance in kilometers
        """
        R = 6371  # Earth's radius in kilometers

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)

        a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
        c = 2 * math.asin(math.sqrt(a))

        return R * c

    def _write_csv(self, filename: str, headers: List[str], rows: List[List[Any]]):
        """Write data to a CSV file.

        Args:
            filename: Name of the CSV file
            headers: List of column headers
            rows: List of data rows
        """
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(rows)
        print(f"  Created {filename} with {len(rows)} rows")

    def generate_agency_txt(self):
        """Generate agency.txt file."""
        print("\nGenerating agency.txt...")
        headers = ["agency_id", "agency_name", "agency_url", "agency_timezone", "agency_lang"]
        rows = [[
            "LTA",
            config.AGENCY_NAME,
            config.AGENCY_URL,
            config.AGENCY_TIMEZONE,
            config.AGENCY_LANG
        ]]
        self._write_csv("agency.txt", headers, rows)

    def generate_stops_txt(self, bus_stops: List[Dict[str, Any]]):
        """Generate stops.txt from bus stops data.

        Args:
            bus_stops: List of bus stop dictionaries from LTA API
        """
        print("\nGenerating stops.txt...")
        headers = ["stop_id", "stop_code", "stop_name", "stop_desc", "stop_lat", "stop_lon"]
        rows = []

        # Build stop coordinates cache for distance calculations
        for stop in bus_stops:
            stop_code = stop["BusStopCode"]
            self.stop_coordinates[stop_code] = (stop["Latitude"], stop["Longitude"])

            rows.append([
                stop_code,
                stop_code,
                stop.get("Description", f"Bus Stop {stop_code}"),
                stop.get("RoadName", ""),
                stop["Latitude"],
                stop["Longitude"]
            ])

        self._write_csv("stops.txt", headers, rows)

    def generate_routes_txt(self, bus_services: List[Dict[str, Any]]):
        """Generate routes.txt from bus services data.

        Args:
            bus_services: List of bus service dictionaries from LTA API
        """
        print("\nGenerating routes.txt...")
        headers = ["route_id", "agency_id", "route_short_name", "route_long_name", "route_type"]
        rows = []

        # Deduplicate routes - only one route per service number
        seen_routes = set()
        for service in bus_services:
            route_id = service["ServiceNo"]
            # route_type = 3 for bus (GTFS standard)

            # Skip if we've already added this route
            if route_id in seen_routes:
                continue

            seen_routes.add(route_id)
            rows.append([
                route_id,
                "LTA",
                service["ServiceNo"],
                f"Bus {service['ServiceNo']} ({service.get('Operator', 'LTA')})",
                "3"  # Bus
            ])

        self._write_csv("routes.txt", headers, rows)

    def generate_trips_and_stop_times(
        self,
        bus_routes: List[Dict[str, Any]],
        bus_services: List[Dict[str, Any]]
    ):
        """Generate trips.txt and stop_times.txt from bus routes data.

        Args:
            bus_routes: List of bus route dictionaries from LTA API
            bus_services: List of bus service dictionaries from LTA API
        """
        print("\nGenerating trips.txt and stop_times.txt...")

        # Group routes by ServiceNo and Direction
        routes_by_service = {}
        for route in bus_routes:
            key = (route["ServiceNo"], route["Direction"])
            if key not in routes_by_service:
                routes_by_service[key] = []
            routes_by_service[key].append(route)

        # Sort stops by StopSequence within each route
        for key in routes_by_service:
            routes_by_service[key].sort(key=lambda x: x["StopSequence"])

        # Generate trips
        trip_headers = ["route_id", "service_id", "trip_id", "trip_headsign", "direction_id"]
        trip_rows = []

        # Generate stop_times
        stop_time_headers = [
            "trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"
        ]
        stop_time_rows = []

        # Create service calendar lookup
        service_info = {s["ServiceNo"]: s for s in bus_services}

        for (service_no, direction), stops in routes_by_service.items():
            # Create trip ID
            trip_id = f"{service_no}_{direction}"

            # Get headsign (destination)
            service_data = service_info.get(service_no, {})
            if direction == 1:
                headsign = f"To {stops[-1]['BusStopCode']}"
            else:
                headsign = f"To {stops[-1]['BusStopCode']}"

            # Add trip
            # Convert LTA direction (1, 2) to GTFS direction_id (0, 1)
            gtfs_direction_id = 0 if direction == 1 else 1

            trip_rows.append([
                service_no,
                "DAILY",  # service_id (we'll create this in calendar.txt)
                trip_id,
                headsign,
                gtfs_direction_id
            ])

            # Add stop_times for this trip
            # Calculate times based on actual distances and realistic bus speeds
            cumulative_time_minutes = 0
            start_hour = 6
            average_speed_kmh = 25  # Average bus speed in urban areas (km/h)
            dwell_time_minutes = 1  # Stop dwell time

            for idx, stop in enumerate(stops):
                stop_code = stop["BusStopCode"]

                # Calculate travel time from previous stop
                if idx > 0:
                    prev_stop_code = stops[idx - 1]["BusStopCode"]

                    # Get coordinates from cache
                    if prev_stop_code in self.stop_coordinates and stop_code in self.stop_coordinates:
                        prev_lat, prev_lon = self.stop_coordinates[prev_stop_code]
                        curr_lat, curr_lon = self.stop_coordinates[stop_code]

                        # Calculate distance in km
                        distance_km = self._haversine_distance(prev_lat, prev_lon, curr_lat, curr_lon)

                        # Calculate travel time in minutes
                        travel_time_minutes = (distance_km / average_speed_kmh) * 60

                        # Add minimum time between stops (to handle very close stops)
                        travel_time_minutes = max(travel_time_minutes, 1.0)

                        cumulative_time_minutes += travel_time_minutes
                    else:
                        # Fallback if coordinates not found
                        cumulative_time_minutes += 2

                # Arrival time
                arrival_minutes = int(cumulative_time_minutes)
                arrival_time = self._format_time(start_hour * 60 + arrival_minutes)

                # Departure time (arrival + dwell time)
                departure_minutes = int(cumulative_time_minutes + dwell_time_minutes)
                departure_time = self._format_time(start_hour * 60 + departure_minutes)

                stop_time_rows.append([
                    trip_id,
                    arrival_time,
                    departure_time,
                    stop_code,
                    stop["StopSequence"]
                ])

                # Add dwell time for next calculation
                cumulative_time_minutes += dwell_time_minutes

        self._write_csv("trips.txt", trip_headers, trip_rows)
        self._write_csv("stop_times.txt", stop_time_headers, stop_time_rows)

    def _format_time(self, minutes: int) -> str:
        """Format minutes since midnight as HH:MM:SS.

        Args:
            minutes: Minutes since midnight

        Returns:
            Time string in HH:MM:SS format
        """
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours:02d}:{mins:02d}:00"

    def generate_calendar_txt(self):
        """Generate calendar.txt file with service periods."""
        print("\nGenerating calendar.txt...")
        headers = [
            "service_id", "monday", "tuesday", "wednesday", "thursday",
            "friday", "saturday", "sunday", "start_date", "end_date"
        ]

        # Create a daily service that runs every day
        today = date.today()
        start_date = today.strftime("%Y%m%d")
        # Set end date to 1 year from now
        end_date = today.replace(year=today.year + 1).strftime("%Y%m%d")

        rows = [[
            "DAILY",
            "1", "1", "1", "1", "1", "1", "1",  # All days of week
            start_date,
            end_date
        ]]

        self._write_csv("calendar.txt", headers, rows)

    def generate_feed_info_txt(self):
        """Generate feed_info.txt file."""
        print("\nGenerating feed_info.txt...")
        headers = [
            "feed_publisher_name", "feed_publisher_url", "feed_lang",
            "feed_start_date", "feed_end_date", "feed_version",
            "feed_contact_email", "feed_contact_url"
        ]

        today = date.today()
        start_date = today.strftime("%Y%m%d")
        end_date = today.replace(year=today.year + 1).strftime("%Y%m%d")
        version = datetime.now().strftime("%Y%m%d_%H%M%S")

        rows = [[
            config.AGENCY_NAME,
            config.AGENCY_URL,
            config.AGENCY_LANG,
            start_date,
            end_date,
            version,
            "feedback@lta.gov.sg",  # Contact email
            "https://www.lta.gov.sg/content/ltagov/en/contact_us.html"  # Contact URL
        ]]

        self._write_csv("feed_info.txt", headers, rows)

    def generate_gtfs_feed(
        self,
        bus_stops: List[Dict[str, Any]],
        bus_services: List[Dict[str, Any]],
        bus_routes: List[Dict[str, Any]]
    ):
        """Generate complete GTFS feed.

        Args:
            bus_stops: List of bus stop dictionaries
            bus_services: List of bus service dictionaries
            bus_routes: List of bus route dictionaries
        """
        print("\n" + "=" * 60)
        print("GENERATING GTFS FEED")
        print("=" * 60)

        self.generate_agency_txt()
        self.generate_stops_txt(bus_stops)
        self.generate_routes_txt(bus_services)
        self.generate_trips_and_stop_times(bus_routes, bus_services)
        self.generate_calendar_txt()
        self.generate_feed_info_txt()

        print("\n" + "=" * 60)
        print(f"GTFS feed generated successfully in: {self.output_dir}")
        print("=" * 60)

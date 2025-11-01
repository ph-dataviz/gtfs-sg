"""Client for LTA DataMall API."""

import requests
import time
from typing import List, Dict, Any, Optional
import config
from api_cache import APICache


class LTADataMallClient:
    """Client for interacting with LTA DataMall API."""

    def __init__(self, api_key: str = None, use_cache: bool = False, cache_dir: str = "api_cache"):
        """Initialize the LTA DataMall client.

        Args:
            api_key: LTA DataMall API key. If not provided, uses config.LTA_API_KEY
            use_cache: If True, load data from cache instead of making API calls
            cache_dir: Directory to store/load cached API responses
        """
        self.api_key = api_key or config.LTA_API_KEY
        self.headers = {
            "AccountKey": self.api_key,
            "accept": "application/json"
        }
        self.base_delay = 0.5  # Delay between requests to avoid rate limiting
        self.use_cache = use_cache
        self.cache = APICache(cache_dir=cache_dir)

    def _make_request(self, url: str, params: Dict = None) -> Dict[str, Any]:
        """Make a request to the LTA DataMall API.

        Args:
            url: API endpoint URL
            params: Query parameters

        Returns:
            JSON response as dictionary
        """
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error making request to {url}: {e}")
            raise

    def _fetch_all_pages(self, endpoint_url: str) -> List[Dict[str, Any]]:
        """Fetch all pages from a paginated endpoint.

        Args:
            endpoint_url: The API endpoint URL

        Returns:
            List of all records from all pages
        """
        all_records = []
        skip = 0

        while True:
            print(f"Fetching records from {endpoint_url} (skip={skip})...")
            params = {"$skip": skip}

            response_data = self._make_request(endpoint_url, params)
            records = response_data.get("value", [])

            if not records:
                break

            all_records.extend(records)
            print(f"  Retrieved {len(records)} records (total: {len(all_records)})")

            # Check if there are more records
            if len(records) < config.RECORDS_PER_PAGE:
                break

            skip += config.RECORDS_PER_PAGE
            time.sleep(self.base_delay)  # Rate limiting

        print(f"Total records fetched: {len(all_records)}")
        return all_records

    def get_bus_stops(self, save_cache: bool = False) -> List[Dict[str, Any]]:
        """Fetch all bus stops.

        Args:
            save_cache: If True, save the API response to cache

        Returns:
            List of bus stop dictionaries
        """
        print("\n=== Fetching Bus Stops ===")

        if self.use_cache:
            try:
                print("Loading from cache...")
                return self.cache.load("bus_stops")
            except FileNotFoundError:
                print("Cache not found, fetching from API...")
                self.use_cache = False

        data = self._fetch_all_pages(config.ENDPOINTS["bus_stops"])

        if save_cache:
            print("Saving to cache...")
            self.cache.save("bus_stops", data)

        return data

    def get_bus_services(self, save_cache: bool = False) -> List[Dict[str, Any]]:
        """Fetch all bus services.

        Args:
            save_cache: If True, save the API response to cache

        Returns:
            List of bus service dictionaries
        """
        print("\n=== Fetching Bus Services ===")

        if self.use_cache:
            try:
                print("Loading from cache...")
                return self.cache.load("bus_services")
            except FileNotFoundError:
                print("Cache not found, fetching from API...")
                self.use_cache = False

        data = self._fetch_all_pages(config.ENDPOINTS["bus_services"])

        if save_cache:
            print("Saving to cache...")
            self.cache.save("bus_services", data)

        return data

    def get_bus_routes(self, save_cache: bool = False) -> List[Dict[str, Any]]:
        """Fetch all bus routes.

        Args:
            save_cache: If True, save the API response to cache

        Returns:
            List of bus route dictionaries (each route-stop combination)
        """
        print("\n=== Fetching Bus Routes ===")

        if self.use_cache:
            try:
                print("Loading from cache...")
                return self.cache.load("bus_routes")
            except FileNotFoundError:
                print("Cache not found, fetching from API...")
                self.use_cache = False

        data = self._fetch_all_pages(config.ENDPOINTS["bus_routes"])

        if save_cache:
            print("Saving to cache...")
            self.cache.save("bus_routes", data)

        return data

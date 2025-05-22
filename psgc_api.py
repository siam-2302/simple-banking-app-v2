import requests
import os
import logging
from functools import lru_cache

# Configure logging
logger = logging.getLogger(__name__)

# Base URL can be overridden with an environment variable
BASE_URL = os.getenv("PSGC_API_BASE_URL", "https://psgc.gitlab.io/api")
TIMEOUT = 5  # seconds

@lru_cache(maxsize=16)
def get_regions():
    url = f"{BASE_URL}/regions"
    try:
        response = requests.get(url, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()
        data.sort(key=lambda x: x['name'])
        return data
    except requests.RequestException as e:
        logger.warning(f"Failed to fetch regions: {e}")
        return []

@lru_cache(maxsize=16)
def get_provinces(region_code=None):
    url = f"{BASE_URL}/provinces"
    try:
        response = requests.get(url, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()
        if region_code:
            data = [p for p in data if p.get('regionCode') == region_code]
        data.sort(key=lambda x: x['name'])
        return data
    except requests.RequestException as e:
        logger.warning(f"Failed to fetch provinces: {e}")
        return []

@lru_cache(maxsize=16)
def get_cities(province_code=None):
    url = f"{BASE_URL}/cities"
    try:
        response = requests.get(url, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()
        if province_code:
            data = [c for c in data if c.get('provinceCode') == province_code]
        data.sort(key=lambda x: x['name'])
        return data
    except requests.RequestException as e:
        logger.warning(f"Failed to fetch cities: {e}")
        return []

@lru_cache(maxsize=16)
def get_municipalities(province_code=None):
    url = f"{BASE_URL}/municipalities"
    try:
        response = requests.get(url, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()
        if province_code:
            data = [m for m in data if m.get('provinceCode') == province_code]
        data.sort(key=lambda x: x['name'])
        return data
    except requests.RequestException as e:
        logger.warning(f"Failed to fetch municipalities: {e}")
        return []

@lru_cache(maxsize=16)
def get_barangays(city_code=None, municipality_code=None):
    url = f"{BASE_URL}/barangays"
    try:
        response = requests.get(url, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()
        if city_code:
            data = [b for b in data if b.get('cityCode') == city_code]
        elif municipality_code:
            data = [b for b in data if b.get('municipalityCode') == municipality_code]
        else:
            return []  # No filter
        data.sort(key=lambda x: x['name'])
        return data
    except requests.RequestException as e:
        logger.warning(f"Failed to fetch barangays: {e}")
        return []

def get_region_by_code(code):
    regions = get_regions()
    return next((r for r in regions if r['code'] == code), None)

def get_province_by_code(code):
    provinces = get_provinces()
    return next((p for p in provinces if p['code'] == code), None)

def get_city_by_code(code):
    cities = get_cities()
    return next((c for c in cities if c['code'] == code), None)

def get_municipality_by_code(code):
    municipalities = get_municipalities()
    return next((m for m in municipalities if m['code'] == code), None)

def get_barangay_by_code(code):
    url = f"{BASE_URL}/barangays/{code}"
    try:
        response = requests.get(url, timeout=TIMEOUT)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.warning(f"Failed to fetch barangay {code}: {e}")
        return None

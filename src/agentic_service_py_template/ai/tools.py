import json
import logging
from random import randint

logger = logging.getLogger(__name__)


async def get_weather(location: str) -> str:
    """Get current weather for a location."""
    logger.info("get_weather(%s)", location)
    conditions = ["sunny", "partly cloudy", "rainy", "stormy"]
    return json.dumps({
        "location": location,
        "condition": conditions[randint(0, 3)],
        "temperature_f": randint(50, 105),
        "humidity": randint(30, 90),
    })


async def get_property_info(address: str, zip_code: str) -> str:
    """Get detailed property information."""
    logger.info("get_property_info(%s, %s)", address, zip_code)
    return json.dumps({
        "address": address,
        "zip_code": zip_code,
        "bedrooms": randint(2, 5),
        "bathrooms": randint(1, 4),
        "square_feet": randint(1000, 3500),
        "year_built": randint(1980, 2024),
        "property_type": "Single Family Residence",
        "lot_size_sqft": randint(4000, 15000),
    })


async def get_mls_property_raw_data(source_listing_key: str) -> str:
    """Get raw MLS property listing data."""
    logger.info("get_mls_property_raw_data(%s)", source_listing_key)
    return json.dumps({
        "listing_key": source_listing_key,
        "list_price": randint(200000, 600000),
        "days_on_market": randint(1, 120),
        "mls_status": "Active",
        "public_remarks": "Beautiful home in great neighborhood...",
    })


ALL_TOOLS = [
    get_weather,
    get_property_info,
    get_mls_property_raw_data,
]

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City and state, e.g. 'Austin, TX'"},
                },
                "required": ["location"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_property_info",
            "description": "Get detailed property information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "address": {"type": "string", "description": "Property street address"},
                    "zip_code": {"type": "string", "description": "Property ZIP code"},
                },
                "required": ["address", "zip_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_mls_property_raw_data",
            "description": "Get raw MLS property listing data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "source_listing_key": {"type": "string", "description": "MLS source listing key"},
                },
                "required": ["source_listing_key"],
            },
        },
    },
]

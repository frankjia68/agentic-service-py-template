import json

import pytest

from agentic_service_py_template.ai.tools import (
    ALL_TOOLS,
    TOOL_DEFINITIONS,
    get_mls_property_raw_data,
    get_property_info,
    get_weather,
)


def test_all_tools_is_list():
    assert isinstance(ALL_TOOLS, list)
    assert len(ALL_TOOLS) == 3


def test_tool_has_required_attributes():
    for tool in ALL_TOOLS:
        assert callable(tool)


def test_tool_definitions_is_list():
    assert isinstance(TOOL_DEFINITIONS, list)
    assert len(TOOL_DEFINITIONS) == 3


def test_tool_definitions_have_correct_structure():
    for td in TOOL_DEFINITIONS:
        assert td["type"] == "function"
        assert "function" in td
        assert "name" in td["function"]
        assert "description" in td["function"]
        assert "parameters" in td["function"]


@pytest.mark.asyncio
async def test_get_weather():
    result = await get_weather(location="Austin, TX")
    data = json.loads(result)
    assert data["location"] == "Austin, TX"
    assert data["condition"] in ["sunny", "partly cloudy", "rainy", "stormy"]
    assert 50 <= data["temperature_f"] <= 105


@pytest.mark.asyncio
async def test_get_property_info():
    result = await get_property_info(address="456 Oak Ave", zip_code="90210")
    data = json.loads(result)
    assert data["address"] == "456 Oak Ave"
    assert 2 <= data["bedrooms"] <= 5


@pytest.mark.asyncio
async def test_get_mls_data():
    result = await get_mls_property_raw_data(source_listing_key="MLS123")
    data = json.loads(result)
    assert data["listing_key"] == "MLS123"

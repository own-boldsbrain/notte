#!/usr/bin/env python3
"""
Test script to verify the fix for the Union of no types issue.
"""

import sys
sys.path.insert(0, './packages/notte-core/src')

from notte_core.utils.pydantic_schema import create_model_from_schema

# This is the schema that was causing the issue
test_schema = {
    "$defs": {
        "DayHours": {
            "properties": {
                "break_end": {"anyOf": [{"type": "string"}, {"type": "null"}], "default": None, "title": "Break End"},
                "break_start": {"anyOf": [{"type": "string"}, {"type": "null"}], "default": None, "title": "Break Start"},
                "close_time": {"anyOf": [{"type": "string"}, {"type": "null"}], "default": None, "title": "Close Time"},
                "is_closed": {"default": False, "title": "Is Closed", "type": "boolean"},
                "is_data_available": {"default": True, "title": "Is Data Available", "type": "boolean"},
                "open_time": {"anyOf": [{"type": "string"}, {"type": "null"}], "default": None, "title": "Open Time"}
            },
            "title": "DayHours",
            "type": "object"
        }
    },
    "properties": {
        "monday": {
            "anyOf": [
                {"$ref": "#/$defs/DayHours"},
                {"type": "null"}
            ],
            "default": None
        },
        "restaurant_name": {
            "title": "Restaurant Name",
            "type": "string"
        }
    },
    "required": ["restaurant_name"],
    "title": "RestaurantHours", 
    "type": "object"
}

try:
    print("Testing the fixed schema processing...")
    model = create_model_from_schema(test_schema)
    print(f"Success! Created model: {model}")
    print(f"Model fields: {model.model_fields}")
    
    # Test creating an instance
    instance = model(restaurant_name="Test Restaurant")
    print(f"Created instance: {instance}")
    print("Fix verified successfully!")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
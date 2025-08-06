# file_schema_validator.py – Validate input/output file schemas for Drone Sawit
import json
import pandas as pd
def validate_geojson(path):
    with open(path) as f:
        data = json.load(f)
    if not isinstance(data, dict) or "features" not in data:
        raise ValueError("Invalid GeoJSON: Missing 'features' key.")
    for feat in data["features"]:
        if "geometry" not in feat or "properties" not in feat:
            raise ValueError("Invalid GeoJSON feature structure.")
    return True

def validate_csv(path, required_columns):
    df = pd.read_csv(path)
    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")
    return True

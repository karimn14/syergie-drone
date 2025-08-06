import json

def load_ai_predictions(path="predicted_trees.geojson"):
    with open(path) as f:
        data = json.load(f)
    trees = []
    for f in data["features"]:
        if f["properties"]["sex"] == "female" and f["properties"].get("bloom", False):
            trees.append({
                "id": f["properties"]["id"],
                "lat": f["geometry"]["coordinates"][1],
                "lon": f["geometry"]["coordinates"][0],
                "age": f["properties"].get("age", 7),
                "confidence": f["properties"].get("confidence", 0.9)
            })
    return trees

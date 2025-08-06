import json

def generate_plan(waypoints, output_file="route_pollination.plan"):
    plan = {
        "fileType": "Plan",
        "mission": {
            "cruiseSpeed": 5, "firmwareType": 12, "hoverSpeed": 3,
            "items": [],
            "plannedHomePosition": [waypoints[0]["lat"], waypoints[0]["lon"], 10],
            "vehicleType": 2, "version": 2
        },
        "geoFence": {"circles": [], "polygons": [], "version": 2},
        "rallyPoints": {"points": [], "version": 2},
        "version": 1
    }
    for i, wp in enumerate(waypoints):
        plan["mission"]["items"].append({
            "command": 16, "doJumpId": i+1, "frame": 3, "type": "SimpleItem",
            "params": [0, 0, 0, None, wp["lat"], wp["lon"], 10],
            "autoContinue": True, "Altitude": 10, "AltitudeMode": 1
        })
    with open(output_file, "w") as f:
        json.dump(plan, f, indent=2)

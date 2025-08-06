# battery_route_splitter.py – Split long route into battery-safe segments
def split_waypoints(waypoints, max_per_segment=30):
    """
    Splits waypoints into chunks for multiple safe flight segments
    Args:
        waypoints (list): list of waypoints
        max_per_segment (int): max points per mission (battery safe)
    Returns:
        List of lists (segments)
    """
    return [waypoints[i:i+max_per_segment] for i in range(0, len(waypoints), max_per_segment)]

def generate_segmented_plans(waypoints, base_filename="segment", altitude=10):
    import json
    segments = split_waypoints(waypoints)
    for idx, seg in enumerate(segments):
        plan = {
            "fileType": "Plan",
            "mission": {
                "cruiseSpeed": 5, "firmwareType": 12, "hoverSpeed": 3,
                "items": [],
                "plannedHomePosition": [seg[0]["lat"], seg[0]["lon"], altitude],
                "vehicleType": 2, "version": 2
            },
            "geoFence": {"circles": [], "polygons": [], "version": 2},
            "rallyPoints": {"points": [], "version": 2},
            "version": 1
        }
        for i, wp in enumerate(seg):
            plan["mission"]["items"].append({
                "command": 16, "doJumpId": i+1, "frame": 3, "type": "SimpleItem",
                "params": [0, 0, 0, None, wp["lat"], wp["lon"], altitude],
                "autoContinue": True, "Altitude": altitude, "AltitudeMode": 1
            })
        with open(f"{base_filename}_{idx+1}.plan", "w") as f:
            json.dump(plan, f, indent=2)

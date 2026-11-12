# enhanced_route_generator.py – Spline-smoothed route with altitude control
import json
import numpy as np
from scipy.interpolate import splprep, splev

def generate_smoothed_plan(waypoints, output_file="route_pollination_smoothed.plan", altitude=10):
    lats = [wp["lat"] for wp in waypoints]
    lons = [wp["lon"] for wp in waypoints]
    tck, _ = splprep([lats, lons], s=0)
    u_fine = np.linspace(0, 1, len(waypoints) * 5)
    smoothed = splev(u_fine, tck)
    plan = {
        "fileType": "Plan",
        "mission": {
            "cruiseSpeed": 5, "firmwareType": 12, "hoverSpeed": 3,
            "items": [],
            "plannedHomePosition": [smoothed[0][0], smoothed[1][0], altitude],
            "vehicleType": 2, "version": 2
        },
        "geoFence": {"circles": [], "polygons": [], "version": 2},
        "rallyPoints": {"points": [], "version": 2},
        "version": 1
    }
    for i in range(len(smoothed[0])):
        plan["mission"]["items"].append({
            "command": 16, "doJumpId": i+1, "frame": 3, "type": "SimpleItem",
            "params": [0, 0, 0, None, smoothed[0][i], smoothed[1][i], altitude],
            "autoContinue": True, "Altitude": altitude, "AltitudeMode": 1
        })
    with open(output_file, "w") as f:
        json.dump(plan, f, indent=2)

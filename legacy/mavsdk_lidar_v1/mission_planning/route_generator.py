# mission_planning/route_generator.py
import json
import logging

logger = logging.getLogger("DroneSawit")

def generate_mission_plan(waypoints, output_file, altitude):
    """
    Membuat file .plan sederhana dari daftar waypoints.
    """
    if not waypoints:
        logger.warning("Tidak ada waypoints untuk dibuatkan rencana misi.")
        return

    # Struktur dasar file .plan
    plan = {
        "fileType": "Plan",
        "geoFence": {"circles": [], "polygons": [], "version": 2},
        "mission": {
            "cruiseSpeed": 5,
            "firmwareType": 12,
            "hoverSpeed": 3,
            "items": [],
            "plannedHomePosition": [waypoints[0]["lat"], waypoints[0]["lon"], altitude],
            "vehicleType": 2,
            "version": 2
        },
        "rallyPoints": {"points": [], "version": 2},
        "version": 1
    }

    # Menambahkan setiap waypoint ke dalam misi
    for i, wp in enumerate(waypoints):
        item = {
            "autoContinue": True,
            "command": 16,  # MAV_CMD_NAV_WAYPOINT
            "doJumpId": i + 1,
            "frame": 3,  # MAV_FRAME_GLOBAL_RELATIVE_ALT
            "params": [
                0,  # Hold time
                0,  # Acceptance radius
                0,  # Pass through
                None,  # Yaw
                wp["lat"],
                wp["lon"],
                altitude
            ],
            "type": "SimpleItem"
        }
        plan["mission"]["items"].append(item)
    
    # Menyimpan file
    try:
        with open(output_file, "w") as f:
            json.dump(plan, f, indent=2)
        logger.info("File .plan berhasil disimpan.")
    except Exception as e:
        logger.error(f"Gagal menyimpan file .plan: {e}", exc_info=True)


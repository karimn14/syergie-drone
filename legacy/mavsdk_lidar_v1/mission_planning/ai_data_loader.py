# mission_planning/ai_data_loader.py
import json
import logging

logger = logging.getLogger("DroneSawit")

def load_waypoints(path):
    """Memuat koordinat dari file GeoJSON."""
    waypoints = []
    try:
        with open(path) as f:
            data = json.load(f)
        
        for feature in data["features"]:
            # Kita hanya butuh koordinat untuk rute
            coords = feature["geometry"]["coordinates"]
            waypoints.append({
                "lat": coords[1],
                "lon": coords[0],
            })
        return waypoints
    except FileNotFoundError:
        logger.error(f"File data AI tidak ditemukan di path: {path}")
        return []
    except Exception as e:
        logger.error(f"Gagal memuat waypoints: {e}", exc_info=True)
        return []


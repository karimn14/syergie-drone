# config.py
# Pusat konfigurasi untuk misi navigasi otonom.
import logging

DRONE_CONFIG = {
    # --- Path File ---
    "AI_PREDICTIONS_FILE": "mission_data/predicted_trees.geojson",
    "MISSION_PLAN_OUTPUT_FILE": "mission_data/route_mission.plan",
    "LOG_FILE": "mission_log.log",

    # --- Koneksi Perangkat Keras ---
    # -> FOR JETSON NANO
    #"PX4_CONNECTION_STRING": "serial:///dev/ttyACM0:57600",
    #-> FOR LAPTOP
    "PX4_CONNECTION_STRING": "serial:///COM4:57600",
    "LIDAR_PORT": "/dev/ttyUSB0", # Asumsikan hanya satu Lidar menghadap depan
    "LIDAR_BAUD": 115200,

    # --- Parameter Penerbangan & Keselamatan ---
    "FLIGHT_ALTITUDE": 10.0,  # meter
    "OBSTACLE_THRESHOLD_M": 3.0, # Jarak aman dalam meter
}

def setup_logging():
    """Menyiapkan logging terpusat."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - [%(name)s:%(funcName)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(DRONE_CONFIG["LOG_FILE"]),
            logging.StreamHandler()
        ]
    )
    # Memberi nama logger utama
    logger = logging.getLogger("DroneSawit")
    return logger

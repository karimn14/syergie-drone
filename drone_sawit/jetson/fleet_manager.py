"""
fleet_manager.py
Multi-drone fleet management and coordination for Drone Sawit.
"""
import requests
import time

FLEET = [
    {"id": "drone1", "api": "http://192.168.1.101:8000/api/mission-status"},
    {"id": "drone2", "api": "http://192.168.1.102:8000/api/mission-status"}
]

def get_fleet_status():
    status = []
    for drone in FLEET:
        try:
            resp = requests.get(drone['api'], timeout=2)
            status.append({"id": drone['id'], **resp.json()})
        except Exception as e:
            status.append({"id": drone['id'], "status": "offline", "error": str(e)})
    return status

def assign_missions():
    # Placeholder: Assign missions based on load, location, and battery
    print("Assigning missions to available drones...")
    status = get_fleet_status()
    # Example: Print status
    for s in status:
        print(s)
    # Extend with mission assignment logic

if __name__ == "__main__":
    assign_missions()

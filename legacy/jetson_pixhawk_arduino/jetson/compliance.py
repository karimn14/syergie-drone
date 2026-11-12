"""
compliance.py
Automated regulatory compliance and geofence enforcement for Drone Sawit.
"""
import requests
import json
import os

GEOFENCE_URL = os.environ.get('GEOFENCE_URL', 'https://example.com/geofence.json')
GEOFENCE_FILE = 'geofence.json'


def update_geofence():
    resp = requests.get(GEOFENCE_URL)
    if resp.status_code == 200:
        with open(GEOFENCE_FILE, 'w') as f:
            f.write(resp.text)
        print('Geofence updated.')
    else:
        print('Failed to update geofence.')


def check_geofence(lat, lon):
    if not os.path.exists(GEOFENCE_FILE):
        return True  # No geofence, allow
    with open(GEOFENCE_FILE) as f:
        geofence = json.load(f)
    # Simple polygon check (placeholder)
    for zone in geofence.get('zones', []):
        if zone['type'] == 'polygon':
            # Implement point-in-polygon logic here
            pass
    return True

if __name__ == "__main__":
    update_geofence()
    print(check_geofence(-2.2, 113.9))

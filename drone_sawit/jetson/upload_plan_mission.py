"""
upload_plan_mission.py
Uploads .plan mission file to Pixhawk using MAVSDK Python API.
"""

import asyncio
from mavsdk import System
import json

async def upload_plan(plan_file, pixhawk_address="udp://:14540"):
    """Upload QGroundControl .plan mission to Pixhawk via MAVSDK."""
    drone = System()
    await drone.connect(system_address=pixhawk_address)
    print(f"Connecting to Pixhawk at {pixhawk_address}...")
    async for state in drone.core.connection_state():
        if state.is_connected:
            print("Connected to Pixhawk!")
            break
    # Load mission items from .plan file
    with open(plan_file, 'r') as f:
        plan_data = json.load(f)
    mission_items = []
    for item in plan_data['mission']['items']:
        # Only supporting basic waypoint missions for now
        if item['command'] == 16:  # MAV_CMD_NAV_WAYPOINT
            mission_items.append(
                {
                    "latitude_deg": item['params'][4],
                    "longitude_deg": item['params'][5],
                    "relative_altitude_m": item['params'][6],
                    "speed_m_s": plan_data['mission'].get('cruiseSpeed', 5)
                }
            )
    from mavsdk.mission import MissionItem, MissionPlan
    mavsdk_items = [MissionItem(
        mi['latitude_deg'], mi['longitude_deg'], mi['relative_altitude_m'],
        mi['speed_m_s'], is_fly_through=True, gimbal_pitch_deg=0, gimbal_yaw_deg=0,
        camera_action=MissionItem.CameraAction.NONE) for mi in mission_items]
    mission_plan = MissionPlan(mavsdk_items)
    await drone.mission.upload_mission(mission_plan)
    print("Mission uploaded.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python upload_plan_mission.py <plan_file> [pixhawk_address]")
    else:
        plan_file = sys.argv[1]
        pixhawk_address = sys.argv[2] if len(sys.argv) > 2 else "udp://:14540"
        asyncio.run(upload_plan(plan_file, pixhawk_address))

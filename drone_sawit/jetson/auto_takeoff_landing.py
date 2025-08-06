"""
auto_takeoff_landing.py
Automated takeoff, precision landing, and docking logic for Drone Sawit.
"""
from mavsdk import System
import asyncio

async def auto_takeoff(drone: System, altitude=10):
    print("Arming...")
    await drone.action.arm()
    print(f"Taking off to {altitude} meters...")
    await drone.action.takeoff()
    await asyncio.sleep(8)
    await drone.action.goto_location(0, 0, altitude, 0)
    print("Takeoff complete.")

async def auto_land(drone: System):
    print("Initiating landing...")
    await drone.action.land()
    await asyncio.sleep(10)
    print("Landing complete.")

async def auto_dock(drone: System, dock_lat, dock_lon, dock_alt):
    print("Navigating to docking station...")
    await drone.action.goto_location(dock_lat, dock_lon, dock_alt, 0)
    await asyncio.sleep(5)
    await auto_land(drone)
    print("Docked and ready for charging.")

if __name__ == "__main__":
    drone = System()
    asyncio.run(auto_takeoff(drone))

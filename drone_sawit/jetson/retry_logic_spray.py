# retry_logic_spray.py – Add retry queue for missed spray attempts
import pandas as pd
from geopy.distance import geodesic
import serial
import asyncio
from mavsdk import System

spray_df = pd.read_csv("spray_commands_linked.csv")
sprayed = set()
retry_queue = []
ser = serial.Serial("/dev/ttyUSB0", 9600, timeout=1)

def match_gps(lat, lon, radius=4.0):
    for _, row in spray_df.iterrows():
        if row.tree_id in sprayed:
            continue
        dist = geodesic((lat, lon), (row.lat, row.lon)).meters
        if dist < radius:
            return row
    return None

async def main():
    drone = System()
    await drone.connect(system_address="serial:///dev/ttyACM0:57600")
    async for pos in drone.telemetry.position():
        match = match_gps(pos.latitude_deg, pos.longitude_deg)
        if match:
            try:
                print(f"\U0001F6E0\uFE0F At {match.tree_id}: Spraying {match.command}")
                ser.write((match.command + "\n").encode())
                sprayed.add(match.tree_id)
                await asyncio.sleep(3)
            except Exception as e:
                print(f"\u26A0\uFE0F Spray failed: {e}. Queuing for retry.")
                retry_queue.append(match)
        # Retry logic
        for retry in retry_queue[:]:
            try:
                print(f"\U0001F501 Retrying {retry.tree_id}")
                ser.write((retry.command + "\n").encode())
                sprayed.add(retry.tree_id)
                retry_queue.remove(retry)
                await asyncio.sleep(3)
            except:
                print("\u26A0\uFE0F Retry failed. Will retry later.")

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
from mavsdk import System
import pandas as pd
import serial
from geopy.distance import geodesic

spray_df = pd.read_csv("spray_commands_linked.csv")
sprayed = set()
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
            print(f"\U0001F6E0\uFE0F At {match.tree_id}: Spraying {match.command}")
            ser.write((match.command + "\n").encode())
            sprayed.add(match.tree_id)
            await asyncio.sleep(3)

if __name__ == "__main__":
    asyncio.run(main())

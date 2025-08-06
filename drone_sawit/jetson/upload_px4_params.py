"""
upload_px4_params.py
Uploads .param file to Pixhawk using MAVSDK Python API.
"""

import asyncio
from mavsdk import System

async def upload_params(param_file, pixhawk_address="udp://:14540"):
    """Upload PX4 parameters to Pixhawk via MAVSDK."""
    drone = System()
    await drone.connect(system_address=pixhawk_address)
    print(f"Connecting to Pixhawk at {pixhawk_address}...")
    async for state in drone.core.connection_state():
        if state.is_connected:
            print("Connected to Pixhawk!")
            break
    # Read param file and upload each parameter
    with open(param_file, 'r') as f:
        for line in f:
            if line.startswith('#') or not line.strip():
                continue
            parts = line.strip().split('\t')
            if len(parts) < 3:
                continue
            param_name, param_value, param_type = parts[0], parts[1], parts[2]
            try:
                value = float(param_value) if '.' in param_value else int(param_value)
                await drone.param.set_param_float(param_name, value) if param_type == 'FLOAT' else await drone.param.set_param_int(param_name, value)
                print(f"Set {param_name} = {value}")
            except Exception as e:
                print(f"Failed to set {param_name}: {e}")
    print("All parameters uploaded.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python upload_px4_params.py <param_file> [pixhawk_address]")
    else:
        param_file = sys.argv[1]
        pixhawk_address = sys.argv[2] if len(sys.argv) > 2 else "udp://:14540"
        asyncio.run(upload_params(param_file, pixhawk_address))

# preflight_diagnostics.py – Pre-mission hardware self-test
import cv2
import serial
import asyncio
from mavsdk import System

def check_camera(camera_index=0):
    cap = cv2.VideoCapture(camera_index)
    ret, _ = cap.read()
    cap.release()
    return ret

def check_arduino(port="/dev/ttyUSB0"):
    try:
        ser = serial.Serial(port, 9600, timeout=1)
        ser.write(b'PING\n')
        resp = ser.readline().decode().strip()
        return resp == 'PONG'
    except:
        return False

async def check_gps():
    drone = System()
    await drone.connect(system_address="serial:///dev/ttyACM0:57600")
    async for health in drone.telemetry.health():
        return health.is_global_position_ok

async def run_checks():
    results = {
        "camera": check_camera(),
        "arduino": check_arduino(),
        "gps": await check_gps()
    }
    print("\u2705 Preflight Diagnostics:", results)
    return all(results.values())

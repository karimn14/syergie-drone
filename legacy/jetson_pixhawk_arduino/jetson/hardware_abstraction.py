# hardware_abstraction.py – Abstract hardware interfaces for Jetson modules
import serial
from mavsdk import System

class SerialSprayer:
    def __init__(self, port="/dev/ttyUSB0", baud=9600):
        self.ser = serial.Serial(port, baud, timeout=1)
    def send_command(self, cmd):
        self.ser.write((cmd + "\n").encode())
    def read_line(self):
        return self.ser.readline().decode().strip()

class PX4Drone:
    def __init__(self, sys_addr="serial:///dev/ttyACM0:57600"):
        self.system_address = sys_addr
        self.drone = System()
    async def connect(self):
        await self.drone.connect(system_address=self.system_address)
    async def get_position(self):
        async for pos in self.drone.telemetry.position():
            return pos

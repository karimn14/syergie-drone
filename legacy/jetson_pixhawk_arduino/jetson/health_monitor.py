"""
health_monitor.py
Monitors health/heartbeat of Jetson, Pixhawk, and Arduino subsystems.
"""
import time
import os
import socket
from pymavlink import mavutil

def check_jetson():
    return True  # If this script runs, Jetson is up

def check_pixhawk(connection_str="udp:127.0.0.1:14550"):
    try:
        mav = mavutil.mavlink_connection(connection_str)
        msg = mav.recv_match(type='HEARTBEAT', blocking=True, timeout=3)
        return msg is not None
    except Exception:
        return False

def check_arduino(serial_port="/dev/ttyUSB0"):
    try:
        import serial
        ser = serial.Serial(serial_port, 115200, timeout=2)
        ser.write(b'PING\n')
        resp = ser.readline()
        return b'PONG' in resp
    except Exception:
        return False

def health_report():
    return {
        'jetson': check_jetson(),
        'pixhawk': check_pixhawk(),
        'arduino': check_arduino()
    }

if __name__ == "__main__":
    print(health_report())

"""
px4_timesync.py
Logs PX4 GPS time for alignment with Jetson logs using pymavlink.
"""

from pymavlink import mavutil
import time

def log_px4_time(connection_str="udp:127.0.0.1:14550", log_file="px4_gps_time.log"):
    """Listen for GPS_RAW_INT and log GPS time to file."""
    mav = mavutil.mavlink_connection(connection_str)
    print(f"Listening for GPS_RAW_INT on {connection_str}...")
    with open(log_file, 'w') as f:
        f.write("# PX4 GPS Time Log\n")
        while True:
            msg = mav.recv_match(type='GPS_RAW_INT', blocking=True, timeout=5)
            if msg:
                log_line = f"{time.time()}, {msg.time_usec}, {msg.lat/1e7}, {msg.lon/1e7}, {msg.alt/1e3}\n"
                print(log_line.strip())
                f.write(log_line)
                f.flush()
            else:
                print("No GPS_RAW_INT message received. Retrying...")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        log_px4_time()
    else:
        connection_str = sys.argv[1]
        log_file = sys.argv[2] if len(sys.argv) > 2 else "px4_gps_time.log"
        log_px4_time(connection_str, log_file)

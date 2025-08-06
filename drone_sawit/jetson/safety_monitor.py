# safety_monitor.py – Hardware safety and fault monitoring
import time
from logger import setup_logger

class SafetyMonitor:
    def __init__(self):
        self.logger = setup_logger("safety_monitor")
        self.fault_detected = False
    def check_communication(self, sprayer):
        try:
            sprayer.send_command("PING")
            resp = sprayer.read_line()
            if resp != "PONG":
                self.logger.error("Sprayer communication fault!")
                self.fault_detected = True
        except Exception as e:
            self.logger.error(f"Communication error: {e}")
            self.fault_detected = True
    def emergency_land(self):
        self.logger.critical("EMERGENCY LANDING TRIGGERED!")
        # Insert actual PX4/MAVSDK landing command here
        print("Landing...")
    def monitor(self, sprayer):
        self.check_communication(sprayer)
        if self.fault_detected:
            self.emergency_land()

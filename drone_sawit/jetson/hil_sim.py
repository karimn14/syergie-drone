"""
hil_sim.py
Hardware-in-the-loop simulation hooks for Jetson mission modules.
"""
import random
import time

def simulate_mission_state():
    # Simulate mission state for HIL
    return {
        "status": random.choice(["Idle", "Active", "Paused", "Error"]),
        "battery": random.randint(10, 100),
        "mission_progress": random.random(),
        "lat": -2.2 + random.uniform(-0.01, 0.01),
        "lon": 113.9 + random.uniform(-0.01, 0.01)
    }

if __name__ == "__main__":
    for _ in range(10):
        print(simulate_mission_state())
        time.sleep(1)

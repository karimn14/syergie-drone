# mission_simulator.py – Offline test of mission loop
import pandas as pd
import time

def simulate_mission(commands_file="spray_commands_linked.csv"):
    df = pd.read_csv(commands_file)
    for _, row in df.iterrows():
        print(f"Simulating spray for tree {row['tree_id']} at ({row['lat']}, {row['lon']}) for {row['duration_ms']} ms")
        time.sleep(0.1)
    print("Simulation complete.")

if __name__ == "__main__":
    simulate_mission()

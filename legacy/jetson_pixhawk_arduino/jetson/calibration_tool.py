# calibration_tool.py – Utility for calibrating sensors and spray parameters
import pandas as pd

def calibrate_flow_sensor(samples=10, port="/dev/ttyUSB0"):
    import serial
    ser = serial.Serial(port, 9600, timeout=1)
    values = []
    for _ in range(samples):
        ser.write(b'READ_FLOW\n')
        val = float(ser.readline().decode().strip())
        values.append(val)
    avg = sum(values) / len(values)
    print(f"Average flow sensor value: {avg}")
    return avg

def calibrate_spray_duration(tree_id, durations, log_file="spray_log.csv"):
    df = pd.read_csv(log_file)
    best = df[df['tree_id'] == tree_id].groupby('duration_ms').mean()['coverage'].idxmax()
    print(f"Optimal spray duration for tree {tree_id}: {best} ms")
    return best

# plan_uploader.py – Upload QGroundControl .plan file to Pixhawk via MAVLink
import subprocess
import os

def upload_plan(plan_path, qgc_path="/usr/bin/QGroundControl"):
    if not os.path.exists(plan_path):
        raise FileNotFoundError(f"Plan file not found: {plan_path}")
    cmd = [qgc_path, '--load-plan', plan_path]
    try:
        subprocess.run(cmd, check=True)
        print(f"\u2705 Plan uploaded: {plan_path}")
    except Exception as e:
        print(f"\u26A0\uFE0F Plan upload failed: {e}")

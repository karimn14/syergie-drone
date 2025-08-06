"""
Drone Sawit System Orchestrator

This script provides a unified entry point to coordinate Jetson, Arduino, and Pixhawk operations.
"""
import subprocess
import sys
import os

def run_jetson_backend():
    """Launch Jetson FastAPI backend."""
    try:
        subprocess.Popen([sys.executable, os.path.join('jetson', 'main.py')])
        print('Jetson backend started.')
    except Exception as e:
        print(f'Error starting Jetson backend: {e}')

def run_preflight_checks():
    """Run preflight diagnostics and compliance checks."""
    try:
        subprocess.run([sys.executable, os.path.join('jetson', 'health_monitor.py')])
        subprocess.run([sys.executable, os.path.join('jetson', 'compliance.py')])
        print('Preflight checks completed.')
    except Exception as e:
        print(f'Error during preflight checks: {e}')

def upload_pixhawk_plan():
    """Upload mission plan to Pixhawk (placeholder for actual implementation)."""
    print('Please upload the .plan file in pixhawk/ to your Pixhawk using QGroundControl.')

def main():
    print('--- Drone Sawit Orchestrator ---')
    run_preflight_checks()
    run_jetson_backend()
    upload_pixhawk_plan()
    print('System is running. Monitor logs and dashboard as needed.')

if __name__ == '__main__':
    main()

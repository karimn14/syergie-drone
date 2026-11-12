# Drone Sawit Quickstart Guide

## Prerequisites
- Jetson Nano/Xavier or compatible onboard computer
- Pixhawk autopilot (PX4/QGroundControl)
- Arduino-compatible microcontroller
- Python 3.8+
- Docker (optional, for containerized deployment)

## Initial Setup
1. **Clone the repository:**
   ```bash
   git clone <repo-url>
   cd drone_sawit
   ```
2. **Install dependencies:**
   - See `jetson/requirements.txt` for Python modules
   - Arduino: Use Arduino IDE to upload `.ino` files from `arduino/`
   - Pixhawk: Load `.plan` and `.params` files from `pixhawk/`

## Running the System
1. **Mission Planning:**
   ```bash
   python jetson/auto_mission_planner.py <image>
   ```
2. **Preflight Checks:**
   - Weather: `python jetson/weather_integration.py`
   - Geofence: `python jetson/compliance.py`
   - Diagnostics: `python jetson/health_monitor.py`
3. **Mission Execution:**
   - Backend: `python jetson/main.py`
   - Dashboard: Open browser to `https://<jetson-ip>:8000/mission_dashboard.html`
4. **Postflight:**
   - Review logs, sync data, check maintenance

## Directory Structure
- `jetson/`   : Main Python modules
- `arduino/`  : Microcontroller code
- `pixhawk/`  : PX4 configs and plans
- `tests/`    : Test scripts
- `data/`     : Mission data and logs

## Troubleshooting
- See `README_DEPLOYMENT.md` for deployment and wiring help
- For hardware issues, refer to `README_WIRING_DIAGRAM.txt`
- For compliance and safety, see `SAFETY_COMPLIANCE.md`

## Support
- For integration or advanced use, contact the development team.

# Drone Sawit Deployment & Troubleshooting Guide

## Hardware Checklist
- Pixhawk autopilot connected and powered
- Jetson board connected and powered
- Arduino actuators connected and flashed
- All sensors (LiDAR, GPS, etc.) connected
- All wiring secure and checked for shorts
- Power supply stable and within specifications
- SD cards (if used) inserted and formatted
- All antennas (GPS, telemetry, WiFi) connected
- Safety switch and kill switch tested
- Spare propellers and batteries available

---

## 1. Hardware Wiring Overview

**Jetson Nano <-> Arduino <-> Pixhawk**

- Jetson Nano USB (ttyUSB0) <-> Arduino Nano/Uno (Serial)
- Jetson Nano USB (ttyACM0) <-> Pixhawk (Telemetry 2)
- Arduino PWM pins to sprayer relay/valve
- Arduino analog input to flow sensor
- Optional: Arduino PWM/servo to gimbal
- Power: Use 5V/12V BEC for Arduino, separate battery for Jetson

**Wiring Diagram:**
```
[Jetson Nano] <==USB==> [Arduino] <==PWM==> [Sprayer]
                                    <==A0==> [Flow Sensor]
                                    <==PWM==> [Gimbal Servo]
[Jetson Nano] <==USB==> [Pixhawk]
```

## 2. Software Setup

- Flash Arduino with firmware (choose appropriate .ino)
- Install all Python dependencies on Jetson:
  ```
  pip install -r jetson/requirements.txt
  ```
- Place all required data/model files in `jetson/`:
  - `predicted_trees.geojson`
  - `pollen_dosage_table.csv`
  - `spray_commands_linked.csv`
  - `bloom_model.pt`
- Ensure QGroundControl is installed on Jetson or ground station

## 3. Permissions

- Add Jetson user to `dialout` group for serial access:
  ```
  sudo usermod -aG dialout $USER
  ```
- Check port names with `ls /dev/tty*`

## 4. Preflight Checklist

- Run `jetson/preflight_diagnostics.py` and verify all tests pass
- Generate mission plan: `python jetson/auto_mission_planner.py <plantation_image>`
- Check weather: `python jetson/weather_integration.py`
- Update geofence: `python jetson/compliance.py`
- Confirm mission plan and parameters are uploaded to Pixhawk
- Visually check all wiring and power connections
- Ensure all logs are cleared or archived

## 5. Launch Sequence

1. Power on Jetson, Arduino, and Pixhawk
2. Start FastAPI backend: `python jetson/main.py`
3. Monitor dashboard at `https://<jetson-ip>:8000/mission_dashboard.html`
4. Use multi-drone/fleet tools as needed: `python jetson/fleet_manager.py`

## 6. Troubleshooting

- **Serial errors:** Check port names and permissions
- **AI/Model errors:** Ensure `bloom_model.pt` is present and compatible
- **Sprayer not working:** Check Arduino logs and flow sensor
- **Mission upload:** Use `jetson/plan_uploader.py` or QGroundControl
- **Failsafe:** Pixhawk will RTL on low battery or geofence breach
- **Weather issues:** Missions auto-delay if unsafe (wind/rain)
- **Geofence breach:** Mission will pause or RTL if outside allowed area

## 7. Field Calibration

- Use `jetson/calibration_tool.py` for flow sensor and spray tuning
- Log and review spray coverage after each mission

## 8. Obstacle Avoidance Sensor Configurations

Drone Sawit supports multiple configurations for obstacle avoidance, balancing weight, coverage, and cost:

### 1. Advanced LiDAR (Single Sensor)
| Model             | FOV (H × V) | Range   | Weight | Power | Notes                             |
|-------------------|-------------|---------|--------|-------|------------------------------------|
| Benewake CE30-C   | 132°×9°     | 10–20m  | 120g   | <5W   | Solid-state, robust, wide frontal  |
| LightWare SF40/C  | 360°×1.5°   | 100m    | 350g   | ~5W   | 2D spinning, long range            |

- **Integration:** Mount forward (CE30-C) or top (SF40/C). Connect via UART/Ethernet. Use Jetson for real-time processing.

### 2. Multi-Sensor (Quasi-360°) Array
| Sensor           | Direction | Coverage         | Model                | Qty | Mount Location    | Weight (g) |
|------------------|-----------|------------------|----------------------|-----|------------------|------------|
| TF-Mini Plus     | Forward   | 0–15 m, frontal  | Benewake TF-Mini Plus| 1   | Nose/front frame | 11         |
| TF-Luna          | Left      | ~0.2–5 m         | Benewake TF-Luna     | 1   | Left arm         | 5          |
| TF-Luna          | Right     | ~0.2–5 m         | Benewake TF-Luna     | 1   | Right arm        | 5          |
| TF-Luna          | Rear      | ~0.2–5 m         | Benewake TF-Luna     | 1   | Tail             | 5          |
| TF-Luna          | Downward  | ~0.2–5 m         | Benewake TF-Luna     | 1   | Center bottom    | 5          |
| **Total**        |           |                  |                      | 5   |                  | ~31        |

- **Integration:** Use UART multiplexer or Jetson Nano UART expansion. Poll sensors in loop or ROS2. Calibrate sensor poses. Sync to Pixhawk via MAVLink.

### 3. Optional 360° Upgrades
- **RPLIDAR A1:** Replace front TF-Mini Plus for 360° scan (adds ~170g, ~5W)
- **Octagonal Array:** 8× TF-Luna for full perimeter coverage

### Integration Notes
- All options are modular and fault-tolerant
- Choose configuration based on payload, mission, and budget
- See main README for diagrams and detailed recommendations

---

## 8. Automation & Fleet Features

- **Automated Takeoff/Landing:** See `jetson/auto_takeoff_landing.py`
- **Predictive Maintenance:** Check/trigger via `jetson/predictive_maintenance.py`
- **Cloud Sync:** Upload logs/reports using dashboard or `jetson/cloud_sync.py`
- **Smart Alerts:** Operator notified only for critical events (see `jetson/smart_alerts.py`)
- **Multi-Drone Fleet:** Assign and monitor missions with `jetson/fleet_manager.py`

## 9. Safety

- Always test in a controlled environment before field use
- Keep emergency landing area clear
- Monitor battery and weather conditions
- Review maintenance and compliance status before each mission

---

_Last updated: 2025-05-14_

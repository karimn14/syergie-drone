# Drone Sawit Project

## ⚠️ Environment Configuration
Before running any part of the system, copy `.env.example` to `.env` and fill in all required environment variables/secrets. This file is critical for backend and cloud/API integration.

```sh
cp .env.example .env
# Edit .env to match your deployment
```


## Overview
Drone Sawit is a fully autonomous, AI-powered drone system for palm oil plantation monitoring and management. It integrates Jetson-based onboard computing, Pixhawk autopilot, and Arduino-controlled actuators for end-to-end mission automation, data analytics, and cloud integration.

## Key Features
- **AI-Driven Mission Planning:** Auto-generates waypoints and spray targets from satellite/drone imagery.
- **Autonomous Flight & Spraying:** Pixhawk executes uploaded missions; Jetson performs real-time AI-based target detection and decision-making.
- **Dynamic Weather Adaptation:** Integrates live weather data for safe, adaptive missions.
- **Full Automation:** Automated takeoff, landing, and docking/charging (hardware-ready).
- **Multi-Drone Fleet Management:** Centralized status and assignment for scalable operations.
- **Predictive Maintenance:** Tracks component cycles and schedules service.
- **Regulatory Compliance:** Geofence enforcement and automated compliance checks.
- **Onboard Data Analysis:** Summarizes mission and sensor data for efficient reporting/cloud upload.
- **Smart Alerts:** Notifies operators only for critical events, with automated escalation.
- **Cloud Sync & API:** Uploads logs/reports and integrates with external farm management systems.

## Recommended Lightweight LiDAR Options

For optimal obstacle avoidance, mapping, and precision landing, Drone Sawit supports integration with several lightweight LiDAR sensors. Below is a comparison of the most suitable models for drone use:

| Model                | Weight  | Max Range | FOV (H × V)   | Data Rate / Resolution | Power   | Price (USD) | Key Features                    |
|----------------------|---------|-----------|---------------|-----------------------|---------|-------------|----------------------------------|
| **Benewake CE30-C**  | 120g    | 20m (in)  | 132° × 9°     | 320×24@20Hz           | <5W     | $400–$600   | Solid-state, compact, robust     |
| **LightWare SF40/C** | 350g    | 100m      | 360° × 1.5°   | 20,000 pts/sec        | ~5W     | $1,300–$1,700| 2D spinning, long-range, proven  |
| **Ouster OS0-32**    | 425g    | 50m       | 360° × 90°    | 655,360 pts/sec       | ~13W    | $3,500–$4,500| 3D, high-res, advanced mapping   |
| **YDLIDAR G4/X4**    | 170–250g| 10–16m    | 360° × 0°     | 9,000–12,000 pts/sec  | <5W     | $150–$350   | Budget, basic obstacle detection |

**Recommended for Drone Sawit:**
- **Benewake CE30-C** offers the best balance of weight, price, and performance for most agricultural drone applications. It is robust, easy to integrate with Jetson, and widely used in commercial drone systems.
- For longer range and full 360° scanning, consider the **LightWare SF40/C** if your drone can handle the extra weight and cost.
- For advanced 3D mapping or research, the **Ouster OS0-32** is top-tier but heavier and more expensive.
- For basic needs and tight budgets, **YDLIDAR G4/X4** is suitable for simple obstacle detection.

For integration guides or software support for any of these sensors, see the documentation or contact the development team.

---

## Main Propulsion Motor: 2312 Series

Drone Sawit uses the reliable and widely adopted 2312 series brushless DC motor for propulsion. This motor is well-suited for agricultural drones due to its balance of power, efficiency, and compatibility with standard drone frames.

**Typical Specs:**
- KV rating: 960–1000KV
- Max thrust: ~850g–950g per motor (on 3S/4S LiPo)
- Weight: ~55g per motor
- Shaft: 3mm
- Compatible propellers: 9–10 inch (e.g., 9450, 1045)
- Voltage: 11.1–14.8V (3S/4S LiPo)
- Continuous current: ~15A

**Bill of Materials (excerpt):**
| Component         | Model/Type     | Qty | Est. Cost (IDR) | Notes                        |
|-------------------|---------------|-----|-----------------|------------------------------|
| Propulsion Motor  | 2312 (e.g., DJI 2312) | 4   | 1,000,000       | Main motors, brushless, CW/CCW |
| ESC               | 20A BLHeli     | 4   | 800,000         | For 2312 motor                |
| Propeller         | 9450/1045      | 4   | 200,000         | Carbon/plastic, matched to motor|

The 2312 motor ensures stable flight and efficient operation for the payload and mission requirements of Drone Sawit. For integration and calibration, see `README_DEPLOYMENT.md`.

## Recommended Multi-Sensor (Quasi-360°) Obstacle Avoidance Configuration

This layout balances weight, cost, and coverage for robust obstacle detection in all directions:

| Sensor           | Direction | Coverage         | Model                | Qty | Mount Location    | Weight (g) |
|------------------|-----------|------------------|----------------------|-----|------------------|------------|
| CE30-C           | Forward   | 0–25 m, wide FOV | Benewake CE30-C      | 1   | Nose/front frame | 135        |
| TF-Luna          | Left      | ~0.2–5 m         | Benewake TF-Luna     | 1   | Left arm         | 5          |
| TF-Luna          | Right     | ~0.2–5 m         | Benewake TF-Luna     | 1   | Right arm        | 5          |
| TF-Luna          | Rear      | ~0.2–5 m         | Benewake TF-Luna     | 1   | Tail             | 5          |
| TF-Luna          | Downward  | ~0.2–5 m         | Benewake TF-Luna     | 1   | Center bottom    | 5          |
| **Total**        |           |                  |                      | 5   |                  | ~155       |

**Wiring + Mounts:** <50 g total

**Sensor Arrangement Note:**
- The Benewake CE30-C provides a wide forward field of view for primary obstacle detection and mapping.
- Four Benewake TF-Luna sensors are mounted to cover the left, right, rear, and downward directions, each offering narrow-beam, short-range obstacle detection.
- This configuration achieves quasi-360° coverage for safe navigation, landing, and branch avoidance.

### 📐 Field of View (FOV) Arrangement
Each sensor has a narrow ~2.3° FOV (beam) except the CE30-C, which has a wide FOV. Placement ensures:
- Frontal long-range detection for navigating tree gaps
- Side/rear awareness for branch/obstacle avoidance
- Downward clearance for safe, precise spraying

```
          [Front]
            ↑
      [L]   ↑   [R]
     ←←←    ↑    →→→
     TF-L   TF-M   TF-L
             ↑
        [Drone Body]
             ↓
           TF-L
         [Bottom]
```

### Optional Upgrades
- For full 360°: Replace front TF-Mini Plus with RPLIDAR A1 (adds 360° scan, +170 g)
- For maximum redundancy: Mount 8× TF-Luna around the perimeter

### 🔌 Integration Notes
- Use UART multiplexer (e.g., MAX14830) or Jetson Nano GPIO/UART expansion
- Poll each sensor in a loop or multithreaded ROS2 node
- Sync to Pixhawk via MAVLink DISTANCE_SENSOR messages
- Calibrate each sensor’s pose in the UAV frame for spatial consistency

### ✅ Benefits
- Lightweight (<50 g total)
- Quasi-360° directional coverage
- Simple, modular, and fault-tolerant
- Cost-effective and easy to maintain

## Project Structure
- `jetson/`   : Main Python modules for AI, automation, and backend
    - `auto_mission_planner.py` – AI mission planner
    - `weather_integration.py` – Weather adaptation
    - `auto_takeoff_landing.py` – Automated takeoff/landing/docking
    - `fleet_manager.py` – Multi-drone management
    - `predictive_maintenance.py` – Maintenance tracking
    - `compliance.py` – Geofence and compliance
    - `onboard_data_analysis.py` – Data filtering/summarization
    - `smart_alerts.py` – Operator notification
    - `main.py` – FastAPI backend (dashboard, API, cloud sync)
    - `health_monitor.py`, `log_utils.py`, ...
- `arduino/`  : Microcontroller code for actuators, sensors, and sprayer
- `pixhawk/`  : PX4/QGroundControl configs and firmware

## Usage
1. **Mission Planning:**
   - Run `python jetson/auto_mission_planner.py <image>` to auto-generate a mission `.plan` file.
2. **Preflight:**
   - Check weather with `python jetson/weather_integration.py`.
   - Ensure geofence is up to date: `python jetson/compliance.py`.
   - Run diagnostics: `python jetson/health_monitor.py`.
3. **Mission Execution:**
   - Start backend: `python jetson/main.py`
   - Monitor dashboard at `https://<jetson-ip>:8000/mission_dashboard.html`
   - Use multi-drone/fleet tools as needed.
4. **Postflight:**
   - Review logs/reports, sync to cloud, and check maintenance status.

## Documentation
- See `README_DEPLOYMENT.md` for wiring, deployment, and troubleshooting.
- Each major module in `jetson/` is documented inline.

---

## ⚠️ Python Dependencies
- The main Python dependencies for Jetson modules are listed in `jetson/requirements.txt`. Install them with:
  ```sh
  pip install -r jetson/requirements.txt
  ```
- If you run orchestration or scripts outside `jetson/`, you may need to manually install additional dependencies (see code comments or script headers).

---
_Last updated: 2025-05-14_

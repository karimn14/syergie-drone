# Synergie Drone — Autonomous Pollination System
## Architecture: new_plan_2_9

---

### 🚨 FIVE DOCUMENTS: Build In Order

| # | Document | When to Use | Status |
|---|----------|-------------|--------|
| 0 | `MASTER_EXECUTION_GUIDE.md` | **FIRST** — Step-by-step terminal commands from zero to working demo | 🛠️ START HERE |
| 0b| `RECOVERY_CHECKPOINT.md` | **If you just re-installed ROS** — Where to continue after fixing ROS installation issues | 🔄 RECOVERY |
| 1 | `ACTION_PLAN_SURVIVAL.md` | **REFERENCE** — 6-day demo sprint strategy, NO optical flow | 🔥 ACTIVE |
| 2 | `ARCHITECTURE_REVIEW.md` | **NEXT** — Single-tree servoing with optical flow | 📋 ROADMAP |
| 3 | `NAVIGATION_ARCHITECTURE.md` | **THEN** — Multi-tree autonomous navigation (tree hopping) | 🗺️ FUTURE |
| 4 | `ADVANCED_SENSOR_FEASIBILITY.md` | **UPGRADE** — Sensor & algorithm options analysis (OAK-D, LiDAR, SLAM, AprilTags) | 🔬 STUDY |

---

### Quick Start — Survival Mode (On Jetson Nano)

```bash
# 1. Create ROS workspace
mkdir -p ~/catkin_ws/src && cd ~/catkin_ws && catkin_make
source devel/setup.bash

# 2. Copy ros_nodes/ contents into the ROS package
#    (See ACTION_PLAN_SURVIVAL.md Day 1 for full setup)

# 3. Build
cd ~/catkin_ws && catkin_make && source devel/setup.bash

# 4. Launch everything
roslaunch sprayer_control demo.launch

# 5. Monitor
rostopic echo /detection/result
rostopic echo /spray/status
```

### Quick Start — Standalone HIL Test (No ROS)

```bash
# Install dependencies
pip install -r requirements.txt

# Phase 1: Detection test (props OFF, safe)
python src/hil_test.py --phase 1 --device 0

# Phase 2: MAVLink command test (props OFF)
python src/hil_test.py --phase 2 --armed --serial /dev/ttyTHS1

# Phase 3: Motor response test (props ON — SECURE DRONE FIRST)
python src/hil_test.py --phase 3 --armed --serial /dev/ttyTHS1
```

### Project Structure

```
new_plan_2_9/
├── MASTER_EXECUTION_GUIDE.md  ← 🛠️ START HERE — Copy-paste commands from zero
├── RECOVERY_CHECKPOINT.md     ← 🔄 Just re-installed ROS? Start here
├── ACTION_PLAN_SURVIVAL.md    ← 🔥 6-Day sprint plan (NO optical flow)
├── ARCHITECTURE_REVIEW.md     ← Full architectural analysis & roadmap
├── NAVIGATION_ARCHITECTURE.md ← 🗺️ Behavior-based multi-tree navigation
├── ADVANCED_SENSOR_FEASIBILITY.md ← 🔬 Sensor upgrade study (OAK-D vs D435i vs LiDAR)
├── README.md                  ← This file
├── requirements.txt           ← Python dependencies
│
├── ros_nodes/                 ← 📦 Copy to ~/catkin_ws/src/sprayer_control/
│   ├── scripts/
│   │   ├── detector_node.py      ← Day 2: Yellow ball detection (ROS node)
│   │   ├── spray_logic_node.py   ← Day 3: State machine + ESP32 serial
│   │   └── hsv_tuner.py          ← Day 2: HSV threshold calibration tool
│   ├── msg/
│   │   └── Detection.msg         ← Custom ROS message
│   └── launch/
│       └── demo.launch           ← Launch all nodes together
│
├── esp32/                     ← 📦 Flash to ESP32-S3 via Arduino IDE
│   └── sprayer_controller/
│       └── sprayer_controller.ino  ← Day 3: Relay control + watchdog
│
├── src/
│   └── hil_test.py            ← Standalone HIL test (no ROS needed)
│
├── config/
│   └── ardupilot_params.param ← Pixhawk params (for when optical flow arrives)
│
└── diagrams/
    ├── system_architecture.mmd    ← Mermaid: full system architecture
    ├── state_machine.mmd          ← Mermaid: spray state machine
    ├── navigation_dataflow.mmd    ← Mermaid: navigation data flow
    ├── navigation_state_machine.mmd ← Mermaid: 18-state navigation FSM
    └── sensor_upgrade_comparison.mmd ← Mermaid: baseline vs mid-tier upgrade
```

### Architecture Summary

**Survival Mode (Now — No Optical Flow):**

| Subsystem        | Component                | Role                          |
|------------------|--------------------------|-------------------------------|
| Position Hold    | **Human Pilot** (AltHold) | Manual hover & approach      |
| Target Detection | Jete USB Cam → Jetson    | OpenCV HSV detection          |
| Spray Decision   | Jetson State Machine     | DETECTED → ALIGNED → SPRAY   |
| Spray Trigger    | Jetson → ESP32 (Serial)  | Relay control + safety watchdog |
| Flight Control   | Pixhawk (ArduPilot)     | AltHold mode (pilot RC)      |

**Full Auto Mode (Future — With Optical Flow):**

| Subsystem        | Component                | Role                          |
|------------------|--------------------------|-------------------------------|
| Position Hold    | Matek 3901-L0X → Pixhawk | Optical flow + rangefinder    |
| Target Detection | Jete USB Cam → Jetson    | YOLOv8-nano (TensorRT FP16)  |
| Approach/Aim     | Jetson PID Controller    | Visual servoing (IBVS)       |
| Spray Trigger    | Jetson → ESP32 (Serial)  | **Same code, unchanged** ✅  |
| Flight Control   | Pixhawk (ArduPilot)     | GUIDED/LOITER mode            |

~70% of the Survival Mode code carries forward to Full Auto Mode. That's the point.

See `ACTION_PLAN_SURVIVAL.md` for the 6-day sprint plan.
See `ARCHITECTURE_REVIEW.md` for the complete architectural analysis.
See `NAVIGATION_ARCHITECTURE.md` for behavior-based multi-tree autonomous navigation.
See `ADVANCED_SENSOR_FEASIBILITY.md` for the sensor upgrade feasibility study (OAK-D Lite recommendation).

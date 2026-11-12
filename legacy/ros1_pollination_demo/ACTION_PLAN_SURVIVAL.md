# 🚨 ACTION PLAN — "SURVIVAL MODE" (6-Day Demo Sprint)
### Date: February 9, 2026
### Reality: No Optical Flow. No GPS. No Time. Ship Anyway.
### Target: Functional Integration Demo in 6 Days

---

## 0. SITUATIONAL AWARENESS — What We're Really Doing

Let me be blunt about what's happening and what's NOT happening in 6 days:

| What the Demo WILL Show | What the Demo WON'T Show |
|---|---|
| ✅ Jetson detects a yellow target in real-time | ❌ Autonomous flight |
| ✅ Jetson calculates aiming error (left/right/close/far) | ❌ Position hold without pilot |
| ✅ Jetson triggers sprayer automatically via Pixhawk servo when aligned | ❌ Complex waypoint navigation |
| ✅ Pilot flies manually in AltHold, Jetson handles spray logic | ❌ SLAM, mapping, or odometry |
| ✅ Full data logging (video + decisions + spray events) | ❌ PID velocity control of Pixhawk |

**The story you tell stakeholders:**
> "The drone's brain (Jetson) can SEE the target, DECIDE when to spray, and TRIGGER the sprayer via Pixhawk servo outputs — all autonomously. The pilot provides the legs (flight), the AI provides the eyes and trigger finger. When the optical flow sensor arrives, we add autonomous approach. The hard part — vision + decision + actuation — is DONE."

This is honest, impressive, and 100% achievable in 6 days.

---

## PART 1: THE "BAND-AID" ARCHITECTURE

### 1.1 System Overview — What Talks to What

```
┌──────────────────────────────────────────────────────────────────┐
│                    "SURVIVAL MODE" ARCHITECTURE                  │
│           Updated: Full Pixhawk Control (Option A)               │
│                                                                  │
│   The pilot is the "Optical Flow" — they hold position.         │
│   Jetson is the "Brain" — it detects and triggers.              │
│   Pixhawk is the "Muscle" — it drives the sprayer servos.       │
│                                                                  │
│   ┌──────────┐     USB      ┌──────────────────────────┐       │
│   │ Jete USB │────────────►│     JETSON NANO 4GB       │       │
│   │ Webcam   │   /dev/      │                          │       │
│   │ 1080p    │   video0     │  ┌────────────────────┐  │       │
│   └──────────┘              │  │ ROS Noetic         │  │       │
│                             │  │                    │  │       │
│                             │  │ ┌────────────────┐ │  │       │
│                             │  │ │ camera_node    │ │  │       │
│                             │  │ │ (usb_cam)      │ │  │       │
│                             │  │ └───────┬────────┘ │  │       │
│                             │  │         │ /camera/ │  │       │
│                             │  │         │ image_raw│  │       │
│                             │  │         ▼          │  │       │
│                             │  │ ┌────────────────┐ │  │       │
│                             │  │ │ detector_node  │ │  │       │
│                             │  │ │ (OpenCV HSV)   │ │  │       │
│                             │  │ └───────┬────────┘ │  │       │
│                             │  │         │/detection│  │       │
│                             │  │         │ /result  │  │       │
│                             │  │         ▼          │  │       │
│                             │  │ ┌────────────────┐ │  │       │
│                             │  │ │ spray_logic    │ │  │       │
│                             │  │ │ _node (mavros) │ │  │       │
│                             │  │ │ (State Machine)│ │  │       │
│                             │  │ └───────┬────────┘ │  │       │
│                             │  │         │          │  │       │
│                             │  └─────────┼──────────┘  │       │
│                             │            │              │       │
│                             └────────────┼──────────────┘       │
│                                          │                      │
│                          UART (ttyTHS1)  │  MAVLink v2          │
│                          921600 baud     │  via mavros           │
│                                          │                      │
│                                          │  DO_SET_SERVO(13,pw) │
│                                          │  DO_SET_SERVO(14,pw) │
│                                          ▼                      │
│   ┌──────────────────────────────────────────────┐              │
│   │            PIXHAWK 2.4.8 (ArduPilot)         │              │
│   │                                              │              │
│   │  Mode: AltHold (Manual Pilot Control)        │              │
│   │  Role: Flight stabilization + Sprayer servo  │              │
│   │                                              │              │
│   │  AUX5 (SERVO13) → EDF Fan ESC (PWM 1000-1800)│             │
│   │  AUX6 (SERVO14) → MG996R Servo (PWM 1500=stop)│            │
│   │                                              │              │
│   │  Jetson connected via TELEM2 UART.           │              │
│   │  mavros bridges ROS ↔ MAVLink.               │              │
│   │                                              │              │
│   │  Future: Will receive velocity commands      │              │
│   │  from Jetson when Optical Flow arrives.      │              │
│   └───────────┬───────────────┬──────────────────┘              │
│               │               │                                 │
│               ▼               ▼                                 │
│   ┌──────────────┐  ┌──────────────────────┐                   │
│   │ EDF Fan      │  │ MG996R Continuous     │                   │
│   │ (Venturi air)│  │ Rotation Servo        │                   │
│   │ ESC → Motor  │  │ (Auger powder feed)   │                   │
│   └──────────────┘  └──────────────────────┘                   │
│                                                                  │
│   ┌──────────────┐                                              │
│   │ RC Radio     │  Pilot holds position manually               │
│   │ (Transmitter)│  in AltHold mode.                            │
│   └──────────────┘  They ARE the "optical flow" for now.        │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 1.2 Why Jetson → Pixhawk → Servo (Full Pixhawk Control)?

> **Architecture Update (Feb 17, 2025):** We originally planned Jetson → ESP32 → Relay.
> After the Design Review, we pivoted to **Option A: Full Pixhawk Control**.
> The ESP32 and relay module are removed from the BOM.

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| Jetson → mavros → Pixhawk AUX Servo | Single communication path (UART already needed for flight commands). Fewer components. No synchronization issues. TRIM values = safe defaults on disconnect. Already flight-proven path. | Requires mavros, UART wiring, BRD_PWM_COUNT configuration. | ✅ **USE THIS** |
| Jetson → ESP32 → Relay | Simple serial protocol. Independent of flight controller. | Extra MCU, extra cable, extra failure mode. Synchronization risk between two serial buses. | ❌ Removed from design |
| Jetson GPIO → Relay directly | Fewer components. | Jetson GPIO is 3.3V, max ~20mA. If Jetson crashes, relay state undefined. No hardware watchdog. | ❌ Not used |

### 1.3 Communication Protocol: Jetson ↔ Pixhawk (via mavros)

MAVLink commands over UART. Clean, proven, flight-standard.

```
JETSON → PIXHAWK (via mavros DO_SET_SERVO):
    DO_SET_SERVO(13, 1800)  → EDF Fan ON (AUX5, full speed)
    DO_SET_SERVO(13, 1000)  → EDF Fan OFF (AUX5, idle)
    DO_SET_SERVO(14, 1650)  → Auger Feed ON (AUX6, CW rotate)
    DO_SET_SERVO(14, 1500)  → Auger Feed STOP (AUX6, center)

SAFETY (built into ArduPilot):
    - SERVO13_TRIM = 1000 → Fan defaults OFF if no command received
    - SERVO14_TRIM = 1500 → Servo defaults STOPPED if no command received
    - If mavros connection drops, Pixhawk reverts to TRIM → both actuators safe
    - spray_logic_node calls all_off() on ROS shutdown
```

---

## PART 2: ROS1 NOETIC — THE "CHEAT SHEET"

### 2.1 Workspace Setup (Run Once, On Day 1)

```bash
# ════════════════════════════════════════════════════════
# STEP 1: Create the catkin workspace
# ════════════════════════════════════════════════════════
mkdir -p ~/catkin_ws/src
cd ~/catkin_ws/
catkin_make

# Source the workspace (add to ~/.bashrc so it loads every terminal)
echo "source ~/catkin_ws/devel/setup.bash" >> ~/.bashrc
source ~/.bashrc

# Verify it works
echo $ROS_PACKAGE_PATH
# Should show: /home/jetson/catkin_ws/src:/opt/ros/noetic/share
```

### 2.2 Create the Package

```bash
# ════════════════════════════════════════════════════════
# STEP 2: Create our ROS package
# ════════════════════════════════════════════════════════
cd ~/catkin_ws/src

catkin_create_pkg sprayer_control std_msgs rospy sensor_msgs cv_bridge

# Package structure AFTER we're done:
# ~/catkin_ws/src/sprayer_control/
# ├── CMakeLists.txt          (auto-generated, mostly untouched)
# ├── package.xml             (auto-generated, mostly untouched)
# ├── launch/
# │   └── demo.launch         (starts mavros + all nodes together)
# ├── scripts/
# │   ├── detector_node.py    (camera + yellow ball detection)
# │   ├── spray_logic_node.py (state machine + mavros servo control)
# │   └── debug_viewer.py     (optional: shows camera + overlay via SSH)
# └── msg/
#     └── Detection.msg       (custom message for detection results)
```

### 2.3 Create Custom Message

```bash
# ════════════════════════════════════════════════════════
# STEP 3: Custom message for detection data
# ════════════════════════════════════════════════════════
cd ~/catkin_ws/src/sprayer_control
mkdir -p msg
```

File: `msg/Detection.msg`
```
# Detection result from the camera
Header header
bool detected           # Is a target visible?
int32 cx                # Bounding box center X (pixels)
int32 cy                # Bounding box center Y (pixels)
int32 area              # Bounding box area (pixels²)
float32 confidence      # Detection confidence (0.0-1.0)
string position_hint    # "LEFT", "RIGHT", "CENTER", "TOO_FAR", "TOO_CLOSE"
```

### 2.4 Make Python Scripts Executable

```bash
# ════════════════════════════════════════════════════════
# STEP 4: After creating your .py files in scripts/
# ════════════════════════════════════════════════════════
cd ~/catkin_ws/src/sprayer_control/scripts
chmod +x detector_node.py
chmod +x spray_logic_node.py
chmod +x debug_viewer.py
```

### 2.5 Edit CMakeLists.txt for Custom Messages

Add to `CMakeLists.txt`:
```cmake
# Near the top, in find_package:
find_package(catkin REQUIRED COMPONENTS
  std_msgs
  rospy
  sensor_msgs
  cv_bridge
  message_generation    # <-- ADD THIS
)

# Uncomment and edit:
add_message_files(
  FILES
  Detection.msg
)

generate_messages(
  DEPENDENCIES
  std_msgs
)

# In catkin_package:
catkin_package(
  CATKIN_DEPENDS std_msgs rospy sensor_msgs cv_bridge message_runtime  # <-- ADD message_runtime
)
```

### 2.6 Edit package.xml

Add these two lines inside `<package>`:
```xml
<build_depend>message_generation</build_depend>
<exec_depend>message_runtime</exec_depend>
```

### 2.7 Build & Verify

```bash
# ════════════════════════════════════════════════════════
# STEP 5: Build the workspace
# ════════════════════════════════════════════════════════
cd ~/catkin_ws
catkin_make
source devel/setup.bash

# Verify the message was generated:
rosmsg show sprayer_control/Detection
# Should print the fields you defined
```

### 2.8 The Launch File

```xml
<!-- File: ~/catkin_ws/src/sprayer_control/launch/demo.launch -->
<launch>
    <!-- USB Camera Node -->
    <node name="usb_cam" pkg="usb_cam" type="usb_cam_node" output="screen">
        <param name="video_device" value="/dev/video0" />
        <param name="image_width" value="640" />
        <param name="image_height" value="480" />
        <param name="framerate" value="30" />
        <param name="pixel_format" value="mjpeg" />
        <param name="camera_name" value="webcam" />
    </node>

    <!-- Yellow Ball Detector -->
    <node name="detector" pkg="sprayer_control" type="detector_node.py" output="screen">
        <param name="confidence_threshold" value="0.5" />
    </node>

    <!-- Spray Logic + ESP32 Communication -->
    <node name="spray_logic" pkg="sprayer_control" type="spray_logic_node.py" output="screen">
        <param name="serial_port" value="/dev/ttyUSB0" />
        <param name="baud_rate" value="115200" />
        <param name="spray_duration" value="0.5" />
    </node>
</launch>
```

### 2.9 How to Run (Daily Command Cheat Sheet)

```bash
# ══ TERMINAL 1: Start ROS Master ══
roscore

# ══ TERMINAL 2: Launch everything ══
roslaunch sprayer_control demo.launch

# ══ TERMINAL 3: Monitor topics (debugging) ══
rostopic echo /detection/result     # See detection messages
rostopic hz /usb_cam/image_raw      # Check camera FPS
rostopic echo /spray/status         # See spray trigger events

# ══ TERMINAL 4: View camera remotely (via SSH X-forwarding) ══
# On your laptop, SSH with: ssh -X jetson@<ip>
rqt_image_view /detector/debug_image

# ══ KILL EVERYTHING ══
# Ctrl+C in Terminal 2 kills all nodes launched by roslaunch.
# Then Ctrl+C in Terminal 1 kills roscore.
```

### 2.10 Essential ROS1 Install Commands (If Missing)

```bash
# Install usb_cam (camera driver):
sudo apt-get install ros-noetic-usb-cam

# Install cv_bridge (OpenCV ↔ ROS):
sudo apt-get install ros-noetic-cv-bridge

# Install rqt tools (for debugging):
sudo apt-get install ros-noetic-rqt-image-view

# Python serial for ESP32 communication:
pip3 install pyserial

# If OpenCV is broken or missing:
pip3 install opencv-python==4.5.5.64
# (Use 4.5.x on Nano — 4.8+ may have build issues with ARM)
```

---

## PART 3: THE 6-DAY EXECUTION PLAN

---

### 📅 DAY 1 (Feb 10): ENVIRONMENT SETUP & CAMERA TEST

**Goal:** ROS Noetic running. Camera publishing frames. You can see live video.

**Morning (3 hours):**

```bash
# 1. Verify ROS Noetic is installed
rosversion -d
# Should print: noetic
# If NOT installed, see: http://wiki.ros.org/noetic/Installation/Ubuntu

# 2. Verify Jetson performance mode
sudo nvpmodel -m 0      # MAXN
sudo jetson_clocks       # Max clocks

# 3. Create workspace
mkdir -p ~/catkin_ws/src
cd ~/catkin_ws && catkin_make
echo "source ~/catkin_ws/devel/setup.bash" >> ~/.bashrc
source ~/.bashrc

# 4. Install camera package
sudo apt-get update
sudo apt-get install ros-noetic-usb-cam ros-noetic-cv-bridge ros-noetic-rqt-image-view

# 5. Plug in Jete webcam and verify
ls /dev/video*
# Should show /dev/video0 (or video1)

# 6. Quick camera test (non-ROS, just OpenCV)
python3 -c "
import cv2
cap = cv2.VideoCapture(0)
ret, frame = cap.read()
print(f'Camera works: {ret}, Frame shape: {frame.shape if ret else None}')
cap.release()
"
```

**Afternoon (3 hours):**

```bash
# 7. Create ROS package
cd ~/catkin_ws/src
catkin_create_pkg sprayer_control std_msgs rospy sensor_msgs cv_bridge message_generation
mkdir -p sprayer_control/launch sprayer_control/scripts sprayer_control/msg

# 8. Create the custom message (see Part 2.3 above)
# 9. Edit CMakeLists.txt and package.xml (see Part 2.5, 2.6)
# 10. Build
cd ~/catkin_ws && catkin_make && source devel/setup.bash

# 11. Test camera via ROS
# Terminal 1:
roscore
# Terminal 2:
rosrun usb_cam usb_cam_node _video_device:=/dev/video0 _image_width:=640 _image_height:=480
# Terminal 3:
rostopic hz /usb_cam/image_raw
# PASS CRITERIA: Shows ~30 Hz (or at least >15 Hz)

# Terminal 4 (from laptop via SSH -X):
rqt_image_view /usb_cam/image_raw
# PASS CRITERIA: You see live video from the webcam.
```

**✅ Day 1 Deliverable:** `rostopic hz /usb_cam/image_raw` shows 25-30 FPS. Live video visible in `rqt_image_view`. Screenshot saved as proof.

---

### 📅 DAY 2 (Feb 11): DETECTOR NODE — YELLOW BALL DETECTION

**Goal:** A ROS node that subscribes to camera images and publishes `Detection` messages when it sees a yellow ball.

**Full Day (6 hours):**

Create the file: `~/catkin_ws/src/sprayer_control/scripts/detector_node.py`

> ⚡ **Coding instruction for Sonnet 3.5:** Use the code I'll provide in the `ros_nodes/` folder. Just copy it to the Jetson's scripts folder and `chmod +x`.

The detector should:
1. Subscribe to `/usb_cam/image_raw`
2. Convert to HSV color space
3. Threshold for yellow (H: 20-35, S: 100-255, V: 100-255)
4. Find the largest contour
5. Compute center (cx, cy), area, and position_hint ("LEFT"/"RIGHT"/"CENTER")
6. Publish a `Detection` message at camera frame rate
7. Publish a debug image with bounding box overlay to `/detector/debug_image`

**Testing protocol:**

```bash
# Terminal 1: roscore
# Terminal 2: roslaunch with camera (or rosrun usb_cam)
# Terminal 3: rosrun sprayer_control detector_node.py
# Terminal 4: rostopic echo /detection/result

# Hold a yellow ball in front of the camera.
# Move it LEFT → check position_hint says "LEFT"
# Move it RIGHT → check "RIGHT"
# Move it CENTER → check "CENTER"
# Remove it → check detected=False
```

**✅ Day 2 Deliverable:** `rostopic echo /detection/result` shows correct detection with cx, cy, area, position_hint updating in real-time. Debug image shows bounding box. Video recording saved.

**🎯 HSV Tuning Tip:** If yellow detection is flaky:
```bash
# Run this quick HSV tuner (standalone, not ROS):
python3 ~/catkin_ws/src/sprayer_control/scripts/hsv_tuner.py
# Adjust sliders until ONLY the yellow ball is white in the mask.
# Write down the H, S, V min/max values.
```

---

### 📅 DAY 3 (Feb 12): ESP32 INTEGRATION — SERIAL COMMUNICATION

**Goal:** Jetson sends "SPRAY_ON" → ESP32 fires the relay → Sprayer activates. Round-trip confirmed.

**Morning (3 hours): ESP32 Firmware**

Flash the ESP32-S3 with Arduino IDE / PlatformIO:

```
ESP32 Firmware Logic:
─────────────────────
1. Listen on Serial (115200 baud)
2. If receive "SPRAY_ON\n"  → Set relay pin HIGH, start watchdog timer, send "ACK_ON\n"
3. If receive "SPRAY_OFF\n" → Set relay pin LOW, send "ACK_OFF\n"
4. If receive "PING\n"      → Send "PONG\n"
5. WATCHDOG: If no "SPRAY_ON" refresh in 2 seconds → auto relay OFF, send "SAFETY_OFF\n"
6. MAX DURATION: If relay HIGH for > 5 seconds continuously → auto OFF
```

> ⚡ **ESP32 code is provided in `esp32/sprayer_controller/sprayer_controller.ino`**

**Afternoon (3 hours): Jetson Serial Test + ROS Node**

```bash
# 1. Connect ESP32 to Jetson via USB cable
# 2. Find the port:
ls /dev/ttyUSB* /dev/ttyACM*
# Usually /dev/ttyUSB0 or /dev/ttyACM0

# 3. Quick serial test (non-ROS):
python3 -c "
import serial, time
ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
time.sleep(2)  # Wait for ESP32 reset
ser.write(b'PING\n')
response = ser.readline().decode().strip()
print(f'ESP32 says: {response}')  # Should print: PONG
ser.write(b'SPRAY_ON\n')
response = ser.readline().decode().strip()
print(f'Spray response: {response}')  # Should print: ACK_ON
time.sleep(1)
ser.write(b'SPRAY_OFF\n')
response = ser.readline().decode().strip()
print(f'Off response: {response}')  # Should print: ACK_OFF
ser.close()
"
```

Now create: `~/catkin_ws/src/sprayer_control/scripts/spray_logic_node.py`

This node:
1. Subscribes to `/detection/result`
2. Implements the state machine: IDLE → DETECTED → ALIGNED → SPRAY → COOLDOWN
3. Sends serial commands to ESP32
4. Publishes spray status to `/spray/status`

**✅ Day 3 Deliverable:** Run `python3 serial_test.py` → ESP32 relay clicks ON and OFF. Spray logic node running and responding to fake detection messages published via `rostopic pub`.

---

### 📅 DAY 4 (Feb 13): THE "TABLE TEST" — FULL HIL INTEGRATION

**Goal:** Everything running together. Move yellow ball by hand → sprayer fires automatically when ball is centered and close enough. This is the KEY demo rehearsal.

**Setup:**

```
    TABLE TEST RIG
    ═══════════════════════════════════════

         Yellow Ball on stick
              🟡
              │    ~0.5 to 1.5 meters
              │
    ┌─────────┼──────────────────┐
    │         ▼                  │
    │   [Jete Webcam]            │
    │   [Jetson Nano]  ← Power  │
    │   [ESP32]        ← USB    │
    │   [Sprayer Pump] ← Relay  │
    │                            │
    │   All on the TABLE.        │
    │   NO drone frame needed.   │
    │   NO props. NO Pixhawk.    │
    └────────────────────────────┘

    Sprayer output: Into a cup/bowl for testing.
```

**Morning: Integration**

```bash
# 1. Launch everything:
roslaunch sprayer_control demo.launch

# 2. On laptop (SSH -X), open debug viewer:
rqt_image_view /detector/debug_image

# 3. Open monitoring terminals:
rostopic echo /detection/result
rostopic echo /spray/status
```

**Afternoon: Validation Tests**

| Test # | Action | Expected Result | ✅/❌ |
|--------|--------|----------------|-------|
| T1 | Ball at 1m, centered | `detected=True`, `position_hint=CENTER`, spray triggers after 1s lock | |
| T2 | Ball at 1m, LEFT of frame | `position_hint=LEFT`, spray does NOT trigger (not aligned) | |
| T3 | Ball at 1m, RIGHT of frame | `position_hint=RIGHT`, spray does NOT trigger | |
| T4 | Ball too far (small in frame) | `position_hint=TOO_FAR`, spray does NOT trigger | |
| T5 | No ball visible | `detected=False`, spray does NOT trigger | |
| T6 | Ball centered → moves away during spray | Spray stops when detection lost | |
| T7 | Run for 10 minutes continuously | No crashes, no memory leaks, FPS stable | |
| T8 | Unplug ESP32 USB during operation | Jetson detects serial error, logs warning, doesn't crash | |

**✅ Day 4 Deliverable:** ALL 8 tests pass. Video recorded of the full table test showing ball movement → spray trigger → spray stop. This video IS your demo backup plan.

---

### 📅 DAY 5 (Feb 14): INTEGRATION ON DRONE FRAME

**Goal:** Mount Jetson + Camera + ESP32 + Sprayer on the F450 frame. Verify nothing changed when it's on the drone.

**Morning: Physical Mounting**

```
    MOUNTING LAYOUT (Top View of F450 Frame)
    ═══════════════════════════════════════════

              FRONT
               ▲
        ┌──────┼──────┐
        │  ┌───┼───┐  │
        │  │ Camera │  │  ← Jete webcam, zip-tied
        │  │ (Front)│  │     facing forward
        │  └───────┘  │
        │              │
    ────┤  [Pixhawk]   ├────
        │  (Center)    │
        │              │
        │ [Jetson Nano]│  ← Secured with velcro +
        │ (Under/Side) │     zip ties. Anti-vibration
        │              │     foam pad underneath.
    ────┤              ├────
        │  [Battery]   │
        │  [ESP32]     │  ← ESP32 taped to arm or
        │  [Sprayer    │     body. Relay wired to pump.
        │   Pump]      │
        └──────────────┘
              REAR

    CABLE CHECKLIST:
    ─────────────────
    □ USB: Webcam → Jetson (short cable, zip-tied to frame)
    □ USB: ESP32 → Jetson (short cable, zip-tied)
    □ Power: Jetson → Battery via BEC/regulator (5V 4A)
    □ Power: ESP32 → Battery via BEC (5V or USB from Jetson)
    □ Power: Sprayer pump → Battery via ESP32 relay/MOSFET
    □ SECURE ALL CABLES with zip ties. Vibration WILL pull things loose.
    □ USB strain relief: Loop cables and zip-tie at both ends.
```

**Afternoon: On-Frame Verification**

```bash
# Same launch as Day 4, but now on the drone frame:
roslaunch sprayer_control demo.launch

# Re-run Table Tests T1-T7 with the drone on the table.
# PASS CRITERIA: Same results as Day 4. Nothing broke from mounting.
```

**Power Test:**
```bash
# Run full system for 15 minutes on battery power (NOT USB from laptop).
# Monitor:
#   - Jetson doesn't brownout (voltage sag)
#   - FPS stays stable
#   - ESP32 stays connected
#   - Battery voltage via Pixhawk telemetry
```

**Weight Check:**
```
Component weights (approximate):
  Jetson Nano + carrier board:  ~140g
  Jete webcam:                  ~50g
  ESP32-S3 + relay:             ~30g
  Sprayer pump + reservoir:     ~150-300g (depends on design)
  Cables + mounting:            ~50g
  ─────────────────────────────────
  TOTAL added weight:           ~420-570g

  F450 frame typical payload:   ~600-800g (with 2212 motors, 3S battery)

  ⚠️ If close to limit: use a 4S battery or reduce spray reservoir size.
```

**✅ Day 5 Deliverable:** Full system runs on the drone frame, powered by battery. Same pass criteria as Day 4. Flight-ready weight verified. Photo of the mounted system saved.

---

### 📅 DAY 6 (Feb 15): FIELD DEMO — THE SHOW

**Goal:** Demonstrate the integrated system. Two parts: ground demo + flight demo.

### Demo Part A: The "Smart Ground Test" (Safe, Impressive)

This is your GUARANTEED success demo. Even if flight goes wrong, this proves the tech.

```
DEMO SCRIPT (Ground):
═════════════════════
1. Drone on table/stand. Powered on. All LEDs green.
2. "The system is booting ROS and initializing the vision pipeline..."
   → Show laptop screen with debug camera view (SSH -X + rqt_image_view)
3. "Watch: I'll present a target (yellow ball simulating a flower)."
   → Hold ball in front. Bbox appears on screen.
4. "The AI has detected the target. See the bounding box and confidence score."
   → Point to the debug overlay.
5. "Now I'll center it. Watch the position indicator change from LEFT to CENTER."
   → Move ball to center of frame.
6. "The target is centered and within spray distance. Watch the sprayer."
   → Sprayer fires! Spray hits the target area.
7. "Now I'll remove the target. The system goes back to SEARCH mode."
   → Remove ball. Spray stops. State changes.
8. "All decisions are autonomous. No human triggers the spray."
```

### Demo Part B: The "Semi-Auto Flight" (If Conditions Allow)

**Pre-flight checklist:**
```
□ Battery fully charged (>95%)
□ Props inspected
□ RC transmitter bound and tested
□ Pixhawk in AltHold mode (FLTMODE1 = 2)
□ Kill switch verified on RC (FLTMODE6 = 9, Land)
□ Jetson powered and demo.launch running
□ ESP32 connected and responding to PING
□ Spray reservoir filled (or use water for demo)
□ Wind < 10 km/h
□ Clear area, no people within 5m
□ Safety goggles on
□ Spotter assigned
```

**Flight Demo Script:**

```
1. PILOT takes off manually → Hover at 1.5-2m altitude (AltHold).
2. ASSISTANT holds yellow ball on a long stick (~2m stick, standing 3m from drone).
3. PILOT yaws the drone to face the ball.
4. PILOT slowly approaches the ball (gentle forward stick).
5. Jetson detects the ball → Overlay shows DETECTED → ALIGNED.
6. When close enough + centered → SPRAYER FIRES AUTOMATICALLY.
7. PILOT holds position for 2 seconds, then backs off.
8. PILOT lands.
9. "The drone's AI decided WHEN to spray. The pilot only provided the movement.
    With the optical flow sensor (arriving next week), the approach will be
    autonomous too."
```

**⚠️ CRITICAL SAFETY RULES FOR FLIGHT DEMO:**
- Pilot NEVER releases the sticks. They are in full control.
- Kill switch is thumb-ready at ALL times.
- If ANYTHING feels wrong → LAND IMMEDIATELY.
- Ball holder stays BEHIND the ball relative to the drone.
- Nobody stands in the prop plane.

**✅ Day 6 Deliverable:** 
1. Video of ground demo (guaranteed impressive).
2. Video of flight demo (if conditions allow).
3. Both videos show: detection overlay + spray trigger + timestamps.

---

## PART 4: FILE STRUCTURE SUMMARY

```
~/catkin_ws/src/sprayer_control/
├── CMakeLists.txt
├── package.xml
├── msg/
│   └── Detection.msg
├── launch/
│   └── demo.launch
├── scripts/
│   ├── detector_node.py        ← Day 2: OpenCV HSV detection
│   ├── spray_logic_node.py     ← Day 3: State machine + ESP32 serial
│   ├── hsv_tuner.py            ← Day 2: Helper to tune HSV thresholds
│   └── debug_viewer.py         ← Optional: standalone debug window
└── config/
    └── detection_params.yaml   ← HSV values, thresholds, etc.

~/esp32_firmware/
└── sprayer_controller/
    └── sprayer_controller.ino  ← Day 3: ESP32 Arduino firmware
```

---

## PART 5: RISK MITIGATION & FALLBACK PLANS

| Risk | Probability | Fallback |
|------|------------|----------|
| Camera doesn't work in ROS (`usb_cam` fails) | Medium | Use raw OpenCV `cv2.VideoCapture(0)` without ROS camera node. Detector reads directly. |
| ESP32 serial port keeps changing (`ttyUSB0` → `ttyUSB1`) | High | Create a udev rule: `SUBSYSTEM=="tty", ATTRS{idVendor}=="xxxx", SYMLINK+="esp32"` then use `/dev/esp32`. |
| Yellow detection picks up other yellow things (shirt, sunlight) | High | Tighten HSV range. Add minimum area filter. Add shape filter (circularity). Control demo environment (dark background). |
| Jetson browns out on battery power | Medium | Use a dedicated 5V 4A BEC for Jetson. Do NOT share the Pixhawk BEC. |
| Flight demo goes wrong | Medium | **That's why Ground Demo exists as Plan A.** The ground demo alone proves the integration. Frame it as "Phase 1: Vision & Actuation validated. Phase 2: Autonomous flight (pending optical flow)." |
| Stakeholders ask "Why can't it fly to the target by itself?" | High | "The optical flow sensor for GPS-denied position hold is in transit. The architecture is designed for it — we just plug it into Pixhawk and enable velocity commands from Jetson. The hard part — the AI brain — is what you just saw working." |

---

## APPENDIX: WHAT HAPPENS AFTER THE DEMO (Week 2+)

When the Matek 3901-L0X arrives:

```
CURRENT (Survival Mode):
    Camera → Jetson (Detect + Align Check) → ESP32 (Spray)
    Pilot manually flies in AltHold.

UPGRADE PATH (With Optical Flow):
    Camera → Jetson (Detect + Visual Servo PID) → Pixhawk (Velocity Cmds)
    Matek 3901-L0X → Pixhawk (Position Hold)
    Jetson → ESP32 (Spray, unchanged)
    Drone flies autonomously in GUIDED mode.

WHAT CHANGES:
    ┌─────────────────────────────────────────────────────┐
    │ spray_logic_node.py  → Add mavros velocity publisher │
    │                        Add PID controllers (from    │
    │                        ARCHITECTURE_REVIEW.md)      │
    │                                                     │
    │ demo.launch          → Add mavros node              │
    │                        Add PID params               │
    │                                                     │
    │ Pixhawk              → Load optical flow params     │
    │                        (config/ardupilot_params.param) │
    │                                                     │
    │ detector_node.py     → UNCHANGED ✅                  │
    │ ESP32 firmware       → UNCHANGED ✅                  │
    │ Camera setup         → UNCHANGED ✅                  │
    └─────────────────────────────────────────────────────┘

    ~70% of your code survives the upgrade. That's the point of good architecture.
```

---

*Document Version: 1.0 | Sprint Start: Feb 10, 2026 | Demo Day: Feb 15, 2026*
*"Done is better than perfect. Especially on Day 6."*

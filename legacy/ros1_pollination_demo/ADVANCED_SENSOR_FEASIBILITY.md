# Advanced Sensor & Algorithm Feasibility Study
### Subtitle: "Should We Upgrade Beyond the Baseline?"
### Date: February 9, 2026
### Budget Ceiling: IDR 4–5 Million (~$300 USD) for additional sensors
### Prerequisite: Read NAVIGATION_ARCHITECTURE.md first (the baseline we're comparing against)

---

## 0. DOCUMENT PURPOSE — WHY THIS EXISTS

The `NAVIGATION_ARCHITECTURE.md` document established a **Behavior-Based baseline**: cheap HSV detection, camera-only obstacle avoidance (`dark_ratio` heuristic), and dead-reckoning with optical flow. That baseline works for the 80% case.

This document asks: **"What if we spend $100–$300 more on sensors — do we get 90%? 95%? 99%?"**

For each upgrade option, I will answer:
1. Does it **actually work** on Jetson Nano 4GB?
2. Does it solve a **real problem** we currently have?
3. What's the **implementation cost** in time and complexity?
4. Is the **robustness gain** worth the money and integration effort?

**Spoiler alert:** One option stands far above the rest. But let's do the engineering first.

---

## 1. THE BASELINE — WHAT WE'RE COMPARING AGAINST

```
    CURRENT "BEHAVIOR-BASED" SYSTEM (from NAVIGATION_ARCHITECTURE.md):
    ═══════════════════════════════════════════════════════════════════

    Sensors:
      ✅ Jete FHD 1080p USB Webcam (front-facing)  — $15
      ✅ Matek 3901-L0X (optical flow + rangefinder) — $25
      ✅ Pixhawk 2.4.8 (IMU, baro, compass)         — existing

    Obstacle Avoidance:
      ⚠️ Camera "dark_ratio" heuristic — detects trunks > 20cm wide at > 0.5m
      ❌ Cannot detect thin objects (wires, branches < 5cm)
      ❌ No true distance measurement to obstacles

    Search:
      ⚠️ 360° rotation scan — works but takes 12 seconds
      ⚠️ Trunk hop heuristic — clever but requires trunk to be visible
      ❌ No depth information — trunk distance estimated from bbox width (±30% error)

    Navigation:
      ✅ Dead-reckoning from optical flow — good for 3-8m hops
      ⚠️ Drift accumulates — ±2-5m after 100m travel
      ❌ No external reference frame correction

    TOTAL ADDITIONAL SENSOR COST: ~$40 (webcam + Matek)
    ROBUSTNESS RATING: ★★★☆☆ (works in good conditions, fragile at edges)
```

---

## 2. OPTION A — DEPTH CAMERA: INTEL REALSENSE D435i

### 2.1 Hardware Specifications

```
    ╔═══════════════════════════════════════════════════════════════════╗
    ║                    INTEL REALSENSE D435i                        ║
    ╠═══════════════════════════════════════╦═══════════════════════════╣
    ║ Depth Technology                      ║ Active IR Stereo          ║
    ║ Depth Resolution                      ║ Up to 1280x720           ║
    ║ Depth FPS                             ║ Up to 90fps (at 480p)    ║
    ║ Depth Range                           ║ 0.1m – 10m               ║
    ║ Depth FOV                             ║ 87° × 58° (H×V)         ║
    ║ RGB Resolution                        ║ 1920x1080 @ 30fps        ║
    ║ RGB FOV                               ║ 69° × 42°               ║
    ║ IMU                                   ║ BMI055 (6-axis, Accel+Gyro)║
    ║ Interface                             ║ USB 3.0 (required)       ║
    ║ Power Consumption                     ║ ~3-4W typical             ║
    ║ Weight                                ║ ~72g                     ║
    ║ Onboard Compute                       ║ Intel D4 ASIC (stereo    ║
    ║                                       ║ matching only)           ║
    ║ Price (2025-2026)                     ║ $250-300 USD             ║
    ║ Indonesian Availability               ║ ⚠️ Limited. Tokopedia/   ║
    ║                                       ║ Shopee ~IDR 4-5 juta     ║
    ╚═══════════════════════════════════════╩═══════════════════════════╝
```

### 2.2 Critical Analysis — Can Jetson Nano Handle It?

**The D435i has a critical advantage most people miss:** The Intel D4 ASIC performs the stereo matching **onboard the camera.** The Jetson receives a **pre-computed depth image** (640×480 uint16 depth map), NOT a raw stereo pair that needs GPU processing.

```
    WHAT THE JETSON ACTUALLY RECEIVES:
    ══════════════════════════════════════════════

    From D435i via USB 3.0:
    ┌────────────────────┐  ┌──────────────────────┐
    │   Depth Frame      │  │    RGB Frame          │
    │   640×480 uint16   │  │    640×480 BGR        │
    │   ~600 KB/frame    │  │    ~900 KB/frame      │
    │   @ 30fps          │  │    @ 30fps            │
    │   = ~18 MB/s       │  │    = ~27 MB/s         │
    └────────────────────┘  └──────────────────────┘
                Total USB 3.0 bandwidth: ~45 MB/s
                USB 3.0 max: ~400 MB/s → ~11% utilization. FINE.

    JETSON NANO DOES NOT NEED TO:
    ✅ Run stereo matching (done by D4 ASIC)
    ✅ Run disparity computation
    ✅ Build 3D point cloud (optional, can skip)

    JETSON NANO DOES NEED TO:
    ⚠️ Read the depth frame at 30fps (~3ms per frame, USB DMA)
    ⚠️ Process the depth frame for obstacle avoidance
    ⚠️ Still run YOLO on the RGB stream for flower detection
```

**Compute budget WITH D435i (replacing the Jete webcam):**

```
    ╔═══════════════════════════════════════════════════════════════╗
    ║          COMPUTE BUDGET: BASELINE + D435i                    ║
    ╠═══════════════════════════════════════════╦═══════════════════╣
    ║ Component                                 ║ Time     Resource ║
    ╠═══════════════════════════════════════════╬═══════════════════╣
    ║ D435i frame capture (USB 3.0 DMA)        ║ ~5ms    USB+DMA   ║
    ║   RGB: 640×480 BGR                        ║ (bundled)         ║
    ║   Depth: 640×480 uint16                   ║ (bundled)         ║
    ║ Depth → Obstacle check (CPU)             ║ ~3ms    CPU       ║
    ║   ROI extraction (danger zone)            ║  0.5ms            ║
    ║   Min/max depth in ROI                    ║  1ms              ║
    ║   Sector scan (left/center/right depth)   ║  1.5ms            ║
    ║ HSV detect (SEARCH mode, CPU)            ║ ~3ms    CPU       ║
    ║ YOLO detect (APPROACH mode, GPU)         ║ ~45ms   GPU 50%   ║
    ║ State machine + PID                       ║ <1ms    CPU       ║
    ║ MAVLink send                              ║ <1ms    CPU       ║
    ║                                           ║                   ║
    ║ TOTAL (SEARCH mode):   ~13ms/frame       ║ CPU ONLY. ✅      ║
    ║ TOTAL (APPROACH mode): ~55ms/frame       ║ GPU ~50%. ✅      ║
    ║                                           ║                   ║
    ║ RAM overhead:  +~200 MB (librealsense2    ║                   ║
    ║   + depth buffers)                        ║                   ║
    ║ Total RAM: ~2.0 GB of 4 GB. SAFE.        ║                   ║
    ╚═══════════════════════════════════════════╩═══════════════════╝

    VERDICT: YES, the Jetson Nano can handle D435i + YOLO.
    The D4 ASIC does the heavy lifting. Nano just reads the result.
```

### 2.3 How It Changes Obstacle Avoidance

**Before (camera-only `dark_ratio`):**
```
    CURRENT: "Is the bottom of the frame dark?"
    ─────────────────────────────────────────────
    Accuracy: ±30% distance estimation
    Min obstacle size: ~20cm wide
    False positives: Shadows, dark leaves
    False negatives: Light-colored obstacles, thin branches
    Reaction distance: Unknown (no depth)
    Rating: ★★☆☆☆
```

**After (D435i depth):**
```
    UPGRADED: "What is the actual distance to every pixel?"
    ─────────────────────────────────────────────────────────
    Method: Read depth values in 3 sectors (Left / Center / Right)

    ┌──────────────────────────────────────────┐
    │              640×480 depth frame          │
    │                                          │
    │   ┌─────────┬──────────┬─────────┐      │
    │   │  LEFT   │  CENTER  │  RIGHT  │      │
    │   │ Sector  │  Sector  │ Sector  │      │
    │   │         │          │         │      │
    │   │ min_d=  │ min_d=   │ min_d=  │      │
    │   │ 2.3m    │ 0.8m ⚠️ │ 3.1m    │      │
    │   │         │          │         │      │
    │   └─────────┴──────────┴─────────┘      │
    │                                          │
    │   Decision: Center obstacle at 0.8m!     │
    │   Action: Strafe RIGHT (clear at 3.1m)   │
    └──────────────────────────────────────────┘

    Accuracy: ±2-5% at < 4m (absolute depth)
    Min obstacle size: Any pixel-level obstacle
    False positives: Very rare (depth is physics, not heuristic)
    False negatives: Very thin wires (< 5mm) might be missed
    Reaction distance: KNOWN precisely → can set exact thresholds
    Rating: ★★★★★

    OBSTACLE AVOIDANCE LOGIC (with depth):
    ════════════════════════════════════════
    if center_min_depth < 1.0m:
        STOP + determine clear direction
    elif center_min_depth < 2.0m:
        SLOW DOWN (0.15 m/s)
    elif center_min_depth < 3.0m:
        CAUTION (maintain current speed, monitor)
    else:
        CLEAR (full speed)

    # Lateral escape direction:
    if left_min_depth > right_min_depth:
        escape_direction = LEFT
    else:
        escape_direction = RIGHT
```

### 2.4 Bonus: What Else D435i Gives You

```
    ADDITIONAL CAPABILITIES (beyond obstacle avoidance):
    ════════════════════════════════════════════════════════

    1. PRECISE DISTANCE TO FLOWER
       Current: Estimate from bbox area (±30% error)
       With D435i: Read depth at bbox center pixel (±2% at <4m)
       Impact: SERVO_FINE state gets TRUE range → better PID → tighter spray

    2. TRUNK DISTANCE (for TRUNK_HOP)
       Current: bbox width heuristic → "close / medium / far"
       With D435i: trunk is exactly 2.3m away → approach at 0.3m/s for 7.7s
       Impact: No more guessing → deterministic approach

    3. 3D POSITION OF DETECTED FLOWERS
       RGB gives (cx, cy). Depth gives distance.
       → You can compute (x, y, z) in camera frame.
       → You can estimate world position of EACH flower.
       Impact: Anti-revisit becomes near-perfect (±10cm 3D, not ±50cm 2D)

    4. IMU DATA (BMI055 onboard D435i)
       Can be used for visual-inertial odometry (VIO)
       on the D435i + Jetson → much better than optical flow alone.
       BUT: adds compute complexity. Leave for future upgrade.
```

### 2.5 D435i — Problems & Risks

```
    ╔═══════════════════════════════════════════════════════════════════╗
    ║                    D435i RISK REGISTER                          ║
    ╠═══════════════════════════════╦═════════════════════════════════╣
    ║ RISK                          ║ MITIGATION                      ║
    ╠═══════════════════════════════╬═════════════════════════════════╣
    ║ Price at budget ceiling       ║ $250-300 leaves almost no       ║
    ║ ($250-300)                    ║ budget for other upgrades.      ║
    ║                               ║ → OAK-D Lite at $149 might     ║
    ║                               ║   be a better value play.      ║
    ╠═══════════════════════════════╬═════════════════════════════════╣
    ║ USB 3.0 REQUIRED              ║ Jetson Nano has ONE USB 3.0    ║
    ║ (will not work on USB 2.0)    ║ port. D435i takes it.          ║
    ║                               ║ → Other USB devices (ESP32     ║
    ║                               ║   serial) go to USB 2.0 hub.  ║
    ║                               ║ → Matek 3901 uses I2C, not    ║
    ║                               ║   USB. No conflict.            ║
    ╠═══════════════════════════════╬═════════════════════════════════╣
    ║ Outdoor IR interference       ║ Sunlight contains IR. The      ║
    ║ (sunlight at 850nm)           ║ D435i active IR projector may  ║
    ║                               ║ be overwhelmed by direct sun.  ║
    ║                               ║ → Under canopy: sunlight is    ║
    ║                               ║   filtered/dappled. Should     ║
    ║                               ║   be manageable.               ║
    ║                               ║ → Worst case: stereo still     ║
    ║                               ║   works passively (no IR).     ║
    ╠═══════════════════════════════╬═════════════════════════════════╣
    ║ Intel discontinued RealSense  ║ Intel ended new development    ║
    ║ (2021 announcement)           ║ in 2021 but D400 series is     ║
    ║                               ║ still manufactured/sold as of  ║
    ║                               ║ 2025. librealsense2 is         ║
    ║                               ║ community-maintained.          ║
    ║                               ║ → Long-term risk. For a        ║
    ║                               ║   research prototype, fine.    ║
    ╠═══════════════════════════════╬═════════════════════════════════╣
    ║ Weight (72g) + cable          ║ F450 frame handles it easily.  ║
    ║                               ║ 72g is < 5% of total AUW.     ║
    ║                               ║ Mount with vibration damping.  ║
    ╠═══════════════════════════════╬═════════════════════════════════╣
    ║ Power draw (3-4W)             ║ Jetson Nano max = 10W. D435i   ║
    ║                               ║ = 3-4W. Total system power     ║
    ║                               ║ = ~16-18W. 4S LiPo can        ║
    ║                               ║ supply this. Check BEC rating. ║
    ╚═══════════════════════════════╩═════════════════════════════════╝
```

---

## 3. OPTION B — DEPTH CAMERA: LUXONIS OAK-D LITE

### 3.1 Hardware Specifications

```
    ╔═══════════════════════════════════════════════════════════════════╗
    ║                      LUXONIS OAK-D LITE                         ║
    ╠═══════════════════════════════════════╦═══════════════════════════╣
    ║ Depth Technology                      ║ Passive Stereo (no IR)   ║
    ║ Stereo Resolution                     ║ 640×480 (OV7251 mono)    ║
    ║ Depth FPS                             ║ Up to 60fps              ║
    ║ Depth Range                           ║ 0.2m – 12m (ideal ~0.8m+)║
    ║ Depth FOV                             ║ 73° × 58° (H×V)         ║
    ║ RGB Sensor                            ║ IMX214, 4K capable       ║
    ║ RGB FOV                               ║ 69° × 54°               ║
    ║ IMU                                   ║ BMI270 (6-axis)          ║
    ║ VPU (Onboard AI)                      ║ Intel Movidius Myriad X  ║
    ║                                       ║ (RVC2), 4 TOPS           ║
    ║                                       ║ 1.4 TOPS for AI models   ║
    ║ Interface                             ║ USB 2.0 or 3.0           ║
    ║ Power Consumption                     ║ 2.5-4.5W (VPU dependent) ║
    ║ Weight                                ║ ~61g                     ║
    ║ IR Dot Projector                      ║ ❌ NO (Lite = passive)   ║
    ║ Onboard Compute                       ║ ✅ Full VPU — can run    ║
    ║                                       ║ YOLO, stereo, tracking   ║
    ║                                       ║ ALL onboard the camera!  ║
    ║ Price (2025-2026)                     ║ $149 USD (~IDR 2.3 juta) ║
    ║ Indonesian Availability               ║ Luxonis ships globally.  ║
    ║                                       ║ ~1 week delivery.        ║
    ╚═══════════════════════════════════════╩═══════════════════════════╝
```

### 3.2 The Killer Feature — Onboard VPU (THIS CHANGES EVERYTHING)

**The OAK-D Lite is not just a camera. It's a camera + co-processor.**

The Intel Movidius Myriad X VPU inside the OAK-D can run:
- Stereo depth computation
- Neural network inference (YOLO, MobileNet-SSD, etc.)
- Feature tracking
- Object tracking (2D and 3D)
- Image processing (resize, warp, edge detection)

**ALL of this runs ON THE CAMERA, not on the Jetson Nano.**

```
    ARCHITECTURE COMPARISON:
    ════════════════════════════════════════════════════════

    CURRENT (Jete Webcam):
    ┌───────────┐     USB      ┌──────────────────┐
    │ Jete Cam  │──── RGB ────►│   JETSON NANO    │
    │ (dumb)    │   640×480    │                  │
    │           │              │ YOLO (GPU 50%)   │
    │           │              │ HSV (CPU)        │
    │           │              │ PID (CPU)        │
    │           │              │ MAVLink (CPU)    │
    └───────────┘              └──────────────────┘
    Camera does: Nothing.
    Jetson does: EVERYTHING.

    WITH REALSENSE D435i:
    ┌───────────┐  USB 3.0  ┌──────────────────┐
    │ D435i     │── RGB ──►│   JETSON NANO    │
    │           │── Depth──►│                  │
    │ D4 ASIC:  │           │ YOLO (GPU 50%)   │
    │ Stereo    │           │ Depth proc (CPU) │
    │ matching  │           │ PID (CPU)        │
    └───────────┘           └──────────────────┘
    Camera does: Stereo matching.
    Jetson does: AI inference + everything else.

    ✅✅ WITH OAK-D LITE (THE GAME CHANGER):
    ┌─────────────────┐  USB   ┌──────────────────┐
    │    OAK-D Lite   │────────►│   JETSON NANO    │
    │                 │  JSON/  │                  │
    │ VPU runs:       │  struct │ PID (CPU ~5%)    │
    │  ✅ YOLO-nano  │  only!  │ MAVLink (CPU)    │
    │  ✅ Stereo     │         │ State machine    │
    │  ✅ Tracking   │         │                  │
    │  ✅ Depth      │         │ GPU: 0% !!!      │
    │                 │         │ CPU: ~15%        │
    └─────────────────┘         └──────────────────┘
    Camera does: AI + Depth + Tracking.
    Jetson does: ONLY decision logic + communication.

    JETSON NANO GPU UTILIZATION:
      Current:    50-60% (YOLO)
      D435i:      50-60% (still runs YOLO on Nano)
      OAK-D Lite: 0%     ← GPU is COMPLETELY FREE
```

### 3.3 Compute Budget with OAK-D Lite

```
    ╔═══════════════════════════════════════════════════════════════╗
    ║          COMPUTE BUDGET: OAK-D LITE (VPU offloaded)          ║
    ╠═══════════════════════════════════════════╦═══════════════════╣
    ║ OAK-D VPU (runs independently):          ║ Nano doesn't care ║
    ║   Stereo depth: ~30fps                    ║ (all on VPU)     ║
    ║   YOLO-nano: ~25fps (300x300, INT8)      ║                   ║
    ║   Feature tracking: ~30fps               ║                   ║
    ║   Object tracking: ~30fps                ║                   ║
    ╠═══════════════════════════════════════════╬═══════════════════╣
    ║ Jetson Nano receives (via USB):          ║                   ║
    ║   Detection results (bbox JSON):  ~1KB   ║ <1ms    CPU      ║
    ║   Depth frame (640×480):          ~600KB  ║ ~3ms    CPU      ║
    ║     (optional — can request only ROI)    ║                   ║
    ║   Tracking IDs:                   ~1KB   ║ <1ms    CPU      ║
    ║                                           ║                   ║
    ║ State machine + PID:                     ║ <1ms    CPU      ║
    ║ MAVLink send:                            ║ <1ms    CPU      ║
    ║ ESP32 serial:                            ║ <1ms    CPU      ║
    ║                                           ║                   ║
    ║ TOTAL JETSON LOAD:                       ║                   ║
    ║   GPU: 0%  ← completely free!            ║                   ║
    ║   CPU: ~10-15%                           ║                   ║
    ║   RAM: ~1.5 GB (OS + ROS + depthai lib)  ║                   ║
    ║   USB: ~20-30 MB/s of USB 3.0 (or 2.0)  ║                   ║
    ║                                           ║                   ║
    ║ HEADROOM: 85% CPU, 100% GPU FREE         ║                   ║
    ║ → Can add MORE features if needed        ║                   ║
    ║ → System is massively over-provisioned   ║                   ║
    ║ → Thermal issues: GONE                   ║                   ║
    ╚═══════════════════════════════════════════╩═══════════════════╝
```

### 3.4 OAK-D Lite — Problems & Risks

```
    ╔═══════════════════════════════════════════════════════════════════╗
    ║                    OAK-D LITE RISK REGISTER                     ║
    ╠═══════════════════════════════╦═════════════════════════════════╣
    ║ RISK                          ║ MITIGATION                      ║
    ╠═══════════════════════════════╬═════════════════════════════════╣
    ║ PASSIVE stereo only (no IR   ║ Under canopy = lots of texture  ║
    ║ dot projector). Fails on     ║ (leaves, bark, ground). Passive ║
    ║ textureless surfaces.        ║ stereo works FINE here.         ║
    ║                               ║ Problem areas: blank walls,    ║
    ║                               ║ clear sky (not in our use case)║
    ║                               ║ → Low risk for plantation.     ║
    ╠═══════════════════════════════╬═════════════════════════════════╣
    ║ Stereo sensors (OV7251) are  ║ 640×480 stereo is sufficient    ║
    ║ only 480p. Lower res than    ║ for obstacle detection at       ║
    ║ D435i stereo (720p).         ║ 0.5-8m range.                   ║
    ║                               ║ → Acceptable for our use case. ║
    ╠═══════════════════════════════╬═════════════════════════════════╣
    ║ YOLO on VPU (Myriad X) is   ║ 25fps YOLO-nano on VPU vs.     ║
    ║ slower than TensorRT on Nano ║ 20fps YOLO-nano on Nano GPU.   ║
    ║ for some model sizes.        ║ Actually comparable or faster!  ║
    ║                               ║ And the Nano GPU is freed up.  ║
    ║                               ║ Net gain: massive.             ║
    ╠═══════════════════════════════╬═════════════════════════════════╣
    ║ Model conversion: Must       ║ Luxonis provides conversion     ║
    ║ convert YOLO to OpenVINO     ║ tools. Well-documented process. ║
    ║ (blob) format for VPU.       ║ YOLOv8-nano → ONNX → blob      ║
    ║ Not TensorRT.                ║ takes ~1 hour first time.       ║
    ╠═══════════════════════════════╬═════════════════════════════════╣
    ║ Different SDK: depthai       ║ depthai SDK is well-maintained, ║
    ║ instead of OpenCV/librealsense║ Python API, ROS node available.║
    ║ Learning curve.              ║ ~2-3 days to learn pipeline.    ║
    ╠═══════════════════════════════╬═════════════════════════════════╣
    ║ Global shutter on stereo     ║ Global shutter is BETTER for    ║
    ║ but rolling shutter on RGB.  ║ fast motion. Stereo (used for   ║
    ║                               ║ depth) won't blur from drone   ║
    ║                               ║ vibration. RGB rolling shutter ║
    ║                               ║ = same as current Jete cam.    ║
    ╚═══════════════════════════════╩═════════════════════════════════╝
```

### 3.5 OAK-D Pro — Is the Upgrade to Pro Worth It?

```
    OAK-D LITE vs. OAK-D PRO:
    ═══════════════════════════════════════════════════════

    Feature            │ OAK-D Lite ($149) │ OAK-D Pro ($249)
    ───────────────────┼───────────────────┼──────────────────
    VPU (Myriad X)     │ ✅ Same           │ ✅ Same
    AI Performance     │ ✅ Same 1.4 TOPS  │ ✅ Same 1.4 TOPS
    Stereo Depth       │ ✅ Passive        │ ✅ Passive + Active
    IR Dot Projector   │ ❌ No             │ ✅ Yes (ASV)
    IR Flood LED       │ ❌ No             │ ✅ Yes (night vision)
    Stereo Sensors     │ OV7251 (480p)     │ OV9282 (800p) ← better
    RGB Sensor         │ IMX214 (13MP)     │ IMX378 (12MP)
    IMU                │ BMI270 (6-axis)   │ BNO086 (9-axis) ← better
    Weight             │ 61g               │ ~91g
    Power (max)        │ ~4.5W             │ ~15W (with IR!) ⚠️
    Vibration Tested   │ No data           │ ✅ EN 60068-2-6 certified

    MY VERDICT: 
    ───────────
    For this project → OAK-D LITE is sufficient.
    
    Why NOT Pro:
    • IR projector is wasted under canopy (textured environment)
    • 15W power draw (with IR) is excessive for drone power budget
    • $100 more for features you don't need
    • 30g heavier
    
    When you WOULD need Pro:
    • Indoor navigation (blank walls, textureless floors)
    • Night operation
    • Need vibration certification for production
    
    SAVE THE $100. Buy the Lite. Use the savings for:
    • A good USB cable with strain relief ($5)
    • A 3D-printed vibration-dampening mount ($10)
    • A forward-facing TFMini LiDAR as backup ($15) ← see Option E
```

---

## 4. OPTION C — LOCAL PLANNING ALGORITHMS (DWA / VFH+)

### 4.1 What Are DWA and VFH+?

```
    DWA (Dynamic Window Approach):
    ══════════════════════════════════════
    Concept: At each timestep, simulate many possible velocity
             combinations (vx, vy, omega). Score each by:
             - Distance to goal
             - Clearance from obstacles
             - Velocity preference
             Pick the highest-scored velocity and execute it.
    
    Requires: 360° obstacle distance data (typically from LiDAR)
    Compute:  Moderate — scoring ~100-500 velocity samples per cycle
    Latency:  Needs to run at ≥10Hz to be responsive
    Typical use: Ground robots with 2D LiDAR

    VFH+ (Vector Field Histogram Plus):
    ══════════════════════════════════════
    Concept: Build a "polar histogram" of obstacle density around
             the robot. Each angular sector gets a score.
             Navigate through the sector with lowest obstacle density
             that also points toward the goal.
    
    Requires: 360° distance data (LiDAR ideal, depth camera possible)
    Compute:  Lower than DWA — histogram binning + sector selection
    Latency:  Runs at 10-20Hz easily
    Typical use: Mobile robots in cluttered environments
```

### 4.2 Can They Run on Jetson Nano?

```
    COMPUTE FEASIBILITY:
    ═══════════════════════════════════════════════════════

    DWA on Jetson Nano:
      Velocity samples: 200 (10 vx × 10 vy × 2 omega)
      Simulation per sample: ~50 μs
      Total per cycle: ~10ms (CPU only)
      At 10Hz: CPU load ~10%
      ✅ YES, DWA can run on Nano.

    VFH+ on Jetson Nano:
      Histogram sectors: 72 (5° each)
      Update per sector: ~20 μs
      Total per cycle: ~2ms (CPU only)
      At 20Hz: CPU load ~4%
      ✅ YES, VFH+ can run on Nano.

    BUT THE REAL QUESTION: Do we have the SENSOR DATA they need?
```

### 4.3 The Sensor Data Problem — This Is Where It Falls Apart

```
    DWA AND VFH+ NEED 360° OBSTACLE DATA.
    WE HAVE A FORWARD-FACING CAMERA.
    ════════════════════════════════════════════════

    WHAT DWA/VFH+ EXPECT:
    ┌──────────────────────────────┐
    │        360° LiDAR scan       │
    │                              │
    │         ▲ 0°                 │
    │        / \                   │
    │       /   \                  │
    │  270°●     ●90°             │
    │       \   /                  │
    │        \ /                   │
    │         ▼ 180°               │
    │                              │
    │  Data: distance at each      │
    │  angle. Full surround.       │
    └──────────────────────────────┘

    WHAT WE HAVE (forward depth camera):
    ┌──────────────────────────────┐
    │                              │
    │         ▲ 0°                 │
    │        ╱ ╲                   │
    │       ╱   ╲                  │
    │      ╱  ~80° ╲  ← Camera    │
    │     ╱  FOV    ╲    cone     │
    │                              │
    │  270°  ??     ??  90°        │
    │                              │
    │  Data: depth only in ~80°    │
    │  forward cone. Blind behind  │
    │  and to the sides.           │
    └──────────────────────────────┘

    PROBLEM: DWA/VFH+ with only forward data → drone can escape
    FORWARD through obstacles but has no idea what's behind it.
    
    During RETREAT (backing up after spray), it's COMPLETELY BLIND.
    During TRUNK_ORBIT (strafing), it has partial coverage.
    
    SOLUTIONS:
    A) Add a 360° 2D LiDAR (RPLidar A1) → see Option D
    B) Use depth camera + aggressive SCAN_360 → build a cached
       "local occupancy" from multiple headings → complex, fragile
    C) Accept the limitation: use DWA/VFH+ only in the forward
       direction, fall back to simple heuristics for lateral/rear
```

### 4.4 Verdict on DWA/VFH+

```
    ╔═══════════════════════════════════════════════════════════════╗
    ║                  DWA / VFH+ VERDICT                          ║
    ║                                                               ║
    ║  Computationally feasible on Nano: ✅ YES                     ║
    ║  Useful with forward depth camera only: ⚠️ PARTIAL            ║
    ║  Useful with 360° LiDAR: ✅ YES, excellent                   ║
    ║  Worth the implementation effort: ❌ NOT YET                  ║
    ║                                                               ║
    ║  Reasoning:                                                   ║
    ║  Our drone flies at 0.3-0.5 m/s. At these speeds, simple    ║
    ║  "STOP → BACK → LATERAL → SCAN" is sufficient. DWA/VFH+    ║
    ║  shine at higher speeds where reaction time matters (1-5 m/s ║
    ║  ground robots). For a slow, hovering drone under canopy:    ║
    ║  engineering overkill.                                        ║
    ║                                                               ║
    ║  WHEN TO REVISIT:                                            ║
    ║  If you add a 360° LiDAR AND want the drone to fly faster   ║
    ║  (> 1 m/s), DWA becomes worthwhile. Not before.             ║
    ╚═══════════════════════════════════════════════════════════════╝
```

---

## 5. OPTION D — 2D LIDAR (RPLidar A1 / A2)

### 5.1 Hardware Specifications

```
    ╔═══════════════════════════════════════════════════════════════════╗
    ║                  SLAMTEC RPLIDAR A1M8                           ║
    ╠═══════════════════════════════════════╦═══════════════════════════╣
    ║ Type                                  ║ 360° 2D Laser Scanner    ║
    ║ Range                                 ║ 0.15m – 12m             ║
    ║ Angular Resolution                    ║ ~1° (360 points/scan)    ║
    ║ Scan Rate                             ║ 5.5 Hz (2000 pts/s)     ║
    ║ Interface                             ║ UART / USB (FTDI)        ║
    ║ Power                                 ║ ~2.5W (with motor)       ║
    ║ Weight                                ║ ~170g ⚠️ (heavy!)       ║
    ║ Price                                 ║ ~$99-120 USD             ║
    ╠═══════════════════════════════════════╬═══════════════════════════╣
    ║                  SLAMTEC RPLIDAR A2M12                          ║
    ╠═══════════════════════════════════════╬═══════════════════════════╣
    ║ Range                                 ║ 0.15m – 18m             ║
    ║ Scan Rate                             ║ 10 Hz (8000 pts/s)      ║
    ║ Weight                                ║ ~190g ⚠️⚠️              ║
    ║ Price                                 ║ ~$200-250 USD            ║
    ╚═══════════════════════════════════════╩═══════════════════════════╝
```

### 5.2 The Fundamental Problem — 2D LiDAR in a 3D World

```
    A 2D LiDAR scans ONE horizontal plane.
    Your drone flies in a 3D world full of obstacles at DIFFERENT heights.
    ════════════════════════════════════════════════════════════

    SIDE VIEW of oil palm plantation:
    ─────────────────────────────────────────────────────
                    🌴 Frond tips (3-4m)
                   /│\
                  / │ \         🌴 Frond tips
                 /  │  \       /│\
    ─ ─ ─ ─ ─ /─ ─│─ ─\─ ─ / ─│─ \─ ─ ─ ─ ─ ─ ─
              /    │    \  /   │   \
             /     │     \/    │    \
            Trunk  │  Trunk    │  Trunk
    ════════│══════│════│══════│════│═══ Ground
    
    WHERE THE 2D LIDAR SCANS (single horizontal plane):
    ─────────────────────────────────────────────────────
                    🌴
                   /│\
    ─ ─ ─ ─ ─ ─ /─│─\─ ─ ─ ─ ─ ─  ← LiDAR at 1.5m
         DRONE  /  │  \               sees frond stems
         ✈️    /   │   \              but MISSES:
              /    │    \             - Low-hanging fronds
             /     │     \            - Trunk base
    ════════│══════│═════│═══ Ground  - Frond tips above

    WHAT THE 2D LIDAR SEES AT 1.5m HEIGHT:
    ┌────────────────────────────────────────────┐
    │  Top view: 360° scan at 1.5m altitude      │
    │                                            │
    │           ● trunk (25cm)                    │
    │          ╱│╲                                │
    │  frond ╱  │  ╲ frond                       │
    │  stem    │    stem          ● trunk         │
    │          │                                  │
    │          │                                  │
    │      ✈️ drone                              │
    │                                            │
    │  The LiDAR sees trunk cross-sections       │
    │  and some frond stems. But it CANNOT see:  │
    │  - Fronds above/below the scan plane       │
    │  - Hanging bunches at different heights     │
    │  - Sloping ground (it assumes flat world)  │
    └────────────────────────────────────────────┘
```

### 5.3 Verdict on 2D LiDAR

```
    ╔═══════════════════════════════════════════════════════════════╗
    ║                  2D LIDAR VERDICT                             ║
    ║                                                               ║
    ║  Trunk detection (2D cross-section): ✅ EXCELLENT             ║
    ║  Full obstacle avoidance: ❌ INSUFFICIENT                     ║
    ║  Weight penalty: ⚠️ SIGNIFICANT (170-190g)                   ║
    ║  Integration complexity: ⚠️ HIGH (motor vibration coupling)  ║
    ║  Cost: $99-250                                               ║
    ║                                                               ║
    ║  PROBLEMS SPECIFIC TO DRONE USE:                             ║
    ║  1. Spinning motor creates vibration (couples with drone     ║
    ║     vibration → noisy data)                                  ║
    ║  2. 170-190g on a F450 is significant (flight time -10-15%)  ║
    ║  3. At 5.5-10 Hz scan rate, drone moving at 0.5 m/s means   ║
    ║     ~5-10cm between scans → acceptable but not great        ║
    ║  4. 2D plane misses the most dangerous obstacles             ║
    ║     (fronds at drone height, hanging bunches)                ║
    ║                                                               ║
    ║  Better alternatives exist for same budget:                  ║
    ║  OAK-D Lite ($149) gives 3D depth in a cone → MORE USEFUL   ║
    ║  for a forward-moving drone than 360° 2D.                   ║
    ║                                                               ║
    ║  WHEN TO USE 2D LIDAR:                                       ║
    ║  If the project pivots to ground robot (rover). For drones:  ║
    ║  depth camera is strictly better.                            ║
    ╚═══════════════════════════════════════════════════════════════╝
```

---

## 6. OPTION E — INFRASTRUCTURE-AIDED NAVIGATION (AprilTags / QR Codes)

### 6.1 Concept

Physically place visual markers (AprilTags, ArUco, or QR codes) on every tree trunk. The drone camera detects these markers and instantly knows:
- **Identity:** Which tree is this? (Tag #42 = Tree at Row 3, Column 7)
- **Pose:** Exact 6-DOF position and orientation relative to the marker
- **Range:** Precise distance from the marker (from marker size + perspective)

### 6.2 How It Solves the "Blind Search" Problem

```
    WITHOUT MARKERS (current):
    ══════════════════════════════════════════════
    Drone: *rotates 360°* "I see... green. And brown. And more green."
           "Is that a trunk or a shadow?"
           "How far is it?"
           "Have I been here before?"
    
    WITH APRILTAGS:
    ══════════════════════════════════════════════
    Drone: *rotates 360°* "I see Tag #42 at 3.2m, bearing 045°."
           "I already sprayed #42. I haven't sprayed #43."
           "Tag #43 should be ~5m at bearing 120° (from pre-loaded map)."
           "Navigating to #43."
    
    SEARCH ALGORITHM SIMPLIFICATION:
    ─────────────────────────────────
    BEFORE: 3-level search hierarchy (SCAN → TRUNK_HOP → EXPLORE)
            Duration: 12s – 120s per tree
            Reliability: ~80-85%
    
    AFTER:  Rotate → Find ANY tag → Look up pre-loaded tree list
            → Navigate to nearest unsprayed tree
            Duration: 3-5 seconds per tree
            Reliability: ~95-98%
```

### 6.3 AprilTag Detection Performance

```
    APRILTAG DETECTION ON JETSON NANO:
    ══════════════════════════════════════════════

    Library: apriltag (C library, Python bindings)
    OR: OpenCV ArUco module (built-in, no extra install)

    Detection speed: ~5-15ms per frame on Jetson Nano CPU
    (depends on number of tags visible, image resolution)
    
    No GPU needed. Runs entirely on CPU.

    Pose estimation: Built-in when you know the tag size.
    Gives: x, y, z translation + rotation quaternion.
    Accuracy: ±1cm at 2m distance (for a 15cm tag). EXCELLENT.

    Min tag size visible at distance:
    ┌──────────┬───────────────┬─────────────────────┐
    │ Tag Size │ Max Readable  │ Pixels at Max Range  │
    │          │ Distance      │ (640×480 camera)     │
    ├──────────┼───────────────┼─────────────────────┤
    │ 10cm     │ ~3m           │ ~21 px (minimum)     │
    │ 15cm     │ ~4.5m         │ ~21 px               │
    │ 20cm     │ ~6m           │ ~21 px               │
    │ 30cm     │ ~9m           │ ~21 px               │
    └──────────┴───────────────┴─────────────────────┘
    (Using AprilTag 36h11 family, needs ~6×6 readable pixels)

    RECOMMENDATION: 20cm × 20cm tags on tree trunks at 1.5m height.
    Readable up to ~6m with 640×480 camera. Good enough for tree spacing.
```

### 6.4 Implementation Cost — The Hidden Killer

```
    THE COST ISN'T THE SOFTWARE. IT'S THE INSTALLATION.
    ══════════════════════════════════════════════════════════

    Software cost:
      AprilTag detection library: FREE
      ROS apriltag_ros package: FREE
      Integration into state machine: ~2 days work
      TOTAL SOFTWARE: ~2 days, $0

    Physical infrastructure cost:
    ┌───────────────────────────────────────────────────────┐
    │ Item              │ Per Tree  │ 100 Trees │ 500 Trees │
    ├───────────────────┼───────────┼───────────┼───────────┤
    │ Print tag (PVC/Al)│ ~$1-2     │ $100-200  │ $500-1000 │
    │ Mounting hardware  │ ~$0.50    │ $50       │ $250      │
    │ Install labor*     │ ~$0.50    │ $50       │ $250      │
    │ TOTAL PER TREE    │ ~$2-3     │ $200-300  │ $750-1500 │
    └───────────────────┴───────────┴───────────┴───────────┘
    * Manual labor: Walk to each tree, mount tag at 1.5m height,
      record tag ID → tree position mapping.
    * Tags degrade: Sun/rain/insects. Need replacement annually?
      PVC or aluminum tags last longer but cost more.

    ALSO REQUIRED: Pre-mapping
    ─────────────────────────────
    You need a database: {tag_id: 42, position: (x:12.5, y:8.3), sprayed: false}
    This requires surveying the plantation and recording each tag's position.
    For 100 trees: ~1-2 hours manual work with a measuring tape.
    For 500 trees: ~1 day with a GPS (or RTK-GPS for accuracy).

    OPERATIONAL BURDEN:
    ─────────────────────
    New trees → new tags.
    Fallen tags → blind spots.
    Tag obscured by growth → detection failure.
    Multiple plantations → different tag sets per site.
```

### 6.5 Verdict on AprilTags

```
    ╔═══════════════════════════════════════════════════════════════╗
    ║                  APRILTAG VERDICT                             ║
    ║                                                               ║
    ║  Search reliability: ★★★★★ (near-perfect when tags visible)  ║
    ║  Computational cost: ★★★★★ (5-15ms CPU, no GPU)             ║
    ║  Implementation complexity: ★★☆☆☆ (physical installation!)  ║
    ║  Scalability: ★★☆☆☆ (works for research plot, not plantation)║
    ║  Maintenance: ★★☆☆☆ (tags degrade, need replacement)        ║
    ║                                                               ║
    ║  PERFECT FOR: Research demo (10-20 trees, controlled area)   ║
    ║  TERRIBLE FOR: Production deployment at plantation scale     ║
    ║                                                               ║
    ║  HYBRID APPROACH (recommended if tags are used):             ║
    ║  Use AprilTags on 10-20 demo trees for the stakeholder       ║
    ║  presentation. Show 99% reliability. Then explain that       ║
    ║  production uses behavior-based search (cheaper to scale)    ║
    ║  with optional tags at "anchor points" every 10th tree for   ║
    ║  drift correction. Best of both worlds.                      ║
    ╚═══════════════════════════════════════════════════════════════╝
```

---

## 7. OPTION F — LIGHTWEIGHT SLAM (Cartographer 2D / Intel T265 / ORB-SLAM3 Lite)

### 7.1 The SLAM Landscape on Jetson Nano

```
    SLAM ALGORITHMS EVALUATED FOR JETSON NANO 4GB:
    ══════════════════════════════════════════════════════

    ┌──────────────────────┬──────────┬────────┬──────────┬───────────┐
    │ Algorithm            │ FPS on   │ RAM    │ Sensor   │ Accuracy  │
    │                      │ Nano     │ Usage  │ Needed   │           │
    ├──────────────────────┼──────────┼────────┼──────────┼───────────┤
    │ ORB-SLAM3 (mono)    │ 3-8 FPS  │ 1-3 GB │ Mono cam │ Scale     │
    │                      │ ❌       │ ❌     │ ✅       │ ambiguity │
    ├──────────────────────┼──────────┼────────┼──────────┼───────────┤
    │ ORB-SLAM3 (stereo)  │ 2-5 FPS  │ 1.5-3GB│ Stereo   │ Good      │
    │                      │ ❌       │ ❌     │ OAK-D    │ when      │
    │                      │          │        │          │ tracking  │
    ├──────────────────────┼──────────┼────────┼──────────┼───────────┤
    │ RTAB-Map (RGB-D)    │ 1-5 FPS  │ 2-4 GB │ Depth cam│ Excellent │
    │                      │ ❌       │ ❌     │          │ when      │
    │                      │          │        │          │ not OOM   │
    ├──────────────────────┼──────────┼────────┼──────────┼───────────┤
    │ Google Cartographer  │ 8-15 FPS │ 0.5-1GB│ 2D LiDAR │ 2D only  │
    │ (2D)                 │ ⚠️       │ ✅     │ RPLidar  │ Good 2D   │
    ├──────────────────────┼──────────┼────────┼──────────┼───────────┤
    │ Intel T265 (VIO)    │ 200 Hz   │ ~0 GB  │ T265 cam │ Excellent │
    │ (was onboard VPU)   │ ✅✅     │ ✅✅   │ DISCONTINUED│         │
    ├──────────────────────┼──────────┼────────┼──────────┼───────────┤
    │ Kimera-VIO          │ 5-10 FPS │ 0.5-1GB│ Stereo+  │ Good      │
    │ (lightweight VIO)   │ ⚠️       │ ✅     │ IMU      │           │
    ├──────────────────────┼──────────┼────────┼──────────┼───────────┤
    │ VINS-Fusion         │ 5-12 FPS │ 0.5-1GB│ Stereo/  │ Good      │
    │                      │ ⚠️       │ ✅     │ Mono+IMU │           │
    ├──────────────────────┼──────────┼────────┼──────────┼───────────┤
    │ OAK-D onboard VIO   │ 30 FPS   │ ~0 GB  │ OAK-D    │ OK (drift │
    │ (depthai feature     │ ✅✅     │ ✅✅   │ (built-in│ over time)│
    │  tracker + IMU)      │ (VPU)   │ (VPU)  │  VPU)    │           │
    └──────────────────────┴──────────┴────────┴──────────┴───────────┘

    COLOR CODE:
    ✅✅ = Definitely works   ✅ = Feasible   ⚠️ = Marginal   ❌ = Won't work
```

### 7.2 The Intel T265 — The One That Got Away

```
    INTEL REALSENSE T265 TRACKING CAMERA:
    ══════════════════════════════════════
    
    What it was: A self-contained VIO (Visual-Inertial Odometry) camera.
    Two fisheye cameras + IMU + Intel Movidius VPU onboard.
    Ran VIO at 200Hz entirely onboard. Zero compute load on host.
    USB interface. Output: 6-DOF pose (position + orientation).
    
    Weight: 55g. Power: 1.5W. Price was: ~$200.
    
    IT WAS PERFECT FOR THIS PROJECT.
    
    Status: DISCONTINUED (2021). No longer manufactured.
    Available used/NOS: ~$300-500 on eBay (unreliable supply).
    Software: librealsense2 support is maintenance-only.
    
    VERDICT: ❌ DO NOT BUILD A SYSTEM AROUND DISCONTINUED HARDWARE.
    If you find one cheap, it's a nice bonus sensor, but don't make
    it a critical dependency.
    
    SPIRITUAL SUCCESSOR: OAK-D + onboard feature tracking (see below).
```

### 7.3 Google Cartographer 2D — The Only SLAM That Might Work

```
    Google Cartographer 2D + RPLidar A1:
    ═══════════════════════════════════════
    
    This is the ONE SLAM option that's computationally feasible on Nano.
    
    How it works:
    - Takes 2D LiDAR scans (360° horizontal plane)
    - Builds a 2D occupancy grid map in real-time
    - Localizes the robot within that map (loop closure)
    - Output: 2D pose (x, y, theta) in the map
    
    On Jetson Nano:
    - CPU: ~20-30% of one core at 5.5 Hz LiDAR input
    - RAM: ~300-500 MB for a 50×50m map
    - Latency: 50-100ms for pose updates
    - ✅ It fits. Barely.
    
    BUT — all the problems from Option D apply:
    - 2D LiDAR on a 3D drone → limited obstacle coverage
    - 170g weight penalty
    - Vibration coupling
    - 2D map of a 3D environment → misses overhead/underfoot obstacles
    
    AND ADDITIONAL PROBLEMS:
    - Repetitive tree trunk cross-sections → aliasing
      (Cartographer thinks it's looped back because all trunks look the same)
    - Map grows over time → RAM usage climbs
    - Loop closure under canopy is unreliable
      (visual features are repetitive)
    
    VERDICT: ⚠️ Technically possible, but fragile and heavy.
    Better alternatives exist for this specific use case.
```

### 7.4 OAK-D Onboard Feature Tracking — The Pragmatic "SLAM-Lite"

```
    THIS IS THE HIDDEN GEM.
    ═══════════════════════════════════════

    The OAK-D cameras (Lite and Pro) have a built-in Feature Tracker 
    on the Myriad X VPU. Combined with the onboard IMU, you get a 
    lightweight Visual-Inertial Odometry (VIO) running ENTIRELY 
    on the camera's VPU.

    What you get:
    - Feature tracking (Harris corners) at 30fps on VPU
    - IMU data (BMI270) at 100-400Hz on VPU
    - Fused VIO output: 6-DOF pose estimate
    - ALL computed on the OAK-D, NOT on Jetson Nano
    - Jetson Nano load: ~0% (just reads the results)

    What you DON'T get:
    - Loop closure (it's odometry, not SLAM)
    - Map building
    - Drift correction over long distances

    In other words: it's a MUCH BETTER version of the Matek 3901-L0X 
    optical flow, but:
    - 6-DOF instead of 2-DOF (optical flow gives only vx, vy)
    - Works at all altitudes (optical flow needs ground texture)
    - Runs on VPU (optical flow runs on Pixhawk EKF)

    COMPARISON:
    ┌─────────────────────┬──────────────┬──────────────────┐
    │ Feature             │ Matek 3901   │ OAK-D VIO        │
    ├─────────────────────┼──────────────┼──────────────────┤
    │ DOF                 │ 2 (vx, vy)   │ 6 (x,y,z,r,p,y) │
    │ Works without ground│ ❌           │ ✅               │
    │ Altitude handling   │ Needs rangef.│ Estimated        │
    │ Drift (5m travel)   │ ~10-25cm     │ ~5-15cm          │
    │ Drift (50m travel)  │ ~50cm-2.5m   │ ~25cm-1.5m       │
    │ Compute on Nano     │ 0% (Pixhawk) │ 0% (VPU)         │
    │ Cost                │ $25          │ Included in OAK-D │
    └─────────────────────┴──────────────┴──────────────────┘

    NOTE: You still keep the Matek 3901-L0X for Pixhawk's EKF
    (ArduPilot needs it for LOITER mode). The OAK-D VIO is an
    ADDITIONAL odometry source for the Jetson's navigation logic.
    Two independent position estimates → you can cross-check for
    consistency → catch drift earlier.
```

---

## 8. OPTION G — MULTI-CAMERA SETUP

### 8.1 The Proposal: Forward Camera + Downward Camera

```
    Camera 1 (Forward): OAK-D Lite or Jete webcam
    → Flower detection + obstacle avoidance + trunk detection

    Camera 2 (Downward): Separate USB camera (e.g., Logitech C270, $20)
    → Ground texture tracking (visual odometry)
    → Landing pad detection during descent
    → Alternative to Matek 3901-L0X optical flow
```

### 8.2 USB Bandwidth Analysis

```
    JETSON NANO USB TOPOLOGY:
    ═══════════════════════════════════════════════════════

    Jetson Nano 4GB has:
    - 1× USB 3.0 port (Type-A)  → up to 5 Gbps (~400 MB/s practical)
    - 3× USB 2.0 ports          → up to 480 Mbps (~35 MB/s practical) each
    - Internal USB hub shares bandwidth

    CAMERA BANDWIDTH REQUIREMENTS:
    ┌──────────────────────┬─────────────────┬──────────────────┐
    │ Camera               │ Resolution/FPS  │ Bandwidth        │
    ├──────────────────────┼─────────────────┼──────────────────┤
    │ OAK-D Lite (USB 3.0)│ RGB+Depth 640×480│ ~45 MB/s        │
    │                      │ @ 30fps         │ (needs USB 3.0)  │
    ├──────────────────────┼─────────────────┼──────────────────┤
    │ Logitech C270 (USB2) │ 640×480 MJPEG  │ ~3-5 MB/s       │
    │                      │ @ 30fps         │ (fine on USB 2.0)│
    ├──────────────────────┼─────────────────┼──────────────────┤
    │ ESP32 Serial (USB 2) │ 115200 baud     │ ~0.01 MB/s      │
    │                      │                 │ (negligible)     │
    └──────────────────────┴─────────────────┴──────────────────┘

    ALLOCATION:
    USB 3.0 port → OAK-D Lite (45 MB/s of 400 MB/s capacity)
    USB 2.0 port 1 → Logitech C270 (5 MB/s of 35 MB/s capacity)
    USB 2.0 port 2 → ESP32 serial (negligible)
    USB 2.0 port 3 → Free (keyboard for debug, or spare)

    TOTAL BANDWIDTH USED: ~50 MB/s of ~500 MB/s available.
    ✅ YES, dual cameras are bandwidth-feasible.
```

### 8.3 Compute Budget with Dual Cameras

```
    ╔═══════════════════════════════════════════════════════════════╗
    ║          DUAL CAMERA COMPUTE BUDGET                          ║
    ╠═══════════════════════════════════════════╦═══════════════════╣
    ║ OAK-D Lite (forward — VPU processes):    ║                   ║
    ║   YOLO detection          → on VPU       ║ 0% Nano GPU      ║
    ║   Stereo depth            → on VPU       ║ 0% Nano GPU      ║
    ║   Feature tracking        → on VPU       ║ 0% Nano GPU      ║
    ║   Results via USB         → ~3ms CPU     ║ ~5% Nano CPU     ║
    ╠═══════════════════════════════════════════╬═══════════════════╣
    ║ Downward camera (Nano processes):        ║                   ║
    ║   OpenCV optical flow (Farneback)        ║ ~15ms CPU        ║
    ║   OR: Landing pad detection (HSV)        ║ ~5ms CPU         ║
    ║   Total for downward cam:                ║ ~10-15% Nano CPU ║
    ╠═══════════════════════════════════════════╬═══════════════════╣
    ║ TOTAL NANO LOAD:                         ║                   ║
    ║   GPU: 0-5%                              ║                   ║
    ║   CPU: 20-30%                            ║                   ║
    ║   RAM: ~1.8 GB                           ║                   ║
    ║                                           ║                   ║
    ║   Headroom: MASSIVE. System is chill.    ║                   ║
    ╚═══════════════════════════════════════════╩═══════════════════╝
```

### 8.4 Verdict on Multi-Camera

```
    ╔═══════════════════════════════════════════════════════════════╗
    ║                  MULTI-CAMERA VERDICT                        ║
    ║                                                               ║
    ║  Bandwidth feasible: ✅ YES                                  ║
    ║  Compute feasible: ✅ YES (especially with OAK-D offloading)║
    ║  Value of downward camera: ⚠️ MARGINAL                      ║
    ║                                                               ║
    ║  REASONING:                                                   ║
    ║  If you already have the Matek 3901-L0X for downward optical ║
    ║  flow (feeding Pixhawk EKF for position hold), the downward  ║
    ║  camera is REDUNDANT for that purpose. The Matek does it     ║
    ║  better (dedicated sensor, hardware-optimized, native        ║
    ║  ArduPilot integration).                                     ║
    ║                                                               ║
    ║  The downward camera adds value ONLY for:                    ║
    ║  1. Visual landing pad detection (nice but not critical)     ║
    ║  2. Redundant position estimate (cross-check Matek)          ║
    ║  3. Ground mapping / terrain classification (future)         ║
    ║                                                               ║
    ║  RECOMMENDATION: Skip the downward camera for now.           ║
    ║  The Matek 3901 + OAK-D forward is a better investment.     ║
    ║  Add downward camera in a future iteration if needed.        ║
    ╚═══════════════════════════════════════════════════════════════╝
```

---

## 9. OPTION H — BUDGET HYBRID: OAK-D LITE + FORWARD TFMINI LIDAR

### 9.1 The "Belt and Suspenders" Approach

Instead of choosing ONE sensor, combine two complementary ones:

```
    OAK-D Lite ($149):
    → Forward-facing: YOLO + depth + feature tracking
    → All heavy compute on VPU (0% Nano GPU)
    → Rich data but FAILS at very close range (<20cm)
      and in zero-texture areas

    TFMini-S LiDAR ($15-25):
    → Forward-facing: single-beam distance sensor
    → Range: 0.1m – 12m, update rate: 100Hz
    → Works in ANY lighting, ANY texture
    → Absolute ground truth distance (no stereo matching needed)
    → Weight: 5g
    → Interface: UART (connect to Pixhawk spare UART or Jetson GPIO)

    COMBINED:
    ┌─────────────────────────────────────────────────┐
    │                                                 │
    │    ┌──────────────┐   ┌──────────────┐         │
    │    │  OAK-D Lite  │   │  TFMini-S   │         │
    │    │  (wide FOV)  │   │  (pencil beam)│        │
    │    │              │   │              │         │
    │    │  Depth MAP   │   │  Depth POINT │         │
    │    │  (80° cone)  │   │  (1° beam)   │         │
    │    │  @30fps      │   │  @100Hz      │         │
    │    │              │   │              │         │
    │    │  Detects:    │   │  Detects:    │         │
    │    │  WHAT is     │   │  HOW FAR the │         │
    │    │  in front    │   │  closest     │         │
    │    │  (rich data) │   │  thing is    │         │
    │    │              │   │  (fast,      │         │
    │    │  Slow to     │   │  absolute)   │         │
    │    │  fail (~30ms)│   │              │         │
    │    └──────────────┘   └──────────────┘         │
    │                                                 │
    │    OAK-D says: "Trunk at 2.3m, flower at 3.1m" │
    │    TFMini says: "Something at 2.35m ahead"      │
    │    Agreement: ✅ High confidence                │
    │                                                 │
    │    OAK-D says: "No depth data" (low texture)    │
    │    TFMini says: "Something at 0.8m ahead!"      │
    │    Disagreement: ⚠️ Trust TFMini, STOP!         │
    │                                                 │
    │    TOTAL COST: $149 + $20 = $169                │
    │    TOTAL WEIGHT: 61g + 5g = 66g                 │
    │    TOTAL POWER: ~4W + 0.1W = ~4.1W              │
    └─────────────────────────────────────────────────┘
```

---

## 10. COMPARATIVE TECHNOLOGY MATRIX

```
╔═════════════════════════╦══════════╦═════════════╦═════════════╦═══════════╦════════════╦══════════╗
║                         ║ROBUSTNESS║ NANO GPU    ║ NANO CPU    ║ IMPLEMENT ║  COST      ║ WEIGHT   ║
║ OPTION                  ║ GAIN     ║ LOAD        ║ LOAD        ║ TIME      ║ (add'l)    ║ PENALTY  ║
╠═════════════════════════╬══════════╬═════════════╬═════════════╬═══════════╬════════════╬══════════╣
║ A. Intel RealSense D435i║ HIGH     ║ 50-60%      ║ 35-45%      ║ 1 week    ║ $250-300   ║ 72g      ║
║    (depth only, YOLO on ║          ║ (YOLO still ║             ║           ║            ║          ║
║     Nano GPU)           ║          ║  on Nano)   ║             ║           ║            ║          ║
╠═════════════════════════╬══════════╬═════════════╬═════════════╬═══════════╬════════════╬══════════╣
║ B. Luxonis OAK-D Lite   ║ HIGH     ║ 0-5% ✅✅   ║ 10-15%      ║ 1 week    ║ $149       ║ 61g      ║
║    (depth + YOLO on VPU)║          ║             ║             ║ (+2d model║            ║          ║
║                         ║          ║             ║             ║  convert) ║            ║          ║
╠═════════════════════════╬══════════╬═════════════╬═════════════╬═══════════╬════════════╬══════════╣
║ C. Luxonis OAK-D Pro    ║ HIGH+    ║ 0-5% ✅✅   ║ 10-15%      ║ 1 week    ║ $249       ║ 91g      ║
║    (depth + IR proj +   ║          ║             ║             ║ (+2d model║            ║          ║
║     YOLO on VPU)        ║          ║             ║             ║  convert) ║            ║          ║
╠═════════════════════════╬══════════╬═════════════╬═════════════╬═══════════╬════════════╬══════════╣
║ D. DWA/VFH+ algo only  ║ LOW-MED  ║ 0%          ║ +10-15%     ║ 3-5 days  ║ $0         ║ 0g       ║
║    (needs sensor data!) ║ (limited ║             ║             ║           ║ (algo only)║          ║
║                         ║ by FOV)  ║             ║             ║           ║            ║          ║
╠═════════════════════════╬══════════╬═════════════╬═════════════╬═══════════╬════════════╬══════════╣
║ E. RPLidar A1 (360° 2D)║ MEDIUM   ║ 0%          ║ +10-20%     ║ 1 week    ║ $99-120    ║ 170g ⚠️  ║
║                         ║ (2D only)║             ║             ║           ║            ║          ║
╠═════════════════════════╬══════════╬═════════════╬═════════════╬═══════════╬════════════╬══════════╣
║ F. AprilTags on trunks  ║ V. HIGH  ║ 0%          ║ +5-10%      ║ 2 days    ║ $1-3/tree  ║ 0g       ║
║    (infra modification) ║ (when    ║             ║             ║ code +    ║ + survey   ║          ║
║                         ║ visible) ║             ║             ║ 1-3 days  ║ labor      ║          ║
║                         ║          ║             ║             ║ install   ║            ║          ║
╠═════════════════════════╬══════════╬═════════════╬═════════════╬═══════════╬════════════╬══════════╣
║ G. SLAM (Cartographer   ║ MEDIUM   ║ 0-10%       ║ +20-40%     ║ 2-3 weeks ║ $0-120     ║ 0-170g   ║
║    2D / VIO)            ║ (fragile)║             ║ ⚠️          ║ (complex) ║ (if LiDAR) ║          ║
╠═════════════════════════╬══════════╬═════════════╬═════════════╬═══════════╬════════════╬══════════╣
║ H. OAK-D + Downward cam║ HIGH+    ║ 0-5%        ║ 20-30%      ║ 1.5 weeks ║ $149+$20   ║ 61g+30g  ║
║    (dual camera)        ║          ║             ║             ║           ║ = $169     ║ = 91g    ║
╠═════════════════════════╬══════════╬═════════════╬═════════════╬═══════════╬════════════╬══════════╣
║ I. OAK-D Lite + TFMini ║ V. HIGH  ║ 0-5% ✅✅   ║ 10-15%      ║ 1 week    ║ $149+$20   ║ 66g      ║
║    (depth cam + lidar   ║          ║             ║             ║           ║ = $169     ║          ║
║     point backup)       ║          ║             ║             ║           ║            ║          ║
╠═════════════════════════╬══════════╬═════════════╬═════════════╬═══════════╬════════════╬══════════╣
║ BASELINE (current):     ║ BASELINE ║ 50-60%      ║ 30-40%      ║ DONE      ║ ~$40       ║ 0g       ║
║ Jete webcam + Matek 3901║ ★★★☆☆   ║             ║             ║           ║            ║ (existing)║
╚═════════════════════════╩══════════╩═════════════╩═════════════╩═══════════╩════════════╩══════════╝
```

### Visual Summary — The Sweet Spots

```
    ROBUSTNESS vs. COST vs. COMPUTE LOAD:
    ══════════════════════════════════════════════

    Robustness ▲
               │
        V.HIGH ┤                 ⬟ AprilTags*     ⬟ OAK-D Lite + TFMini
               │                 (needs tags)      ★ BEST BALANCE
               │
          HIGH ┤    ⬟ OAK-D Lite              ⬟ D435i
               │    $149 / 0% GPU             $300 / 50% GPU
               │
           MED ┤              ⬟ RPLidar 2D         ⬟ SLAM
               │              (2D only, heavy)      (fragile, complex)
               │
           LOW ┤    ⬟ DWA/VFH+ only
               │    (no data to drive it)
               │
      BASELINE ┤    ⬟ Current (webcam + Matek)
               │
               └──────┬──────┬──────┬──────┬──────── Cost ($)
                     $0    $50   $100  $150  $200  $300

    ★ = Recommended "Mid-Tier" upgrade
    * = AprilTags are off the chart on robustness BUT
        require physical installation labor (hidden cost)
```

---

## 11. THE RECOMMENDATION — MID-TIER UPGRADE

### 11.1 Primary Recommendation: OAK-D Lite ($149)

```
    ╔═══════════════════════════════════════════════════════════════════╗
    ║                                                                   ║
    ║   ★ RECOMMENDED MID-TIER UPGRADE: LUXONIS OAK-D LITE            ║
    ║                                                                   ║
    ║   Cost: $149 (IDR ~2.3 juta — well within budget)               ║
    ║   Weight: 61g                                                    ║
    ║   Power: 2.5-4.5W                                                ║
    ║                                                                   ║
    ║   WHY THIS ONE:                                                  ║
    ║                                                                   ║
    ║   1. OFFLOADS YOLO to onboard VPU → Jetson Nano GPU = 0%       ║
    ║      This is the single biggest quality-of-life improvement.    ║
    ║      No thermal throttling. No FPS drops. No GPU contention.    ║
    ║                                                                   ║
    ║   2. DEPTH for obstacle avoidance → replaces "dark_ratio" hack  ║
    ║      Real distance to obstacles, not guesswork.                  ║
    ║      Clear direction selection (left vs right) based on depth.  ║
    ║                                                                   ║
    ║   3. TRUE DISTANCE to flowers → better visual servoing         ║
    ║      No more "bbox area → distance" estimation (±30% error).    ║
    ║      Direct depth readout at detection pixel (±2% at <4m).     ║
    ║                                                                   ║
    ║   4. ONBOARD FEATURE TRACKING → "free" VIO                     ║
    ║      Cross-check optical flow odometry with VPU-computed VIO.   ║
    ║      Two independent position estimates = catch drift early.    ║
    ║                                                                   ║
    ║   5. REPLACES the Jete webcam → fewer USB devices, simpler     ║
    ║                                                                   ║
    ║   6. $149 leaves $150 budget headroom for:                      ║
    ║      - TFMini-S forward LiDAR backup ($20)                     ║
    ║      - 3D-printed vibration mount ($10)                         ║
    ║      - Good USB-C cable with strain relief ($5)                 ║
    ║      - AprilTags for 10-20 demo trees ($30)                    ║
    ║      - Spare budget for contingencies ($85)                     ║
    ║                                                                   ║
    ╚═══════════════════════════════════════════════════════════════════╝
```

### 11.2 Upgrade Path — How the Architecture Evolves

```
    ARCHITECTURE EVOLUTION:
    ══════════════════════════════════════════════════

    PHASE 1 (NOW — Survival Mode):
    Jete webcam → HSV on CPU → Pilot flies → ESP32 spray
    Cost: $15 (webcam)
    Robustness: ★★☆☆☆

    PHASE 2 (Week 2 — Single Tree Auto):
    Jete webcam → YOLO on GPU (50%) → Matek opt.flow → Pixhawk LOITER
    Cost: $15 + $25 = $40
    Robustness: ★★★☆☆

    PHASE 3 (Week 3-4 — OAK-D Lite Upgrade): ★ NEW RECOMMENDED
    ┌────────────────────────────────────────────────────┐
    │                                                    │
    │   OAK-D Lite (replaces Jete webcam)                │
    │     VPU: YOLO-nano + Stereo Depth + Feature Track  │
    │     ↓ (USB, results only)                          │
    │   Jetson Nano                                      │
    │     CPU: State machine + PID + MAVLink (15%)       │
    │     GPU: FREE (0%) ← thermal problem SOLVED       │
    │     ↓ (MAVLink)                                    │
    │   Pixhawk + Matek 3901 (unchanged)                 │
    │     Position hold via optical flow                  │
    │     ↓ (serial)                                     │
    │   ESP32 → Sprayer (unchanged)                      │
    │                                                    │
    │   Optional add-on: TFMini-S ($20)                  │
    │     → Forward LiDAR → Pixhawk spare UART           │
    │     → Backup obstacle distance                     │
    │                                                    │
    │   Optional add-on: AprilTags ($30 for 20 tags)     │
    │     → On demo trees only                           │
    │     → Detected on OAK-D VPU (custom model)         │
    │     → 99% search reliability for stakeholder demo   │
    │                                                    │
    └────────────────────────────────────────────────────┘
    Cost: $149 + $25 (Matek) + optional $50 = $174-224
    Robustness: ★★★★☆ (★★★★★ with AprilTags on demo site)

    PHASE 4 (Future — Production):
    Add whatever the field data tells you is missing.
    Maybe: forward LiDAR, better frame, larger battery.
    The OAK-D Lite architecture has MASSIVE compute headroom
    to absorb future features without hardware changes.
```

### 11.3 What Changes in the Code

```
    CODE IMPACT ASSESSMENT:
    ══════════════════════════════════════════════════════

    WHAT STAYS THE SAME:
    ✅ ESP32 sprayer_controller.ino — No change
    ✅ spray_logic_node.py state machine — Same states
    ✅ ArduPilot params — Same optical flow + rangefinder
    ✅ MAVLink interface — Same velocity commands
    ✅ PID controllers — Same error → velocity mapping
    ✅ Mission memory — Same sprayed_trees list

    WHAT CHANGES:
    🔄 detector_node.py:
       BEFORE: Subscribe to /usb_cam/image_raw, run HSV/YOLO on Jetson
       AFTER:  Subscribe to OAK-D depthai pipeline, receive detection
               results + depth frame from VPU. Jetson does NO detection.
       Effort: Rewrite ~60% of detector_node.py (~1-2 days)

    🔄 Obstacle avoidance:
       BEFORE: dark_ratio heuristic on RGB frame
       AFTER:  Read depth frame, compute min-distance in 3 sectors
       Effort: Replace ~30 lines of code (~2 hours)

    🔄 Visual servoing distance:
       BEFORE: error_z = TARGET_AREA - bbox_area (proxy)
       AFTER:  error_z = TARGET_DISTANCE - depth_at_bbox_center (real)
       Effort: Change ~5 lines of code (~30 minutes)

    🔄 YOLO model conversion:
       BEFORE: YOLOv8-nano → ONNX → TensorRT FP16 (for Nano GPU)
       AFTER:  YOLOv8-nano → ONNX → OpenVINO → .blob (for OAK VPU)
       Effort: ~2-4 hours (Luxonis tools, well-documented)

    NEW CODE:
    ➕ depthai_pipeline.py — OAK-D initialization and pipeline config
       Effort: ~1 day (follow Luxonis examples)

    TOTAL CODE CHANGE EFFORT: 3-5 days
    RISK: LOW (same architecture, different sensor backend)
```

---

## 12. SHOPPING LIST & BUDGET BREAKDOWN

```
    ╔═══════════════════════════════════════════════════════════════════╗
    ║                    RECOMMENDED SHOPPING LIST                     ║
    ╠═════════════════════════════════════╦═════════════╦══════════════╣
    ║ Item                                ║ Price (USD) ║ Priority     ║
    ╠═════════════════════════════════════╬═════════════╬══════════════╣
    ║ Luxonis OAK-D Lite                 ║ $149        ║ ★ ESSENTIAL  ║
    ║ (replaces Jete webcam)             ║             ║              ║
    ╠═════════════════════════════════════╬═════════════╬══════════════╣
    ║ Matek 3901-L0X (if not bought yet) ║ $25         ║ ★ ESSENTIAL  ║
    ║ (optical flow + rangefinder)       ║             ║              ║
    ╠═════════════════════════════════════╬═════════════╬══════════════╣
    ║ TFMini-S (forward LiDAR backup)   ║ $20         ║ ★★ RECOMMENDED║
    ║                                     ║             ║              ║
    ╠═════════════════════════════════════╬═════════════╬══════════════╣
    ║ USB-C cable (high quality, short)  ║ $5          ║ ★★ RECOMMENDED║
    ║ + strain relief hardware           ║             ║              ║
    ╠═════════════════════════════════════╬═════════════╬══════════════╣
    ║ 3D-printed vibration mount         ║ $10         ║ ★★ RECOMMENDED║
    ║ (or laser-cut aluminum bracket)    ║             ║              ║
    ╠═════════════════════════════════════╬═════════════╬══════════════╣
    ║ AprilTags printed on PVC (20 pcs)  ║ $30         ║ ★★★ NICE     ║
    ║ (for demo site only)               ║             ║ TO HAVE      ║
    ╠═════════════════════════════════════╬═════════════╬══════════════╣
    ║ Spare USB hub (powered)            ║ $10         ║ ★★★ NICE     ║
    ║                                     ║             ║ TO HAVE      ║
    ╠═════════════════════════════════════╬═════════════╬══════════════╣
    ║                                     ║             ║              ║
    ║ ESSENTIAL TOTAL:                    ║ $174        ║ IDR ~2.7 juta║
    ║ RECOMMENDED TOTAL:                  ║ $209        ║ IDR ~3.2 juta║
    ║ FULL PACKAGE:                       ║ $249        ║ IDR ~3.8 juta║
    ║                                     ║             ║              ║
    ║ BUDGET CEILING:                     ║ $300        ║ IDR ~4.6 juta║
    ║ REMAINING CONTINGENCY:              ║ $51-126     ║ ✅ Healthy   ║
    ╚═════════════════════════════════════╩═════════════╩══════════════╝
```

---

## 13. FINAL VERDICT — THE ONE-PARAGRAPH SUMMARY

Buy the **OAK-D Lite** ($149). It replaces your Jete webcam and gives you three things the webcam can't: **real depth** (kills the obstacle avoidance guesswork), **onboard AI inference** (drops Jetson Nano GPU from 50-60% to 0%, eliminating thermal throttling forever), and **onboard feature tracking** (free VIO cross-check against Matek optical flow). Keep the Matek 3901-L0X for Pixhawk position hold. Add a $20 TFMini-S forward LiDAR as a belt-and-suspenders backup for obstacle distance. The total is ~$209, well under your $300 ceiling, leaves $90 for contingencies, and transforms the Jetson Nano from a "barely keeping up" system to a "massively over-provisioned" one. Everything in `spray_logic_node.py`, the ESP32 firmware, and the ArduPilot parameters stays the same. You rewrite `detector_node.py` to use the depthai SDK instead of OpenCV USB camera capture. Three days of code changes for a step-function improvement in robustness. This is the highest-ROI upgrade available.

---

*Document Version: 1.0 | Date: 2026-02-09*
*Builds on: NAVIGATION_ARCHITECTURE.md, ARCHITECTURE_REVIEW.md, ACTION_PLAN_SURVIVAL.md*
*"Buy the sensor that does the thinking so your Jetson doesn't have to."*

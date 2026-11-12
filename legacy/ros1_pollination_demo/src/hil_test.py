#!/usr/bin/env python3
"""
HIL Test Script — Visual Servo Pipeline for Autonomous Pollination Drone
========================================================================
Purpose:  Hardware-In-the-Loop validation of Camera → YOLO → PID → MAVLink pipeline.
Hardware: Jetson Nano 4GB + Jete FHD 1080p USB Cam + Pixhawk (ArduPilot)
Target:   Yellow ball (proxy for oil palm flower)

Usage:
    Phase 1 (Detection Only):   python3 hil_test.py --phase 1
    Phase 2 (MAVLink Commands):  python3 hil_test.py --phase 2
    Phase 3 (Motor Response):    python3 hil_test.py --phase 3 --armed

Safety:
    - Phase 1-2: Props OFF. Safe to run on bench.
    - Phase 3:   Props ON. DRONE MUST BE SECURED TO TEST STAND. Wear safety glasses.

Author:   Architecture Review — Feb 2026
"""

import argparse
import time
import sys
import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Tuple

import cv2
import numpy as np

# ═══════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class CameraConfig:
    device: int = 0
    width: int = 640
    height: int = 480
    fps: int = 30
    # GStreamer pipeline for Jetson Nano (GPU-accelerated capture)
    # Set use_gstreamer=True when running on actual Jetson hardware
    use_gstreamer: bool = False
    gstreamer_pipeline: str = (
        "v4l2src device=/dev/video0 ! "
        "video/x-raw, width=640, height=480, framerate=30/1 ! "
        "videoconvert ! video/x-raw, format=BGRx ! "
        "videoconvert ! video/x-raw, format=BGR ! "
        "appsink drop=1"
    )


@dataclass
class DetectionConfig:
    # For HIL test, we use simple HSV color detection for the yellow ball.
    # In production, replace with YOLOv8-nano TensorRT inference.
    use_yolo: bool = False                  # Set True when YOLO TensorRT engine is ready
    yolo_engine_path: str = "models/yolov8n_flower.engine"
    confidence_threshold: float = 0.65

    # HSV range for yellow ball detection (fallback / HIL test)
    hsv_lower: Tuple[int, int, int] = (20, 100, 100)
    hsv_upper: Tuple[int, int, int] = (35, 255, 255)
    min_contour_area: int = 500             # Minimum bbox area in pixels² to be valid


@dataclass
class ServoConfig:
    """PID gains for visual servoing. Start conservative, tune during HIL Phase 2."""

    # Image center (target point)
    image_center_x: int = 320
    image_center_y: int = 240

    # Yaw PID — controls horizontal centering (error_x → yaw_rate)
    yaw_kp: float = 0.002
    yaw_ki: float = 0.0001
    yaw_kd: float = 0.0005
    max_yaw_rate: float = 0.5              # rad/s

    # Altitude PID — controls vertical centering (error_y → vz)
    alt_kp: float = 0.003
    alt_ki: float = 0.0001
    alt_kd: float = 0.0008
    max_vz: float = 0.3                    # m/s

    # Forward PID — controls approach distance (error_z → vx)
    fwd_kp: float = 0.00001
    fwd_ki: float = 0.000001
    fwd_kd: float = 0.000005
    max_vx: float = 0.3                    # m/s

    # Spray trigger thresholds
    spray_target_area: int = 15000         # bbox area (pixels²) at ideal spray distance
    spray_center_tolerance: int = 50       # pixels — max error to allow spray
    spray_duration_ms: int = 500           # ms — relay on time

    # State machine timeouts
    search_timeout_s: float = 30.0
    acquire_timeout_s: float = 10.0
    approach_timeout_s: float = 15.0
    detection_lost_timeout_s: float = 3.0
    retreat_duration_s: float = 2.0
    retreat_speed: float = 0.3             # m/s backward

    # Safety limits
    max_safe_bbox_area: int = 40000        # Too close! Retreat.
    min_rangefinder_m: float = 0.3         # Emergency climb if below this

    # HIL scaling factor (0.0 = log only, 0.3 = 30% power, 1.0 = full)
    command_scale: float = 0.0


# ═══════════════════════════════════════════════════════════════════════
# STATE MACHINE
# ═══════════════════════════════════════════════════════════════════════

class DroneState(Enum):
    IDLE = auto()
    SEARCH = auto()
    ACQUIRE = auto()
    APPROACH = auto()
    SPRAY = auto()
    RETREAT = auto()
    EMERGENCY = auto()


# ═══════════════════════════════════════════════════════════════════════
# SIMPLE PID CONTROLLER
# ═══════════════════════════════════════════════════════════════════════

class PIDController:
    """Minimal PID with anti-windup and derivative filter."""

    def __init__(self, kp: float, ki: float, kd: float,
                 output_min: float, output_max: float,
                 integral_limit: float = 100.0):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.output_min = output_min
        self.output_max = output_max
        self.integral_limit = integral_limit

        self._integral = 0.0
        self._prev_error = 0.0
        self._prev_time = None

    def reset(self):
        self._integral = 0.0
        self._prev_error = 0.0
        self._prev_time = None

    def compute(self, error: float) -> float:
        now = time.monotonic()
        if self._prev_time is None:
            dt = 0.033  # Assume ~30fps on first call
        else:
            dt = now - self._prev_time
            dt = max(dt, 0.001)  # Guard against zero dt
        self._prev_time = now

        # Proportional
        p = self.kp * error

        # Integral with anti-windup clamping
        self._integral += error * dt
        self._integral = max(-self.integral_limit, min(self.integral_limit, self._integral))
        i = self.ki * self._integral

        # Derivative (on error, with simple filter)
        derivative = (error - self._prev_error) / dt
        d = self.kd * derivative
        self._prev_error = error

        # Total output, clamped
        output = p + i + d
        output = max(self.output_min, min(self.output_max, output))
        return output


# ═══════════════════════════════════════════════════════════════════════
# DETECTION (HSV Color — for HIL. Replace with YOLO for production.)
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class Detection:
    cx: int                 # Bounding box center x
    cy: int                 # Bounding box center y
    area: int               # Bounding box area (w * h)
    confidence: float       # Detection confidence (0-1)
    bbox: Tuple[int, int, int, int]  # (x, y, w, h)


def detect_yellow_ball(frame: np.ndarray, config: DetectionConfig) -> Optional[Detection]:
    """
    Simple HSV-based yellow ball detector for HIL testing.
    Replace this function body with TensorRT YOLOv8 inference for production.
    """
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array(config.hsv_lower), np.array(config.hsv_upper))

    # Morphological cleanup
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return None

    # Take the largest contour
    largest = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(largest)

    if area < config.min_contour_area:
        return None

    x, y, w, h = cv2.boundingRect(largest)
    cx = x + w // 2
    cy = y + h // 2

    # Simple "confidence" based on circularity (ball should be round)
    perimeter = cv2.arcLength(largest, True)
    if perimeter == 0:
        return None
    circularity = 4 * np.pi * area / (perimeter * perimeter)
    confidence = min(circularity, 1.0)

    return Detection(cx=cx, cy=cy, area=w * h, confidence=confidence, bbox=(x, y, w, h))


# ═══════════════════════════════════════════════════════════════════════
# MAVLink INTERFACE (Stub for HIL — replace with real mavros/pymavlink)
# ═══════════════════════════════════════════════════════════════════════

class MAVLinkInterface:
    """
    Abstraction for MAVLink communication with Pixhawk.

    For HIL Phase 1: All commands are logged, not sent.
    For Phase 2+:    Uncomment the pymavlink / mavros implementation.
    """

    def __init__(self, connection_string: str = "/dev/ttyTHS1",
                 baud: int = 921600, enabled: bool = False):
        self.enabled = enabled
        self.connection_string = connection_string
        self.baud = baud
        self.connection = None
        self.logger = logging.getLogger("MAVLink")

        if self.enabled:
            try:
                from pymavlink import mavutil
                self.connection = mavutil.mavlink_connection(
                    connection_string, baud=baud
                )
                self.connection.wait_heartbeat(timeout=10)
                self.logger.info(
                    f"Connected to Pixhawk: system {self.connection.target_system}, "
                    f"component {self.connection.target_component}"
                )
            except Exception as e:
                self.logger.error(f"MAVLink connection failed: {e}")
                self.enabled = False

    def send_velocity_body(self, vx: float, vy: float, vz: float, yaw_rate: float):
        """Send velocity command in body frame (NED)."""
        self.logger.debug(
            f"CMD → vx={vx:+.3f} vy={vy:+.3f} vz={vz:+.3f} ωz={yaw_rate:+.3f}"
        )
        if self.enabled and self.connection:
            # SET_POSITION_TARGET_LOCAL_NED with velocity-only type mask
            # type_mask: ignore position, acceleration, yaw (use yaw_rate)
            # 0b0000_01_0_111_000_111 = 0x01C7 = 455
            from pymavlink import mavutil
            self.connection.mav.set_position_target_local_ned_send(
                0,                              # time_boot_ms (ignored)
                self.connection.target_system,
                self.connection.target_component,
                mavutil.mavlink.MAV_FRAME_BODY_NED,
                0b0000_01_0_111_000_111,       # type_mask: velocity + yaw_rate only
                0, 0, 0,                        # x, y, z (ignored)
                vx, vy, vz,                     # vx, vy, vz (m/s, body NED)
                0, 0, 0,                        # afx, afy, afz (ignored)
                0,                              # yaw (ignored)
                yaw_rate                        # yaw_rate (rad/s)
            )

    def trigger_spray(self, duration_ms: int = 500):
        """Trigger sprayer via MAV_CMD_DO_SET_RELAY or Pixhawk AUX."""
        self.logger.info(f"🔫 SPRAY TRIGGERED ({duration_ms}ms)")
        if self.enabled and self.connection:
            from pymavlink import mavutil
            # Option A: Relay command
            self.connection.mav.command_long_send(
                self.connection.target_system,
                self.connection.target_component,
                mavutil.mavlink.MAV_CMD_DO_SET_RELAY,
                0,      # confirmation
                0,      # relay number
                1,      # setting (1 = ON)
                0, 0, 0, 0, 0
            )
            time.sleep(duration_ms / 1000.0)
            self.connection.mav.command_long_send(
                self.connection.target_system,
                self.connection.target_component,
                mavutil.mavlink.MAV_CMD_DO_SET_RELAY,
                0, 0, 0,  # relay OFF
                0, 0, 0, 0, 0
            )

    def set_mode_guided(self):
        """Switch Pixhawk to GUIDED mode."""
        if self.enabled and self.connection:
            from pymavlink import mavutil
            self.connection.mav.set_mode_send(
                self.connection.target_system,
                mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
                4  # GUIDED mode number for ArduCopter
            )
            self.logger.info("Set mode → GUIDED")


# ═══════════════════════════════════════════════════════════════════════
# GPIO SPRAYER (Jetson Nano GPIO — alternative to MAVLink relay)
# ═══════════════════════════════════════════════════════════════════════

class GPIOSprayer:
    """Direct GPIO control for sprayer relay on Jetson Nano."""

    def __init__(self, pin: int = 18, enabled: bool = False):
        self.pin = pin
        self.enabled = enabled
        self.logger = logging.getLogger("GPIO")

        if self.enabled:
            try:
                import Jetson.GPIO as GPIO
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(self.pin, GPIO.OUT, initial=GPIO.LOW)
                self.GPIO = GPIO
                self.logger.info(f"GPIO pin {pin} configured for sprayer.")
            except ImportError:
                self.logger.warning("Jetson.GPIO not available. GPIO disabled.")
                self.enabled = False

    def trigger(self, duration_ms: int = 500):
        self.logger.info(f"💦 GPIO SPRAY: pin {self.pin} HIGH for {duration_ms}ms")
        if self.enabled:
            self.GPIO.output(self.pin, self.GPIO.HIGH)
            time.sleep(duration_ms / 1000.0)
            self.GPIO.output(self.pin, self.GPIO.LOW)

    def cleanup(self):
        if self.enabled:
            self.GPIO.cleanup()


# ═══════════════════════════════════════════════════════════════════════
# VISUAL SERVO + STATE MACHINE — MAIN CONTROL LOOP
# ═══════════════════════════════════════════════════════════════════════

class VisualServoController:
    """Main controller: Detection → PID → Commands → State Machine."""

    def __init__(self, servo_cfg: ServoConfig, det_cfg: DetectionConfig,
                 mavlink: MAVLinkInterface, gpio_sprayer: GPIOSprayer):
        self.cfg = servo_cfg
        self.det_cfg = det_cfg
        self.mav = mavlink
        self.sprayer = gpio_sprayer
        self.logger = logging.getLogger("Servo")

        # State
        self.state = DroneState.IDLE
        self.state_enter_time = time.monotonic()
        self.last_detection_time = 0.0
        self.spray_count = 0

        # PID controllers
        self.pid_yaw = PIDController(
            servo_cfg.yaw_kp, servo_cfg.yaw_ki, servo_cfg.yaw_kd,
            -servo_cfg.max_yaw_rate, servo_cfg.max_yaw_rate
        )
        self.pid_alt = PIDController(
            servo_cfg.alt_kp, servo_cfg.alt_ki, servo_cfg.alt_kd,
            -servo_cfg.max_vz, servo_cfg.max_vz
        )
        self.pid_fwd = PIDController(
            servo_cfg.fwd_kp, servo_cfg.fwd_ki, servo_cfg.fwd_kd,
            -servo_cfg.max_vx, servo_cfg.max_vx
        )

    def _transition(self, new_state: DroneState):
        if new_state != self.state:
            self.logger.info(f"STATE: {self.state.name} → {new_state.name}")
            self.state = new_state
            self.state_enter_time = time.monotonic()
            # Reset PIDs on state change to avoid integral windup carryover
            self.pid_yaw.reset()
            self.pid_alt.reset()
            self.pid_fwd.reset()

    def _time_in_state(self) -> float:
        return time.monotonic() - self.state_enter_time

    def _time_since_detection(self) -> float:
        return time.monotonic() - self.last_detection_time

    def update(self, detection: Optional[Detection]) -> dict:
        """
        Main update loop. Call once per frame.
        Returns a dict with debug info for the overlay.
        """
        now = time.monotonic()
        vx, vy, vz, yaw_rate = 0.0, 0.0, 0.0, 0.0
        debug = {
            "state": self.state.name,
            "detection": detection,
            "vx": 0, "vy": 0, "vz": 0, "yaw_rate": 0,
            "error_x": 0, "error_y": 0, "error_z": 0,
            "spray_active": False,
            "spray_count": self.spray_count,
        }

        if detection is not None:
            self.last_detection_time = now

        # ── State: IDLE ──
        if self.state == DroneState.IDLE:
            # Waiting for start command. In HIL, transition immediately.
            pass  # Call start_mission() externally to transition to SEARCH.

        # ── State: SEARCH ──
        elif self.state == DroneState.SEARCH:
            # Rotate slowly to scan for target
            yaw_rate = 0.3  # rad/s, slow scan

            if detection is not None and detection.confidence > self.det_cfg.confidence_threshold:
                self._transition(DroneState.ACQUIRE)

            elif self._time_in_state() > self.cfg.search_timeout_s:
                self.logger.warning("SEARCH timeout. Returning to IDLE.")
                self._transition(DroneState.IDLE)

        # ── State: ACQUIRE ──
        elif self.state == DroneState.ACQUIRE:
            if detection is None:
                if self._time_since_detection() > self.cfg.detection_lost_timeout_s:
                    self.logger.warning("Detection lost in ACQUIRE. Back to SEARCH.")
                    self._transition(DroneState.SEARCH)
            else:
                error_x = self.cfg.image_center_x - detection.cx
                error_y = self.cfg.image_center_y - detection.cy

                yaw_rate = self.pid_yaw.compute(error_x)
                vz = self.pid_alt.compute(error_y)

                debug["error_x"] = error_x
                debug["error_y"] = error_y

                # Transition to APPROACH when roughly centered
                if abs(error_x) < 80 and abs(error_y) < 60:
                    self._transition(DroneState.APPROACH)

            if self._time_in_state() > self.cfg.acquire_timeout_s:
                self._transition(DroneState.SEARCH)

        # ── State: APPROACH ──
        elif self.state == DroneState.APPROACH:
            if detection is None:
                if self._time_since_detection() > 1.0:
                    self._transition(DroneState.ACQUIRE)
            else:
                error_x = self.cfg.image_center_x - detection.cx
                error_y = self.cfg.image_center_y - detection.cy
                error_z = self.cfg.spray_target_area - detection.area

                yaw_rate = self.pid_yaw.compute(error_x)
                vz = self.pid_alt.compute(error_y)
                vx = self.pid_fwd.compute(error_z)

                debug["error_x"] = error_x
                debug["error_y"] = error_y
                debug["error_z"] = error_z

                # Safety: too close!
                if detection.area > self.cfg.max_safe_bbox_area:
                    self.logger.warning("TOO CLOSE! Retreating.")
                    self._transition(DroneState.RETREAT)

                # Spray condition: close enough AND centered
                elif (detection.area > self.cfg.spray_target_area and
                      abs(error_x) < self.cfg.spray_center_tolerance and
                      abs(error_y) < self.cfg.spray_center_tolerance):
                    self._transition(DroneState.SPRAY)

            if self._time_in_state() > self.cfg.approach_timeout_s:
                self._transition(DroneState.RETREAT)

        # ── State: SPRAY ──
        elif self.state == DroneState.SPRAY:
            # HOLD position — zero all velocities
            vx, vy, vz, yaw_rate = 0.0, 0.0, 0.0, 0.0
            debug["spray_active"] = True

            # Trigger spray (blocking for duration — acceptable at 500ms)
            self.sprayer.trigger(self.cfg.spray_duration_ms)
            self.mav.trigger_spray(self.cfg.spray_duration_ms)
            self.spray_count += 1
            debug["spray_count"] = self.spray_count

            self.logger.info(f"✅ Spray #{self.spray_count} complete!")
            self._transition(DroneState.RETREAT)

        # ── State: RETREAT ──
        elif self.state == DroneState.RETREAT:
            vx = -self.cfg.retreat_speed  # Backward

            if self._time_in_state() > self.cfg.retreat_duration_s:
                self._transition(DroneState.SEARCH)

        # Apply command scaling (HIL safety)
        scale = self.cfg.command_scale
        vx *= scale
        vy *= scale
        vz *= scale
        yaw_rate *= scale

        # Send commands
        self.mav.send_velocity_body(vx, vy, vz, yaw_rate)

        debug.update({"vx": vx, "vy": vy, "vz": vz, "yaw_rate": yaw_rate})
        return debug

    def start_mission(self):
        """Transition from IDLE to SEARCH."""
        if self.state == DroneState.IDLE:
            self._transition(DroneState.SEARCH)

    def abort_mission(self):
        """Emergency stop — zero all commands, return to IDLE."""
        self.mav.send_velocity_body(0, 0, 0, 0)
        self._transition(DroneState.IDLE)


# ═══════════════════════════════════════════════════════════════════════
# VISUALIZATION / DEBUG OVERLAY
# ═══════════════════════════════════════════════════════════════════════

def draw_debug_overlay(frame: np.ndarray, debug: dict, cfg: ServoConfig) -> np.ndarray:
    """Draw detection results, error vectors, and state info on frame."""
    h, w = frame.shape[:2]
    overlay = frame.copy()

    # Draw image center crosshair
    cx, cy = cfg.image_center_x, cfg.image_center_y
    cv2.line(overlay, (cx - 20, cy), (cx + 20, cy), (0, 255, 0), 1)
    cv2.line(overlay, (cx, cy - 20), (cx, cy + 20), (0, 255, 0), 1)

    # Draw detection
    det = debug.get("detection")
    if det is not None:
        x, y, bw, bh = det.bbox
        # Bounding box
        cv2.rectangle(overlay, (x, y), (x + bw, y + bh), (0, 255, 255), 2)
        # Center dot
        cv2.circle(overlay, (det.cx, det.cy), 5, (0, 0, 255), -1)
        # Error vector
        cv2.arrowedLine(overlay, (cx, cy), (det.cx, det.cy), (255, 0, 255), 2)
        # Detection info
        cv2.putText(overlay, f"conf: {det.confidence:.2f}  area: {det.area}",
                     (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

    # State info panel (top-left)
    state_color = {
        "IDLE": (128, 128, 128), "SEARCH": (255, 200, 0),
        "ACQUIRE": (0, 200, 255), "APPROACH": (0, 165, 255),
        "SPRAY": (0, 0, 255), "RETREAT": (255, 0, 0),
        "EMERGENCY": (0, 0, 255),
    }
    state = debug["state"]
    color = state_color.get(state, (255, 255, 255))

    # Background rectangle for text
    cv2.rectangle(overlay, (0, 0), (300, 160), (0, 0, 0), -1)
    cv2.putText(overlay, f"STATE: {state}", (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    cv2.putText(overlay, f"err_x: {debug['error_x']:+4d}px", (10, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    cv2.putText(overlay, f"err_y: {debug['error_y']:+4d}px", (10, 70),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    cv2.putText(overlay, f"err_z: {debug['error_z']:+6d}px2", (10, 90),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    cv2.putText(overlay, f"vx:{debug['vx']:+.2f} vz:{debug['vz']:+.2f} wz:{debug['yaw_rate']:+.2f}",
                (10, 115), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (100, 255, 100), 1)
    cv2.putText(overlay, f"Sprays: {debug['spray_count']}",
                (10, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 255), 1)

    # Spray indicator
    if debug.get("spray_active"):
        cv2.rectangle(overlay, (w - 150, 0), (w, 40), (0, 0, 255), -1)
        cv2.putText(overlay, "SPRAYING!", (w - 140, 28),
                     cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    return overlay


# ═══════════════════════════════════════════════════════════════════════
# MAIN — HIL TEST RUNNER
# ═══════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="HIL Test — Visual Servo Pipeline")
    parser.add_argument("--phase", type=int, default=1, choices=[1, 2, 3],
                        help="Test phase: 1=Detection, 2=MAVLink, 3=Motors")
    parser.add_argument("--armed", action="store_true",
                        help="Enable MAVLink command sending (Phase 2+)")
    parser.add_argument("--device", type=int, default=0,
                        help="Camera device index")
    parser.add_argument("--jetson", action="store_true",
                        help="Use Jetson GStreamer pipeline")
    parser.add_argument("--serial", type=str, default="/dev/ttyTHS1",
                        help="Pixhawk serial port")
    parser.add_argument("--baud", type=int, default=921600,
                        help="Pixhawk baud rate")
    args = parser.parse_args()

    # Logging
    logging.basicConfig(
        level=logging.DEBUG if args.phase == 1 else logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S"
    )
    logger = logging.getLogger("HIL")

    # ── Configuration based on phase ──
    cam_cfg = CameraConfig(device=args.device, use_gstreamer=args.jetson)
    det_cfg = DetectionConfig()
    servo_cfg = ServoConfig()

    if args.phase == 1:
        servo_cfg.command_scale = 0.0   # Log only, no commands sent
        logger.info("═══ PHASE 1: Detection Validation (Props OFF) ═══")
    elif args.phase == 2:
        servo_cfg.command_scale = 0.0   # Still log only, but verify MAVLink
        logger.info("═══ PHASE 2: MAVLink Command Validation (Props OFF) ═══")
    elif args.phase == 3:
        servo_cfg.command_scale = 0.3   # 30% power — CAREFUL!
        logger.info("═══ PHASE 3: Motor Response Test (Props ON, 30% scale) ═══")
        logger.warning("⚠️  PROPS SPINNING! Drone MUST be secured to test stand!")

    # ── Initialize subsystems ──
    mavlink_enabled = args.armed and args.phase >= 2
    mav = MAVLinkInterface(args.serial, args.baud, enabled=mavlink_enabled)
    gpio = GPIOSprayer(pin=18, enabled=False)  # Enable on real Jetson

    controller = VisualServoController(servo_cfg, det_cfg, mav, gpio)

    # ── Open camera ──
    if cam_cfg.use_gstreamer:
        cap = cv2.VideoCapture(cam_cfg.gstreamer_pipeline, cv2.CAP_GSTREAMER)
    else:
        cap = cv2.VideoCapture(cam_cfg.device)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, cam_cfg.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cam_cfg.height)
        cap.set(cv2.CAP_PROP_FPS, cam_cfg.fps)

    if not cap.isOpened():
        logger.error("Failed to open camera!")
        sys.exit(1)

    logger.info(f"Camera opened: {int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x"
                f"{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))} @ "
                f"{cap.get(cv2.CAP_PROP_FPS):.0f}fps")

    # ── Start mission ──
    controller.start_mission()

    # ── Main Loop ──
    fps_counter = 0
    fps_timer = time.monotonic()
    current_fps = 0.0

    logger.info("Press 'q' to quit. Press 's' to force SPRAY state. Press 'r' to reset.")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                logger.warning("Frame grab failed!")
                continue

            # Detect
            detection = detect_yellow_ball(frame, det_cfg)

            # Update controller
            debug = controller.update(detection)

            # FPS calculation
            fps_counter += 1
            elapsed = time.monotonic() - fps_timer
            if elapsed >= 1.0:
                current_fps = fps_counter / elapsed
                fps_counter = 0
                fps_timer = time.monotonic()

            # Draw overlay
            display = draw_debug_overlay(frame, debug, servo_cfg)
            cv2.putText(display, f"FPS: {current_fps:.1f}", (540, 25),
                         cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            cv2.imshow("HIL Test — Visual Servo", display)

            # Keyboard input
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                controller._transition(DroneState.SPRAY)
            elif key == ord('r'):
                controller.abort_mission()
                controller.start_mission()

    except KeyboardInterrupt:
        logger.info("Interrupted by user.")

    finally:
        controller.abort_mission()
        cap.release()
        cv2.destroyAllWindows()
        gpio.cleanup()
        logger.info("HIL test ended. Resources cleaned up.")


if __name__ == "__main__":
    main()

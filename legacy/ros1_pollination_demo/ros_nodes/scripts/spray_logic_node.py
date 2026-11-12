#!/usr/bin/env python3
"""
spray_logic_node.py — Spray Decision State Machine + Pixhawk Servo Control (ROS1 Noetic)
==========================================================================================
Architecture: OPTION A — Full Pixhawk Control (No ESP32)
Date Updated: 2025-02-17

Subscribes to detection results, decides when to spray, sends MAVLink
DO_SET_SERVO commands to Pixhawk via mavros to control:
  - AUX Channel 5 (SERVO13) → EDF Fan ESC (air source / blower)
  - AUX Channel 6 (SERVO14) → MG996R Continuous Servo (auger feeder)

State Machine:
    IDLE → DETECTED → ALIGNED → SPRAY_FAN_SPOOL → SPRAY_ACTIVE → SPRAY_SHUTDOWN → COOLDOWN → IDLE

Topics:
    Subscribes: /detection/result (sprayer_control/Detection)
    Publishes:  /spray/status (std_msgs/String)

MAVLink Servo Control (via mavros):
    Service:  /mavros/cmd/command  (mavros_msgs/CommandLong)
    Command:  MAV_CMD_DO_SET_SERVO (183)
    Params:   param1 = servo channel (13 or 14)
              param2 = PWM value (1000-2000 us)

Hardware Mapping:
    Pixhawk AUX5 = SERVO13 = EDF Fan ESC
      PWM 1000 = Fan OFF (ESC idle)
      PWM 1400 = Fan LOW  (soft-start step 1)
      PWM 1600 = Fan MED  (soft-start step 2)
      PWM 1800 = Fan FULL (operating speed)

    Pixhawk AUX6 = SERVO14 = MG996R Continuous Rotation Servo (Auger)
      PWM 1500 = Servo STOP (center deadband)
      PWM 1650 = Servo CW moderate speed (feed powder)
      PWM 1800 = Servo CW full speed
      PWM 1350 = Servo CCW moderate (reverse — clear clog)

NOTE: This replaces the old ESP32 serial-based control entirely.
      The ESP32 and sprayer_controller.ino are NO LONGER needed.
"""

import rospy
import time
from std_msgs.msg import String
from sprayer_control.msg import Detection

# mavros service for sending MAVLink commands
from mavros_msgs.srv import CommandLong


# ═══════════════════════════════════════════════════
# CONFIGURATION — Adjust for your hardware
# ═══════════════════════════════════════════════════

# Pixhawk servo channel numbers (ArduPilot numbering)
# AUX1 = SERVO9, AUX2 = SERVO10, ... AUX5 = SERVO13, AUX6 = SERVO14
FAN_CHANNEL = 13      # AUX5 → EDF Fan ESC
FEEDER_CHANNEL = 14   # AUX6 → MG996R Continuous Servo

# PWM values (microseconds)
FAN_OFF = 1000        # ESC idle / motor stopped
FAN_LOW = 1400        # Soft-start step 1
FAN_MED = 1600        # Soft-start step 2
FAN_FULL = 1800       # Operating speed

FEEDER_STOP = 1500    # Servo center = stopped
FEEDER_FWD = 1650     # Servo CW = feed powder forward
FEEDER_REV = 1350     # Servo CCW = reverse (unclog)

# MAVLink command ID
MAV_CMD_DO_SET_SERVO = 183


class SprayState:
    """State enum for the spray state machine."""
    IDLE = "IDLE"
    DETECTED = "DETECTED"
    ALIGNED = "ALIGNED"
    SPRAY_FAN_SPOOL = "SPRAY_FAN_SPOOL"   # Fan ramping up, waiting for airflow
    SPRAY_ACTIVE = "SPRAY_ACTIVE"          # Fan + feeder both running
    SPRAY_SHUTDOWN = "SPRAY_SHUTDOWN"      # Feeder stopped, fan clearing residual
    COOLDOWN = "COOLDOWN"
    ERROR = "ERROR"


class SprayLogicNode:
    def __init__(self):
        rospy.init_node('spray_logic_node', anonymous=False)

        # ─── Parameters ───
        self.spray_duration = rospy.get_param('~spray_duration', 0.5)
        self.cooldown_duration = rospy.get_param('~cooldown_duration', 2.0)
        self.alignment_hold_time = rospy.get_param('~alignment_hold_time', 1.0)
        self.detection_timeout = rospy.get_param('~detection_timeout', 2.0)
        self.fan_spool_time = rospy.get_param('~fan_spool_time', 0.4)
        self.fan_shutdown_time = rospy.get_param('~fan_shutdown_time', 0.3)
        self.fan_pwm = rospy.get_param('~fan_pwm', FAN_FULL)
        self.feeder_pwm = rospy.get_param('~feeder_pwm', FEEDER_FWD)

        # ─── State ───
        self.state = SprayState.IDLE
        self.state_enter_time = time.monotonic()
        self.last_detection_time = 0.0
        self.alignment_start_time = 0.0
        self.spray_count = 0
        self.last_position_hint = "NONE"
        self.mavros_connected = False

        # ─── MAVLink Servo Control via mavros ───
        self.cmd_srv = None
        self._connect_mavros()

        # ─── ROS Publishers / Subscribers ───
        self.status_pub = rospy.Publisher('/spray/status', String, queue_size=10)
        self.det_sub = rospy.Subscriber(
            '/detection/result', Detection,
            self.detection_callback, queue_size=1
        )

        # ─── Periodic status publisher ───
        self.status_timer = rospy.Timer(rospy.Duration(0.5), self.publish_status)

        # ─── Periodic mavros reconnect check ───
        self.mavros_timer = rospy.Timer(rospy.Duration(10.0), self.check_mavros)

        rospy.loginfo("=" * 50)
        rospy.loginfo("  Spray Logic Node Started (Pixhawk Servo Mode)")
        rospy.loginfo("=" * 50)
        rospy.loginfo(f"  Fan channel:    SERVO{FAN_CHANNEL} (AUX5)")
        rospy.loginfo(f"  Feeder channel: SERVO{FEEDER_CHANNEL} (AUX6)")
        rospy.loginfo(f"  Fan PWM:        {FAN_OFF} (off) -> {self.fan_pwm} (on)")
        rospy.loginfo(f"  Feeder PWM:     {FEEDER_STOP} (stop) -> {self.feeder_pwm} (feed)")
        rospy.loginfo(f"  Spool time:     {self.fan_spool_time}s")
        rospy.loginfo(f"  Spray duration: {self.spray_duration}s")
        rospy.loginfo(f"  Cooldown:       {self.cooldown_duration}s")
        rospy.loginfo("=" * 50)

    # ─── MAVLink Servo Communication ────────────────────────

    def _connect_mavros(self):
        """Connect to mavros command service."""
        service_name = '/mavros/cmd/command'
        try:
            rospy.loginfo(f"Waiting for mavros service: {service_name} ...")
            rospy.wait_for_service(service_name, timeout=10.0)
            self.cmd_srv = rospy.ServiceProxy(service_name, CommandLong)
            self.mavros_connected = True
            rospy.loginfo("mavros command service connected")
        except rospy.ROSException:
            rospy.logwarn(
                "mavros service not available (timeout). "
                "Sprayer will be UNAVAILABLE until mavros connects. "
                "Detection will still work."
            )
            self.mavros_connected = False

    def check_mavros(self, event=None):
        """Periodic reconnect attempt if mavros was not available at start."""
        if not self.mavros_connected:
            rospy.logwarn_throttle(30, "mavros not connected. Retrying...")
            self._connect_mavros()

    def set_servo(self, channel, pwm):
        """
        Set a Pixhawk servo output via MAVLink DO_SET_SERVO command.

        Args:
            channel: ArduPilot servo channel (13=AUX5, 14=AUX6)
            pwm: PWM value in microseconds (1000-2000)
        Returns:
            True if command sent successfully, False otherwise.
        """
        if not self.mavros_connected or self.cmd_srv is None:
            rospy.logwarn_throttle(5, "Cannot send servo cmd: mavros not connected")
            return False
        try:
            resp = self.cmd_srv(
                broadcast=False,
                command=MAV_CMD_DO_SET_SERVO,
                confirmation=0,
                param1=float(channel),
                param2=float(pwm),
                param3=0.0,
                param4=0.0,
                param5=0.0,
                param6=0.0,
                param7=0.0
            )
            if resp.success:
                rospy.logdebug(f"Servo CH{channel} = {pwm}us OK")
            else:
                rospy.logwarn(f"Servo CH{channel} = {pwm}us FAILED (result={resp.result})")
            return resp.success
        except rospy.ServiceException as e:
            rospy.logerr(f"Servo command service call failed: {e}")
            self.mavros_connected = False
            return False

    def all_off(self):
        """Emergency: set both fan and feeder to safe defaults."""
        self.set_servo(FAN_CHANNEL, FAN_OFF)
        self.set_servo(FEEDER_CHANNEL, FEEDER_STOP)

    # ─── State Machine ──────────────────────────────────────

    def _transition(self, new_state):
        """Change state with logging."""
        if new_state != self.state:
            rospy.loginfo(f"STATE: {self.state} -> {new_state}")
            self.state = new_state
            self.state_enter_time = time.monotonic()

    def _time_in_state(self):
        return time.monotonic() - self.state_enter_time

    def detection_callback(self, msg):
        """
        Called every time a Detection message arrives.
        This is the main control loop driver.
        """
        now = time.monotonic()
        self.last_position_hint = msg.position_hint

        if msg.detected:
            self.last_detection_time = now

        time_since_detection = now - self.last_detection_time

        # ═══ STATE: IDLE ═══
        if self.state == SprayState.IDLE:
            if msg.detected and msg.confidence > 0.4:
                self._transition(SprayState.DETECTED)

        # ═══ STATE: DETECTED ═══
        elif self.state == SprayState.DETECTED:
            if not msg.detected or time_since_detection > self.detection_timeout:
                self._transition(SprayState.IDLE)
            elif msg.position_hint == "CENTER":
                self.alignment_start_time = now
                self._transition(SprayState.ALIGNED)

        # ═══ STATE: ALIGNED ═══
        elif self.state == SprayState.ALIGNED:
            if not msg.detected or time_since_detection > self.detection_timeout:
                self._transition(SprayState.IDLE)
            elif msg.position_hint != "CENTER":
                # Lost alignment — go back to DETECTED
                self._transition(SprayState.DETECTED)
            elif msg.position_hint == "TOO_FAR":
                # Centered but too far — wait for pilot to approach
                self._transition(SprayState.DETECTED)
            elif (now - self.alignment_start_time) >= self.alignment_hold_time:
                # Held center for long enough — begin spray sequence!
                self._begin_spray_sequence()
                self._transition(SprayState.SPRAY_FAN_SPOOL)

        # ═══ STATE: SPRAY_FAN_SPOOL (Fan ramping up, no powder yet) ═══
        elif self.state == SprayState.SPRAY_FAN_SPOOL:
            if self._time_in_state() >= self.fan_spool_time:
                # Airflow established — start powder feed
                self._start_feeder()
                self._transition(SprayState.SPRAY_ACTIVE)

        # ═══ STATE: SPRAY_ACTIVE (Fan + Feeder both running) ═══
        elif self.state == SprayState.SPRAY_ACTIVE:
            if self._time_in_state() >= self.spray_duration:
                # Spray duration complete — stop feeder first
                self._stop_feeder()
                self._transition(SprayState.SPRAY_SHUTDOWN)

        # ═══ STATE: SPRAY_SHUTDOWN (Feeder stopped, fan clears tube) ═══
        elif self.state == SprayState.SPRAY_SHUTDOWN:
            if self._time_in_state() >= self.fan_shutdown_time:
                # Tube cleared — stop fan
                self._stop_fan()
                self._transition(SprayState.COOLDOWN)

        # ═══ STATE: COOLDOWN ═══
        elif self.state == SprayState.COOLDOWN:
            if self._time_in_state() >= self.cooldown_duration:
                self._transition(SprayState.IDLE)

        # ═══ STATE: ERROR ═══
        elif self.state == SprayState.ERROR:
            if self._time_in_state() > 5.0:
                self.all_off()
                self._transition(SprayState.IDLE)

    # ─── Spray Actions ──────────────────────────────────────

    def _begin_spray_sequence(self):
        """
        Phase 1: Start EDF fan with soft-start ramp.
        Feeder does NOT start yet — we must wait for airflow.
        """
        self.spray_count += 1
        rospy.loginfo(f"SPRAY #{self.spray_count} -- Fan spool-up (soft-start)")

        # Soft-start ramp: LOW → MED → FULL over ~200ms
        ok = self.set_servo(FAN_CHANNEL, FAN_LOW)
        if not ok:
            rospy.logerr("Failed to start fan! Aborting spray.")
            self._transition(SprayState.ERROR)
            return

        # Schedule ramp steps using ROS timers (non-blocking)
        rospy.Timer(
            rospy.Duration(0.1),
            lambda e: self.set_servo(FAN_CHANNEL, FAN_MED),
            oneshot=True
        )
        rospy.Timer(
            rospy.Duration(0.2),
            lambda e: self.set_servo(FAN_CHANNEL, self.fan_pwm),
            oneshot=True
        )

    def _start_feeder(self):
        """Phase 2: Airflow established — start auger servo to feed powder."""
        rospy.loginfo("Airflow ready -- starting powder feed")
        ok = self.set_servo(FEEDER_CHANNEL, self.feeder_pwm)
        if not ok:
            rospy.logerr("Failed to start feeder!")
            self.all_off()
            self._transition(SprayState.ERROR)

    def _stop_feeder(self):
        """Phase 3a: Stop powder feed (fan continues to clear tube)."""
        rospy.loginfo("Stopping powder feed")
        self.set_servo(FEEDER_CHANNEL, FEEDER_STOP)

    def _stop_fan(self):
        """Phase 3b: Stop fan after tube is cleared."""
        rospy.loginfo("SPRAY OFF -- Fan stopped")
        self.set_servo(FAN_CHANNEL, FAN_OFF)

    # ─── Status Publishing ──────────────────────────────────

    def publish_status(self, event=None):
        """Publish current state for monitoring."""
        status_msg = String()
        status_msg.data = (
            f"STATE={self.state} | "
            f"POS={self.last_position_hint} | "
            f"SPRAYS={self.spray_count} | "
            f"MAVROS={'OK' if self.mavros_connected else 'DISCONNECTED'}"
        )
        self.status_pub.publish(status_msg)

    # ─── Cleanup ────────────────────────────────────────────

    def shutdown(self):
        """Clean shutdown: ensure both actuators are OFF."""
        rospy.loginfo("Shutting down spray logic node...")
        self.all_off()
        rospy.loginfo("Fan OFF, Feeder STOP. Safe shutdown complete.")


def main():
    node = SprayLogicNode()
    rospy.on_shutdown(node.shutdown)
    try:
        rospy.spin()
    except rospy.ROSInterruptException:
        pass


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
detector_node.py — Yellow Ball Detection Node (ROS1 Noetic)
============================================================
Subscribes to USB camera image, detects yellow objects via HSV thresholding,
publishes Detection messages and a debug overlay image.

Part of the 6-Day Survival Sprint.

Usage:
    rosrun sprayer_control detector_node.py
    OR via launch file (preferred).

Topics:
    Subscribes: /usb_cam/image_raw (sensor_msgs/Image)
    Publishes:  /detection/result (sprayer_control/Detection)
                /detector/debug_image (sensor_msgs/Image)
"""

import rospy
import cv2
import numpy as np
from sensor_msgs.msg import Image
from cv_bridge import CvBridge, CvBridgeError

# Import our custom message
# This will work after catkin_make generates the Python bindings
from sprayer_control.msg import Detection


class YellowBallDetector:
    def __init__(self):
        rospy.init_node('detector_node', anonymous=False)

        # ─── Parameters (overridable via launch file / rosparam) ───
        # HSV range for yellow detection
        self.hsv_lower = np.array([
            rospy.get_param('~hsv_h_low', 20),
            rospy.get_param('~hsv_s_low', 100),
            rospy.get_param('~hsv_v_low', 100),
        ])
        self.hsv_upper = np.array([
            rospy.get_param('~hsv_h_high', 35),
            rospy.get_param('~hsv_s_high', 255),
            rospy.get_param('~hsv_v_high', 255),
        ])

        # Minimum contour area to count as a valid detection (pixels²)
        self.min_area = rospy.get_param('~min_contour_area', 500)

        # Image dimensions (will be updated from first frame)
        self.img_width = 640
        self.img_height = 480

        # Position hint thresholds (fraction of image width)
        self.center_tolerance = rospy.get_param('~center_tolerance', 0.15)  # ±15% of width = "CENTER"
        self.close_area = rospy.get_param('~close_area_threshold', 15000)   # bbox area (pixels²)
        self.far_area = rospy.get_param('~far_area_threshold', 2000)        # bbox area (pixels²)

        # ─── ROS Plumbing ───
        self.bridge = CvBridge()

        # Publishers
        self.det_pub = rospy.Publisher('/detection/result', Detection, queue_size=1)
        self.debug_pub = rospy.Publisher('/detector/debug_image', Image, queue_size=1)

        # Subscriber
        self.image_sub = rospy.Subscriber(
            '/usb_cam/image_raw', Image, self.image_callback, queue_size=1, buff_size=2**24
        )
        # buff_size=2**24 prevents subscriber lag on slow processing

        # FPS tracking
        self.frame_count = 0
        self.fps_timer = rospy.Time.now()
        self.current_fps = 0.0

        rospy.loginfo("═══ Yellow Ball Detector Node Started ═══")
        rospy.loginfo(f"HSV Lower: {self.hsv_lower}, HSV Upper: {self.hsv_upper}")
        rospy.loginfo(f"Min contour area: {self.min_area}")

    def image_callback(self, msg):
        """Process each camera frame."""
        try:
            # Convert ROS Image → OpenCV BGR
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except CvBridgeError as e:
            rospy.logerr(f"CvBridge Error: {e}")
            return

        self.img_height, self.img_width = frame.shape[:2]

        # ─── Detection Pipeline ───
        detection = self._detect_yellow(frame)

        # ─── Publish Detection Result ───
        det_msg = Detection()
        det_msg.header = msg.header

        if detection is not None:
            cx, cy, area, confidence, bbox = detection
            det_msg.detected = True
            det_msg.cx = cx
            det_msg.cy = cy
            det_msg.area = area
            det_msg.confidence = confidence
            det_msg.position_hint = self._get_position_hint(cx, area)
        else:
            det_msg.detected = False
            det_msg.cx = 0
            det_msg.cy = 0
            det_msg.area = 0
            det_msg.confidence = 0.0
            det_msg.position_hint = "NONE"

        self.det_pub.publish(det_msg)

        # ─── Publish Debug Image ───
        if self.debug_pub.get_num_connections() > 0:
            debug_frame = self._draw_debug_overlay(frame, detection, det_msg.position_hint)
            try:
                debug_msg = self.bridge.cv2_to_imgmsg(debug_frame, encoding='bgr8')
                self.debug_pub.publish(debug_msg)
            except CvBridgeError as e:
                rospy.logerr(f"Debug image error: {e}")

        # ─── FPS Update ───
        self.frame_count += 1
        elapsed = (rospy.Time.now() - self.fps_timer).to_sec()
        if elapsed >= 1.0:
            self.current_fps = self.frame_count / elapsed
            self.frame_count = 0
            self.fps_timer = rospy.Time.now()

    def _detect_yellow(self, frame):
        """
        Detect the largest yellow object in the frame.

        Returns: (cx, cy, area, confidence, (x,y,w,h)) or None
        """
        # Convert to HSV
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Threshold for yellow
        mask = cv2.inRange(hsv, self.hsv_lower, self.hsv_upper)

        # Morphological cleanup — remove noise, fill gaps
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)   # Remove small noise
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)  # Fill small holes

        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return None

        # Get the largest contour by area
        largest = max(contours, key=cv2.contourArea)
        contour_area = cv2.contourArea(largest)

        if contour_area < self.min_area:
            return None

        # Bounding box
        x, y, w, h = cv2.boundingRect(largest)
        cx = x + w // 2
        cy = y + h // 2
        bbox_area = w * h

        # Confidence: based on how "round" the object is (circularity)
        perimeter = cv2.arcLength(largest, True)
        if perimeter == 0:
            return None
        circularity = 4 * np.pi * contour_area / (perimeter * perimeter)
        confidence = min(circularity, 1.0)

        return (cx, cy, bbox_area, confidence, (x, y, w, h))

    def _get_position_hint(self, cx, area):
        """Determine where the target is relative to the frame center."""
        center_x = self.img_width / 2.0
        tolerance_px = self.img_width * self.center_tolerance

        if area < self.far_area:
            return "TOO_FAR"
        elif area > self.close_area:
            return "TOO_CLOSE"
        elif cx < center_x - tolerance_px:
            return "LEFT"
        elif cx > center_x + tolerance_px:
            return "RIGHT"
        else:
            return "CENTER"

    def _draw_debug_overlay(self, frame, detection, position_hint):
        """Draw detection info on the frame for visual debugging."""
        overlay = frame.copy()
        h, w = overlay.shape[:2]

        # Draw center crosshair
        cv2.line(overlay, (w // 2 - 30, h // 2), (w // 2 + 30, h // 2), (0, 255, 0), 1)
        cv2.line(overlay, (w // 2, h // 2 - 30), (w // 2, h // 2 + 30), (0, 255, 0), 1)

        # Draw center tolerance zone
        tol_px = int(w * self.center_tolerance)
        cv2.rectangle(overlay,
                      (w // 2 - tol_px, 50),
                      (w // 2 + tol_px, h - 50),
                      (0, 255, 0), 1)

        if detection is not None:
            cx, cy, area, confidence, (bx, by, bw, bh) = detection

            # Bounding box
            cv2.rectangle(overlay, (bx, by), (bx + bw, by + bh), (0, 255, 255), 2)

            # Center point
            cv2.circle(overlay, (cx, cy), 6, (0, 0, 255), -1)

            # Error line from image center to target center
            cv2.arrowedLine(overlay, (w // 2, h // 2), (cx, cy), (255, 0, 255), 2)

            # Info text
            cv2.putText(overlay, f"CONF: {confidence:.2f}  AREA: {area}",
                        (bx, by - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            cv2.putText(overlay, f"POS: ({cx}, {cy})",
                        (bx, by + bh + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        # Status panel (top-left)
        color_map = {
            "NONE": (128, 128, 128),
            "LEFT": (0, 165, 255),
            "RIGHT": (255, 165, 0),
            "CENTER": (0, 255, 0),
            "TOO_FAR": (255, 255, 0),
            "TOO_CLOSE": (0, 0, 255),
        }
        color = color_map.get(position_hint, (255, 255, 255))

        cv2.rectangle(overlay, (0, 0), (250, 70), (0, 0, 0), -1)
        cv2.putText(overlay, f"TARGET: {position_hint}", (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        cv2.putText(overlay, f"FPS: {self.current_fps:.1f}", (10, 55),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)

        return overlay


def main():
    try:
        detector = YellowBallDetector()
        rospy.spin()
    except rospy.ROSInterruptException:
        rospy.loginfo("Detector node shutting down.")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
hsv_tuner.py — Interactive HSV Threshold Tuner
================================================
Standalone tool (NO ROS needed) to find the right HSV values
for yellow ball detection. Run this on Day 2 to calibrate.

Usage:
    python3 hsv_tuner.py
    python3 hsv_tuner.py --device 1      # If camera is on /dev/video1
    python3 hsv_tuner.py --width 640 --height 480

Instructions:
    1. Point the camera at the yellow ball.
    2. Adjust the sliders until ONLY the ball is white in the mask.
    3. Note down the H, S, V min/max values.
    4. Update these values in the detector_node.py parameters
       (or in the launch file as rosparam).
    5. Press 'q' to quit. Press 's' to save values to file.
"""

import cv2
import numpy as np
import argparse
import json
import os


def nothing(x):
    """Trackbar callback (required by OpenCV, does nothing)."""
    pass


def main():
    parser = argparse.ArgumentParser(description="HSV Threshold Tuner for Yellow Ball Detection")
    parser.add_argument('--device', type=int, default=0, help='Camera device index')
    parser.add_argument('--width', type=int, default=640, help='Frame width')
    parser.add_argument('--height', type=int, default=480, help='Frame height')
    args = parser.parse_args()

    # Open camera
    cap = cv2.VideoCapture(args.device)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)

    if not cap.isOpened():
        print(f"ERROR: Cannot open camera {args.device}")
        return

    print(f"Camera opened: {int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}")

    # Create window with trackbars
    cv2.namedWindow('HSV Tuner', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('HSV Tuner', 640, 100)

    # Default values for YELLOW
    cv2.createTrackbar('H Low', 'HSV Tuner', 20, 179, nothing)
    cv2.createTrackbar('H High', 'HSV Tuner', 35, 179, nothing)
    cv2.createTrackbar('S Low', 'HSV Tuner', 100, 255, nothing)
    cv2.createTrackbar('S High', 'HSV Tuner', 255, 255, nothing)
    cv2.createTrackbar('V Low', 'HSV Tuner', 100, 255, nothing)
    cv2.createTrackbar('V High', 'HSV Tuner', 255, 255, nothing)

    print("\n════════════════════════════════════════════")
    print("  HSV TUNER — Adjust sliders to isolate the yellow ball")
    print("  Press 'q' to quit")
    print("  Press 's' to save current values to hsv_values.json")
    print("  Press 'r' to reset to default yellow values")
    print("════════════════════════════════════════════\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Frame grab failed!")
            break

        # Read trackbar values
        h_low = cv2.getTrackbarPos('H Low', 'HSV Tuner')
        h_high = cv2.getTrackbarPos('H High', 'HSV Tuner')
        s_low = cv2.getTrackbarPos('S Low', 'HSV Tuner')
        s_high = cv2.getTrackbarPos('S High', 'HSV Tuner')
        v_low = cv2.getTrackbarPos('V Low', 'HSV Tuner')
        v_high = cv2.getTrackbarPos('V High', 'HSV Tuner')

        hsv_lower = np.array([h_low, s_low, v_low])
        hsv_upper = np.array([h_high, s_high, v_high])

        # Process
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, hsv_lower, hsv_upper)

        # Morphological cleanup
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        mask_clean = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask_clean = cv2.morphologyEx(mask_clean, cv2.MORPH_CLOSE, kernel)

        # Apply mask to original image
        result = cv2.bitwise_and(frame, frame, mask=mask_clean)

        # Find contours and draw on result
        contours, _ = cv2.findContours(mask_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            largest = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(largest)
            if area > 500:
                x, y, w, h = cv2.boundingRect(largest)
                cv2.rectangle(result, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(result, f"Area: {w*h}", (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # Add text overlay to frames
        info_text = f"HSV: [{h_low},{s_low},{v_low}] - [{h_high},{s_high},{v_high}]"
        cv2.putText(frame, info_text, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.putText(frame, "Press 'q' quit | 's' save | 'r' reset", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        # Stack images side by side: Original | Mask | Result
        mask_bgr = cv2.cvtColor(mask_clean, cv2.COLOR_GRAY2BGR)
        display = np.hstack([frame, mask_bgr, result])

        # Resize for display if too wide
        display_h, display_w = display.shape[:2]
        if display_w > 1920:
            scale = 1920.0 / display_w
            display = cv2.resize(display, None, fx=scale, fy=scale)

        cv2.imshow('Original | Mask | Result', display)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            # Save values
            values = {
                "hsv_h_low": h_low, "hsv_h_high": h_high,
                "hsv_s_low": s_low, "hsv_s_high": s_high,
                "hsv_v_low": v_low, "hsv_v_high": v_high,
            }
            save_path = os.path.join(os.path.dirname(__file__), "hsv_values.json")
            with open(save_path, 'w') as f:
                json.dump(values, f, indent=2)
            print(f"\n✅ HSV values saved to {save_path}")
            print(f"   Values: {values}")
            print(f"\n   For launch file, use:")
            print(f'   <param name="hsv_h_low" value="{h_low}" />')
            print(f'   <param name="hsv_h_high" value="{h_high}" />')
            print(f'   <param name="hsv_s_low" value="{s_low}" />')
            print(f'   <param name="hsv_s_high" value="{s_high}" />')
            print(f'   <param name="hsv_v_low" value="{v_low}" />')
            print(f'   <param name="hsv_v_high" value="{v_high}" />')
        elif key == ord('r'):
            # Reset to default yellow
            cv2.setTrackbarPos('H Low', 'HSV Tuner', 20)
            cv2.setTrackbarPos('H High', 'HSV Tuner', 35)
            cv2.setTrackbarPos('S Low', 'HSV Tuner', 100)
            cv2.setTrackbarPos('S High', 'HSV Tuner', 255)
            cv2.setTrackbarPos('V Low', 'HSV Tuner', 100)
            cv2.setTrackbarPos('V High', 'HSV Tuner', 255)
            print("🔄 Reset to default yellow values.")

    cap.release()
    cv2.destroyAllWindows()
    print("HSV Tuner closed.")


if __name__ == '__main__':
    main()

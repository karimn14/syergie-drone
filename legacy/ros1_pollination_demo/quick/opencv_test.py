# ════════════════════════════════════════════════════
# STEP 2: Test the camera with raw OpenCV (no ROS yet)
# ════════════════════════════════════════════════════
# This is a quick sanity check. If this works, the camera hardware is OK.

python3 << 'CAMTEST'
import cv2
import time

print("Opening camera...")
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("❌ FAILED: Cannot open camera /dev/video0")
    print("   Try: python3 -c \"import cv2; cap=cv2.VideoCapture(1); print(cap.isOpened())\"")
    exit(1)

# Set resolution
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# Grab 10 frames and measure FPS
start = time.time()
for i in range(10):
    ret, frame = cap.read()
    if not ret:
        print(f"❌ FAILED: Frame {i} grab failed")
        break

elapsed = time.time() - start
fps = 10 / elapsed if elapsed > 0 else 0

w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

print(f"✅ Camera works!")
print(f"   Resolution: {w}x{h}")
print(f"   Measured FPS: {fps:.1f}")
print(f"   Frame shape: {frame.shape}")

# Save a test frame (so you can verify the image is correct)
cv2.imwrite("/tmp/camera_test.jpg", frame)
print(f"   Test frame saved to /tmp/camera_test.jpg")

cap.release()
print("Done.")
CAMTEST

# ════════════════════════════════════════════════════
# View the test frame (from your laptop via VS Code):
# ════════════════════════════════════════════════════
# In VS Code Remote-SSH, navigate to /tmp/camera_test.jpg
# and click on it. VS Code can display JPEG images.
# OR download it:
#   On laptop PowerShell: scp jetson@192.168.55.1:/tmp/camera_test.jpg .
# Detection.msg — Custom ROS message for target detection results
# Package: sprayer_control
#
# Published by: detector_node.py
# Subscribed by: spray_logic_node.py

Header header
bool detected           # Is a target visible in this frame?
int32 cx                # Bounding box center X (pixels)
int32 cy                # Bounding box center Y (pixels)
int32 area              # Bounding box area in pixels² (w * h)
float32 confidence      # Detection confidence (0.0 - 1.0)
string position_hint    # "LEFT", "RIGHT", "CENTER", "TOO_FAR", "TOO_CLOSE", "NONE"

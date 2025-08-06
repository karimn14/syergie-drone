# tree_proximity_checker.py – Multi-Sensor Obstacle Avoidance
# Supports TF-Mini Plus (front), TF-Luna (left, right, rear, down)
# Integration notes:
#   - Map each sensor to a dedicated UART port on Jetson Nano or via UART multiplexer
#   - Example mapping:
#       FRONT: /dev/ttyUSB1
#       LEFT:  /dev/ttyUSB2
#       RIGHT: /dev/ttyUSB3
#       REAR:  /dev/ttyUSB4
#       DOWN:  /dev/ttyUSB5
#   - Adjust port names as needed for your hardware
import serial

def check_multi_sensor_proximity(sensor_ports, threshold_cm=200):
    """
    sensor_ports: dict mapping direction to serial port, e.g.
        {
            'front': '/dev/ttyUSB1',
            'left':  '/dev/ttyUSB2',
            'right': '/dev/ttyUSB3',
            'rear':  '/dev/ttyUSB4',
            'down':  '/dev/ttyUSB5',
        }
    threshold_cm: distance threshold for obstacle detection
    Returns: dict with detection status and measured distances for each direction
    """
    status = {}
    for direction, port in sensor_ports.items():
        try:
            ser = serial.Serial(port, 115200, timeout=1)
            line = ser.readline().decode().strip()
            distance = float(line)
            detected = 0 < distance < threshold_cm
            status[direction] = {
                'detected': detected,
                'distance_cm': distance if distance > 0 else None
            }
            if detected:
                print(f"\U0001F6A8 Obstacle Detected [{direction}] at {distance} cm!")
            ser.close()
        except Exception as e:
            status[direction] = {
                'detected': False,
                'distance_cm': None,
                'error': str(e)
            }
    return status

# Example usage:
# sensor_ports = {
#     'front': '/dev/ttyUSB1',
#     'left':  '/dev/ttyUSB2',
#     'right': '/dev/ttyUSB3',
#     'rear':  '/dev/ttyUSB4',
#     'down':  '/dev/ttyUSB5',
# }
# result = check_multi_sensor_proximity(sensor_ports, threshold_cm=200)
# print(result)

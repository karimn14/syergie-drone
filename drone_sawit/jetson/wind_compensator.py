# wind_compensator.py – Adjust spray parameters based on wind
def compensate_spray(wind_speed, wind_direction_deg, tree_direction_deg, base_duration):
    """
    Adjust spray duration and gimbal angle based on relative wind
    Args:
        wind_speed (float): wind in m/s
        wind_direction_deg (float): wind direction in degrees
        tree_direction_deg (float): direction from drone to tree in degrees
        base_duration (int): base spray duration in ms
    Returns:
        dict: {'duration': int, 'gimbal_angle': float}
    """
    relative_angle = (tree_direction_deg - wind_direction_deg + 360) % 360
    angle_offset = 90 - abs(180 - relative_angle)
    duration = int(base_duration * (1 + 0.1 * wind_speed * abs(angle_offset) / 90))
    gimbal_angle = angle_offset
    return {'duration': duration, 'gimbal_angle': gimbal_angle}

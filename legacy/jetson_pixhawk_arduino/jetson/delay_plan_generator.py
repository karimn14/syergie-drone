"""
delay_plan_generator.py
Adds delay commands after each waypoint in a QGroundControl .plan file.
"""

import json

def add_delay_to_plan(plan_file, delay_seconds, output_file=None):
    """Modify plan to add delay (MAV_CMD_NAV_DELAY) after each waypoint."""
    with open(plan_file, 'r') as f:
        plan = json.load(f)
    new_items = []
    for item in plan['mission']['items']:
        new_items.append(item)
        if item['command'] == 16:  # MAV_CMD_NAV_WAYPOINT
            delay_item = {
                "autoContinue": True,
                "command": 93,  # MAV_CMD_NAV_DELAY
                "doJumpId": item['doJumpId'] + 1,
                "frame": 2,
                "params": [delay_seconds, 0, 0, 0, 0, 0, 0],
                "type": "SimpleItem"
            }
            new_items.append(delay_item)
    plan['mission']['items'] = new_items
    if not output_file:
        output_file = plan_file.replace('.plan', f'_delay{delay_seconds}.plan')
    with open(output_file, 'w') as f:
        json.dump(plan, f, indent=2)
    print(f"Delay-added plan saved to {output_file}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python delay_plan_generator.py <plan_file> <delay_seconds> [output_file]")
    else:
        plan_file = sys.argv[1]
        delay_seconds = float(sys.argv[2])
        output_file = sys.argv[3] if len(sys.argv) > 3 else None
        add_delay_to_plan(plan_file, delay_seconds, output_file)

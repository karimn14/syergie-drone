# Pixhawk Configuration for Drone Sawit

This folder contains all configuration and mission files for the Pixhawk autopilot used in the Drone Sawit project.

## Files
- `drone_sawit.params`: Main parameter set with comments and rationale.
- `route_pollination.plan`: QGroundControl-compatible route (auto-generated).
- `custom_mission_items.plan`: Example plan with custom mission items and geofence.
- `geofence_polygon.json`: Example geofence polygon for QGC import.

## Usage
1. Load `drone_sawit.params` into PX4 via QGroundControl or direct parameter upload.
2. Import `.plan` files into QGroundControl for mission planning.
3. Use `geofence_polygon.json` to define operational boundaries.
4. Review and adjust parameters for your operational environment.

## Safety & Compliance
- All parameters are chosen for safe autonomous operation.
- Geofence and rally points are set for safety.
- Return-to-launch, low battery, and RC-loss actions are enabled.

## Created
2025-05-14

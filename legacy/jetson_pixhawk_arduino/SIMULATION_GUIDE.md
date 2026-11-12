# Hardware-in-the-Loop (HIL) & Simulation Guide

## Overview
Drone Sawit supports hardware-in-the-loop (HIL) simulation and mission replay for robust system validation.

## Types of Simulation
- **Software-in-the-loop (SITL):** Use PX4 SITL for flight logic testing.
- **Hardware-in-the-loop (HIL):** Connect Pixhawk and Jetson to simulate real missions with live feedback.

## Running SITL
```bash
# Example using PX4 SITL
cd pixhawk/
# Launch PX4 SITL (requires PX4 and Gazebo installed)
make px4_sitl gazebo
```

## Running HIL
- Connect Jetson and Pixhawk via telemetry or USB
- Use `jetson/hil_sim.py` to coordinate data exchange
- Monitor logs in `data/` for validation

## Best Practices
- Always run preflight diagnostics before simulation
- Log all data for post-mission analysis
- Use test plans in `pixhawk/` for repeatable scenarios

## References
- See `README_DEPLOYMENT.md` for troubleshooting
- PX4 HIL docs: https://docs.px4.io/main/en/simulation/hitl.html

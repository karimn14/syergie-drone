# Drone Sawit System Architecture

## Overview
Drone Sawit is an integrated drone system for automated spraying and mission management in plantation environments. The system consists of three main hardware components:

- **Pixhawk**: Flight control and mission execution
- **Jetson**: AI, mission planning, health monitoring, dashboard
- **Arduino**: Sprayer control, diagnostics, sensor feedback

## Block Diagram

```
[Ground Station/Web Dashboard]
         |
         v
     [Jetson Xavier]
         |
         v
     [Pixhawk Flight Controller] <-> [Arduino Sprayer Controller]
         |
         v
    [Drone Actuators/Sensors]
```

## Communication
- **Jetson <-> Pixhawk**: MAVLink/Serial
- **Jetson <-> Arduino**: Serial/UART
- **Jetson <-> Dashboard**: WebSocket/HTTP

## Data Flow
1. Mission plan uploaded to Jetson
2. Jetson processes and sends plan to Pixhawk
3. Pixhawk executes flight, relays status to Jetson
4. Jetson controls sprayer via Arduino
5. All telemetry and logs are available via Dashboard

---

For more details, see `README.md` and `README_DEPLOYMENT.md`.

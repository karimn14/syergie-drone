# Alternate dashboard snapshot

This folder preserves a separate dashboard-oriented QGC experiment from the standalone MAVSDK repository. It uses a FastAPI/WebSocket dashboard and a different `FlightSupervisor` API with shared state. It is not wired into the primary module copy and is not a ROS 2 component. Do not launch it against a vehicle.

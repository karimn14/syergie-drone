# API & Protocol Documentation

## 1. Jetson <-> Pixhawk (MAVLink)
- **Protocol**: MAVLink over Serial/UDP
- **Messages**:
  - Mission upload/download
  - Status/heartbeat
  - Command/control (takeoff, land, RTL, etc.)

## 2. Jetson <-> Arduino (Serial)
- **Protocol**: Custom serial protocol (9600/115200 baud)
- **Commands**:
  - `SPRAY_ON`, `SPRAY_OFF`
  - `SET_MODE <auto/manual>`
  - `STATUS_REQUEST`
- **Responses**:
  - `STATUS <ok/error>`
  - `SENSOR <value>`

## 3. Jetson <-> Dashboard (Web)
- **Protocol**: HTTP/REST, WebSocket
- **Endpoints**:
  - `/status`, `/logs`, `/mission`, `/health`

---

For implementation details, see relevant Python and Arduino files.

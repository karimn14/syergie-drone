"""
main.py
Backend server entry point for mission dashboard and API using FastAPI.
"""

from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Drone Sawit Mission Dashboard API"}

@app.get("/logs")
def get_logs():
    log_path = os.path.join(os.path.dirname(__file__), "mission.log")
    if os.path.exists(log_path):
        with open(log_path) as f:
            return {"logs": f.read()}
    return {"logs": "No logs found."}

@app.get("/status")
def get_status():
    # Example: load mission state from persistent file
    state_file = os.path.join(os.path.dirname(__file__), "mission_state.json")
    if os.path.exists(state_file):
        with open(state_file) as f:
            state = json.load(f)
    else:
        state = {"status": "Idle", "battery": 87, "mission_progress": 0.0}
    return state

@app.get("/health")
def get_health():
    try:
        from health_monitor import health_report
        return health_report()
    except Exception as e:
        return {"error": str(e)}

@app.get("/errors")
def get_errors():
    error_log = os.path.join(os.path.dirname(__file__), "error.log")
    if os.path.exists(error_log):
        with open(error_log) as f:
            return {"errors": f.read()}
    return {"errors": "No errors."}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    for i in range(10):  # Example: send 10 status updates
        await websocket.send_json({"status": "Active", "progress": i*10})
    await websocket.close()

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import ssl

security = HTTPBasic()
USERS = {"admin": "adminpass"}

def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    correct_pw = USERS.get(credentials.username)
    if not correct_pw or credentials.password != correct_pw:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return credentials.username

@app.get("/secure-status")
def get_secure_status(user: str = Depends(authenticate)):
    state_file = os.path.join(os.path.dirname(__file__), "mission_state.json")
    if os.path.exists(state_file):
        with open(state_file) as f:
            state = json.load(f)
    else:
        state = {"status": "Idle", "battery": 87, "mission_progress": 0.0}
    return state

@app.post("/cloud-sync")
def cloud_sync(file: str, url: str, username: str = None, password: str = None):
    from cloud_sync import upload_file
    try:
        upload_file(file, url, username, password)
        return {"result": "success"}
    except Exception as e:
        return {"result": "error", "detail": str(e)}

@app.get("/api/mission-status")
def api_mission_status():
    state_file = os.path.join(os.path.dirname(__file__), "mission_state.json")
    if os.path.exists(state_file):
        with open(state_file) as f:
            state = json.load(f)
    else:
        state = {"status": "Idle", "battery": 87, "mission_progress": 0.0}
    return state

@app.get("/hil-status")
def hil_status():
    from hil_sim import simulate_mission_state
    return simulate_mission_state()

@app.get("/api/multi-drone-status")
def multi_drone_status():
    # Placeholder: In production, aggregate from multiple Jetson/mission_state.json
    drones = [
        {"id": "drone1", **api_mission_status()},
        {"id": "drone2", **hil_status()}
    ]
    return {"drones": drones}

if __name__ == "__main__":
    ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_ctx.load_cert_chain(certfile="cert.pem", keyfile="key.pem")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, ssl_certfile="cert.pem", ssl_keyfile="key.pem")

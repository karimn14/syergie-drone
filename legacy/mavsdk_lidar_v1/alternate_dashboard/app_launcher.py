# app_launcher.py
# File utama baru untuk menjalankan logika drone DAN server web secara bersamaan.

import asyncio
import logging
import uvicorn
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import threading

# Impor dari proyek Anda
from config import DRONE_CONFIG, setup_logging
from mission_planning import ai_data_loader, route_generator
from mission_execution.flight_supervisor import FlightSupervisor

# Setup logging di awal
setup_logging()
logger = logging.getLogger("DroneSawit")

# --- Wadah untuk Berbagi Data (Shared State) ---
# Dictionary sederhana ini akan diakses oleh FlightSupervisor dan Web Server
# untuk berbagi data secara real-time.
drone_status = {
    "is_connected": False,
    "lidar_distance": -1.0,
    "mission_status": "INITIALIZING",  # Status: "FLYING", "PAUSED_OBSTACLE"
    "lat": 0.0,
    "lon": 0.0,
    "battery_percent": 0
}

# --- Konfigurasi Backend Web (FastAPI) ---
app = FastAPI()
templates = Jinja2Templates(directory="templates") # Pastikan HTML ada di folder 'templates'

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Menyajikan halaman utama dashboard."""
    return templates.TemplateResponse("mission_dashboard.html", {"request": request})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Endpoint WebSocket untuk mengirim update status drone ke frontend."""
    await websocket.accept()
    try:
        while True:
            # Kirim data dari shared state ke frontend setiap 0.5 detik
            await websocket.send_json(drone_status)
            await asyncio.sleep(0.5)
    except Exception:
        logger.info("Koneksi WebSocket ditutup.")

# --- Fungsi Logika Drone ---
def prepare_mission_assets():
    """Fase offline: memuat data dan membuat rencana misi."""
    logger.info("Memulai fase persiapan aset misi...")
    try:
        waypoints = ai_data_loader.load_waypoints(DRONE_CONFIG["AI_PREDICTIONS_FILE"])
        if not waypoints:
            logger.error("Tidak ada waypoints yang dimuat. Misi dibatalkan.")
            return False
        logger.info(f"{len(waypoints)} waypoints berhasil dimuat.")

        route_generator.generate_mission_plan(
            waypoints=waypoints,
            output_file=DRONE_CONFIG["MISSION_PLAN_OUTPUT_FILE"],
            altitude=DRONE_CONFIG["FLIGHT_ALTITUDE"]
        )
        logger.info(f"File rencana misi telah dibuat di: {DRONE_CONFIG['MISSION_PLAN_OUTPUT_FILE']}")
        return True
    except Exception as e:
        logger.critical(f"Gagal mempersiapkan aset misi: {e}", exc_info=True)
        return False

async def run_flight_supervisor():
    """Menjalankan supervisor penerbangan."""
    logger.info("Supervisor penerbangan akan dimulai setelah ENTER...")
    # Menunggu input di terminal sebelum memulai supervisor
    await asyncio.to_thread(input, "Tekan ENTER di terminal untuk memulai Flight Supervisor...")
    
    supervisor = FlightSupervisor(DRONE_CONFIG, drone_status)
    await supervisor.run()

# --- Titik Masuk Utama ---
if __name__ == "__main__":
    # 1. Jalankan persiapan misi (offline)
    if not prepare_mission_assets():
        exit()

    # 2. Siapkan untuk menjalankan supervisor di background thread setelah server start
    supervisor_thread = threading.Thread(target=lambda: asyncio.run(run_flight_supervisor()), daemon=True)

    logger.info("Persiapan selesai. Server web akan dimulai.")
    logger.info("Buka browser dan akses http://<IP_JETSON>:8000")
    logger.info("Setelah itu, kembali ke terminal ini.")
    
    supervisor_thread.start()

    # 3. Jalankan server web (online)
    uvicorn.run(app, host="0.0.0.0", port=8000)

# main.py
# File utama untuk menjalankan seluruh alur kerja: persiapan dan eksekusi.
import asyncio
import logging
from config import DRONE_CONFIG, setup_logging
from mission_planning import ai_data_loader, route_generator
from mission_execution.flight_supervisor import FlightSupervisor

def prepare_mission_assets():
    """
    Menjalankan fase offline: memuat data AI dan membuat file rencana misi.
    """
    logger = logging.getLogger("DroneSawit")
    logger.info("Memulai fase persiapan aset misi...")
    
    try:
        # 1. Memuat waypoints dari data AI
        waypoints = ai_data_loader.load_waypoints(
            DRONE_CONFIG["AI_PREDICTIONS_FILE"]
        )
        if not waypoints:
            logger.error("Tidak ada waypoints yang dimuat. Misi dibatalkan.")
            return False
        logger.info(f"{len(waypoints)} waypoints berhasil dimuat.")

        # 2. Membuat file .plan untuk Pixhawk
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

async def run_flight_mission():
    """
    Menjalankan fase online: menghubungkan ke drone dan memulai pengawasan.
    """
    logger = logging.getLogger("DroneSawit")
    logger.info("Memulai fase eksekusi misi...")
    
    supervisor = FlightSupervisor(DRONE_CONFIG)
    await supervisor.run()

def main():
    """Fungsi utama untuk mengorkestrasi seluruh proses."""
    setup_logging()
    logger = logging.getLogger("DroneSawit")
    
    # --- TAHAP 1: PERSIAPAN (OFFLINE) ---
    if not prepare_mission_assets():
        return # Hentikan jika persiapan gagal

    # --- TAHAP 2: EKSEKUSI (ONLINE) ---
    logger.info("Persiapan selesai. Menunggu untuk memulai eksekusi penerbangan.")
    logger.info("Silakan unggah file .plan ke QGroundControl dan bersiap untuk terbang.")
    input("Tekan ENTER untuk memulai Flight Supervisor...")
    
    asyncio.run(run_flight_mission())

if __name__ == "__main__":
    main()

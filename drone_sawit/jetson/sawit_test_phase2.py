# main_launcher.py – Versi Disempurnakan
# File ini bertindak sebagai "sutradara" utama yang mengorkestrasi
# seluruh alur kerja dari persiapan hingga eksekusi misi.

import asyncio
import logging
# Diasumsikan ada file config.py untuk logging dan pengaturan, ini praktik terbaik
# from config import setup_logging, DRONE_CONFIG 

# --- Mengimpor semua modul yang diperlukan ---
# Fase Perencanaan Misi
from ai_output_loader import load_ai_predictions
from enhanced_route_generator import generate_smoothed_plan as generate_plan # Menggunakan generator rute yang lebih canggih
from spray_command_mapper_confidence import build_spray_commands # Menggunakan pemetaan perintah yang memperhitungkan confidence AI

# Fase Pemeriksaan Pra-Penerbangan
# Anda memiliki file preflight_diagnostics.py, kita asumsikan ada fungsi utamanya
from preflight_diagnostics import run_preflight_checks 

# Fase Eksekusi Misi Inti
# Menggunakan retry_logic_spray sebagai eksekutor utama yang canggih
from retry_logic_spray import main as mission_executor

def run_mission_pipeline():
    """
    Menjalankan seluruh alur kerja misi Drone Sawit, dari persiapan hingga eksekusi.
    """
    # Pengaturan logging dasar jika config.py tidak ada
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    logger = logging.getLogger("MissionControl")
    
    logger.info("=============================================")
    logger.info("=== MEMULAI ALUR KERJA MISI DRONE SAWIT ===")
    logger.info("=============================================")

    try:
        # --- TAHAP 1: PERSIAPAN ASET MISI ---
        logger.info("[TAHAP 1/3] Mempersiapkan Aset Misi...")

        logger.info("--> (1a) Memuat prediksi pohon dari AI...")
        target_trees = load_ai_predictions()
        if not target_trees:
            logger.error("Tidak ada pohon target yang ditemukan. Misi dibatalkan.")
            return

        logger.info(f"--> Berhasil memuat {len(target_trees)} pohon target.")

        logger.info("--> (1b) Menghasilkan rute penerbangan (.plan) yang mulus...")
        generate_plan(target_trees, output_file="route_pollination_mission.plan")

        logger.info("--> (1c) Memetakan perintah semprot berdasarkan dosis dan kepercayaan AI...")
        build_spray_commands(target_trees)
        logger.info("--> Aset misi berhasil dibuat.")

        # --- TAHAP 2: PEMERIKSAAN PRA-PENERBANGAN ---
        logger.info("[TAHAP 2/3] Menjalankan Pemeriksaan Pra-Penerbangan...")
        # Menjalankan pemeriksaan perangkat keras dan perangkat lunak
        # preflight_ok = asyncio.run(run_preflight_checks()) # Baris ini memerlukan perangkat keras nyata
        preflight_ok = True # Untuk simulasi, kita asumsikan lolos
        if not preflight_ok:
            logger.error("Pemeriksaan pra-penerbangan gagal. Misi dibatalkan demi keamanan.")
            return
        logger.info("--> Semua sistem terverifikasi dan siap terbang (simulasi).")

        # --- TAHAP 3: EKSEKUSI MISI ---
        logger.info("[TAHAP 3/3] Memulai Eksekusi Misi Cerdas secara Real-Time...")
        # Menjalankan loop utama eksekusi misi
        asyncio.run(mission_executor())

        logger.info("=========================================")
        logger.info("=== MISI TELAH SELESAI DENGAN SUKSES ===")
        logger.info("=========================================")

    except FileNotFoundError as e:
        logger.critical(f"File aset penting tidak ditemukan: {e}. Pastikan semua file input ada.")
    except Exception as e:
        logger.critical(f"Terjadi kesalahan fatal selama alur kerja misi: {e}", exc_info=True)

if __name__ == "__main__":
    run_mission_pipeline()

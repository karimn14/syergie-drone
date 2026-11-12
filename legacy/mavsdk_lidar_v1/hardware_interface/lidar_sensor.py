# hardware_interface/lidar_sensor.py
import serial
import logging
import time

logger = logging.getLogger("DroneSawit")
ser = None

def init_lidar(port, baud):
    """Membuka koneksi serial ke Lidar."""
    global ser
    try:
        ser = serial.Serial(port, baud, timeout=1)
        # Beri waktu sejenak untuk port serial stabil
        time.sleep(2)
        logger.info(f"Lidar terhubung di port {port}")
        return True
    except serial.SerialException as e:
        logger.critical(f"Gagal terhubung ke Lidar di port {port}: {e}")
        ser = None
        return False

def get_distance():
    """
    Membaca dan mem-parsing data dari Lidar TF-Luna.
    Mengembalikan jarak dalam meter atau None jika gagal.
    """
    global ser
    if not ser or not ser.is_open:
        logger.warning("Koneksi Lidar tidak tersedia.")
        return None

    try:
        # TF-Luna biasanya mengirim data dalam format teks sederhana: "XXX.XX\\r\\n" (jarak dalam m)
        # Atau bisa juga dalam format biner, pastikan sensor Anda diatur ke mode output yang sesuai.
        # Kode ini mengasumsikan output teks sederhana.
        line = ser.readline().decode('utf-8').strip()
        if line:
            # Mengubah dari cm ke m jika sensor outputnya cm
            # return float(line) / 100.0 
            
            # Jika output sudah dalam m
            return float(line)
    except (ValueError, TypeError, UnicodeDecodeError) as e:
        # Sering terjadi saat startup atau jika ada noise
        logger.debug(f"Gagal mem-parsing data Lidar: {e}")
        return None
    except serial.SerialException as e:
        logger.error(f"Error pada port serial Lidar: {e}")
        ser.close()
        ser = None
        return None
    return None


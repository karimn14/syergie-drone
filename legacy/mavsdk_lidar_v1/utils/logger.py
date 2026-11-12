# /drone_otonom_v1/utils/logger.py
import logging
import sys

def setup_logging(log_file="mission_log.log", level=logging.INFO):
    """
    Mengkonfigurasi dan mengembalikan sebuah logger terpusat.
    Semua pesan akan dicetak ke terminal dan disimpan ke file.
    """
    # Memberi nama logger utama untuk seluruh aplikasi
    logger = logging.getLogger("DroneSawit")
    
    # Mencegah logger di-setting ulang jika fungsi ini dipanggil berkali-kali
    if logger.hasHandlers():
        logger.handlers.clear()
        
    logger.setLevel(level)
    
    # Menentukan format pesan log
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - [%(name)s:%(funcName)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler untuk menyimpan log ke file
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Handler untuk mencetak log ke terminal
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    
    return logger
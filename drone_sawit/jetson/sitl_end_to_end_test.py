# sitl_end_to_end_test.py – Simulate full Jetson-Arduino-Pixhawk stack (SITL)
import subprocess
import time
from logger import setup_logger

def run_sitl():
    logger = setup_logger("sitl_test")
    try:
        logger.info("Starting PX4 SITL (Software In The Loop)...")
        px4_proc = subprocess.Popen(["px4", "--no-ui"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(5)
        logger.info("Running main pipeline in SITL mode...")
        result = subprocess.run(["python", "main_launcher.py"], cwd="jetson", capture_output=True)
        logger.info(result.stdout.decode())
        logger.info(result.stderr.decode())
    finally:
        px4_proc.terminate()
        logger.info("SITL test complete.")

if __name__ == "__main__":
    run_sitl()

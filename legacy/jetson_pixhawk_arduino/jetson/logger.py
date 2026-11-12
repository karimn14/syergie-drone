# logger.py – Central logging utility for Drone Sawit
import logging
import sys

def setup_logger(name="drone_sawit", log_file="drone_sawit.log", level=logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    fh = logging.FileHandler(log_file)
    sh = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
    fh.setFormatter(formatter)
    sh.setFormatter(formatter)
    logger.addHandler(fh)
    logger.addHandler(sh)
    logger.propagate = False
    return logger

# Usage example:
# logger = setup_logger()
# logger.info("Test log")

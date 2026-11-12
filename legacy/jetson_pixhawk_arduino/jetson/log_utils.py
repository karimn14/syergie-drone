"""
log_utils.py
Advanced logging and log rotation for Drone Sawit.
"""
import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logger(name, log_file='mission.log', level=logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not logger.handlers:
        handler = RotatingFileHandler(log_file, maxBytes=1024*1024, backupCount=5)
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger

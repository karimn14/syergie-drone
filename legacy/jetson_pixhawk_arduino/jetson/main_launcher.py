# main_launcher.py – Orchestrates the full pipeline
from ai_output_loader import load_ai_predictions
from route_generator import generate_plan
from spray_command_mapper import build_spray_commands
from px4_spray_sync import main as px4_sync_main
import asyncio

from logger import setup_logger

def main():
    logger = setup_logger("main_launcher")
    try:
        logger.info("[1/4] Loading AI-predicted trees...")
        trees = load_ai_predictions()
        logger.info(f"Loaded {len(trees)} trees.")
        logger.info("[2/4] Generating PX4 .plan route...")
        generate_plan(trees)
        logger.info("[3/4] Mapping spray commands...")
        build_spray_commands(trees)
        logger.info("[4/4] Starting real-time PX4-GPS to sprayer sync...")
        asyncio.run(px4_sync_main())
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)

if __name__ == "__main__":
    main()

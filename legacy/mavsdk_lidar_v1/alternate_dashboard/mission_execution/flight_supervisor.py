# mission_execution/flight_supervisor.py
import asyncio
from mavsdk import System
from mavsdk.action import ActionError
import logging
from hardware_interface import lidar_sensor

logger = logging.getLogger("DroneSawit")

class FlightSupervisor:
    """
    Mengawasi penerbangan, memantau sensor, dan meng-update shared state
    untuk dibaca oleh GUI.
    """
    def __init__(self, config, shared_state):
        """
        Menerima config dan shared_state dictionary.
        """
        self.config = config
        self.drone = System() # Hapus parameter server address, akan connect ke default
        self.shared_state = shared_state # Simpan referensi ke shared state

    async def initialize(self):
        """Menghubungkan ke drone dan Lidar."""
        logger.info("Menghubungkan ke mavsdk_server...")
        await self.drone.connect() # Connect ke server default (localhost:50051)

        async for state in self.drone.core.connection_state():
            if state.is_connected:
                logger.info("Drone terhubung!")
                self.shared_state["is_connected"] = True # Update state
                lidar_sensor.init_lidar(self.config['LIDAR_PORT'], self.config['LIDAR_BAUD'])
                return True
        logger.error("Gagal terhubung ke drone.")
        self.shared_state["is_connected"] = False # Update state
        return False

    async def monitor_telemetry(self):
        """Memantau telemetri drone dan update shared state."""
        async for position in self.drone.telemetry.position():
            self.shared_state["lat"] = position.latitude_deg
            self.shared_state["lon"] = position.longitude_deg
        
        async for battery in self.drone.telemetry.battery():
            self.shared_state["battery_percent"] = round(battery.remaining_percent * 100)

    async def monitor_safety(self):
        """Loop utama untuk memantau Lidar dan mengambil tindakan."""
        self.shared_state["mission_status"] = "FLYING" # Update state
        while True:
            distance = lidar_sensor.get_distance()
            self.shared_state["lidar_distance"] = distance # Update state
            
            is_paused = self.shared_state["mission_status"] == "PAUSED_OBSTACLE"

            if distance is not None and distance < self.config["OBSTACLE_THRESHOLD_M"]:
                if not is_paused:
                    logger.warning(f"Rintangan terdeteksi pada {distance:.2f}m! MENGHENTIKAN DRONE.")
                    self.shared_state["mission_status"] = "PAUSED_OBSTACLE" # Update state
                    try:
                        await self.drone.action.hold()
                    except ActionError as e:
                        logger.error(f"Gagal mengirim perintah HOLD: {e}")
            else:
                if is_paused:
                    logger.info("Area kembali aman. Melanjutkan misi.")
                    self.shared_state["mission_status"] = "FLYING" # Update state
                    try:
                        await self.drone.action.arm()
                    except ActionError as e:
                        logger.error(f"Gagal melanjutkan misi: {e}")
            
            await asyncio.sleep(0.2)

    async def run(self):
        """Memulai semua tugas supervisor secara bersamaan."""
        if not await self.initiali  ze():
            return
        
        logger.info("Memulai pengawasan telemetri dan keselamatan penerbangan...")
        
        # Jalankan monitor telemetri dan monitor keselamatan secara konkuren
        await asyncio.gather(
            self.monitor_telemetry(),
            self.monitor_safety()
        )
        logger.info("Supervisor penerbangan dihentikan.")
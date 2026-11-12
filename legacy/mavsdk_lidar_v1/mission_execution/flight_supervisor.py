# mission_execution/flight_supervisor.py
import asyncio
from mavsdk import System
from mavsdk.action import ActionError
import logging
from hardware_interface import lidar_sensor

logger = logging.getLogger("DroneSawit")

class FlightSupervisor:
    """
    Kelas ini bertanggung jawab untuk mengawasi penerbangan
    dan melakukan intervensi jika ada rintangan.
    """
    def __init__(self, config):
        self.config = config
        self.drone = System(mavsdk_server_address='localhost', port=50051)
        self.mission_paused = False

    async def initialize(self):
        """Menghubungkan ke drone dan Lidar."""
        logger.info(f"Menghubungkan ke drone di {self.config['PX4_CONNECTION_STRING']}...")
        #await self.drone.connect(system_address=self.config['PX4_CONNECTION_STRING'])
        await self.drone.connect()

        async for state in self.drone.core.connection_state():
            if state.is_connected:
                logger.info("Drone terhubung!")
                # Inisialisasi Lidar setelah drone terhubung
                lidar_sensor.init_lidar(self.config['LIDAR_PORT'], self.config['LIDAR_BAUD'])
                return True
        logger.error("Gagal terhubung ke drone.")
        return False

    async def monitor_safety(self):
        """Loop utama untuk memantau Lidar dan mengambil tindakan."""
        while True:
            distance = lidar_sensor.get_distance()
            
            if distance is not None and distance < self.config["OBSTACLE_THRESHOLD_M"]:
                if not self.mission_paused:
                    logger.warning(f"Rintangan terdeteksi pada {distance:.2f}m! MENGHENTIKAN DRONE.")
                    try:
                        await self.drone.action.hold()
                        self.mission_paused = True
                    except ActionError as e:
                        logger.error(f"Gagal mengirim perintah HOLD: {e}")
            else:
                if self.mission_paused:
                    logger.info("Area kembali aman. Melanjutkan misi.")
                    try:
                        # Menggunakan arm() seringkali cara yang efektif untuk 'membangunkan'
                        # drone dari mode HOLD dalam beberapa kasus.
                        await self.drone.action.arm()
                        # Atau coba lanjutkan misi jika didukung
                        # await self.dr one.mission.resume_mission()
                        self.mission_paused = False
                    except ActionError as e:
                        logger.error(f"Gagal melanjutkan misi: {e}")
            
            await asyncio.sleep(0.2) # Frekuensi pengecekan 5Hz

    async def run(self):
        """Memulai supervisor."""
        if not await self.initialize():
            return
        
        logger.info("Memulai pengawasan keselamatan penerbangan...")
        await self.monitor_safety()


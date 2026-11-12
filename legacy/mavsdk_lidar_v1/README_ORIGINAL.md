# Drone Otonom v1: Navigasi & Obstacle Avoidance

## Tujuan Proyek

Versi pertama sistem drone otonom ini bertujuan untuk:
- Terbang mengikuti rute yang telah ditentukan secara mandiri.
- Secara aktif dan otomatis menghindari rintangan yang terdeteksi oleh sensor Lidar.

---

## Alur Kerja Sistem

### 1. Persiapan Misi (Offline, di Darat)

1. **Jalankan Program**
   - Di terminal Jetson:  
     ```bash
     python main.py
     ```

2. **main.py**
   - Membaca pengaturan dari `config.py`.
   - Memanggil `prepare_mission_assets()`.

3. **prepare_mission_assets()**
   - Memanggil `ai_data_loader.py` untuk membaca `predicted_trees.geojson` dan mengubahnya menjadi daftar waypoint.
   - Memberikan waypoint ke `route_generator.py` untuk membuat file `mission_data/route_mission.plan` (rute penerbangan untuk Pixhawk).

---

### 2. Eksekusi Misi (Online, Saat Terbang)

1. **Unggah Misi ke Drone**
   - Hubungkan Pixhawk ke laptop dengan QGroundControl.
   - Di QGroundControl, buka menu **Plan** dan unggah file `mission_data/route_mission.plan`.

2. **main.py Melanjutkan**
   - Membuat instance `FlightSupervisor` (`mission_execution/flight_supervisor.py`).
   - Memanggil metode `run()`.

3. **flight_supervisor.py (Jantung Operasi)**
   - **Inisialisasi:** Terhubung ke Pixhawk via MAVSDK.
   - **Loop Pemantauan:**  
     Loop berjalan selama drone terbang (`async for is_in_air in self.drone.telemetry.in_air()`).
     - **Setiap Iterasi:**
       - Memanggil `check_for_obstacles()` dari `hardware_interface/lidar_sensor.py`.
       - Membaca jarak dari Lidar TF-Luna.
       - **Logika Pengambilan Keputusan:**
         - Jika jarak < ambang batas (misal 2.5m) & drone tidak HOLD:  
           Kirim perintah `await self.drone.action.hold()`.
         - Jika jarak >= ambang batas & drone sedang HOLD:  
           Kirim perintah `await self.drone.action.arm()` (atau resume_mission).
         - Jika tidak ada rintangan: lanjutkan pemantauan.

---

## Panduan Operasional

### 1. Persiapan Perangkat Keras

**Komponen Wajib:**
- **Drone:** Frame, motor, ESC, baling-baling.
- **Flight Controller:** Pixhawk (atau kompatibel).
- **Komputer Pendamping:** NVIDIA Jetson Nano/Xavier.
- **Sensor Jarak:** 1x Lidar TF-Luna (atau kompatibel).
- **Baterai LiPo** untuk drone.
- **Power bank/UBEC** untuk Jetson.
- **Kabel:** Micro USB (Jetson-Lidar), Serial-to-USB FTDI (Jetson-Pixhawk).
- **Perangkat Tambahan:** Laptop (QGroundControl), remote control (RC).

**Diagram Koneksi:**
- **Jetson ↔ Pixhawk:**  
  Serial (TX, RX, GND) FTDI ke TELEM2 Pixhawk, USB ke Jetson.
  - Pastikan parameter `MAV_2_MODE` di Pixhawk = "Onboard".
- **Jetson ↔ Lidar:**  
  Lidar TF-Luna ke USB Jetson.
- **Daya Jetson:**  
  5V dari power bank/UBEC ke Jetson (bukan dari USB laptop).

---

### 2. Persiapan Fisik & Pra-Penerbangan

- Pastikan semua komponen terpasang kencang.
- Lidar menghadap ke depan.
- Baterai LiPo terisi penuh.
- Baling-baling terpasang benar.
- Letakkan drone di permukaan datar, jauh dari halangan.
- Nyalakan remote control, lalu drone (baterai LiPo).
- Tunggu Jetson booting (1-2 menit).
- (Opsional) Hubungkan laptop ke Pixhawk via QGroundControl.
- Tunggu GPS lock.

---

### 3. Menjalankan Sistem Program

**Langkah 1: SSH ke Jetson**
bash
ssh username_jetson@alamat_ip_jetson

**Langkah 2: Aktifkan Virtual Environment**
bash
cd /path/to/drone_otonom_v1/
source venv/bin/activate

**Langkah 3: Jalankan Program Utama**
python main.py

Output:
Waypoint dimuat dari .geojson.
File .plan dibuat.
Pesan: Persiapan selesai, unggah .plan ke QGroundControl.
**Langkah 4: Unggah Rencana Misi**
Di QGroundControl:
Menu Plan → "Load from File" → pilih route_mission.plan → Upload.

**Langkah 5: Mulai Flight Supervisor**
Di terminal Jetson: Tekan ENTER saat diminta.
Output:
Fase eksekusi misi dimulai.
Koneksi ke drone & Lidar.
Pengawasan keselamatan aktif.

**Langkah 6: Mulai Misi Otonom** 
Di QGroundControl/RC: Start Mission.
Drone akan takeoff, mengikuti waypoint.
- Jika ada rintangan:
    Log: Rintangan terdeteksi pada X m! MENGHENTIKAN DRONE. Drone HOLD.
- Jika aman:
    Log: Area kembali aman. Melanjutkan misi.

**Langkah 7: Take Over & Landing**
Siap ambil alih manual via RC (mode Position Hold/RTL).
Setelah misi selesai, drone akan melakukan aksi akhir (misal RTL).

**Catatan**
Selalu cek keamanan fisik sebelum terbang.
Pastikan parameter Pixhawk sudah benar.
Siapkan RC untuk intervensi manual kapan saja.
Ikuti urutan langkah di atas untuk operasi yang aman dan terstruktur.
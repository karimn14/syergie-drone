# Jalur simulasi ROS 2

Folder ini adalah jalur implementasi aktif. Target lingkungan: Ubuntu 22.04 + ROS 2 Humble + Gazebo Fortress. ROS 2 Humble dipasangkan secara resmi dengan Gazebo Fortress; gunakan paket `ros-humble-ros-gz` dan hindari instruksi Harmonic dari rancangan lama. Lihat [panduan pairing Gazebo/ROS](https://gazebosim.org/docs/fortress/ros_installation/) dan [instalasi ROS 2 Humble untuk Ubuntu](https://docs.ros.org/en/humble/Installation/Ubuntu-Install-Debians.html).

## Status saat ini

`src/` hanya berisi placeholder. Belum ada paket yang dapat dibangun dengan `colcon`, world kebun, model drone, launch file, detector, mission manager, safety supervisor, atau adapter SITL. Jadi saat ini belum ada perintah launch simulasi yang bisa dijalankan.

Jangan menyalin node dari [`legacy/ros1_pollination_demo/`](../legacy/ros1_pollination_demo/) langsung ke sini. Node lama memakai `rospy`, custom message ROS 1, launch XML, dan deteksi bola kuning.

## Persiapan Ubuntu 22.04

Jalankan perintah ini dari terminal Ubuntu, bukan PowerShell. ROS 2 Humble harus sudah terpasang dari repositori ROS resmi.

```bash
sudo apt update
sudo apt install -y ros-dev-tools python3-colcon-common-extensions ros-humble-ros-gz
source /opt/ros/humble/setup.bash
echo "$ROS_DISTRO"
```

Baris terakhir harus menampilkan `humble`. Jika `rosdep` belum pernah diinisialisasi pada mesin tersebut, lakukan satu kali:

```bash
sudo rosdep init
rosdep update
```

Masuk ke workspace dan lihat apakah paket sudah dibuat:

```bash
cd ~/syergie-drone/ros2_ws
find src -name package.xml -print
```

> Saat ini perintah `find` belum menghasilkan paket. **Jangan jalankan `colcon build` dulu**—belum ada package manifest untuk dibangun.

Setelah paket pertama dibuat, alur build berikut yang dipakai:

```bash
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
```

## Arsitektur sasaran

```text
kamera dan range simulator
          │
          ▼
     perception ── deteksi + pose ──► target manager
                                            │ ID pohon berikutnya
                                            ▼
range/obstacle ──► safety supervisor ──► mission manager
                                            │
                              ┌─────────────┴─────────────┐
                              ▼                           ▼
                       flight adapter              spray manager
                              │                  event simulasi saja
                       MAVROS2/MAVLink
                              │
                        autopilot SITL
```

Flight controller tetap menstabilkan drone dan menjalankan failsafe. ROS 2 mengatur tujuan misi, bukan motor secara langsung. Spray manager awal hanya menerbitkan event simulasi; ia tidak mengendalikan servo, relay, ESP32, atau perangkat payload fisik.

## Paket yang akan dibuat

Paket berikut adalah rancangan, belum ada di `src/`:

| Paket | Tanggung jawab |
|---|---|
| `syergie_interfaces` | Interface target, kondisi kendaraan, status safety, dan event perlakuan |
| `syergie_sim` | World kebun, model drone, kamera/range simulator, dan bridge Gazebo–ROS |
| `syergie_perception` | Deteksi target dari gambar simulasi dan asosiasi dengan pose |
| `syergie_mission` | Pemilihan pohon berikutnya dan state machine misi |
| `syergie_safety` | Obstacle, watchdog sensor/pose/telemetri, dan spray interlock |
| `syergie_bringup` | Launch file, konfigurasi, dan skenario simulasi |

## Rencana implementasi dan kriteria selesai

### Tahap 1 — Workspace dan interface

Buat paket interface dan paket bringup minimal. Definisikan kontrak untuk target pohon, pose kendaraan, status obstacle, status misi, izin perlakuan, dan event perlakuan. Build harus berhasil pada Ubuntu 22.04 dengan Humble.

### Tahap 2 — World dan kendaraan simulasi

Buat world kebun kecil dengan beberapa baris pohon, model quadrotor sederhana, kamera, dan range sensor. Tampilkan gambar, pose, frame TF, serta range dengan timestamp yang konsisten. Hubungkan ke satu autopilot SITL setelah simulasi dasar stabil.

### Tahap 3 — Persepsi dan target berikutnya

Mulai dari gambar sintetis/rosbag. Deteksi target harus memberi hasil bertimestamp; target manager mencatat ID pohon dengan status `unvisited`, `selected`, `visited`, atau `skipped`. Setelah satu pohon selesai, sistem memilih ID berikutnya dan tidak mengulang target.

### Tahap 4 — State machine misi

Implementasikan `IDLE → TAKEOFF → TRANSIT → APPROACH → VERIFY → TREAT_SIMULATED → RETREAT → NEXT_TARGET → RETURN → LAND`, dengan `HOLD`, `ABORT`, dan `FAILSAFE` yang bisa dipicu kapan saja. Kehilangan target saat approach tidak boleh menghasilkan event perlakuan.

### Tahap 5 — Obstacle dan interlock

Obstacle supervisor harus mengalahkan perintah planner. Sensor basi, pose hilang, koneksi autopilot putus, atau abort harus menolak event perlakuan dengan alasan tercatat. Perlakuan tetap simulasi sampai mekanisme, dosis, dan emergency stop diuji terpisah.

### Tahap 6 — Skenario berulang

Sediakan konfigurasi dan rosbag untuk: misi beberapa pohon, target hilang, obstacle saat transit/approach, kamera/range/pose putus, baterai rendah, abort, RTL, dan landing. Metrik minimal: urutan/kunjungan pohon, event perlakuan yang diizinkan/ditolak, jarak obstacle minimum, dan alasan recovery.

## Pekerjaan pertama

Setelah ROS 2 Humble dan Gazebo Fortress terpasang, buat `syergie_interfaces` dan `syergie_sim` terlebih dahulu. Target hasil pertama adalah `colcon build` berhasil dan sebuah world sederhana menampilkan drone serta beberapa pohon dengan topic kamera, pose, dan range yang bisa diperiksa. Jangan mulai dari model AI atau kontrol payload.

## Prinsip keputusan

- Planner global memilih urutan pohon dari peta atau daftar target; behavior lokal menangani approach dan avoidance. Pencarian tanpa peta hanya fallback lokal.
- Ukuran bounding box bukan ukuran jarak atau dosis tanpa kalibrasi kamera dan geometri target.
- Threshold lama di dokumen eksperimen bukan parameter aman dan tidak dipakai tanpa uji simulasi.
- F450 tidak dianggap mampu membawa Jetson, sensor, dan dispenser. Model simulasi awal mewakili dinamika secara abstrak; kapasitas angkat harus diukur terpisah sebelum uji fisik.
- Skenario simulasi lulus bukan izin untuk uji terbang.

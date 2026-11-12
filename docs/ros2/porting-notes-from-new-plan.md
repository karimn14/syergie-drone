# Temuan yang dipakai dari `new_plan_2_9`

`new_plan_2_9` tidak saya buang. Seluruh folder dipertahankan di [`legacy/ros1_pollination_demo/`](../../legacy/ros1_pollination_demo/) karena memuat hasil pemikiran desain dan riwayat percobaan yang relevan. Catatan ini memisahkan ide yang layak dibawa ke ROS 2 dari instruksi lama yang tidak cocok dijalankan sekarang.

## Yang berharga untuk rancangan ROS 2

Dokumen `NAVIGATION_ARCHITECTURE.md` menyusun navigasi sebagai state machine, bukan kumpulan callback terpisah. Ia menguraikan urutan preflight, takeoff, scan/acquire, approach, perlakuan, retreat, cari target berikutnya, dan return/land. Di dalamnya juga ada anti-revisit, timeout, recovery ladder, risk register, serta skenario kehilangan kamera, optical flow, baterai, dan heartbeat. Struktur ini cocok dijadikan sumber kebutuhan dan skenario simulasi.

`ARCHITECTURE_REVIEW.md` menekankan pemisahan posisi/stabilisasi oleh flight controller dari persepsi dan pemilihan target. `design_review.md` merekam perubahan usulan dispenser: kontrol awal ESP32/relay berubah menjadi percobaan perintah servo Pixhawk karena timing dan sinkronisasi; firmware ESP32 tetap ada sebagai catatan opsi lama. Konflik ini menunjukkan kontrol dispenser belum diputuskan dan belum dibuktikan.

`ADVANCED_SENSOR_FEASIBILITY.md` dan bagian lanjutan navigation architecture membandingkan optical flow, rangefinder, kamera depth, LiDAR, marker, UWB, serta VIO. Ini bahan daftar sensor untuk simulator dan eksperimen berikutnya, bukan daftar belanja: asumsi berat, harga, FPS Jetson, range, serta akurasi di dalamnya belum diukur pada drone ini.

## Pemetaan ke ROS 2 yang dituju

| Temuan lama | Adaptasi simulasi ROS 2 |
|---|---|
| State machine dengan batas waktu dan jalur recovery | `mission_manager` dengan transisi yang tercatat dan keadaan `hold`, `abort`, `return`, `land` |
| Daftar pohon yang sudah dikunjungi | `target_manager` menyimpan ID/status pohon dan memilih pohon berikutnya secara deterministik |
| Scan dan pendekatan berdasarkan deteksi | `perception` menerbitkan deteksi bertimestamp; `mission_manager` menguji acquire/approach dari gambar dan pose simulator |
| Obstacle dapat memotong alur target | `safety_supervisor` berprioritas di atas planner dan membatalkan tujuan serta event perlakuan saat obstacle/data tidak valid |
| Spray pulse dengan urutan fan/feeder | `spray_manager` hanya mengeluarkan event simulasi dan alasan allow/deny; belum mengirim perintah fisik |
| Kehilangan kamera/flow/heartbeat | Skenario SITL/rosbag yang menyuntikkan data basi, dropout, dan disconnect lalu mengukur respons hold/abort |

## Keputusan navigasi yang perlu disesuaikan

Dokumen 2026 mengusulkan behavior-based navigation tanpa peta global karena keterbatasan Jetson Nano, GPS-denied, dan dead-reckoning optical flow. Tujuan proyek sekarang juga mencakup mengetahui pohon berikutnya. Rancangan yang lebih cocok adalah hierarki: **planner memilih urutan pohon dari peta/row atau daftar target; local behavior melakukan approach, verifikasi, dan avoidance di sekitar pohon**. Jika pose/peta tidak tersedia, pencarian lokal behavior-based bisa menjadi mode fallback, bukan pengganti route planner.

Jangan memakai ukuran bounding box sebagai jarak atau dosis tanpa kalibrasi dan geometri target. Jangan menganggap optical-flow odometry akurat untuk seluruh kebun; reset lokal dan drift hanya hipotesis untuk diuji pada simulator dan data. Heuristik `dark_ratio` tidak cukup mendeteksi kabel atau cabang tipis. Threshold 0,3 m, 0,8 m, baterai 15/25%, FPS, dan durasi spray yang tertulis di dokumen adalah angka konseptual lama, bukan parameter aman.

## Yang tidak boleh diperlakukan sebagai implementasi aktif

- `RECOVERY_CHECKPOINT.md` menyatakan ROS Melodic, Python 2, dan Jetson Ubuntu 18 berhasil dipasang, lalu menyuruh mulai dari tes kamera. Ia tidak melaporkan paket ROS 2 atau keberhasilan deteksi sawit.
- `MASTER_EXECUTION_GUIDE.md` dan `ACTION_PLAN_SURVIVAL.md` berisi perintah Catkin/Melodic, Python 2, dan setup Jetson. Jangan menjalankan instruksi itu pada Ubuntu 22.04/Humble.
- `ros_nodes/scripts/detector_node.py` dan `src/hil_test.py` mendeteksi bola kuning dengan HSV; data `Detection` belum berarti deteksi pohon/bunga.
- `spray_logic_node.py` memanggil `DO_SET_SERVO` ke Pixhawk. HIL standalone memiliki stub MAVLink tetapi juga implementasi GPIO/relay. Keduanya bukan node ROS 2 yang aman untuk SITL/hardware.
- `esp32/sprayer_controller.ino`, diagram, dan dokumen Option A/Option B berbeda-beda soal siapa yang mengendalikan payload. Belum ada keputusan hardware yang tervalidasi.
- Pseudocode menggunakan optical flow, rangefinder, dark-ratio, dan beberapa angka baterai/range seolah tersedia. Sensor-sensor itu belum dipasang atau dibuktikan di airframe yang disebut.

## Skenario simulasi yang langsung diturunkan

1. Kebun sintetis dengan beberapa baris pohon; target pertama selesai dan sistem memilih ID pohon berikutnya tanpa mengulang target.
2. Target hilang saat acquire/approach; tidak ada event spray, kendaraan berhenti/beralih ke keadaan pencarian yang ditetapkan.
3. Obstacle muncul saat transit dan saat approach; safety supervisor mengalahkan perintah planner dan event perlakuan dibatalkan.
4. Kamera, pose/optical flow, range, atau koneksi autopilot menjadi basi/putus; log harus menyebut penyebab deny/recovery.
5. Misi mencapai batas baterai/waktu/jumlah target; sistem melakukan return dan land SITL sesuai skenario.
6. Event dispenser simulasi hanya diterbitkan saat target terverifikasi, posisi/kecepatan valid, sensor tidak basi, dan state misi mengizinkan.

Belum ada paket yang menjalankan skenario tersebut. Implementasi berikutnya perlu membuat paket ROS 2 Humble di `ros2_ws/src` dan membangun skenario satu per satu.

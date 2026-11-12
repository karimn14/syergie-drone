# Status dan audit proyek

Dokumen ini mencatat apa yang benar-benar tersedia di workspace dan apa yang masih berupa rancangan. Ia melengkapi [README utama](../README.md) dan [panduan workspace ROS 2](../ros2_ws/README.md).

## Tujuan akhir

Drone diharapkan mengenali target pohon sawit, memilih pohon berikutnya, bernavigasi sambil menghindari rintangan, lalu mensimulasikan perlakuan serbuk hanya ketika kondisi aman. Arsitektur akhir harus memisahkan planner, persepsi, mission state machine, safety supervisor, dan adapter flight controller.

Jenis target, metode dosis, bentuk dispenser, airframe, serta data deteksi sawit yang akan dipakai belum diputuskan atau divalidasi.

## Kondisi implementasi

| Komponen | Kondisi saat ini |
|---|---|
| ROS 2 Humble | Belum ada paket di `ros2_ws/src/`; belum bisa dibangun dengan `colcon` |
| Simulator | Belum ada world kebun, model drone, kamera/range sensor simulasi, atau launch terpadu |
| Autopilot SITL | Belum ada adapter MAVROS2/MAVLink yang terhubung ke simulator |
| Persepsi | Belum ada detector sawit/bunga yang dijalankan dari stream simulasi |
| Pemilihan target | Belum ada target manager yang menyimpan ID pohon dan status kunjungan |
| Hindar rintangan | Baru ada usulan algoritma dan prototype LiDAR; belum diuji di SITL |
| Perlakuan serbuk | Belum ada aktuator/dosis tervalidasi; hanya boleh berupa event simulasi |
| Hardware nyata | Jetson Nano dan kamera belum diuji terpasang; F450 pernah terlalu berat dan motor cepat panas |

Tidak ada komponen yang saat ini dapat disebut siap terbang.

## Hasil membaca progres lama

### `new_plan_2_9`

Seluruh materi dipertahankan di [`legacy/ros1_pollination_demo/`](../legacy/ros1_pollination_demo/). Dokumen `NAVIGATION_ARCHITECTURE.md` mengusulkan state machine, pemilihan target yang tidak berulang, search/approach/retreat, dan recovery ladder. `ARCHITECTURE_REVIEW.md`, `ADVANCED_SENSOR_FEASIBILITY.md`, serta `design_review.md` merekam asumsi sensor dan beberapa rancangan dispenser.

Kode dan instruksinya adalah ROS Melodic/Python 2, bukan ROS 2. Detector HSV mencari bola kuning, bukan pohon atau bunga sawit. Recovery checkpoint menyebut setup kamera sebagai langkah berikutnya; tidak ada bukti di sana bahwa deteksi sawit, HIL, atau autonomous flight berhasil. Gunakan [catatan porting](./ros2/porting-notes-from-new-plan.md), bukan perintah setup lama.

### Stack Jetson/Pixhawk dan MAVSDK

`legacy/jetson_pixhawk_arduino/` berisi banyak skrip dan dokumen dari rancangan yang berbeda. Sejumlah nama modul menggambarkan fitur yang direncanakan, bukan integrasi yang sudah selesai. `legacy/mavsdk_lidar_v1/` adalah prototype terpisah; lognya mencatat tiga waypoint contoh berhasil dimuat pada 10 September 2025, kemudian LiDAR berulang kali tidak terhubung. Itu bukan bukti obstacle avoidance atau autonomous flight.

### Planner dan hardware

`legacy/palm_planner/` adalah aplikasi Flask/React untuk eksperimen peta satelit. Aplikasi dapat memakai data dummy; hasil dummy bukan deteksi. Ia belum terhubung ke kamera drone atau ROS 2.

Semua 109 file CAD `mekanik` dan 82 file CAD Tarot dipindahkan ke `hardware/cad/`, termasuk model lama dan ZIP asli. Raw ZIP tetap tersimpan lokal; CAD hasil ekstrak tersedia di struktur yang sama. Sketch optical-flow dipindahkan ke `hardware/firmware/optical_flow/` dan belum menjadi driver ROS 2.

## Batas pemakaian komponen lama

- Jangan jalankan `ros1_pollination_demo` sebagai ROS 2 atau kendalikan servo dari node spray lamanya.
- Supervisor MAVSDK lama mencoba `arm()` setelah `hold()` dan mengasumsikan format teks untuk data LiDAR; jangan hubungkan ke autopilot nyata.
- Angka threshold jarak, ukuran bounding box, dosis, baterai, waktu, dan performa sensor dalam dokumen lama adalah asumsi rancangan, bukan parameter aman.
- Simpan semua output perlakuan sebagai event simulasi. Jangan aktifkan perangkat fisik sebelum kontrol dosis, interlock, emergency stop, dan pengujian bench dirancang.

## Urutan pekerjaan berikutnya

1. Siapkan lingkungan Humble/Fortress sesuai [`ros2_ws/README.md`](../ros2_ws/README.md).
2. Buat paket interface dan bringup ROS 2, lalu pastikan satu paket contoh dapat dibangun.
3. Buat world kebun sintetis dan drone sederhana dengan kamera, pose, dan range yang memiliki frame/timestamp benar.
4. Buat peta target ber-ID, target manager, dan uji pemilihan pohon berikutnya tanpa kunjungan ganda.
5. Tambahkan perception, mission state machine, safety supervisor, dan interlock event perlakuan simulasi.
6. Tambahkan SITL dan skenario gagal: obstacle, target hilang, sensor basi/putus, abort, RTL, dan landing.

Selesaikan satu tahap dan rekam hasilnya sebelum memulai tahap berikutnya. Lulus simulasi tidak membuktikan kapasitas angkat, waktu baterai, dosis, atau keselamatan hardware.

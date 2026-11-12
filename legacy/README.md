# Prototipe lama

Kode di folder ini adalah beberapa eksperimen yang berkembang sendiri-sendiri. Tidak ada integrasi build atau uji end-to-end antar-subproyek. Perlakukan sebagai bahan referensi, bukan software siap penerbangan.

| Folder | Isi | Status |
|---|---|---|
| `ros1_pollination_demo/` | Detector HSV bola kuning, custom message ROS 1, logika servo MAVROS, dokumen sprint | ROS 1, bukan deteksi sawit dan belum dipindahkan ke ROS 2 |
| `jetson_pixhawk_arduino/` | Banyak skrip Jetson/Pixhawk, Arduino, konfigurasi, dan dokumen deployment | Prototype campuran; beberapa modul adalah stub/rencana dan jalur perangkat belum tervalidasi |
| `mavsdk_lidar_v1/` | Generator misi QGC, MAVSDK, pembacaan LiDAR serial, supervisor, dan dashboard FastAPI alternatif | Kode lama; supervisor memakai `arm()` setelah hold dan parser LiDAR mengasumsikan format teks. Varian dashboard di `alternate_dashboard/` belum terintegrasi |
| `palm_planner/` | Flask/React untuk peta satelit, deteksi model/Roboflow, data contoh | Aplikasi mandiri; memiliki dummy fallback, bukan pipeline kamera atau node ROS 2 |
| `sawit_test_phase1/` | Skrip pembuat rute, mapper dosis, contoh GeoJSON/QGC | Eksperimen offline; bukan kontroler penerbangan |

Jangan menghubungkan output prototype ini langsung ke motor atau dispenser. Porting ke ROS 2 perlu adapter, interface, validasi data, safety supervisor, dan skenario SITL yang terpisah.

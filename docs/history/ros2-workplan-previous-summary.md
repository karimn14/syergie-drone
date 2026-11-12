# Jalur ROS 2 Humble

Folder ini adalah lokasi dokumentasi dan implementasi ROS 2 yang baru. Tujuan pertama adalah membuat simulasi yang bisa diulang di Ubuntu 22.04; integrasi perangkat fisik belum menjadi target.

## Status dokumen dan kode

`new.md` adalah catatan rancangan yang dikumpulkan sebelumnya. Ia menggambarkan Iris, Gazebo Harmonic, MAVROS2, ArduPilot SITL, dan sejumlah node, tetapi komponen-komponen itu **belum tersedia sebagai paket yang dapat dibangun atau launch yang dapat dijalankan**. Anggap diagram, nama topic, versi simulator, dan perintah setup di sana sebagai usulan yang harus diverifikasi, bukan status implementasi.

Repo utama saat ini belum memiliki paket ROS 2 (`package.xml`), `setup.py`/`CMakeLists.txt`, atau launch ROS 2. Skrip `new_plan_2_9/ros_nodes/` adalah eksperimen ROS 1. Jangan mencampur keduanya dalam satu build.

## Arsitektur sasaran

```text
Kamera / sensor simulator
          │
          ▼
  palm_perception ── detections + pose ──► target_manager
                                                │ target berikutnya
                                                ▼
  range / obstacle ──► safety_supervisor ──► mission_manager
                                                │ tujuan misi
                                  ┌─────────────┴─────────────┐
                                  ▼                           ▼
                         flight_adapter                 spray_manager
                                  │                           │
                           MAVROS2/MAVLink             simulasi saja
                                  │
                           ArduPilot SITL
```

- **Flight controller** menstabilkan kendaraan dan mengelola failsafe penerbangan. ROS 2 hanya memberi tujuan misi melalui adapter yang dibatasi dan tervalidasi.
- **Persepsi** mengubah citra menjadi deteksi pohon dengan timestamp dan frame kamera yang benar. Deteksi tunggal tidak cukup untuk menetapkan target; target harus diproyeksikan ke peta/pose dan dikonsolidasikan.
- **Target manager** memilih pohon berikutnya dari daftar/map, mengingat status `unvisited / selected / visited / skipped`, dan mencegah target berulang.
- **Mission manager** mengatur urutan `IDLE → TAKEOFF → TRANSIT → APPROACH → VERIFY → TREAT → RETREAT → NEXT_TARGET → RETURN → LAND`, dengan transisi abort/hold yang eksplisit.
- **Spray manager** mula-mula hanya menghasilkan event simulasi. Event mensyaratkan target aktif dan terverifikasi, posisi/kecepatan dalam ambang, kondisi sensor valid, serta safety supervisor mengizinkan. Obstacle, data basi, komunikasi putus, atau abort harus membatalkan event.
- **Safety supervisor** memiliki prioritas tertinggi: menahan gerak menuju obstacle, meminta hold/loiter melalui adapter, memblokir event dispenser, dan mengeluarkan alasan yang bisa dilog.

Perintah ke dispenser fisik harus tetap nonaktif sampai mekanisme serbuk, aktuator, pengukuran dosis, dan emergency stop sudah ditentukan serta diuji terpisah di bangku. Simulasi event bukan bukti dosis lapangan benar.

## Tahap implementasi dan kriteria selesai

1. **Dasar workspace:** buat `~/syergie_ws/src`, paket `ament_python`/`ament_cmake`, parameter YAML, launch, dan README setup Humble. `colcon build` berhasil di Ubuntu 22.04.
2. **SITL dan sensor:** pilih satu kombinasi simulator/autopilot yang kompatibel dan pin versinya. Drone dapat arm/takeoff/land di SITL; topic pose, kamera, dan range memiliki timestamp, frame, dan frekuensi yang terdokumentasi.
3. **Perception & target:** replay gambar/rosbag tanpa kamera fisik; detections terasosiasi dengan pose; target berikutnya deterministik dan tidak dipilih dua kali.
4. **Misi & perlakuan simulasi:** misi menyelesaikan beberapa pohon dan menulis event dosis hanya saat syarat lengkap. Kondisi target tidak valid, kendaraan bergerak, atau sensor basi wajib menghasilkan `spray_denied` beserta alasannya.
5. **Obstacle & failsafe:** obstacle di jalur membuat hold/retreat/abort yang terdefinisi; kehilangan pose, MAVLink, atau sensor memblokir perlakuan dan menuju keadaan aman.
6. **Evaluasi berulang:** setiap skenario punya rosbag, konfigurasi, hasil yang diharapkan, metrik cakupan/urutan target, dan cara mengulangnya. Simulasi selesai bukan persetujuan untuk uji terbang.

## Urutan instalasi yang disarankan

Gunakan Ubuntu 22.04 native atau VM Linux yang mendukung akselerasi simulator. Mulai dari **ROS 2 Humble + Gazebo Fortress** sebagai pasangan distro ROS yang tersedia untuk Jammy. ArduPilot SITL dan MAVROS2 ditambahkan setelah versi ROS dan simulator dasar terverifikasi. Gazebo Harmonic dapat dievaluasi kemudian melalui jalur kompatibilitas `ros_gz`; jangan menganggap instruksi Harmonic di `new.md` pasti cocok untuk instalasi Humble standar.

Urutan bring-up: ROS 2 → satu paket demo → simulator kosong → model dan sensor → SITL → adapter autopilot → node misi. Jangan mulai dari semua komponen sekaligus.

## Struktur yang dituju

```text
~/syergie_ws/
└── src/
    ├── syergie_interfaces/   # message/service/action yang memang diperlukan
    ├── syergie_sim/          # model, world, sensor, parameter simulasi
    ├── syergie_perception/   # kamera, deteksi, asosiasi pose
    ├── syergie_mission/      # target manager dan state machine
    ├── syergie_safety/       # obstacle, validity, interlock
    └── syergie_bringup/      # launch, konfigurasi, skenario rosbag
```

Mulai dengan sedikit paket; interface kustom baru dibuat ketika message standar ROS tidak cukup. Jangan menyalin seluruh `drone_sawit` atau skrip ROS 1 ke workspace baru.

## Batas dan asumsi yang masih terbuka

- Kamera/Jetson Nano belum dipasang pada airframe dan belum masuk uji terbang.
- Kapasitas angkat F450 tidak memadai untuk diasumsikan membawa Jetson, sensor, dan payload; angka payload harus diukur, bukan ditebak dari simulasi.
- Durasi baterai sekitar 10 menit adalah perkiraan historis tanpa konfigurasi dan data log yang cukup.
- Sistem perlakuan serbuk belum selesai. Jenis aktuator dan tabel dosis lapangan belum tervalidasi.
- “Deteksi sawit”, “deteksi bunga”, dan target perlakuan adalah masalah berbeda. Dataset dan label harus menetapkan yang mana sebelum model detector dipilih.
- Hindari mengklaim siap terbang sebelum uji hardware, failsafe, dan keselamatan operasional dilakukan.

# Syergie Drone

Proyek riset untuk membangun sistem drone otonom yang mengenali target pohon sawit, memilih pohon berikutnya, menghindari rintangan, dan mensimulasikan perlakuan serbuk. **Kondisi saat ini masih tahap persiapan simulasi; belum ada stack ROS 2 atau simulasi yang berjalan terpadu.**

## Posisi proyek sekarang

- Platform pengembangan yang dituju: Ubuntu 22.04, ROS 2 Humble, dan Gazebo Fortress.
- [`ros2_ws/src/`](./ros2_ws/src/) belum berisi paket ROS 2. Belum ada `package.xml`, node, launch file, model drone, world kebun, detector sawit, atau koneksi SITL.
- Kode lama di [`legacy/`](./legacy/README.md) adalah eksperimen terpisah. Kode ROS 1 mendeteksi bola kuning; kode Jetson/MAVSDK memiliki asumsi dan stub yang belum tervalidasi. Jangan gunakan untuk mengendalikan drone atau dispenser.
- F450 pernah terlalu berat untuk konfigurasi yang dicoba; motor cepat panas. Jetson Nano dan kamera belum diuji terpasang, waktu baterai hanya perkiraan sekitar 10 menit, dan penebar serbuk belum selesai.
- Untuk saat ini semua perintah perlakuan harus berupa event simulasi. Tidak ada angka dosis, kapasitas payload, durasi terbang, atau klaim keselamatan yang sudah tervalidasi.

## Mulai dari sini

1. Baca [panduan workspace ROS 2](./ros2_ws/README.md) untuk langkah setup Ubuntu dan urutan kerja simulasi.
2. Baca [status dan audit proyek](./docs/PROJECT_AUDIT.md) untuk memahami hasil kerja lama serta temuan yang masih bisa dipakai.
3. Gunakan [catatan porting `new_plan_2_9`](./docs/ros2/porting-notes-from-new-plan.md) saat menerjemahkan ide ROS 1 menjadi rancangan ROS 2.
4. Lihat [hardware dan CAD](./hardware/README.md) untuk inventaris mekanik, serta [prototipe lama](./legacy/README.md) untuk status tiap subproyek.

## Struktur workspace

```text
syergie-drone/
├── ros2_ws/                 # satu-satunya jalur implementasi aktif
│   └── src/                 # paket ROS 2 belum dibuat
├── hardware/
│   ├── cad/                 # Tarot 650 dan desain dispenser serbuk
│   └── firmware/            # eksperimen firmware sensor
├── legacy/                  # prototipe lama, hanya untuk referensi
├── docs/                    # status proyek, keputusan, dan catatan porting
├── research/                # paper dan model Simulink
└── media/                   # rekaman simulasi lama
```

## Urutan pengembangan berikutnya

1. Siapkan ROS 2 Humble dan Gazebo Fortress di Ubuntu 22.04; pastikan ROS dapat di-source.
2. Buat paket interface, paket simulasi, dan launch minimal. Model awal cukup memakai drone sederhana, baris pohon sintetis, kamera, dan sensor jarak.
3. Buat peta target dengan ID pohon tetap; target manager memilih pohon berikutnya dan menandai pohon yang sudah dikunjungi.
4. Tambahkan detector pada gambar simulasi dan hubungkan deteksi dengan pose kendaraan.
5. Tambahkan mission state machine: transit, approach, verifikasi target, event perlakuan simulasi, retreat, target berikutnya, return, dan landing.
6. Tambahkan safety supervisor. Obstacle, data sensor basi, pose hilang, koneksi putus, atau abort harus membatalkan event perlakuan dan mengarah ke keadaan aman.
7. Ulangi skenario normal dan gagal di SITL/rosbag sebelum mempertimbangkan pengujian hardware.

Flight controller tetap menangani stabilisasi dan failsafe. ROS 2 hanya mengatur tujuan tingkat misi dan tidak mengirim perintah motor langsung. Untuk rancangan simulasi yang lebih rinci, lihat [`ros2_ws/README.md`](./ros2_ws/README.md).

## Hal yang belum diputuskan

- Apakah target utama adalah pohon, bunga, atau keduanya; dataset dan label belum ditetapkan.
- Apakah pemilihan target memakai peta barisan pohon, hasil kamera, atau gabungan keduanya.
- Bentuk akhir dispenser serbuk, aktuator, metode ukur dosis, dan interlock hardware.
- Airframe pengganti F450 dan kapasitas angkat yang benar-benar terukur.

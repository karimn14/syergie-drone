# Eksperimen MAVSDK + LiDAR (arsip)

Kode ini adalah eksperimen Python/MAVSDK terpisah dari ROS 2. Ia membuat berkas rencana QGroundControl dan memantau satu LiDAR serial.

Dokumentasi asli tersedia di [`README_ORIGINAL.md`](./README_ORIGINAL.md). Implementasi supervisor tidak siap untuk penerbangan: parser mengasumsikan LiDAR mengirim teks dalam meter, sementara TF-Luna umumnya dapat dikonfigurasi ke protokol berbeda; jalur pulih dari `hold` mencoba memanggil `arm()` alih-alih melanjutkan misi secara aman. Jangan jalankan terhadap autopilot atau motor.

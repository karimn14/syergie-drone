# Palm Planner lama (opsional)

Aplikasi Flask/React untuk eksperimen peta dan deteksi dari citra satelit. Backend dapat memakai model lokal atau layanan Roboflow, dan memiliki fallback dummy yang bisa mengembalikan pohon sintetis. Hasil dummy tidak boleh dianggap hasil deteksi.

Aplikasi ini tidak terhubung ke ROS 2, pose kamera onboard, target manager, atau flight controller. Salinan YOLOv5 upstream dan dataset COCO8 dipertahankan sebagai bahan historis di dalam folder planner, tetapi bukan bagian dari alur sawit aktif. Kode aplikasi memuat model lokal atau layanan eksternal dan dapat jatuh ke data dummy; bobot lokal `backend/models/best.pt` belum diverifikasi sebagai model sawit.

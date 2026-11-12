# Hardware dan firmware

CAD dipisahkan dari prototype flight software agar desain mekanik mudah ditemukan. `cad/powder_dispenser_prototypes/` berisi beberapa versi hopper/auger/venturi serta komponen referensi; `cad/tarot_650/` berisi model frame Tarot. Folder `firmware/optical_flow/` hanya berisi demo sensor.

CAD belum dihitung atau diuji bersama airframe yang tersedia. F450 yang pernah digunakan tidak boleh diasumsikan sanggup membawa Jetson Nano, kamera, obstacle sensors, dan dispenser. Timbang semua komponen, ukur thrust/current/temperatur di bench, dan verifikasi center of gravity sebelum perencanaan uji terbang.

Seluruh 109 file `mekanik` dan 82 file `Tarot 650` dipertahankan, termasuk arsip ZIP asli, model hasil ekstrak, dan folder `OldVersions`. File ZIP T-Motor yang lebih dari 50 MiB lokal saja; model CAD hasil ekstraknya tetap ada di `cad/vendor_models/`. Beberapa ZIP memang berisi model yang juga tersedia dalam bentuk ekstrak; keduanya dibiarkan untuk mempertahankan bahan sumber asli.

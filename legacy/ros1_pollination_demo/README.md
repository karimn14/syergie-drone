# Demo pollination ROS 1 (arsip)

Eksperimen ini **bukan ROS 2**. `ros_nodes/scripts/` menggunakan `rospy`, custom message ROS 1, dan launch XML. Detector yang ada mengklasifikasikan objek kuning berbasis HSV; itu bukan model deteksi pohon sawit atau bunga.

Node spray mengirim `MAV_CMD_DO_SET_SERVO` langsung ke Pixhawk. Jangan menjalankannya pada drone atau dispenser fisik. Tidak ada paket ROS lengkap yang membuat isi folder ini dapat di-build secara mandiri.

Panduan asli yang panjang dipertahankan sebagai [`README.legacy.md`](./README.legacy.md), [`MASTER_EXECUTION_GUIDE.md`](./MASTER_EXECUTION_GUIDE.md), dan dokumen terkait. Banyak bagian mengasumsikan ROS Melodic/Noetic dan tidak cocok dengan target ROS 2 Humble.

# Rancangan ROS 2 awal (arsip)

Dokumen ini dipindahkan dari `new_ros_syergie/new.md`. Isinya adalah usulan awal, bukan catatan implementasi yang berhasil dijalankan. Nama node, topic, model drone, sensor, versi simulator, dan urutan setup di dalamnya belum diverifikasi.

Lihat [`ros2_ws/README.md`](../../../ros2_ws/README.md) untuk status workspace dan urutan pengembangan saat ini. Untuk ROS 2 Humble, Gazebo Fortress adalah pairing ROS yang direkomendasikan; lihat [matriks kompatibilitas Gazebo/ROS](https://gazebosim.org/docs/fortress/ros_installation/).

---

# Syergie Drone — Autonomous Palm Oil Pollinator
## Dokumentasi Teknis Lengkap: Phase 0 – Phase 4
### Sistem Simulasi ROS2 + Gazebo Harmonic + ArduPilot SITL

> **Versi:** 1.0.0 | **OS:** Ubuntu 22.04 | **ROS2:** Humble | **Gazebo:** Harmonic | **Workspace:** `~/syergie_ws/`

---

## DAFTAR ISI

- [Gambaran Umum Arsitektur](#gambaran-umum-arsitektur)
- [PHASE 0 — Environment Setup & Verifikasi Dasar](#phase-0)
- [PHASE 1 — Drone Model & Plugin Verification](#phase-1)
- [PHASE 2 — World Environment Kebun Sawit](#phase-2)
- [PHASE 3 — MAVROS2 & ArduPilot Integration](#phase-3)
- [PHASE 4 — ROS2 Node Stack](#phase-4)

---

## GAMBARAN UMUM ARSITEKTUR

```
┌──────────────────────────────────────────────────────────────────┐
│                   GAZEBO HARMONIC (Simulator)                    │
│  ┌────────────┐  ┌──────────────┐  ┌────────────┐  ┌─────────┐  │
│  │ Iris Model │  │ Kamera Depan │  │ Optical    │  │ Range-  │  │
│  │ + Plugin   │  │  640x480 30Hz│  │ Flow Plugin│  │ finder  │  │
│  └─────┬──────┘  └──────┬───────┘  └─────┬──────┘  └────┬────┘  │
└────────┼────────────────┼────────────────┼───────────────┼───────┘
         │                │                │               │
         ▼                ▼                ▼               ▼
┌──────────────────────────────────────────────────────────────────┐
│             ros_gz_bridge  (Gazebo ↔ ROS2 Topics)               │
└────────────────────────────┬─────────────────────────────────────┘
                             │ MAVLink UDP :14550/:14551
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│              ArduPilot SITL  (EKF3, Flight Controller)           │
│   EK3_SRC: optical flow + rangefinder │ FLOWHOLD / GUIDED mode   │
└────────────────────────────┬─────────────────────────────────────┘
                             │ MAVROS2
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                    ROS2 NODE GRAPH                               │
│  PERCEPTION: [row_det]→row_info  [bloom_det]→bloom_detected      │
│  CONTROL:    [fsm]→cmd_vel  [spray_ctrl]→/spray/cmd              │
│  TRACKING:   [coverage]→coverage_grid                            │
└──────────────────────────────────────────────────────────────────┘
```

**Urutan startup yang WAJIB diikuti:**
```
1. gz sim (Gazebo)           → tunggu GUI muncul
2. sim_vehicle.py (SITL)     → tunggu "EKF3 IMU0 initialised"
3. ros2 launch mavros         → tunggu "connected: true"
4. ros2 launch nodes          → semua node persepsi & kontrol
```

---

# PHASE 0 — Environment Setup & Verifikasi Dasar {#phase-0}

> **Tujuan:** Memastikan semua dependensi terinstall dan bisa berjalan
> independen sebelum diintegrasikan. Jangan lewati langkah verifikasi.

---

## 0.1 Install ROS2 Humble

### Penjelasan
ROS2 Humble adalah distribusi LTS yang berjalan di Ubuntu 22.04. Instalasi dari repository OSRF resmi — **bukan** dari apt default Ubuntu.

### Step 1: Setup Locale
```bash
sudo apt update && sudo apt install -y locales
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8
locale
```
**Expected output:** `LANG=en_US.UTF-8` ... `LC_ALL=en_US.UTF-8`

### Step 2: Tambah Repository ROS2
```bash
sudo apt install -y software-properties-common curl gnupg lsb-release
sudo add-apt-repository universe
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
    -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) \
    signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] \
    http://packages.ros.org/ros2/ubuntu \
    $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | \
    sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
sudo apt update
```

### Step 3: Install ROS2 Humble Desktop
```bash
sudo apt install -y ros-humble-desktop
sudo apt install -y ros-dev-tools python3-colcon-common-extensions \
    python3-rosdep python3-vcstool
```

### Step 4: Setup .bashrc
```bash
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
echo "source /usr/share/colcon_argcomplete/hook/colcon-argcomplete.bash" >> ~/.bashrc
source ~/.bashrc
sudo rosdep init
rosdep update
```

### Verifikasi
```bash
ros2 --version
# PASS: "ros2 humble ..."

# Terminal 1:
ros2 run demo_nodes_cpp talker
# Terminal 2:
ros2 run demo_nodes_cpp listener
# PASS: listener mencetak "I heard: Hello World: N"
```

### Troubleshooting 0.1

**Error: `ros2: command not found`**
```bash
source /opt/ros/humble/setup.bash
grep "ros/humble" ~/.bashrc   # pastikan sudah ada
```

**Error: `Failed to connect to raw.githubusercontent.com`**
```bash
# Alternatif download key:
curl -s https://packages.ros.org/ros.key | sudo apt-key add -
```

**Error: `No installation candidate ros-humble-desktop`**
```bash
lsb_release -c   # harus: jammy
# Ulangi langkah Step 2 dengan memastikan UBUNTU_CODENAME = jammy
```

---

## 0.2 Install Gazebo Harmonic

### Penjelasan
Gazebo Harmonic (versi 8.x) diinstall dari OSRF repository. **Bukan** `apt install gazebo` (itu Gazebo Classic 11) dan **bukan** snap.

> ⚠️ **PERHATIAN:** Binary yang benar adalah `gz`, bukan `gazebo` atau `ign`. Jika ada Gazebo lain terinstall (Fortress/Garden), uninstall dulu untuk menghindari konflik library.

### Install
```bash
sudo wget https://packages.osrfoundation.org/gazebo.gpg \
    -O /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) \
    signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] \
    http://packages.osrfoundation.org/gazebo/ubuntu-stable \
    $(lsb_release -cs) main" | \
    sudo tee /etc/apt/sources.list.d/gazebo-stable.list > /dev/null
sudo apt-get update
sudo apt-get install -y gz-harmonic
```

### Verifikasi
```bash
gz sim --version
# PASS: "Gazebo Sim, version 8.x.x"

gz sim shapes.sdf
# PASS: GUI muncul dengan beberapa shape geometri
```

### Test Headless
```bash
timeout 10 gz sim -s empty.sdf --headless-rendering && echo "OK"
gz topic -l   # di terminal lain saat Gazebo running
# PASS: ada /clock, /stats, dll
```

### Troubleshooting 0.2

**Error: `gz: command not found`**
```bash
find /usr -name "gz" 2>/dev/null   # cari lokasi binary
echo "export PATH=/usr/bin:\$PATH" >> ~/.bashrc && source ~/.bashrc
```

**Error: Blank window / no render engine**
```bash
sudo apt install -y libgl1-mesa-glx libgl1-mesa-dri
LIBGL_ALWAYS_SOFTWARE=1 gz sim shapes.sdf   # fallback software rendering
glxinfo | grep "OpenGL renderer"
```

**Error: Segfault saat launch**
```bash
export __GLX_VENDOR_LIBRARY_NAME=mesa
gz sim shapes.sdf
# atau:
sudo apt full-upgrade && reboot
```

---

## 0.3 Install ros_gz Bridge

### Penjelasan
`ros_gz` menjembatani Gazebo Harmonic ↔ ROS2 Humble. Terdiri dari:
- `ros_gz_bridge`: konversi pesan (Protobuf ↔ DDS/CDR)
- `ros_gz_sim`: spawn model, interact dengan world
- `ros_gz_interfaces`: definisi tipe Gazebo untuk ROS2

```bash
sudo apt install -y ros-humble-ros-gz
```

### Verifikasi
```bash
ros2 pkg list | grep ros_gz
# PASS: minimal 3 baris (ros_gz_bridge, ros_gz_image, ros_gz_sim, ros_gz_interfaces)

ros2 run ros_gz_bridge parameter_bridge --help | head -5
```

### Test Bridge Clock
```bash
# Terminal 1:
gz sim empty.sdf

# Terminal 2:
source /opt/ros/humble/setup.bash
ros2 run ros_gz_bridge parameter_bridge \
    /clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock

# Terminal 3:
ros2 topic echo /clock
# PASS: sec/nanosec berubah sesuai simulasi
```

### Troubleshooting 0.3

**Error: `Type mapping not found for gz.msgs.Clock`**
```bash
# Versi mismatch. Cek:
ros2 pkg xml ros_gz_bridge | grep version
gz sim --version
# Humble harus pair dengan Harmonic (gz 8.x)
sudo apt update && sudo apt upgrade ros-humble-ros-gz
```

**Bridge jalan tapi tidak ada data:**
```bash
gz topic -l | grep clock       # pastikan Gazebo topic ada
gz topic -e -t /clock | head  # pastikan data mengalir di Gazebo
```

---

## 0.4 Install MAVROS2

### Penjelasan
MAVROS2 mengimplementasikan MAVLink protocol sebagai ROS2 topics/services. Bertindak sebagai translator antara ArduPilot SITL ↔ ROS2.

```
ArduPilot SITL ←── MAVLink UDP ──→ MAVROS2 ←── ROS2 ──→ Node kita
   port 14550                    fcu_url          /mavros/...
```

### Install
```bash
sudo apt install -y ros-humble-mavros ros-humble-mavros-extras ros-humble-mavros-msgs
sudo apt install -y geographiclib-tools
# WAJIB: dataset geoid untuk konversi koordinat
sudo /opt/ros/humble/lib/mavros/install_geographiclib_datasets.sh
```

> ⚠️ **PERHATIAN:** Langkah `install_geographiclib_datasets.sh` WAJIB. Tanpa ini MAVROS2 crash dengan `GeographicLib exception: File not readable`.

### Verifikasi
```bash
ros2 pkg list | grep mavros
# PASS: mavros, mavros_extras, mavros_msgs

ls /usr/share/GeographicLib/
# PASS: ada folder geoids, gravity, magnetic
```

### Troubleshooting 0.4

**Error: `GeographicLib exception`**
```bash
sudo /opt/ros/humble/lib/mavros/install_geographiclib_datasets.sh
ls /usr/share/GeographicLib/  # harus ada geoids/
```

**Error: plugin blocked saat startup**
```bash
sudo apt install -y ros-humble-mavros-extras  # install plugin tambahan
```

---

## 0.5 Build ardupilot_gazebo dari Source

### Penjelasan
Plugin Gazebo dari Khancyr yang menyediakan `ArduCopterPlugin`, `OpticalFlowPlugin`, dan `SonarPlugin`. Harus build dari source branch `gz-harmonic`.

### Clone dan Build
```bash
mkdir -p ~/ardupilot_tools
cd ~/ardupilot_tools
git clone https://github.com/khancyr/ardupilot_gazebo.git
cd ardupilot_gazebo
git checkout gz-harmonic
git branch   # harus: * gz-harmonic

# Install build dependencies
sudo apt install -y \
    libgz-sim8-dev libgz-transport13-dev \
    libgz-sensors8-dev libgz-math7-dev \
    libgz-msgs10-dev rapidjson-dev

# Build
mkdir -p ~/ardupilot_gz_ws/src
cp -r ~/ardupilot_tools/ardupilot_gazebo ~/ardupilot_gz_ws/src/
cd ~/ardupilot_gz_ws
colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release
```

**Expected:**
```
Starting >>> ardupilot_gazebo
Finished <<< ardupilot_gazebo [~45s]
Summary: 1 packages finished
```

### Identifikasi Plugin Tersedia
```bash
ls ~/ardupilot_gz_ws/install/ardupilot_gazebo/lib/*.so
# Cari: libArduCopterPlugin.so, libOpticalFlowPlugin.so, libSonarPlugin.so

# Cek source untuk konfirmasi
find ~/ardupilot_tools/ardupilot_gazebo/src -name "*.cpp" | sort
```

### Setup Environment Variables
```bash
cat >> ~/.bashrc << 'ENVEOF'

# ardupilot_gazebo
export GZ_SIM_SYSTEM_PLUGIN_PATH=$HOME/ardupilot_gz_ws/install/ardupilot_gazebo/lib:$GZ_SIM_SYSTEM_PLUGIN_PATH
export GZ_SIM_RESOURCE_PATH=$HOME/ardupilot_gz_ws/install/ardupilot_gazebo/share/ardupilot_gazebo/models:$HOME/ardupilot_gz_ws/install/ardupilot_gazebo/share/ardupilot_gazebo/worlds:$GZ_SIM_RESOURCE_PATH
source $HOME/ardupilot_gz_ws/install/setup.bash
ENVEOF
source ~/.bashrc
```

### Verifikasi Plugin Terload
```bash
gz sim -v 4 iris_runway.sdf 2>&1 | grep -i "plugin\|ardupilot\|loaded"
# PASS: "Loaded system plugin [libArduCopterPlugin.so]"
```

### Troubleshooting 0.5

**Error: `Could not find package gz-sim8`**
```bash
sudo apt search "libgz-sim" | grep "libgz-sim[0-9]-dev"
sudo apt install -y libgz-sim8-dev
pkg-config --modversion gz-sim8  # verifikasi
```

**Error: `fatal error: rapidjson/document.h`**
```bash
sudo apt install -y rapidjson-dev
cd ~/ardupilot_gz_ws && colcon build --symlink-install
```

**Plugin tidak terload (`not found`)**
```bash
echo $GZ_SIM_SYSTEM_PLUGIN_PATH
ls $HOME/ardupilot_gz_ws/install/ardupilot_gazebo/lib/
ldd ~/ardupilot_gz_ws/install/ardupilot_gazebo/lib/libArduCopterPlugin.so | grep "not found"
# Install semua .so dependency yang kurang
```

---

## 0.6 Install ArduPilot SITL

### Penjelasan
ArduPilot SITL mengemulasikan flight controller ArduCopter di komputer biasa. Sangat realistis: EKF, mode flight, parameter system semuanya identik dengan hardware asli.

### Clone dan Build
```bash
cd ~
git clone --recurse-submodules https://github.com/ArduPilot/ardupilot.git
cd ardupilot
git checkout Copter-4.5.x
git submodule update --init --recursive

# Install semua dependencies
Tools/environment_install/install-prereqs-ubuntu.sh -y
. ~/.profile

# Build ArduCopter untuk SITL
./waf configure --board sitl
./waf copter   # ~5-15 menit

# Verifikasi
ls build/sitl/bin/arducopter
file build/sitl/bin/arducopter
# PASS: "ELF 64-bit LSB executable"
```

### Setup PATH
```bash
cat >> ~/.bashrc << 'PATHEOF'
export PATH=$PATH:$HOME/ardupilot/Tools/autotest
export PATH=$PATH:$HOME/.local/bin
PATHEOF
source ~/.bashrc
which sim_vehicle.py   # harus ditemukan
```

### Test SITL Standalone
```bash
cd ~/ardupilot
sim_vehicle.py -v ArduCopter --console --no-rebuild

# Di MAVProxy console:
# mode GUIDED
# arm throttle
# takeoff 3
# (altitude naik) → land
```

### Troubleshooting 0.6

**Error: `WAF version too old`**
```bash
cd ~/ardupilot
git submodule update --init Tools/ardupilotwaf
./waf distclean && ./waf configure --board sitl
```

**Error: `No module named 'pymavlink'`**
```bash
pip3 install pymavlink mavproxy
```

---

## 0.7 Smoke Test Individual

### Test A: SITL Standalone
```bash
cd ~/ardupilot
sim_vehicle.py -v ArduCopter -f quad --console --no-rebuild

# MAVProxy: mode GUIDED → arm throttle → takeoff 3
# PASS: altitude naik, tidak crash
```

### Test B: Gazebo Standalone
```bash
gz sim iris_runway.sdf
# Terminal lain:
gz topic -l | grep iris
gz model -l
# PASS: iris_with_standoffs muncul di list
```

### Test C: MAVROS2 Standalone
```bash
ros2 run mavros mavros_node \
    --ros-args \
    -p fcu_url:="udp://:14550@" \
    -p target_system_id:=1 \
    -p target_component_id:=1 &
sleep 3
ros2 topic list | grep mavros | head -10
# PASS: ada /mavros/state, /mavros/imu/data, dll
```

---

## 0.8 Integrasi SITL + ardupilot_gazebo + MAVROS2

### Urutan Startup

**Terminal 1 — Gazebo:**
```bash
source ~/.bashrc
gz sim iris_runway.sdf -v 3
# Tunggu GUI muncul sepenuhnya
```

**Terminal 2 — ArduPilot SITL:**
```bash
source ~/.bashrc
cd ~/ardupilot
sim_vehicle.py \
    -v ArduCopter \
    -f gazebo-iris \
    --model=gazebo \
    --console \
    --no-rebuild \
    --out=127.0.0.1:14551 \
    --out=127.0.0.1:14553 \
    -l 37.613,-122.357,-3.45,270

# Tunggu: "EKF3 IMU0 initialised"
```

**Terminal 3 — MAVROS2:**
```bash
source /opt/ros/humble/setup.bash
ros2 run mavros mavros_node \
    --ros-args \
    -p fcu_url:="udp://:14550@127.0.0.1:14551" \
    -p gcs_url:="udp://@127.0.0.1:14553" \
    -p system_id:=255 \
    -p component_id:=240 \
    -p target_system_id:=1 \
    -p target_component_id:=1
```

**Terminal 4 — Verifikasi:**
```bash
source /opt/ros/humble/setup.bash
ros2 topic echo /mavros/state --once
# PASS: connected: true

ros2 topic hz /mavros/imu/data
# PASS: ~100 Hz

# Arm dari MAVProxy (Terminal 2):
# mode GUIDED → arm throttle
# Motor Gazebo harus berputar
gz topic -e -t /world/iris_runway/model/iris_with_standoffs/joint/rotor_0_joint/cmd_force
# PASS: nilai non-zero
```

### Troubleshooting 0.8

**Motor tidak berputar di Gazebo saat arm:**
```bash
gz sim iris_runway.sdf -v 4 2>&1 | grep -i "plugin\|ardupilot"
# PASS: "Loaded system plugin [libArduCopterPlugin.so]"
# FAIL: tidak ada → cek GZ_SIM_SYSTEM_PLUGIN_PATH
```

**`connected: false` setelah MAVROS2 start:**
```bash
sudo ss -ulnp | grep 14550   # pastikan hanya satu listener
python3 -c "
from pymavlink import mavutil
m = mavutil.mavlink_connection('udp:127.0.0.1:14550')
msg = m.recv_match(type='HEARTBEAT', blocking=True, timeout=5)
print('Connected!' if msg else 'TIMEOUT')
"
```

**`gz sim: world not found`:**
```bash
echo $GZ_SIM_RESOURCE_PATH
find ~/ardupilot_gz_ws -name "iris_runway.sdf"
export GZ_SIM_RESOURCE_PATH=~/ardupilot_gz_ws/install/ardupilot_gazebo/share/ardupilot_gazebo/worlds:$GZ_SIM_RESOURCE_PATH
```

---

## MILESTONE CHECKPOINT PHASE 0

> Semua item harus PASS sebelum lanjut ke Phase 1.

**[ ] Item 1: ROS2 Humble**
```bash
ros2 --version | grep humble
# PASS jika output mengandung "humble"
```

**[ ] Item 2: Gazebo Harmonic**
```bash
gz sim --version | grep "version 8"
# PASS jika "version 8.x.x"
```

**[ ] Item 3: ros_gz packages (≥3)**
```bash
ros2 pkg list | grep ros_gz | wc -l
# PASS: output ≥ 3
```

**[ ] Item 4: MAVROS2 packages**
```bash
ros2 pkg list | grep mavros | wc -l
# PASS: output ≥ 2
```

**[ ] Item 5: GeographicLib datasets**
```bash
ls /usr/share/GeographicLib/ | sort
# PASS: ada geoids, gravity, magnetic
```

**[ ] Item 6: ardupilot_gazebo plugin**
```bash
ls ~/ardupilot_gz_ws/install/ardupilot_gazebo/lib/libArduCopterPlugin.so
# PASS: file ada
```

**[ ] Item 7: SITL binary**
```bash
file ~/ardupilot/build/sitl/bin/arducopter | grep "ELF"
# PASS: "ELF 64-bit LSB executable"
```

**[ ] Item 8: sim_vehicle.py di PATH**
```bash
which sim_vehicle.py
# PASS: path ditemukan
```

**[ ] Item 9: GZ_SIM_SYSTEM_PLUGIN_PATH terisi**
```bash
echo $GZ_SIM_SYSTEM_PLUGIN_PATH | grep ardupilot
# PASS: mengandung "ardupilot_gz_ws"
```

**[ ] Item 10: Integrasi SITL+Gazebo+MAVROS2**
```bash
# (Dengan 3 terminal startup seperti 0.8)
ros2 topic echo /mavros/state --once | grep "connected: true"
# PASS: "connected: true"
```

**[ ] Item 11: IMU data mengalir**
```bash
timeout 5 ros2 topic hz /mavros/imu/data 2>&1 | grep "average rate"
# PASS: rate > 90 Hz
```

**[ ] Item 12: Motor Gazebo berputar saat arm**
```bash
# Manual: arm throttle di MAVProxy → lihat rotor berputar di Gazebo
# PASS: visual konfirmasi
```

### Kriteria PASS/FAIL dan Tindakan Remediasi

| FAIL | Tindakan |
|------|----------|
| ROS2 tidak terinstall | Ulangi 0.1 dari Step 2, pastikan codename=jammy |
| Gazebo crash | Cek GPU driver, coba `LIBGL_ALWAYS_SOFTWARE=1` |
| ros_gz < 3 pkg | `sudo apt install -y ros-humble-ros-gz` lagi |
| GeographicLib error | Re-run `install_geographiclib_datasets.sh` |
| Plugin tidak loaded | Cek `GZ_SIM_SYSTEM_PLUGIN_PATH`, rebuild ardupilot_gazebo |
| SITL binary tidak ada | `./waf copter` ulang, cek error compiler |
| connected: false | Cek port UDP, pastikan SITL berjalan dulu |

---

# PHASE 1 — Drone Model & Plugin Verification {#phase-1}

> **Tujuan:** Memodifikasi model Iris dengan semua sensor dan payload yang dibutuhkan, memastikan data mengalir dari Gazebo ke ROS2.

---

## 1.1 Analisis Struktur Iris Model

### Lokasi Model
```bash
IRIS_DIR=~/ardupilot_gz_ws/install/ardupilot_gazebo/share/ardupilot_gazebo/models
ls $IRIS_DIR/
ls $IRIS_DIR/iris_with_standoffs/
```

**Struktur:**
```
iris_with_standoffs/
├── model.config     ← metadata (nama, versi, author)
└── model.sdf        ← deskripsi lengkap model
```

### Hierarki SDF Iris
```xml
<model name="iris_with_standoffs">
  <link name="base_link">        ← Badan utama (mass, collision, visual)
    <inertial>...</inertial>
    <sensor name="imu_sensor">   ← IMU sensor
  </link>
  <link name="rotor_0">          ← Motor kanan-depan (CW)
  <link name="rotor_1">          ← Motor kiri-belakang (CW)
  <link name="rotor_2">          ← Motor kiri-depan (CCW)
  <link name="rotor_3">          ← Motor kanan-belakang (CCW)
  <joint name="rotor_0_joint" type="revolute">
  ...
  <plugin filename="libArduCopterPlugin.so">
    <control channel="0">        ← Motor 0: jointName, multiplier, PWM range
    <control channel="1">
    <control channel="2">
    <control channel="3">
    <fdm_addr>127.0.0.1</fdm_addr>
    <fdm_port_in>9002</fdm_port_in>
    <fdm_port_out>9003</fdm_port_out>
  </plugin>
</model>
```

### Buat Salinan Model Kustom

> ⚠️ **PERHATIAN:** JANGAN modifikasi model di `install/`. Selalu buat salinan ke workspace sendiri — model original tertimpa saat rebuild.

```bash
mkdir -p ~/syergie_ws/src/syergie_description/models/iris_syergie

# Salin model original
cp $IRIS_DIR/iris_with_standoffs/model.config \
   ~/syergie_ws/src/syergie_description/models/iris_syergie/
cp $IRIS_DIR/iris_with_standoffs/model.sdf \
   ~/syergie_ws/src/syergie_description/models/iris_syergie/

# Update model.config
cat > ~/syergie_ws/src/syergie_description/models/iris_syergie/model.config << 'CFGEOF'
<?xml version="1.0"?>
<model>
  <name>Iris Syergie</name>
  <version>1.0</version>
  <sdf version="1.9">model.sdf</sdf>
  <author><name>Syergie Team</name></author>
  <description>Modified Iris: forward cam, down cam (optical flow),
    rangefinder, spray payload + ParticleEmitter.</description>
</model>
CFGEOF

# Daftarkan path model ke Gazebo resource path
echo "export GZ_SIM_RESOURCE_PATH=\$HOME/syergie_ws/src/syergie_description/models:\$GZ_SIM_RESOURCE_PATH" >> ~/.bashrc
source ~/.bashrc
```

---

## 1.2 Audit Plugin Iris yang Sudah Ada

### ArduCopterPlugin — Parameter Kunci
```xml
<plugin filename="libArduCopterPlugin.so" name="ardupilot_plugin">
  <!-- Motor channel 0-3: mapping PWM ke joint velocity -->
  <control channel="0">
    <jointName>rotor_0_joint</jointName>
    <multiplier>838</multiplier>    <!-- RPM scale, negatif = CCW -->
    <offset>-0.5</offset>          <!-- offset PWM center -->
    <servo_min>1000</servo_min>    <!-- PWM min µs -->
    <servo_max>2000</servo_max>    <!-- PWM max µs -->
    <type>VELOCITY</type>
  </control>
  <!-- UDP ports: Gazebo ↔ SITL -->
  <fdm_addr>127.0.0.1</fdm_addr>
  <fdm_port_in>9002</fdm_port_in>   <!-- Gazebo listen dari SITL -->
  <fdm_port_out>9003</fdm_port_out> <!-- Gazebo kirim ke SITL -->
  <!-- IMU reference -->
  <imuName>imu_link::imu_sensor</imuName>
</plugin>
```

### GPS Plugin — Disable untuk GPS-Denied
```bash
# Cek apakah ada GPS sensor di model:
grep -n "gps\|navsat\|GPS" ~/syergie_ws/src/syergie_description/models/iris_syergie/model.sdf

# Cara disable: set parameter ArduPilot (lebih aman daripada hapus dari SDF)
# Di MAVProxy setelah SITL running:
# param set GPS_TYPE 0
# param set GPS_TYPE2 0
```

### List Semua Topic Gazebo saat Iris Spawn
```bash
gz sim iris_runway.sdf &
sleep 5
gz topic -l | grep -v "^/stats\|^/clock" | sort
# Expected:
# /world/iris_runway/model/iris_with_standoffs/link/base_link/sensor/imu_sensor/imu
# /world/iris_runway/model/iris_with_standoffs/joint/rotor_0_joint/cmd_force
# /world/iris_runway/pose/info
```

---

## 1.3 Menambah Kamera Forward ke Model Iris

### Tambahkan ke `model.sdf` (sebelum `</model>`):

```bash
cat >> ~/syergie_ws/src/syergie_description/models/iris_syergie/model.sdf << 'SDFEOF'
  <!-- ============================================================
       FORWARD CAMERA
       Posisi: 0.1m depan, 0m samping, 0.02m atas CoG
       FOV: 90deg, Resolusi: 640x480, Rate: 30Hz
       ============================================================ -->
  <link name="camera_front_link">
    <pose>0.1 0 0.02 0 0 0</pose>
    <inertial>
      <mass>0.015</mass>
      <inertia>
        <ixx>0.0000011</ixx><ixy>0</ixy><ixz>0</ixz>
        <iyy>0.0000011</iyy><iyz>0</iyz>
        <izz>0.0000011</izz>
      </inertia>
    </inertial>
    <collision name="cam_front_col">
      <geometry><box><size>0.03 0.04 0.03</size></box></geometry>
    </collision>
    <visual name="cam_front_vis">
      <geometry><box><size>0.03 0.04 0.03</size></box></geometry>
      <material>
        <ambient>0.1 0.1 0.1 1</ambient>
        <diffuse>0.1 0.1 0.1 1</diffuse>
      </material>
    </visual>
    <sensor name="camera_front" type="camera">
      <always_on>1</always_on>
      <update_rate>30</update_rate>
      <visualize>false</visualize>
      <camera>
        <horizontal_fov>1.5708</horizontal_fov>
        <image>
          <width>640</width>
          <height>480</height>
          <format>R8G8B8</format>
        </image>
        <clip><near>0.05</near><far>100.0</far></clip>
        <noise>
          <type>gaussian</type>
          <mean>0.0</mean>
          <stddev>0.007</stddev>
        </noise>
      </camera>
    </sensor>
  </link>
  <joint name="camera_front_joint" type="fixed">
    <parent>base_link</parent>
    <child>camera_front_link</child>
  </joint>
SDFEOF
```

### ros_gz_bridge untuk Kamera Forward
```bash
# Bridge image dari Gazebo ke ROS2
ros2 run ros_gz_bridge parameter_bridge \
  "/world/palm_world/model/iris_syergie/link/camera_front_link/sensor/camera_front/image\
@sensor_msgs/msg/Image[gz.msgs.Image" \
  --ros-args --remap \
  /world/palm_world/model/iris_syergie/link/camera_front_link/sensor/camera_front/image:=/camera/front/image_raw
```

### Verifikasi
```bash
ros2 topic hz /camera/front/image_raw
# PASS: average rate: 30.0 Hz

# Lihat gambar:
ros2 run rqt_image_view rqt_image_view
# pilih topic /camera/front/image_raw
```

### Troubleshooting 1.3

**Gambar blank/hitam:**
```bash
gz sim -v 4 ... 2>&1 | grep -i "render\|ogre"
# Jika ogre2 error, ganti ke ogre:
# Tambahkan di sensor: <plugin filename="libgz-sim-sensors-system.so"...>
#   <render_engine>ogre</render_engine>
```

**Topic tidak muncul di ROS2:**
```bash
gz topic -l | grep camera_front   # pastikan nama topic exact
# Salin nama persis, paste ke bridge command
```

---

## 1.4 Verifikasi OpticalFlowPlugin

### Cek Keberadaan Plugin
```bash
ls ~/ardupilot_gz_ws/install/ardupilot_gazebo/lib/ | grep -i "optical\|flow"
find ~/ardupilot_tools/ardupilot_gazebo/src -name "*optical*" -o -name "*flow*" 2>/dev/null
```

---

### OPSI A: Jika `libOpticalFlowPlugin.so` Ada

Tambahkan sensor ke model SDF:
```xml
  <!-- DOWNWARD CAMERA + OPTICAL FLOW PLUGIN -->
  <link name="camera_down_link">
    <pose>0 0 -0.05 0 1.5708 0</pose>  <!-- pitch=π/2: pointing down -->
    <inertial>
      <mass>0.010</mass>
      <inertia>
        <ixx>0.0000006</ixx><ixy>0</ixy><ixz>0</ixz>
        <iyy>0.0000006</iyy><iyz>0</iyz>
        <izz>0.0000006</izz>
      </inertia>
    </inertial>
    <visual name="cam_down_vis">
      <geometry><box><size>0.02 0.02 0.015</size></box></geometry>
      <material><ambient>0.1 0.1 0.8 1</ambient></material>
    </visual>
    <collision name="cam_down_col">
      <geometry><box><size>0.02 0.02 0.015</size></box></geometry>
    </collision>
    <sensor name="camera_down" type="camera">
      <always_on>1</always_on>
      <update_rate>50</update_rate>
      <camera>
        <horizontal_fov>1.0472</horizontal_fov>
        <image><width>64</width><height>64</height><format>L8</format></image>
        <clip><near>0.01</near><far>30.0</far></clip>
      </camera>
    </sensor>
    <sensor name="optical_flow_sensor" type="custom">
      <plugin filename="libOpticalFlowPlugin.so" name="optical_flow_plugin">
        <fdm_addr>127.0.0.1</fdm_addr>
        <fdm_port_in>9005</fdm_port_in>
        <hasOpticalFlow>true</hasOpticalFlow>
      </plugin>
    </sensor>
  </link>
  <joint name="camera_down_joint" type="fixed">
    <parent>base_link</parent>
    <child>camera_down_link</child>
  </joint>
```

---

### OPSI B: Jika Plugin TIDAK Ada — Node ROS2 Optical Flow

Tambahkan kamera downward (tanpa sensor custom), lalu buat node Python:

```bash
mkdir -p ~/syergie_ws/src/syergie_perception/syergie_perception/
cat > ~/syergie_ws/src/syergie_perception/syergie_perception/optical_flow_node.py << 'PYEOF'
#!/usr/bin/env python3
"""
Optical Flow Node: hitung kecepatan dari kamera downward.
Algoritma: Lucas-Kanade Sparse Optical Flow (Pyramid).
"""
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import Image, Range
from geometry_msgs.msg import TwistStamped
from cv_bridge import CvBridge
import cv2
import numpy as np
from typing import Optional, Tuple


class OpticalFlowNode(Node):
    def __init__(self):
        super().__init__('optical_flow_node')
        self.declare_parameter('camera_fov_rad', 1.0472)
        self.declare_parameter('image_width', 64)
        self.declare_parameter('image_height', 64)
        self.fov    = self.get_parameter('camera_fov_rad').value
        self.img_w  = self.get_parameter('image_width').value
        self.img_h  = self.get_parameter('image_height').value

        self.bridge = CvBridge()
        self.prev_gray: Optional[np.ndarray] = None
        self.prev_pts:  Optional[np.ndarray] = None
        self.altitude: float = 0.5
        self.last_stamp = None

        self.lk_params = dict(
            winSize=(15, 15), maxLevel=3,
            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.03))
        self.feature_params = dict(maxCorners=100, qualityLevel=0.3,
                                   minDistance=5.0, blockSize=7)

        sensor_qos = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT,
                                history=HistoryPolicy.KEEP_LAST, depth=1)
        self.create_subscription(Image,  '/camera/down/image_raw', self.image_cb, sensor_qos)
        self.create_subscription(Range,  '/rangefinder/range',     self.range_cb,  sensor_qos)
        self.flow_pub = self.create_publisher(TwistStamped, '/optical_flow/velocity', 10)
        self.get_logger().info('OpticalFlowNode started')

    def range_cb(self, msg: Range):
        if 0.05 < msg.range < 10.0:
            self.altitude = msg.range

    def image_cb(self, msg: Image):
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, 'mono8') \
                if msg.encoding == 'mono8' else \
                cv2.cvtColor(self.bridge.imgmsg_to_cv2(msg, 'bgr8'), cv2.COLOR_BGR2GRAY)
        except Exception as e:
            self.get_logger().error(str(e)); return

        if self.prev_gray is None:
            self.prev_gray = frame
            self.prev_pts  = cv2.goodFeaturesToTrack(frame, mask=None, **self.feature_params)
            self.last_stamp = msg.header.stamp; return

        curr_stamp = msg.header.stamp
        dt = (curr_stamp.sec - self.last_stamp.sec) + \
             (curr_stamp.nanosec - self.last_stamp.nanosec) * 1e-9
        if dt <= 0 or dt > 1.0:
            self.prev_gray = frame; self.last_stamp = curr_stamp; return

        vx, vy = 0.0, 0.0
        if self.prev_pts is not None and len(self.prev_pts) >= 10:
            curr_pts, status, _ = cv2.calcOpticalFlowPyrLK(
                self.prev_gray, frame, self.prev_pts, None, **self.lk_params)
            if curr_pts is not None and status is not None:
                good_c = curr_pts[status == 1]
                good_p = self.prev_pts[status == 1]
                if len(good_c) >= 10:
                    disp = good_c - good_p
                    dx = float(np.median(disp[:, 0]))
                    dy = float(np.median(disp[:, 1]))
                    scale_x = self.altitude * np.tan(self.fov/2) / (self.img_w/2)
                    scale_y = self.altitude * np.tan(self.fov/2) / (self.img_h/2)
                    vx = -(dx * scale_x) / dt
                    vy = -(dy * scale_y) / dt
                    self.prev_pts = good_c.reshape(-1, 1, 2)

        if self.prev_pts is None or len(self.prev_pts) < 10:
            self.prev_pts = cv2.goodFeaturesToTrack(frame, mask=None, **self.feature_params)

        out = TwistStamped()
        out.header.stamp = curr_stamp
        out.header.frame_id = 'base_link'
        out.twist.linear.x = vx
        out.twist.linear.y = vy
        self.flow_pub.publish(out)
        self.prev_gray  = frame
        self.last_stamp = curr_stamp


def main(args=None):
    rclpy.init(args=args)
    node = OpticalFlowNode()
    try:    rclpy.spin(node)
    except KeyboardInterrupt: pass
    finally: node.destroy_node(); rclpy.shutdown()

if __name__ == '__main__':
    main()
PYEOF
echo "optical_flow_node.py created"
```

---

## 1.5 Verifikasi Rangefinder/Sonar Plugin

### OPSI A: SonarPlugin Ada
```xml
  <!-- RANGEFINDER dengan SonarPlugin -->
  <link name="rangefinder_link">
    <pose>0 0 -0.06 0 0 0</pose>
    <inertial>
      <mass>0.005</mass>
      <inertia>
        <ixx>0.0000002</ixx><ixy>0</ixy><ixz>0</ixz>
        <iyy>0.0000002</iyy><iyz>0</iyz>
        <izz>0.0000002</izz>
      </inertia>
    </inertial>
    <sensor name="sonar_down" type="gpu_ray">
      <always_on>1</always_on><update_rate>25</update_rate>
      <ray>
        <scan>
          <horizontal>
            <samples>1</samples><resolution>1</resolution>
            <min_angle>0</min_angle><max_angle>0</max_angle>
          </horizontal>
        </scan>
        <range><min>0.05</min><max>4.0</max><resolution>0.01</resolution></range>
        <noise><type>gaussian</type><mean>0.0</mean><stddev>0.005</stddev></noise>
      </ray>
      <plugin filename="libSonarPlugin.so" name="sonar_plugin">
        <fdm_addr>127.0.0.1</fdm_addr>
        <fdm_port_in>9007</fdm_port_in>
      </plugin>
    </sensor>
  </link>
  <joint name="rangefinder_joint" type="fixed">
    <parent>base_link</parent><child>rangefinder_link</child>
  </joint>
```

### OPSI B: Pakai Ray Sensor + Node Konverter

```xml
  <!-- RAY SENSOR standard Gazebo Harmonic -->
  <link name="rangefinder_link">
    <pose>0 0 -0.06 0 1.5708 0</pose>
    <inertial>
      <mass>0.005</mass>
      <inertia>
        <ixx>0.0000002</ixx><ixy>0</ixy><ixz>0</ixz>
        <iyy>0.0000002</iyy><iyz>0</iyz>
        <izz>0.0000002</izz>
      </inertia>
    </inertial>
    <sensor name="rangefinder_sensor" type="ray">
      <always_on>1</always_on><update_rate>25</update_rate>
      <visualize>true</visualize>
      <ray>
        <scan>
          <horizontal>
            <samples>1</samples><resolution>1</resolution>
            <min_angle>0</min_angle><max_angle>0</max_angle>
          </horizontal>
        </scan>
        <range><min>0.05</min><max>4.0</max><resolution>0.01</resolution></range>
        <noise><type>gaussian</type><mean>0</mean><stddev>0.005</stddev></noise>
      </ray>
    </sensor>
  </link>
  <joint name="rangefinder_joint" type="fixed">
    <parent>base_link</parent><child>rangefinder_link</child>
  </joint>
```

```bash
# Bridge + node konverter LaserScan→Range
cat > ~/syergie_ws/src/syergie_perception/syergie_perception/rangefinder_node.py << 'PYEOF'
#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan, Range

class RangefinderNode(Node):
    def __init__(self):
        super().__init__('rangefinder_node')
        self.sub = self.create_subscription(LaserScan, '/rangefinder/scan_raw', self.cb, 10)
        self.pub = self.create_publisher(Range, '/rangefinder/range', 10)
    def cb(self, msg: LaserScan):
        r = Range()
        r.header = msg.header
        r.radiation_type = Range.INFRARED
        r.field_of_view = 0.0523599  # 3 degrees
        r.min_range = msg.range_min
        r.max_range = msg.range_max
        if msg.ranges:
            v = msg.ranges[0]
            r.range = v if (msg.range_min <= v <= msg.range_max) else float('inf')
        else:
            r.range = float('inf')
        self.pub.publish(r)

def main(args=None):
    rclpy.init(args=args)
    n = RangefinderNode()
    try:    rclpy.spin(n)
    except KeyboardInterrupt: pass
    finally: n.destroy_node(); rclpy.shutdown()

if __name__ == '__main__':
    main()
PYEOF
```

### Verifikasi Rangefinder
```bash
ros2 topic echo /rangefinder/range --once
# PASS: range: 0.2xx (saat spawn z=0.2)

# Takeoff 2m, cek lagi:
ros2 topic echo /rangefinder/range --once
# PASS: range: ~2.0
```

---

## 1.6 Tambah Payload Spray ke SDF Iris

```bash
cat >> ~/syergie_ws/src/syergie_description/models/iris_syergie/model.sdf << 'SDFEOF'
  <!-- ============================================================
       SPRAY PAYLOAD: kotak 12x8x15cm, 350g
       Posisi: 12cm di bawah CoG drone
       ============================================================ -->
  <link name="spray_payload_link">
    <pose>0 0 -0.12 0 0 0</pose>
    <inertial>
      <mass>0.35</mass>
      <!-- Box: Ixx=m(b²+c²)/12, Iyy=m(a²+c²)/12, Izz=m(a²+b²)/12 -->
      <!-- a=0.12, b=0.08, c=0.15 -->
      <inertia>
        <ixx>0.000831</ixx><ixy>0</ixy><ixz>0</ixz>
        <iyy>0.000607</iyy><iyz>0</iyz>
        <izz>0.001114</izz>
      </inertia>
    </inertial>
    <collision name="payload_col">
      <geometry><box><size>0.12 0.08 0.15</size></box></geometry>
    </collision>
    <visual name="tank_vis">
      <geometry><cylinder><radius>0.04</radius><length>0.12</length></cylinder></geometry>
      <material>
        <ambient>1.0 0.9 0.0 1</ambient>
        <diffuse>1.0 0.85 0.0 1</diffuse>
      </material>
    </visual>
    <visual name="nozzle_vis">
      <pose>0 0 -0.07 0 0 0</pose>
      <geometry><box><size>0.03 0.03 0.02</size></box></geometry>
      <material><ambient>0.3 0.3 0.3 1</ambient></material>
    </visual>
  </link>
  <joint name="spray_payload_joint" type="fixed">
    <parent>base_link</parent><child>spray_payload_link</child>
  </joint>

  <!-- PARTICLE EMITTER untuk efek visual serbuk sari -->
  <link name="particle_emitter_link">
    <pose>0 0 -0.27 0 0 0</pose>
    <inertial>
      <mass>0.001</mass>
      <inertia>
        <ixx>0.00000001</ixx><ixy>0</ixy><ixz>0</ixz>
        <iyy>0.00000001</iyy><iyz>0</iyz>
        <izz>0.00000001</izz>
      </inertia>
    </inertial>
    <visual name="emitter_marker">
      <geometry><sphere><radius>0.005</radius></sphere></geometry>
      <material><ambient>1 1 0 0.5</ambient></material>
    </visual>
    <particle_emitter name="spray_emitter" type="box">
      <emitting>false</emitting>
      <size>0.05 0.05 0.01</size>
      <particle_size>0.01 0.01 0.01</particle_size>
      <lifetime>2.0</lifetime>
      <min_velocity>0.5</min_velocity>
      <max_velocity>1.5</max_velocity>
      <scale_rate>0.5</scale_rate>
      <color_start>1.0 0.95 0.7 0.8</color_start>
      <color_end>1.0 0.95 0.7 0.0</color_end>
    </particle_emitter>
  </link>
  <joint name="particle_emitter_joint" type="fixed">
    <parent>spray_payload_link</parent><child>particle_emitter_link</child>
  </joint>
SDFEOF
echo "Payload SDF appended"
```

---

## 1.7 Perhitungan Weight Budget dan Inertia

### Formula Momen Inersia

```
BOX (a×b×c, massa m):
  Ixx = m(b²+c²)/12    Iyy = m(a²+c²)/12    Izz = m(a²+b²)/12

CYLINDER (radius r, panjang l, massa m, sumbu Z):
  Ixx = Iyy = m(3r²+l²)/12    Izz = mr²/2

SPHERE (radius r, massa m):
  Ixx = Iyy = Izz = 2mr²/5

PARALLEL AXIS THEOREM (offset d dari CoM):
  I_total = I_cm + m·d²
```

### Weight Budget

| Komponen | Massa (kg) |
|----------|-----------|
| Iris base + electronics | 1.500 |
| Baterai 4S 5000mAh | 0.450 |
| Kamera forward | 0.015 |
| Kamera downward | 0.010 |
| Rangefinder | 0.005 |
| Spray payload (penuh) | 0.350 |
| **TOTAL** | **2.330** |

```
T_hover = 2.330 × 9.81 = 22.86 N
T_max   ≈ 4 × 13 N   = 52 N
Safety  = 52 / 22.86  = 2.27× → AMAN (hover ≈ 44% throttle)
```

### Script Kalkulator
```python
#!/usr/bin/env python3
# python3 ~/syergie_ws/calc_inertia.py

def box_inertia(m, a, b, c):
    return m*(b**2+c**2)/12, m*(a**2+c**2)/12, m*(a**2+b**2)/12

def cylinder_inertia(m, r, l):
    Ixx = m*(3*r**2+l**2)/12
    return Ixx, Ixx, m*r**2/2

def sphere_inertia(m, r):
    I = 2*m*r**2/5; return I, I, I

print("=== Spray Payload (box 12x8x15cm, 0.35kg) ===")
Ixx,Iyy,Izz = box_inertia(0.35, 0.12, 0.08, 0.15)
print(f"  Ixx={Ixx:.6f}  Iyy={Iyy:.6f}  Izz={Izz:.6f}")

print("=== Canopy (sphere r=2m, 5kg) ===")
I,_,_ = sphere_inertia(5.0, 2.0)
print(f"  Ixx=Iyy=Izz={I:.4f}")

total = 2.330
print(f"\n=== Weight Budget ===")
print(f"  Total: {total} kg  |  T_hover: {total*9.81:.2f}N  |  Safety: {52/(total*9.81):.2f}x")
```

---

## 1.8 ros_gz_bridge Configuration Lengkap

### Cara Kerja Bridge

```
Gazebo Transport (Protobuf binary)
         │
         │  ros_gz_bridge
         │  Type Registry: gz.msgs.Image ↔ sensor_msgs/Image
         │  Deserialize → Map fields → Serialize
         │
ROS2 DDS/CDR binary
```

**Sintaks arah bridge:**
- `[gz_type` → Gazebo ke ROS2 (GZ_TO_ROS)
- `]gz_type` → ROS2 ke Gazebo (ROS_TO_GZ)
- `@gz_type` → Bidirectional (hati-hati: bisa loop!)

### bridge_config.yaml
```bash
mkdir -p ~/syergie_ws/src/syergie_bringup/config
cat > ~/syergie_ws/src/syergie_bringup/config/bridge_config.yaml << 'YAMLEOF'
bridges:
  # Clock sinkronisasi
  - gz_topic_name: /clock
    ros_topic_name: /clock
    gz_type_name: gz.msgs.Clock
    ros_type_name: rosgraph_msgs/msg/Clock
    direction: GZ_TO_ROS

  # Kamera forward → /camera/front/image_raw
  - gz_topic_name: /world/palm_world/model/iris_syergie/link/camera_front_link/sensor/camera_front/image
    ros_topic_name: /camera/front/image_raw
    gz_type_name: gz.msgs.Image
    ros_type_name: sensor_msgs/msg/Image
    direction: GZ_TO_ROS

  # Camera info (untuk vision algorithms)
  - gz_topic_name: /world/palm_world/model/iris_syergie/link/camera_front_link/sensor/camera_front/camera_info
    ros_topic_name: /camera/front/camera_info
    gz_type_name: gz.msgs.CameraInfo
    ros_type_name: sensor_msgs/msg/CameraInfo
    direction: GZ_TO_ROS

  # Kamera downward (optical flow)
  - gz_topic_name: /world/palm_world/model/iris_syergie/link/camera_down_link/sensor/camera_down/image
    ros_topic_name: /camera/down/image_raw
    gz_type_name: gz.msgs.Image
    ros_type_name: sensor_msgs/msg/Image
    direction: GZ_TO_ROS

  # Rangefinder (LaserScan single-beam)
  - gz_topic_name: /world/palm_world/model/iris_syergie/link/rangefinder_link/sensor/rangefinder_sensor/scan
    ros_topic_name: /rangefinder/scan_raw
    gz_type_name: gz.msgs.LaserScan
    ros_type_name: sensor_msgs/msg/LaserScan
    direction: GZ_TO_ROS

  # IMU (backup/debug)
  - gz_topic_name: /world/palm_world/model/iris_syergie/link/base_link/sensor/imu_sensor/imu
    ros_topic_name: /imu/data_raw
    gz_type_name: gz.msgs.IMU
    ros_type_name: sensor_msgs/msg/Imu
    direction: GZ_TO_ROS

  # Kontrol Spray: ROS2 → Gazebo ParticleEmitter
  - gz_topic_name: /world/palm_world/model/iris_syergie/link/particle_emitter_link/particle_emitter/spray_emitter/cmd
    ros_topic_name: /spray/cmd
    gz_type_name: gz.msgs.Boolean
    ros_type_name: std_msgs/msg/Bool
    direction: ROS_TO_GZ
YAMLEOF
echo "bridge_config.yaml created"
```

### Mapping Type Referensi

| Sensor | ROS2 Type | Gazebo Type | Arah |
|--------|-----------|-------------|------|
| Kamera | `sensor_msgs/msg/Image` | `gz.msgs.Image` | GZ→ROS |
| Camera Info | `sensor_msgs/msg/CameraInfo` | `gz.msgs.CameraInfo` | GZ→ROS |
| IMU | `sensor_msgs/msg/Imu` | `gz.msgs.IMU` | GZ→ROS |
| LaserScan | `sensor_msgs/msg/LaserScan` | `gz.msgs.LaserScan` | GZ→ROS |
| Bool/Switch | `std_msgs/msg/Bool` | `gz.msgs.Boolean` | ROS→GZ |
| Pose | `geometry_msgs/msg/Pose` | `gz.msgs.Pose` | GZ→ROS |
| Clock | `rosgraph_msgs/msg/Clock` | `gz.msgs.Clock` | GZ→ROS |

### Jalankan Bridge dengan Config File
```bash
ros2 run ros_gz_bridge parameter_bridge \
    --ros-args \
    -p config_file:=$HOME/syergie_ws/src/syergie_bringup/config/bridge_config.yaml
```

---

## 1.9 Launch File Phase 1

```bash
mkdir -p ~/syergie_ws/src/syergie_bringup/launch
cat > ~/syergie_ws/src/syergie_bringup/launch/spawn_drone.launch.py << 'PYEOF'
"""spawn_drone.launch.py — Phase 1: spawn iris_syergie + bridge semua sensor"""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import ExecuteProcess, TimerAction, DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    desc_dir    = get_package_share_directory('syergie_description')
    bringup_dir = get_package_share_directory('syergie_bringup')
    model_dir   = os.path.join(desc_dir, 'models')
    iris_sdf    = os.path.join(model_dir, 'iris_syergie', 'model.sdf')
    bridge_cfg  = os.path.join(bringup_dir, 'config', 'bridge_config.yaml')
    gz_resource = f"{model_dir}:{os.environ.get('GZ_SIM_RESOURCE_PATH','')}"

    gazebo = ExecuteProcess(
        cmd=['gz', 'sim', '-r', 'empty.sdf', '-v', '3'],
        additional_env={'GZ_SIM_RESOURCE_PATH': gz_resource},
        output='screen')

    spawn = TimerAction(period=3.0, actions=[
        ExecuteProcess(cmd=[
            'gz', 'model', '--spawn-file', iris_sdf,
            '--model-name', 'iris_syergie', '-x','0','-y','0','-z','0.2'],
            output='screen')])

    bridge = TimerAction(period=5.0, actions=[
        Node(package='ros_gz_bridge', executable='parameter_bridge',
             name='ros_gz_bridge',
             parameters=[{'config_file': bridge_cfg}], output='screen')])

    rangefinder = TimerAction(period=6.0, actions=[
        Node(package='syergie_perception', executable='rangefinder_node',
             name='rangefinder_node', output='screen')])

    return LaunchDescription([gazebo, spawn, bridge, rangefinder])
PYEOF
echo "spawn_drone.launch.py created"
```

### Verifikasi Semua Sensor Aktif
```bash
# Setelah launch:
for topic in /camera/front/image_raw /camera/down/image_raw \
             /rangefinder/range /imu/data_raw; do
    rate=$(timeout 5 ros2 topic hz $topic 2>&1 | grep "average rate" | awk '{print $3}')
    printf "%-35s %s Hz\n" "$topic" "${rate:-0}"
done
```

---

## MILESTONE CHECKPOINT PHASE 1

**[ ] Item 1: Model iris_syergie tersimpan**
```bash
ls ~/syergie_ws/src/syergie_description/models/iris_syergie/
# PASS: ada model.config dan model.sdf
```

**[ ] Item 2: Kamera forward topic tersedia di Gazebo**
```bash
gz topic -l 2>/dev/null | grep camera_front
# PASS: ada topic kamera
```

**[ ] Item 3: Kamera forward 30 Hz di ROS2**
```bash
timeout 5 ros2 topic hz /camera/front/image_raw 2>&1 | grep "average rate"
# PASS: ~30.0 Hz
```

**[ ] Item 4: Kamera downward tersedia**
```bash
timeout 5 ros2 topic hz /camera/down/image_raw 2>&1 | grep "average rate"
# PASS: ~50.0 Hz
```

**[ ] Item 5: Rangefinder data valid**
```bash
ros2 topic echo /rangefinder/range --once 2>/dev/null | grep "range:"
# PASS: nilai antara 0.05 dan 4.0
```

**[ ] Item 6: Optical flow node berjalan**
```bash
ros2 node list | grep optical_flow
# PASS: /optical_flow_node
```

**[ ] Item 7: Optical flow publish**
```bash
timeout 5 ros2 topic hz /optical_flow/velocity 2>&1 | grep "average rate"
# PASS: rate > 0
```

**[ ] Item 8: Spray payload visible di Gazebo**
```bash
# Manual: lihat di Gazebo GUI, harus ada silinder kuning di bawah drone
gz model -m iris_syergie --info 2>/dev/null | grep "spray_payload"
# PASS: link spray_payload_link ada
```

**[ ] Item 9: ParticleEmitter bisa dikontrol**
```bash
ros2 topic pub --once /spray/cmd std_msgs/msg/Bool "data: true"
# PASS: partikel muncul di Gazebo GUI selama ~3 detik
```

**[ ] Item 10: bridge_config.yaml loaded**
```bash
ros2 node info /ros_gz_bridge 2>/dev/null | grep "Publications\|Subscriptions" -A 5
# PASS: ada minimal 5 topic
```

**[ ] Item 11: IMU data tersedia**
```bash
ros2 topic echo /imu/data_raw --once 2>/dev/null | grep angular_velocity
# PASS: ada nilai numerik
```

**[ ] Item 12: Weight budget aman**
```bash
python3 -c "m=2.33; T=52; print(f'Safety: {T/(m*9.81):.2f}x'); assert T/(m*9.81)>1.5"
# PASS: Safety > 1.5x
```

---

# PHASE 2 — World Environment Kebun Sawit {#phase-2}

> **Tujuan:** Membangun lingkungan simulasi kebun sawit yang performant — 100 pohon sawit, AprilTag markers, ground plane luas, dan fisika yang terkonfigurasi dengan baik.

---

## 2.1 Membuat Model Pohon Sawit Minimal

### Mengapa Primitif SDF, Bukan Mesh CAD?

| Aspek | SDF Primitif | Mesh CAD (.dae) |
|-------|-------------|-----------------|
| Vertex count | ~20 per pohon | 5.000-50.000 |
| 100 pohon | ~2.000 vertex | 500.000-5.000.000 vertex |
| FPS sim | 40-60 FPS | 5-15 FPS |
| Build time | 0 menit | beberapa jam |
| Tujuan nav | ✓ cukup | ✓ terlalu detail |

### Buat Model
```bash
mkdir -p ~/syergie_ws/src/syergie_description/models/palm_tree
cat > ~/syergie_ws/src/syergie_description/models/palm_tree/model.config << 'EOF'
<?xml version="1.0"?>
<model>
  <name>Palm Tree Syergie</name>
  <version>1.0</version>
  <sdf version="1.9">model.sdf</sdf>
  <description>Simplified palm tree: trunk (cylinder), canopy (sphere),
    bloom target (red sphere). Optimized for simulation performance.</description>
</model>

```xml
<?xml version="1.0"?>
<sdf version="1.9">
  <model name="palm_tree">
    <static>true</static>
    <link name="trunk">
      <pose>0 0 2.5 0 0 0</pose>
      <inertial><mass>50.0</mass>
        <inertia><ixx>104.69</ixx><ixy>0</ixy><ixz>0</ixz>
          <iyy>104.69</iyy><iyz>0</iyz><izz>0.5625</izz></inertia>
      </inertial>
      <collision name="trunk_col"><geometry>
        <cylinder><radius>0.15</radius><length>5.0</length></cylinder>
      </geometry></collision>
      <visual name="trunk_vis">
        <geometry><cylinder><radius>0.15</radius><length>5.0</length></cylinder></geometry>
        <material><ambient>0.35 0.22 0.08 1</ambient><diffuse>0.45 0.28 0.10 1</diffuse></material>
      </visual>
    </link>
    <link name="canopy">
      <pose>0 0 5.5 0 0 0</pose>
      <inertial><mass>5.0</mass>
        <inertia><ixx>8.0</ixx><ixy>0</ixy><ixz>0</ixz>
          <iyy>8.0</iyy><iyz>0</iyz><izz>8.0</izz></inertia>
      </inertial>
      <collision name="canopy_col"><geometry><sphere><radius>2.0</radius></sphere></geometry></collision>
      <visual name="canopy_vis">
        <geometry><sphere><radius>2.0</radius></sphere></geometry>
        <material><ambient>0.1 0.5 0.1 0.7</ambient><diffuse>0.15 0.6 0.12 0.7</diffuse></material>
        <transparency>0.3</transparency>
      </visual>
    </link>
    <link name="bloom_target">
      <pose>0.5 0 5.0 0 0 0</pose>
      <inertial><mass>0.1</mass>
        <inertia><ixx>0.000576</ixx><ixy>0</ixy><ixz>0</ixz>
          <iyy>0.000576</iyy><iyz>0</iyz><izz>0.000576</izz></inertia>
      </inertial>
      <visual name="bloom_vis">
        <geometry><sphere><radius>0.12</radius></sphere></geometry>
        <material><ambient>0.8 0.1 0.1 1</ambient><emissive>0.3 0.0 0.0 1</emissive></material>
      </visual>
    </link>
    <joint name="canopy_j" type="fixed"><parent>trunk</parent><child>canopy</child></joint>
    <joint name="bloom_j"  type="fixed"><parent>canopy</parent><child>bloom_target</child></joint>
  </model>
</sdf>
```

### Verifikasi Model
```bash
xmllint --noout ~/syergie_ws/src/syergie_description/models/palm_tree/model.sdf && echo "PASS: XML valid"
```

---

## 2.2 Python Script Generator Baris Pohon

```bash
mkdir -p ~/syergie_ws/src/syergie_description/scripts
cat > ~/syergie_ws/src/syergie_description/scripts/generate_palm_field.py << 'PYEOF'
#!/usr/bin/env python3
"""Generate SDF grid pohon sawit. Usage: python3 generate_palm_field.py --rows 10 --cols 10"""
import argparse, os, random

def generate_palm_field_sdf(rows=10, cols=10, spacing_x=9.0, spacing_y=9.0,
                             origin_x=-40.0, origin_y=-40.0, jitter=0.3,
                             yaw_jitter=0.3, output_file=None):
    random.seed(42)
    lines = ['<?xml version="1.0"?>', '<sdf version="1.9">',
             f'  <!-- Palm Field: {rows}x{cols}, spacing {spacing_x}x{spacing_y}m -->',
             '  <world name="palm_field_fragment">']
    for row in range(rows):
        for col in range(cols):
            x   = origin_x + col*spacing_x + random.uniform(-jitter, jitter)
            y   = origin_y + row*spacing_y + random.uniform(-jitter, jitter)
            yaw = random.uniform(-yaw_jitter, yaw_jitter)
            lines += [
                f'    <!-- [{row},{col}] -->',
                f'    <include>',
                f'      <uri>model://palm_tree</uri>',
                f'      <name>palm_{row:02d}_{col:02d}</name>',
                f'      <pose>{x:.4f} {y:.4f} 0 0 0 {yaw:.4f}</pose>',
                f'    </include>'
            ]
    lines += ['  </world>', '</sdf>']
    sdf = '\n'.join(lines) + '\n'
    if output_file:
        os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
        with open(output_file, 'w') as f: f.write(sdf)
        print(f"[OK] {rows*cols} pohon → {output_file}")
    return sdf

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--rows', type=int, default=10)
    p.add_argument('--cols', type=int, default=10)
    p.add_argument('--spacing_x', type=float, default=9.0)
    p.add_argument('--spacing_y', type=float, default=9.0)
    p.add_argument('--origin_x',  type=float, default=-40.0)
    p.add_argument('--origin_y',  type=float, default=-40.0)
    p.add_argument('--jitter',    type=float, default=0.3)
    p.add_argument('--output', type=str,
        default=os.path.expanduser(
            '~/syergie_ws/src/syergie_description/worlds/palm_field.sdf'))
    a = p.parse_args()
    generate_palm_field_sdf(**vars(a))
PYEOF
chmod +x ~/syergie_ws/src/syergie_description/scripts/generate_palm_field.py

# Jalankan:
mkdir -p ~/syergie_ws/src/syergie_description/worlds
python3 ~/syergie_ws/src/syergie_description/scripts/generate_palm_field.py
grep -c "<include>" ~/syergie_ws/src/syergie_description/worlds/palm_field.sdf
# PASS: 100
```

---

## 2.3 World File Utama

```bash
cat > ~/syergie_ws/src/syergie_description/worlds/palm_world.sdf << 'EOF'
<?xml version="1.0"?>
<sdf version="1.9">
  <world name="palm_world">
    <physics name="default_physics" default="true" type="ode">
      <max_step_size>0.001</max_step_size>
      <real_time_factor>1.0</real_time_factor>
      <real_time_update_rate>1000</real_time_update_rate>
      <ode>
        <solver><type>quick</type><iters>50</iters><sor>1.3</sor></solver>
      </ode>
    </physics>
    <light name="sun" type="directional">
      <diffuse>0.9 0.9 0.9 1</diffuse>
      <direction>-0.5 0.1 -0.9</direction>
      <cast_shadows>false</cast_shadows>
    </light>
    <model name="ground_plane">
      <static>true</static>
      <link name="link">
        <collision name="c"><geometry>
          <plane><normal>0 0 1</normal><size>200 200</size></plane>
        </geometry></collision>
        <visual name="v">
          <geometry><plane><normal>0 0 1</normal><size>200 200</size></plane></geometry>
          <material><ambient>0.45 0.35 0.25 1</ambient></material>
        </visual>
      </link>
    </model>
    <scene>
      <ambient>0.4 0.4 0.4 1</ambient>
      <background>0.53 0.81 0.94 1</background>
      <shadows>false</shadows>
    </scene>
  </world>
</sdf>
EOF
```

```bash
# Script build world lengkap (embed pohon):
cat > ~/syergie_ws/src/syergie_description/scripts/build_world.py << 'PYEOF'
#!/usr/bin/env python3
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from generate_palm_field import generate_palm_field_sdf

def build():
    field = generate_palm_field_sdf(rows=10, cols=10,
        spacing_x=9.0, spacing_y=9.0, origin_x=-40.0, origin_y=-40.0)
    # Ekstrak <include> blocks saja
    includes = [l for l in field.split('\n')
                if not any(x in l for x in ['<?xml','<sdf','</sdf>','<world','</world>'])]
    section = '\n'.join('    '+l for l in includes if l.strip())
    tpl = os.path.join(os.path.dirname(__file__),'..','worlds','palm_world.sdf')
    with open(tpl) as f: world = f.read()
    world = world.replace('  </world>', section + '\n  </world>')
    out = os.path.expanduser('~/syergie_ws/src/syergie_description/worlds/palm_world_complete.sdf')
    with open(out, 'w') as f: f.write(world)
    print(f"[OK] Complete world → {out}")

if __name__ == '__main__':
    build()
PYEOF
python3 ~/syergie_ws/src/syergie_description/scripts/build_world.py
```

---

## 2.4 AprilTag Models

```bash
mkdir -p ~/syergie_ws/src/syergie_description/models/apriltag_pole
cat > ~/syergie_ws/src/syergie_description/models/apriltag_pole/model.config << 'EOF'
<?xml version="1.0"?>
<model>
  <name>AprilTag Pole</name><version>1.0</version>
  <sdf version="1.9">model.sdf</sdf>
  <description>Tiang 2m dengan AprilTag untuk navigasi drone</description>
</model>
EOF

cat > ~/syergie_ws/src/syergie_description/models/apriltag_pole/model.sdf << 'EOF'
<?xml version="1.0"?>
<sdf version="1.9">
  <model name="apriltag_pole">
    <static>true</static>
    <link name="pole">
      <pose>0 0 1 0 0 0</pose>
      <inertial><mass>2.0</mass>
        <inertia><ixx>0.67</ixx><ixy>0</ixy><ixz>0</ixz>
          <iyy>0.67</iyy><iyz>0</iyz><izz>0.009</izz></inertia>
      </inertial>
      <collision name="c"><geometry>
        <cylinder><radius>0.03</radius><length>2.0</length></cylinder>
      </geometry></collision>
      <visual name="v">
        <geometry><cylinder><radius>0.03</radius><length>2.0</length></cylinder></geometry>
        <material><ambient>0.5 0.5 0.5 1</ambient></material>
      </visual>
    </link>
    <link name="tag_marker">
      <pose>0 0 2.1 0 0 0</pose>
      <inertial><mass>0.01</mass>
        <inertia><ixx>0.00003</ixx><ixy>0</ixy><ixz>0</ixz>
          <iyy>0.00003</iyy><iyz>0</iyz><izz>0.00006</izz></inertia>
      </inertial>
      <collision name="c"><geometry><box><size>0.2 0.2 0.005</size></box></geometry></collision>
      <visual name="v">
        <geometry><box><size>0.2 0.2 0.005</size></box></geometry>
        <material><ambient>1 1 1 1</ambient><diffuse>1 1 1 1</diffuse></material>
      </visual>
    </link>
    <joint name="j" type="fixed"><parent>pole</parent><child>tag_marker</child></joint>
  </model>
</sdf>
EOF

# Tambah ke world:
for pole in "tag_NE 50 50" "tag_NW -50 50" "tag_SE 50 -50" "tag_SW -50 -50"; do
    name=$(echo $pole | cut -d' ' -f1)
    x=$(echo $pole | cut -d' ' -f2)
    y=$(echo $pole | cut -d' ' -f3)
    sed -i "s|  </world>|    <include><uri>model://apriltag_pole</uri><name>${name}</name><pose>${x} ${y} 0 0 0 0</pose></include>\n  </world>|" \
        ~/syergie_ws/src/syergie_description/worlds/palm_world_complete.sdf
done
```

---

## 2.5 Spawn Point dan World Frame

```
ENU (Gazebo/ROS2): X=East, Y=North, Z=Up
NED (ArduPilot):   X=North, Y=East, Z=Down
MAVROS2 otomatis konversi → pakai ENU di semua node ROS2 kita.
```

```bash
# Verifikasi: takeoff 2m → z ≈ +2.0
ros2 topic echo /mavros/local_position/pose --once | grep "z:"
# PASS: z: 2.0xxx
```

---

## 2.6 Performance Testing

```bash
gz stats -w palm_world 2>/dev/null | tail -3
# PASS: Factor > 0.8

# Jika lambat:
# 1. --rows 5 --cols 5 untuk development
# 2. kamera update_rate 30→15
# 3. real_time_factor 1.0→0.5
```

---

## MILESTONE CHECKPOINT PHASE 2

**[ ] Item 1:** `xmllint --noout ~/syergie_ws/src/syergie_description/models/palm_tree/model.sdf && echo PASS`

**[ ] Item 2: Generator 100 pohon**
```bash
python3 ~/syergie_ws/src/syergie_description/scripts/generate_palm_field.py \
    --rows 10 --cols 10 --output /tmp/t.sdf
grep -c "<include>" /tmp/t.sdf   # PASS: 100
```

**[ ] Item 3:** `xmllint --noout ~/syergie_ws/src/syergie_description/worlds/palm_world_complete.sdf && echo PASS`

**[ ] Item 4: Gazebo load world**
```bash
timeout 15 gz sim -s ~/syergie_ws/src/syergie_description/worlds/palm_world_complete.sdf \
    --headless-rendering 2>&1 | grep -i "critical\|fatal" | wc -l
# PASS: 0 fatal errors
```

**[ ] Item 5:** `gz model -l 2>/dev/null | grep palm | wc -l` → PASS: ≥ 25

**[ ] Item 6:** `ls ~/syergie_ws/src/syergie_description/models/apriltag_pole/model.sdf && echo PASS`

**[ ] Item 7: Spawn di (0,0,0.2)**
```bash
ros2 topic echo /mavros/local_position/pose --once 2>/dev/null | grep "z:"
# PASS: z ≈ 0.2
```

**[ ] Item 8: Real-time factor > 0.8** — check `gz stats` output manually

**[ ] Item 9: Collision aktif** — drone tidak menembus pohon (visual check)

**[ ] Item 10: Z positif saat naik** — ENU frame benar

---

# PHASE 3 — MAVROS2 & ArduPilot Integration {#phase-3}

> **Tujuan:** Konfigurasi EKF3 GPS-denied, verifikasi optical flow + rangefinder, kontrol drone penuh via ROS2.

---

## 3.1 Parameter Setup GPS-Denied

### Penjelasan EKF3 Singkat

EKF3 menggabungkan prediksi dari IMU dengan koreksi dari sensor. Untuk GPS-denied:

```
PREDICT: State_t = f(State_{t-1}, IMU_data)
UPDATE:  State_t += K * (sensor_measurement - predicted_measurement)

Optical flow → update velocity (vx, vy)
Rangefinder  → update altitude + scale optical flow
Barometer    → update altitude Z

WAJIB: rangefinder aktif agar optical flow bisa di-scale ke m/s
```

### EK3_SRC Parameter

| Parameter | Nilai | Keterangan |
|-----------|-------|------------|
| `EK3_SRC1_POSXY` | 5 | XY position: optical flow |
| `EK3_SRC1_VELXY` | 5 | XY velocity: optical flow |
| `EK3_SRC1_POSZ`  | 1 | Z position: barometer |
| `EK3_SRC1_VELZ`  | 6 | Z velocity: rangefinder |
| `EK3_SRC1_YAW`   | 1 | Yaw: magnetometer |

```bash
cat > ~/syergie_ws/src/syergie_bringup/config/ardupilot_params_gpsdeny.parm << 'EOF'
GPS_TYPE,0
GPS_TYPE2,0
AHRS_EKF_TYPE,3
EK3_ENABLE,1
EK2_ENABLE,0
EK3_SRC1_POSXY,5
EK3_SRC1_VELXY,5
EK3_SRC1_POSZ,1
EK3_SRC1_VELZ,6
EK3_SRC1_YAW,1
FLOW_TYPE,10
RNGFND1_TYPE,10
RNGFND1_MIN_CM,5
RNGFND1_MAX_CM,400
RNGFND1_ORIENT,25
EK3_FLOW_NOISE,0.15
EK3_RNG_M_NSE,0.05
ARMING_CHECK,0
FS_THR_ENABLE,0
FS_GCS_ENABLE,0
BATT_MONITOR,0
EOF

# Load via MAVProxy:
# param load ~/syergie_ws/src/syergie_bringup/config/ardupilot_params_gpsdeny.parm
# param save && reboot
```

```bash
# Set via ROS2:
for p in "GPS_TYPE 0" "EK3_SRC1_POSXY 5" "EK3_SRC1_VELXY 5" "FLOW_TYPE 10" "RNGFND1_TYPE 10"; do
    name=$(echo $p|cut -d' ' -f1); val=$(echo $p|cut -d' ' -f2)
    ros2 service call /mavros/param/set mavros_msgs/srv/ParamSetV2 \
        "{param_id: '$name', value: {integer: $val}}" 2>/dev/null | grep success
done
```

---

## 3.2 apm_config.yaml dan mavros.launch.py

```bash
mkdir -p ~/syergie_ws/src/syergie_bringup/config ~/syergie_ws/src/syergie_bringup/launch

cat > ~/syergie_ws/src/syergie_bringup/config/apm_config.yaml << 'EOF'
mavros:
  ros__parameters:
    fcu_url: "udp://:14550@127.0.0.1:14551"
    gcs_url: "udp://@127.0.0.1:14553"
    system_id: 255
    component_id: 240
    target_system_id: 1
    target_component_id: 1
    map_frame_id: "map"
    odom_frame_id: "odom"
    base_link_frame_id: "base_link"
    conn:
      timeout: 10.0
      timesync_rate: 10.0
      heartbeat_rate: 1.0
      heartbeat_mav_type: 2
EOF
```

```bash
cat > ~/syergie_ws/src/syergie_bringup/launch/mavros.launch.py << 'EOF'
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    bringup = get_package_share_directory('syergie_bringup')
    cfg = os.path.join(bringup, 'config', 'apm_config.yaml')
    fcu = DeclareLaunchArgument('fcu_url', default_value='udp://:14550@127.0.0.1:14551')
    node = Node(package='mavros', executable='mavros_node',
        name='mavros', namespace='mavros', output='screen',
        parameters=[cfg, {'fcu_url': LaunchConfiguration('fcu_url')}])
    return LaunchDescription([fcu, node])
EOF
```

### Verifikasi
```bash
ros2 topic echo /mavros/state --once
# connected: true, armed: false, mode: STABILIZE

ros2 topic hz /mavros/imu/data
# average rate: ~100.0 Hz

ros2 topic echo /mavros/local_position/pose --once
# ada nilai position.x/y/z
```

---

## 3.3 Verifikasi EKF Status

```bash
ros2 topic echo /mavros/estimator_status --once
# Untuk GPS-denied, HARUS true:
#   attitude_status_flag: true
#   velocity_horiz_status_flag: true
#   pos_horiz_rel_status_flag: true
#   pos_vert_agl_status_flag: true
# BOLEH false (expected):
#   pos_horiz_abs_status_flag: false  ← GPS disabled, NORMAL
```

```bash
# Monitor otomatis:
python3 -c "
import rclpy
from rclpy.node import Node
from mavros_msgs.msg import EstimatorStatus
class EKF(Node):
    def __init__(self):
        super().__init__('ekf')
        self.create_subscription(EstimatorStatus,'/mavros/estimator_status',self.cb,10)
    def cb(self,m):
        ok=m.velocity_horiz_status_flag and m.pos_horiz_rel_status_flag
        self.get_logger().info(('OK' if ok else 'FAIL')+
            f' vel={m.velocity_horiz_status_flag} pos={m.pos_horiz_rel_status_flag} agl={m.pos_vert_agl_status_flag}')
rclpy.init()
n=EKF()
try: rclpy.spin(n)
except: pass
finally: n.destroy_node(); rclpy.shutdown()
"
```

---

## 3.4 Test Basic Control

```bash
# Arm:
ros2 service call /mavros/cmd/arming mavros_msgs/srv/CommandBool "{value: true}"

# Mode GUIDED:
ros2 service call /mavros/set_mode mavros_msgs/srv/SetMode "{custom_mode: 'GUIDED'}"

# Takeoff 2m:
ros2 service call /mavros/cmd/takeoff mavros_msgs/srv/CommandTOL \
    "{altitude: 2.0, latitude: 0.0, longitude: 0.0, min_pitch: 0.0, yaw: 0.0}"

# Forward 0.5 m/s:
ros2 topic pub /mavros/setpoint_velocity/cmd_vel geometry_msgs/msg/TwistStamped \
    "{header:{frame_id:'base_link'},twist:{linear:{x:0.5,y:0.0,z:0.0}}}" --rate 10

# Land:
ros2 service call /mavros/set_mode mavros_msgs/srv/SetMode "{custom_mode: 'LAND'}"
```

---

## 3.5 Test FLOWHOLD Mode

```bash
ros2 service call /mavros/set_mode mavros_msgs/srv/SetMode "{custom_mode: 'FLOWHOLD'}"
ros2 topic echo /mavros/state --once | grep mode
# PASS: mode: FLOWHOLD

# Monitor drift posisi:
watch -n1 "ros2 topic echo /mavros/local_position/pose --once 2>/dev/null | grep position -A 3"
# PASS: x,y tidak drift > 0.5m dalam 30 detik
```

---

## 3.6 sitl_mavros.launch.py

```bash
cat > ~/syergie_ws/src/syergie_bringup/launch/sitl_mavros.launch.py << 'EOF'
import os
from launch import LaunchDescription
from launch.actions import ExecuteProcess, TimerAction, RegisterEventHandler, Shutdown, DeclareLaunchArgument
from launch.event_handlers import OnProcessExit
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    ardupilot = os.path.expanduser('~/ardupilot')
    bringup   = get_package_share_directory('syergie_bringup')
    cfg       = os.path.join(bringup, 'config', 'apm_config.yaml')
    fcu_arg   = DeclareLaunchArgument('fcu_url', default_value='udp://:14550@127.0.0.1:14551')

    sitl = ExecuteProcess(
        cmd=['bash','-c',
             f'cd {ardupilot} && python3 Tools/autotest/sim_vehicle.py '
             f'-v ArduCopter -f gazebo-iris --model=gazebo --no-rebuild '
             f'--out=127.0.0.1:14551 --out=127.0.0.1:14553 '
             f'-l 37.613,-122.357,-3.45,270 2>&1 | tee /tmp/sitl.log'],
        name='ardupilot_sitl', shell=True, output='screen')

    mavros = TimerAction(period=8.0, actions=[
        Node(package='mavros', executable='mavros_node',
             name='mavros', namespace='mavros', output='screen',
             parameters=[cfg,{'fcu_url':LaunchConfiguration('fcu_url')}])])

    return LaunchDescription([fcu_arg, sitl, mavros,
        RegisterEventHandler(OnProcessExit(target_action=sitl,
            on_exit=[Shutdown(reason='SITL exited')]))])
EOF
```

---

## MILESTONE CHECKPOINT PHASE 3

**[ ] Item 1:** `ls ~/syergie_ws/src/syergie_bringup/config/ardupilot_params_gpsdeny.parm && echo PASS`

**[ ] Item 2:** `ros2 topic echo /mavros/state --once | grep "connected: true"`

**[ ] Item 3:** `ros2 service call /mavros/param/get mavros_msgs/srv/ParamGet "{param_id: 'GPS_TYPE'}" | grep "integer: 0"`

**[ ] Item 4:** `ros2 service call /mavros/param/get mavros_msgs/srv/ParamGet "{param_id: 'EK3_SRC1_POSXY'}" | grep "integer: 5"`

**[ ] Item 5:** `ros2 topic echo /mavros/estimator_status --once | grep "attitude_status_flag: true"`

**[ ] Item 6:** `timeout 5 ros2 topic hz /mavros/imu/data | grep "average rate"` → > 90 Hz

**[ ] Item 7:** `ros2 topic echo /mavros/local_position/pose --once | grep position -A 3` → ada nilai

**[ ] Item 8:** Arm sukses: `ros2 service call /mavros/cmd/arming ... "{value: true}" | grep "success: true"`

**[ ] Item 9:** GUIDED sukses: `... "{custom_mode: 'GUIDED'}" | grep "mode_sent: true"`

**[ ] Item 10:** Takeoff: `... "{altitude: 2.0, ...}" | grep "success: true"` + drone naik

**[ ] Item 11:** Velocity: drone bergerak di Gazebo setelah pub `/mavros/setpoint_velocity/cmd_vel`

**[ ] Item 12:** `ros2 launch syergie_bringup sitl_mavros.launch.py --dry-run` → tidak ada error


---

# PHASE 4 — ROS2 Node Stack (Implementasi Awal) {#phase-4}

> **Tujuan:** Implementasikan semua node ROS2 untuk stack persepsi dan kontrol awal: spray controller, coverage tracker, bloom detector (mock), row detector, custom messages, dan launch file full stack.

---

## 4.1 Setup Workspace dan Semua Packages

### Buat Semua Packages

```bash
cd ~/syergie_ws/src
for pkg in syergie_msgs syergie_bringup syergie_description syergie_perception syergie_spray palm_nav; do
    [ ! -d "$pkg" ] && ros2 pkg create --build-type ament_python $pkg && echo "Created $pkg"
done
```

### Struktur Direktori Final

```
~/syergie_ws/src/
├── syergie_msgs/           ← Custom messages (CMake-based)
│   ├── msg/
│   │   ├── BloomDetection.msg
│   │   ├── RowInfo.msg
│   │   ├── SprayCommand.msg
│   │   └── CoverageGrid.msg
│   ├── package.xml
│   └── CMakeLists.txt
├── syergie_bringup/        ← Launch files, configs
│   ├── launch/
│   │   ├── spawn_drone.launch.py
│   │   ├── mavros.launch.py
│   │   ├── sitl_mavros.launch.py
│   │   └── sim_phase4.launch.py
│   ├── config/
│   │   ├── bridge_config.yaml
│   │   ├── apm_config.yaml
│   │   └── ardupilot_params_gpsdeny.parm
│   └── scripts/
│       ├── test_basic_control.py
│       └── verify_phase4.py
├── syergie_description/    ← SDF models + worlds
│   ├── models/
│   │   ├── iris_syergie/
│   │   ├── palm_tree/
│   │   └── apriltag_pole/
│   └── worlds/
├── syergie_perception/     ← Perception nodes
│   └── syergie_perception/
│       ├── optical_flow_node.py
│       ├── rangefinder_node.py
│       ├── bloom_detection_node.py
│       └── row_detection_node.py
├── syergie_spray/          ← Spray controller
│   └── syergie_spray/
│       └── spray_controller_node.py
└── palm_nav/               ← Navigation nodes
    └── palm_nav/
        └── coverage_tracker_node.py
```

### package.xml untuk syergie_msgs (CMake-based!)

```bash
cat > ~/syergie_ws/src/syergie_msgs/package.xml << 'EOF'
<?xml version="1.0"?>
<package format="3">
  <name>syergie_msgs</name>
  <version>1.0.0</version>
  <description>Custom messages for Syergie Drone</description>
  <maintainer email="team@syergie.com">Syergie Team</maintainer>
  <license>Apache-2.0</license>
  <buildtool_depend>ament_cmake</buildtool_depend>
  <buildtool_depend>rosidl_default_generators</buildtool_depend>
  <depend>std_msgs</depend>
  <depend>geometry_msgs</depend>
  <exec_depend>rosidl_default_runtime</exec_depend>
  <member_of_group>rosidl_interface_packages</member_of_group>
  <export><build_type>ament_cmake</build_type></export>
</package>
EOF

cat > ~/syergie_ws/src/syergie_msgs/CMakeLists.txt << 'EOF'
cmake_minimum_required(VERSION 3.8)
project(syergie_msgs)
find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(std_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/BloomDetection.msg"
  "msg/RowInfo.msg"
  "msg/SprayCommand.msg"
  "msg/CoverageGrid.msg"
  DEPENDENCIES std_msgs geometry_msgs)
ament_export_dependencies(rosidl_default_runtime)
ament_package()
EOF
```

---

## 4.2 syergie_spray: spray_controller_node

```bash
mkdir -p ~/syergie_ws/src/syergie_spray/syergie_spray
touch ~/syergie_ws/src/syergie_spray/syergie_spray/__init__.py

cat > ~/syergie_ws/src/syergie_spray/syergie_spray/spray_controller_node.py << 'PYEOF'
#!/usr/bin/env python3
"""
Spray Controller Node.
Subscribe /palm_nav/spray_command → publish /spray/cmd ke Gazebo.
Auto-stop setelah durasi, publish /palm_nav/spray_done.
"""
import rclpy, threading, time
from rclpy.node import Node
from std_msgs.msg import Bool
from syergie_msgs.msg import SprayCommand

class SprayControllerNode(Node):
    IDLE, SPRAYING = 'IDLE', 'SPRAYING'

    def __init__(self):
        super().__init__('spray_controller_node')
        self.declare_parameter('spray_duration_sec', 3.0)
        self.declare_parameter('min_spray_interval_sec', 1.0)
        self.declare_parameter('max_spray_duration_sec', 10.0)
        self.dur     = self.get_parameter('spray_duration_sec').value
        self.min_ivl = self.get_parameter('min_spray_interval_sec').value
        self.max_dur = self.get_parameter('max_spray_duration_sec').value

        self.state        = self.IDLE
        self.lock         = threading.Lock()
        self.spray_start  = 0.0
        self.last_end     = 0.0
        self.count        = 0
        self.spray_timer  = None

        self.create_subscription(SprayCommand, '/palm_nav/spray_command',
            self._cmd_cb, 10)
        self.create_subscription(Bool, '/palm_nav/spray_command_bool',
            self._bool_cb, 10)

        self.gz_pub    = self.create_publisher(Bool, '/spray/cmd', 10)
        self.done_pub  = self.create_publisher(Bool, '/palm_nav/spray_done', 10)
        self.status_pub= self.create_publisher(Bool, '/spray/is_active', 10)
        self.create_timer(1.0, self._status_pub)
        self.get_logger().info(f'SprayController ready | dur={self.dur}s')

    def _bool_cb(self, msg: Bool):
        if msg.data: self._start(self.dur)
        else:        self._stop('bool_cmd')

    def _cmd_cb(self, msg: SprayCommand):
        if msg.spray_on:
            dur = min(msg.duration_sec if msg.duration_sec > 0 else self.dur, self.max_dur)
            self._start(dur)
        else:
            self._stop('cmd')

    def _start(self, dur: float):
        with self.lock:
            if time.time() - self.last_end < self.min_ivl:
                self.get_logger().warn('Spray cooldown active'); return
            self.state       = self.SPRAYING
            self.spray_start = time.time()
            self.count      += 1
            self.get_logger().info(f'SPRAY START #{self.count} | {dur:.1f}s')
        self._pub_gz(True)
        if self.spray_timer: self.destroy_timer(self.spray_timer)
        self.spray_timer = self.create_timer(dur, self._timeout)

    def _stop(self, reason=''):
        with self.lock:
            if self.state != self.SPRAYING: return
            self.state    = self.IDLE
            self.last_end = time.time()
            self.get_logger().info(f'SPRAY STOP ({reason})')
        if self.spray_timer: self.destroy_timer(self.spray_timer); self.spray_timer=None
        self._pub_gz(False)
        self.done_pub.publish(Bool(data=True))

    def _timeout(self):
        self._stop('timeout')
        if self.spray_timer: self.destroy_timer(self.spray_timer); self.spray_timer=None

    def _pub_gz(self, on: bool):
        msg = Bool(data=on)
        self.gz_pub.publish(msg)
        self.status_pub.publish(msg)

    def _status_pub(self):
        with self.lock:
            self.status_pub.publish(Bool(data=(self.state==self.SPRAYING)))

    def destroy_node(self):
        self._stop('shutdown')
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    n = SprayControllerNode()
    try:    rclpy.spin(n)
    except KeyboardInterrupt: pass
    finally: n.destroy_node(); rclpy.shutdown()

if __name__ == '__main__':
    main()
PYEOF
```

---

## 4.3 palm_nav: coverage_tracker_node

### Konsep Spatial Hash Grid

```
Area 100x100m dibagi menjadi sel 1x1m = 10.000 sel.
Setiap sel: (cx, cy) = (floor(wx/cell_size), floor(wy/cell_size))
Status: 0=UNVISITED, 1=VISITED, 2=SPRAYED

Spatial hash dictionary {(cx,cy): status}:
  - O(1) lookup: sangat cepat
  - Memory efficient: hanya simpan sel yang dikunjungi
  - Publish sebagai OccupancyGrid untuk RViz
```

```bash
mkdir -p ~/syergie_ws/src/palm_nav/palm_nav
touch ~/syergie_ws/src/palm_nav/palm_nav/__init__.py

cat > ~/syergie_ws/src/palm_nav/palm_nav/coverage_tracker_node.py << 'PYEOF'
#!/usr/bin/env python3
"""Coverage Tracker Node — spatial hash grid untuk track area yang sudah di-spray."""
import rclpy, json, os
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import Bool, Header
from nav_msgs.msg import OccupancyGrid, MapMetaData
from datetime import datetime
from typing import Dict, Tuple, Optional

UNVISITED, VISITED, SPRAYED = 0, 1, 2

class CoverageTrackerNode(Node):
    def __init__(self):
        super().__init__('coverage_tracker_node')
        self.declare_parameter('cell_size_m', 1.0)
        self.declare_parameter('grid_min_x', -55.0)
        self.declare_parameter('grid_max_x',  55.0)
        self.declare_parameter('grid_min_y', -55.0)
        self.declare_parameter('grid_max_y',  55.0)
        self.declare_parameter('log_dir', os.path.expanduser('~/syergie_ws/logs'))
        self.declare_parameter('publish_rate_hz', 1.0)
        self.declare_parameter('frame_id', 'map')

        self.cs   = self.get_parameter('cell_size_m').value
        self.minx = self.get_parameter('grid_min_x').value
        self.maxx = self.get_parameter('grid_max_x').value
        self.miny = self.get_parameter('grid_min_y').value
        self.maxy = self.get_parameter('grid_max_y').value
        self.logd = self.get_parameter('log_dir').value
        self.fid  = self.get_parameter('frame_id').value
        os.makedirs(self.logd, exist_ok=True)

        self.gw = int((self.maxx - self.minx) / self.cs)
        self.gh = int((self.maxy - self.miny) / self.cs)
        self.grid: Dict[Tuple[int,int], int] = {}

        self.pose: Optional[PoseStamped] = None
        self.cell: Optional[Tuple[int,int]] = None
        self.t0   = datetime.now().isoformat()
        self.events = []
        self.n_vis = 0
        self.n_spr = 0

        be_qos = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT,
                            history=HistoryPolicy.KEEP_LAST, depth=1)
        self.create_subscription(PoseStamped, '/mavros/local_position/pose',
            self._pose_cb, be_qos)
        self.create_subscription(Bool, '/palm_nav/spray_done',
            self._spray_cb, 10)

        self.og_pub = self.create_publisher(OccupancyGrid, '/palm_nav/coverage_grid', 10)
        rate = 1.0 / self.get_parameter('publish_rate_hz').value
        self.create_timer(rate, self._publish_og)
        self.get_logger().info(f'CoverageTracker | Grid {self.gw}x{self.gh} | cell={self.cs}m')

    def _w2c(self, wx, wy) -> Optional[Tuple[int,int]]:
        if not (self.minx<=wx<=self.maxx and self.miny<=wy<=self.maxy):
            return None
        return (max(0,min(int((wx-self.minx)/self.cs), self.gw-1)),
                max(0,min(int((wy-self.miny)/self.cs), self.gh-1)))

    def _pose_cb(self, msg: PoseStamped):
        self.pose = msg
        c = self._w2c(msg.pose.position.x, msg.pose.position.y)
        if c and self.grid.get(c, UNVISITED) == UNVISITED:
            self.grid[c] = VISITED; self.n_vis += 1
        self.cell = c

    def _spray_cb(self, msg: Bool):
        if not msg.data or not self.cell or not self.pose: return
        if self.grid.get(self.cell, UNVISITED) != SPRAYED:
            self.grid[self.cell] = SPRAYED; self.n_spr += 1
            p = self.pose.pose.position
            self.events.append({'ts': datetime.now().isoformat(),
                'cell': list(self.cell), 'pos': {'x':p.x,'y':p.y,'z':p.z}})
            self.get_logger().info(f'SPRAYED {self.cell} | total={self.n_spr}')
            self._save_log()

    def _publish_og(self):
        og = OccupancyGrid()
        og.header = Header(stamp=self.get_clock().now().to_msg(), frame_id=self.fid)
        og.info = MapMetaData(resolution=self.cs, width=self.gw, height=self.gh)
        og.info.origin.position.x = self.minx
        og.info.origin.position.y = self.miny
        og.info.origin.orientation.w = 1.0
        data = [-1] * (self.gw * self.gh)
        for (cx,cy), s in self.grid.items():
            idx = cy*self.gw + cx
            if 0 <= idx < len(data):
                data[idx] = 50 if s==VISITED else (100 if s==SPRAYED else 0)
        og.data = data
        self.og_pub.publish(og)

    def _save_log(self):
        total = self.gw * self.gh
        pct   = (self.n_spr / total) * 100
        log   = {'mission_start':self.t0, 'last_updated':datetime.now().isoformat(),
                 'statistics':{'cells_visited':self.n_vis,'cells_sprayed':self.n_spr,
                               'coverage_percent':round(pct,2)},
                 'spray_events':self.events}
        fname = os.path.join(self.logd, f'coverage_{datetime.now().strftime("%Y%m%d")}.json')
        with open(fname,'w') as f: json.dump(log, f, indent=2)

    def destroy_node(self):
        self._save_log()
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    n = CoverageTrackerNode()
    try:    rclpy.spin(n)
    except KeyboardInterrupt: pass
    finally: n.destroy_node(); rclpy.shutdown()

if __name__ == '__main__':
    main()
PYEOF
```

---

## 4.4 syergie_perception: bloom_detection_node (MOCK)

```bash
cat > ~/syergie_ws/src/syergie_perception/syergie_perception/bloom_detection_node.py << 'PYEOF'
#!/usr/bin/env python3
"""
Bloom Detection Node — MOCK mode.
Deteksi berdasarkan jarak Euclidean ke target yang di-hardcode.
Interface identik dengan implementasi Roboflow (Phase 6).
"""
import rclpy, json, math
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import Header
from syergie_msgs.msg import BloomDetection
from typing import List, Dict, Optional

class BloomDetectionNode(Node):
    def __init__(self):
        super().__init__('bloom_detection_node')
        self.declare_parameter('detection_threshold_m', 0.8)
        self.declare_parameter('publish_rate_hz', 10.0)
        self.declare_parameter('debug', True)
        self.declare_parameter('bloom_targets_json', self._default_targets())

        self.thr   = self.get_parameter('detection_threshold_m').value
        self.debug = self.get_parameter('debug').value

        raw = self.get_parameter('bloom_targets_json').value
        try:   self.targets: List[Dict] = json.loads(raw)
        except: self.targets = []

        self.pose: Optional[PoseStamped] = None
        self.last_id = -1

        be_qos = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT,
                            history=HistoryPolicy.KEEP_LAST, depth=1)
        self.create_subscription(PoseStamped, '/mavros/local_position/pose',
            lambda m: setattr(self,'pose',m), be_qos)
        self.pub = self.create_publisher(BloomDetection, '/palm_nav/bloom_detected', 10)
        period = 1.0 / self.get_parameter('publish_rate_hz').value
        self.create_timer(period, self._detect)
        self.get_logger().info(f'BloomDetection(MOCK) | {len(self.targets)} targets | thr={self.thr}m')

    def _default_targets(self) -> str:
        targets = []
        for i,(row,col) in enumerate([(0,0),(0,9),(9,0),(9,9),(5,5)]):
            targets.append({'id':i,'x':-40.0+col*9.0+0.5,'y':-40.0+row*9.0,'z':5.0})
        return json.dumps(targets)

    def _detect(self):
        if self.pose is None: return
        dx,dy,dz = (self.pose.pose.position.x,
                    self.pose.pose.position.y,
                    self.pose.pose.position.z)
        best, best_d = None, float('inf')
        for t in self.targets:
            d = math.sqrt((dx-t['x'])**2+(dy-t['y'])**2+(dz-t['z'])**2)
            if d < best_d: best, best_d = t, d

        msg = BloomDetection()
        msg.header = Header(stamp=self.get_clock().now().to_msg(), frame_id='map')
        if best and best_d <= self.thr:
            msg.detected       = True
            msg.target_id      = int(best['id'])
            msg.distance_m     = best_d
            msg.confidence     = max(0.0, 1.0 - best_d/self.thr)
            msg.bbox_x_center  = 0.5
            msg.bbox_y_center  = 0.5
            msg.bbox_width     = 0.15
            msg.bbox_height    = 0.15
            msg.target_world_x = float(best['x'])
            msg.target_world_y = float(best['y'])
            msg.target_world_z = float(best['z'])
            if self.debug and self.last_id != best['id']:
                self.get_logger().info(f'BLOOM DETECTED id={best["id"]} d={best_d:.2f}m')
            self.last_id = int(best['id'])
        else:
            msg.detected   = False
            msg.target_id  = -1
            msg.distance_m = best_d if best else -1.0
            self.last_id   = -1
        self.pub.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    n = BloomDetectionNode()
    try:    rclpy.spin(n)
    except KeyboardInterrupt: pass
    finally: n.destroy_node(); rclpy.shutdown()

if __name__ == '__main__':
    main()
PYEOF
```

---

## 4.5 syergie_perception: row_detection_node

### Pipeline Deteksi Baris

```
Input image (640x480 BGR)
  │
  ▼ [1] Grayscale: cv2.cvtColor(BGR→GRAY)
  ▼ [2] Blur: cv2.GaussianBlur(ksize=5)
  ▼ [3] Canny: cv2.Canny(low=50, high=150)
  ▼ [4] ROI mask: trapezoid polygon
  ▼ [5] HoughLinesP: rho=1, theta=1°, threshold=40
  ▼ [6] Filter: |angle| < 45° (garis horizontal)
  ▼ [7] Median angle + mean midpoint_x
  ▼ [8] Publish RowInfo + debug image
```

```bash
cat > ~/syergie_ws/src/syergie_perception/syergie_perception/row_detection_node.py << 'PYEOF'
#!/usr/bin/env python3
"""Row Detection Node — Probabilistic Hough Transform untuk deteksi baris pohon sawit."""
import rclpy, cv2, numpy as np, math
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import Image
from std_msgs.msg import Header
from syergie_msgs.msg import RowInfo
from cv_bridge import CvBridge, CvBridgeError
from typing import List, Tuple, Optional

class RowDetectionNode(Node):
    def __init__(self):
        super().__init__('row_detection_node')
        # Parameter
        self.declare_parameter('canny_low',     50)
        self.declare_parameter('canny_high',   150)
        self.declare_parameter('hough_threshold', 40)
        self.declare_parameter('hough_min_length', 60)
        self.declare_parameter('hough_max_gap',   25)
        self.declare_parameter('angle_filter_deg', 45.0)
        self.declare_parameter('blur_ksize',    5)
        self.declare_parameter('image_scale',  0.5)
        self.declare_parameter('publish_debug', True)
        self.declare_parameter('camera_hfov_rad', 1.5708)
        self.declare_parameter('camera_height_m', 3.0)

        self.cl   = self.get_parameter('canny_low').value
        self.ch   = self.get_parameter('canny_high').value
        self.ht   = self.get_parameter('hough_threshold').value
        self.hml  = self.get_parameter('hough_min_length').value
        self.hmg  = self.get_parameter('hough_max_gap').value
        self.af   = math.radians(self.get_parameter('angle_filter_deg').value)
        bk        = int(self.get_parameter('blur_ksize').value)
        self.bk   = bk if bk%2!=0 else bk+1
        self.sc   = self.get_parameter('image_scale').value
        self.pd   = self.get_parameter('publish_debug').value
        self.hfov = self.get_parameter('camera_hfov_rad').value
        self.camh = self.get_parameter('camera_height_m').value
        self.bridge = CvBridge()

        sensor_qos = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT,
                                history=HistoryPolicy.KEEP_LAST, depth=1)
        self.create_subscription(Image, '/camera/front/image_raw',
            self._img_cb, sensor_qos)
        self.row_pub   = self.create_publisher(RowInfo, '/palm_nav/row_info', 10)
        self.debug_pub = self.create_publisher(Image, '/palm_nav/row_debug_image', 10) \
                         if self.pd else None
        self.get_logger().info(f'RowDetection | Canny [{self.cl},{self.ch}] | Hough thr={self.ht}')

    def _img_cb(self, msg: Image):
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
        except CvBridgeError as e:
            self.get_logger().error(str(e)); return

        if self.sc != 1.0:
            nw,nh = int(frame.shape[1]*self.sc), int(frame.shape[0]*self.sc)
            frame = cv2.resize(frame, (nw,nh), interpolation=cv2.INTER_AREA)
        h,w = frame.shape[:2]

        # [1] Grayscale: perlu karena Canny hanya untuk 1-channel
        gray    = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # [2] Gaussian blur: kurangi noise sebelum edge detection
        blurred = cv2.GaussianBlur(gray, (self.bk,self.bk), 0)
        # [3] Canny: deteksi tepi dengan hysteresis thresholding
        edges   = cv2.Canny(blurred, self.cl, self.ch)
        # [4] ROI mask: trapezoid untuk fokus area baris pohon
        mask = np.zeros_like(edges)
        pts  = np.array([[0,h],[w,h],[int(w*0.8),int(h*0.3)],[int(w*0.2),int(h*0.3)]], np.int32)
        cv2.fillPoly(mask, [pts], 255)
        edges_roi = cv2.bitwise_and(edges, mask)
        # [5] Probabilistic Hough Transform
        lines = cv2.HoughLinesP(edges_roi, 1, np.pi/180, self.ht,
                                minLineLength=self.hml, maxLineGap=self.hmg)
        # [6-7] Filter + analyze
        angle, offset, conf, filt = self._analyze(lines, w, h)
        offset_m = self._px2m(offset, w)

        # Publish RowInfo
        ri = RowInfo()
        ri.header = Header(stamp=self.get_clock().now().to_msg(), frame_id='camera_front_link')
        ri.angle_rad       = float(angle)
        ri.lateral_offset_m = float(offset_m)
        ri.confidence      = float(conf)
        ri.lines_detected  = len(filt) if filt else 0
        self.row_pub.publish(ri)

        # Publish debug image
        if self.pd and self.debug_pub:
            dbg = self._draw_debug(frame, edges_roi, filt, angle, offset, conf, w, h)
            try:
                dm = self.bridge.cv2_to_imgmsg(dbg, 'bgr8')
                dm.header = ri.header
                self.debug_pub.publish(dm)
            except: pass

    def _analyze(self, lines, fw, fh) -> Tuple[float,float,float,List]:
        if lines is None or len(lines)==0: return 0.0,0.0,0.0,[]
        filt, angles, mids = [], [], []
        cx = fw/2.0
        for l in lines:
            x1,y1,x2,y2 = l[0]
            dx,dy = float(x2-x1), float(y2-y1)
            if abs(dx)<1e-6: continue
            a = math.atan2(dy,dx)
            if a > math.pi/2:  a -= math.pi
            elif a < -math.pi/2: a += math.pi
            if abs(a) <= self.af:
                filt.append((x1,y1,x2,y2,a))
                angles.append(a)
                mids.append((x1+x2)/2.0)
        if not filt: return 0.0,0.0,0.0,[]
        row_angle = float(np.median(angles))
        offset    = float(np.mean(mids)) - cx
        std       = float(np.std(angles)) if len(angles)>1 else 0.0
        conf_n    = min(1.0, len(filt)/5.0)
        conf_s    = max(0.0, 1.0 - std/self.af)
        conf      = 0.6*conf_n + 0.4*conf_s
        return row_angle, offset, conf, filt

    def _px2m(self, px, fw) -> float:
        fl = (fw/2.0)/math.tan(self.hfov/2.0) if self.hfov>0 else fw
        return (px * self.camh / fl) if fl>0 else 0.0

    def _draw_debug(self, frame, edges, filt, angle, offset, conf, fw, fh):
        dbg = frame.copy()
        ec  = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        dbg = cv2.addWeighted(dbg, 0.8, ec, 0.3, 0)
        cx,cy = fw//2, fh//2
        for x1,y1,x2,y2,_ in filt:
            cv2.line(dbg,(x1,y1),(x2,y2),(0,255,0),2)
        if conf > 0.1 and filt:
            ax = int(cx+offset); ta = math.tan(angle) if abs(angle)<math.pi/2 else 0
            cv2.line(dbg,(ax-int(cy*ta),0),(ax+int(cy*ta),fh),(0,0,255),3)
        cv2.line(dbg,(cx,0),(cx,fh),(255,100,0),1)
        ov = dbg.copy()
        cv2.rectangle(ov,(5,5),(195,5+4*22),(0,0,0),-1)
        dbg = cv2.addWeighted(dbg,0.7,ov,0.3,0)
        for i,txt in enumerate([f'Angle:{math.degrees(angle):+.1f}d',
                                  f'Offset:{offset:+.0f}px',
                                  f'Conf:{conf:.2f}',
                                  f'Lines:{len(filt)}']):
            col = (0,255,0) if conf>0.5 else (0,165,255)
            cv2.putText(dbg,txt,(10,25+i*22),cv2.FONT_HERSHEY_SIMPLEX,0.55,col,1,cv2.LINE_AA)
        return dbg

def main(args=None):
    rclpy.init(args=args)
    n = RowDetectionNode()
    try:    rclpy.spin(n)
    except KeyboardInterrupt: pass
    finally: n.destroy_node(); rclpy.shutdown()

if __name__ == '__main__':
    main()
PYEOF
```

---

## 4.6 Custom Message Definitions

```bash
mkdir -p ~/syergie_ws/src/syergie_msgs/msg

cat > ~/syergie_ws/src/syergie_msgs/msg/BloomDetection.msg << 'EOF'
std_msgs/Header header
bool detected
int32 target_id
float32 distance_m
float32 confidence
float32 bbox_x_center
float32 bbox_y_center
float32 bbox_width
float32 bbox_height
float32 target_world_x
float32 target_world_y
float32 target_world_z
EOF

cat > ~/syergie_ws/src/syergie_msgs/msg/RowInfo.msg << 'EOF'
std_msgs/Header header
float32 angle_rad
float32 lateral_offset_m
float32 confidence
int32 lines_detected
EOF

cat > ~/syergie_ws/src/syergie_msgs/msg/SprayCommand.msg << 'EOF'
std_msgs/Header header
bool spray_on
float32 duration_sec
int32 target_id
int32 reason
EOF

cat > ~/syergie_ws/src/syergie_msgs/msg/CoverageGrid.msg << 'EOF'
std_msgs/Header header
int32 grid_width
int32 grid_height
float32 cell_size_m
float32 origin_x
float32 origin_y
int8[] cell_status
int32 cells_total
int32 cells_visited
int32 cells_sprayed
float32 coverage_percent
EOF
```

```bash
# Build dan verifikasi:
cd ~/syergie_ws
colcon build --packages-select syergie_msgs --symlink-install
source install/setup.bash
ros2 interface list | grep syergie_msgs
# PASS: 4 message types
ros2 interface show syergie_msgs/msg/BloomDetection
```

---

## 4.7 setup.py untuk Package Python

```bash
# syergie_spray
cat > ~/syergie_ws/src/syergie_spray/setup.py << 'EOF'
from setuptools import setup, find_packages
setup(name='syergie_spray', version='1.0.0',
      packages=find_packages(exclude=['test']),
      data_files=[
          ('share/ament_index/resource_index/packages',['resource/syergie_spray']),
          ('share/syergie_spray',['package.xml'])],
      install_requires=['setuptools'],
      entry_points={'console_scripts':[
          'spray_controller_node=syergie_spray.spray_controller_node:main']})
EOF
cat > ~/syergie_ws/src/syergie_spray/package.xml << 'EOF'
<?xml version="1.0"?>
<package format="3"><name>syergie_spray</name><version>1.0.0</version>
  <description>Spray controller</description>
  <maintainer email="t@t.com">T</maintainer><license>Apache-2.0</license>
  <exec_depend>rclpy</exec_depend><exec_depend>std_msgs</exec_depend>
  <exec_depend>syergie_msgs</exec_depend>
  <export><build_type>ament_python</build_type></export></package>
EOF

# palm_nav
cat > ~/syergie_ws/src/palm_nav/setup.py << 'EOF'
from setuptools import setup, find_packages
setup(name='palm_nav', version='1.0.0',
      packages=find_packages(exclude=['test']),
      data_files=[
          ('share/ament_index/resource_index/packages',['resource/palm_nav']),
          ('share/palm_nav',['package.xml'])],
      install_requires=['setuptools'],
      entry_points={'console_scripts':[
          'coverage_tracker_node=palm_nav.coverage_tracker_node:main']})
EOF
cat > ~/syergie_ws/src/palm_nav/package.xml << 'EOF'
<?xml version="1.0"?>
<package format="3"><name>palm_nav</name><version>1.0.0</version>
  <description>Navigation nodes</description>
  <maintainer email="t@t.com">T</maintainer><license>Apache-2.0</license>
  <exec_depend>rclpy</exec_depend><exec_depend>std_msgs</exec_depend>
  <exec_depend>geometry_msgs</exec_depend><exec_depend>nav_msgs</exec_depend>
  <exec_depend>mavros_msgs</exec_depend><exec_depend>syergie_msgs</exec_depend>
  <export><build_type>ament_python</build_type></export></package>
EOF

# Buat resource files
for pkg in syergie_spray palm_nav syergie_perception; do
    mkdir -p ~/syergie_ws/src/$pkg/resource
    touch ~/syergie_ws/src/$pkg/resource/$pkg
    touch ~/syergie_ws/src/$pkg/$pkg/__init__.py
done
```

---

## 4.8 sim_phase4.launch.py — Full Stack

```bash
cat > ~/syergie_ws/src/syergie_bringup/launch/sim_phase4.launch.py << 'PYEOF'
"""sim_phase4.launch.py — Full stack Phase 4"""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import ExecuteProcess, TimerAction, RegisterEventHandler, Shutdown
from launch.event_handlers import OnProcessExit
from launch_ros.actions import Node

def generate_launch_description():
    bringup  = get_package_share_directory('syergie_bringup')
    desc     = get_package_share_directory('syergie_description')
    ardupilot= os.path.expanduser('~/ardupilot')
    world    = os.path.join(desc,'worlds','palm_world_complete.sdf')
    models   = os.path.join(desc,'models')
    iris_sdf = os.path.join(models,'iris_syergie','model.sdf')
    bridge_c = os.path.join(bringup,'config','bridge_config.yaml')
    mavros_c = os.path.join(bringup,'config','apm_config.yaml')
    gz_res   = f"{models}:{os.environ.get('GZ_SIM_RESOURCE_PATH','')}"

    gazebo = ExecuteProcess(cmd=['gz','sim','-r',world,'-v','3'],
        additional_env={'GZ_SIM_RESOURCE_PATH':gz_res,
                        'GZ_SIM_SYSTEM_PLUGIN_PATH':os.environ.get('GZ_SIM_SYSTEM_PLUGIN_PATH','')},
        name='gazebo', output='screen')

    spawn  = TimerAction(period=4.0, actions=[ExecuteProcess(
        cmd=['gz','model','--spawn-file',iris_sdf,'--model-name','iris_syergie',
             '-x','0','-y','0','-z','0.2'], output='screen')])

    bridge = TimerAction(period=6.0, actions=[Node(
        package='ros_gz_bridge', executable='parameter_bridge', name='ros_gz_bridge',
        parameters=[{'config_file':bridge_c}], output='screen')])

    sitl = TimerAction(period=8.0, actions=[ExecuteProcess(
        cmd=['bash','-c',
             f'cd {ardupilot} && python3 Tools/autotest/sim_vehicle.py '
             f'-v ArduCopter -f gazebo-iris --model=gazebo --no-rebuild '
             f'--out=127.0.0.1:14551 --out=127.0.0.1:14553 '
             f'-l 37.613,-122.357,-3.45,270 2>&1|tee /tmp/sitl.log'],
        name='sitl', shell=True, output='screen')])

    mavros = TimerAction(period=16.0, actions=[Node(
        package='mavros', executable='mavros_node',
        name='mavros', namespace='mavros', output='screen',
        parameters=[mavros_c,{'fcu_url':'udp://:14550@127.0.0.1:14551',
                               'gcs_url':'udp://@127.0.0.1:14553'}])])

    nodes = TimerAction(period=18.0, actions=[
        Node(package='syergie_perception',executable='rangefinder_node',
             name='rangefinder_node',output='screen'),
        Node(package='syergie_perception',executable='optical_flow_node',
             name='optical_flow_node',output='screen',
             parameters=[{'camera_fov_rad':1.0472,'image_width':64,'image_height':64}]),
        Node(package='syergie_perception',executable='bloom_detection_node',
             name='bloom_detection_node',output='screen',
             parameters=[{'detection_threshold_m':0.8,'debug':True}]),
        Node(package='syergie_perception',executable='row_detection_node',
             name='row_detection_node',output='screen',
             parameters=[{'publish_debug':True,'image_scale':0.5}]),
        Node(package='syergie_spray',executable='spray_controller_node',
             name='spray_controller_node',output='screen',
             parameters=[{'spray_duration_sec':3.0}]),
        Node(package='palm_nav',executable='coverage_tracker_node',
             name='coverage_tracker_node',output='screen',
             parameters=[{'cell_size_m':1.0,'publish_rate_hz':1.0}]),
    ])

    return LaunchDescription([
        gazebo, spawn, bridge, sitl, mavros, nodes,
        RegisterEventHandler(OnProcessExit(target_action=gazebo,
            on_exit=[Shutdown(reason='Gazebo exited')]))])
PYEOF
```

### Build Semua Packages
```bash
cd ~/syergie_ws
colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release
source install/setup.bash
echo "Build complete: $(colcon build --symlink-install 2>&1 | tail -3)"
```

### Kill Script
```bash
cat > ~/syergie_ws/kill_sim.sh << 'EOF'
#!/bin/bash
echo "=== Killing Syergie Simulation ==="
pkill -f "gz sim"          && echo "Gazebo killed"
pkill -f "sim_vehicle.py"  && echo "SITL killed"
pkill -f "arducopter"      && echo "ArduCopter killed"
pkill -f "mavros_node"     && echo "MAVROS killed"
pkill -f "bloom_detection" 2>/dev/null
pkill -f "row_detection"   2>/dev/null
pkill -f "spray_controller"2>/dev/null
pkill -f "coverage_tracker"2>/dev/null
pkill -f "optical_flow"    2>/dev/null
pkill -f "parameter_bridge"2>/dev/null
sleep 2
echo "=== Done ==="
EOF
chmod +x ~/syergie_ws/kill_sim.sh
```

---

## 4.9 Verifikasi Aliran Data End-to-End

```bash
# Monitor semua topic kritis setelah sim_phase4 berjalan ~20 detik:
for topic in \
    /mavros/state \
    /camera/front/image_raw \
    /camera/down/image_raw \
    /optical_flow/velocity \
    /rangefinder/range \
    /palm_nav/bloom_detected \
    /palm_nav/row_info \
    /palm_nav/coverage_grid \
    /spray/is_active; do
    rate=$(timeout 4 ros2 topic hz $topic 2>&1 | grep "average rate" | awk '{print $3}' || echo "0")
    status=$([[ "${rate%.*}" -gt "0" ]] 2>/dev/null && echo "✓" || echo "✗")
    printf "  %s %-38s %s Hz\n" "$status" "$topic" "$rate"
done

# rqt_graph untuk visualisasi koneksi:
rqt_graph &
# Pilih: Nodes/Topics (all)

# Cek log coverage tracker:
ls ~/syergie_ws/logs/*.json 2>/dev/null && \
    python3 -m json.tool ~/syergie_ws/logs/*.json 2>/dev/null | \
    grep -E "coverage_percent|cells_sprayed|spray_events"
```

---

## MILESTONE CHECKPOINT PHASE 4

**[ ] Item 1: Build workspace sukses**
```bash
cd ~/syergie_ws && colcon build --symlink-install 2>&1 | tail -3
# PASS: "Summary: N packages finished"
```

**[ ] Item 2: Custom messages (4 types)**
```bash
source ~/syergie_ws/install/setup.bash
ros2 interface list | grep syergie_msgs | wc -l   # PASS: 4
```

**[ ] Item 3: Semua node bisa dijalankan**
```bash
source ~/syergie_ws/install/setup.bash
for node in "syergie_perception bloom_detection_node" \
            "syergie_perception row_detection_node" \
            "syergie_spray spray_controller_node" \
            "palm_nav coverage_tracker_node"; do
    pkg=$(echo $node|cut -d' ' -f1); exe=$(echo $node|cut -d' ' -f2)
    timeout 2 ros2 run $pkg $exe --help >/dev/null 2>&1
    echo "[$?] $pkg $exe"
done
# PASS: semua exit 0 atau 1 (1=help printed=binary found)
```

**[ ] Item 4: Launch file parseable**
```bash
ros2 launch syergie_bringup sim_phase4.launch.py --show-args
# PASS: tampilkan arguments
```

**[ ] Item 5: spray_controller menerima perintah**
```bash
ros2 topic pub --once /palm_nav/spray_command_bool std_msgs/msg/Bool "data: true"
timeout 3 ros2 topic echo /spray/is_active --once | grep "data: true"
# PASS: spray aktif
```

**[ ] Item 6: spray_done dipublish setelah timeout**
```bash
timeout 8 ros2 topic echo /palm_nav/spray_done --once | grep "data: true"
# PASS: muncul setelah ~3 detik
```

**[ ] Item 7: coverage_tracker publish OccupancyGrid**
```bash
timeout 5 ros2 topic echo /palm_nav/coverage_grid --once 2>/dev/null | \
    grep "grid_width\|cells_total"
# PASS: nilai > 0
```

**[ ] Item 8: bloom_detection publish valid**
```bash
timeout 5 ros2 topic echo /palm_nav/bloom_detected --once 2>/dev/null | \
    grep "detected\|confidence"
# PASS: detected: false/true, confidence [0,1]
```

**[ ] Item 9: row_detection publish RowInfo**
```bash
timeout 5 ros2 topic echo /palm_nav/row_info --once 2>/dev/null | \
    grep "confidence\|angle_rad"
# PASS: ada nilai
```

**[ ] Item 10: Debug image dipublish**
```bash
timeout 5 ros2 topic hz /palm_nav/row_debug_image 2>/dev/null | grep "average rate"
# PASS: rate > 0
```

**[ ] Item 11: optical_flow publish velocity**
```bash
timeout 5 ros2 topic echo /optical_flow/velocity --once 2>/dev/null | grep "linear"
# PASS: ada linear x,y,z
```

**[ ] Item 12: Coverage log tersimpan**
```bash
# Setelah spray event:
ls ~/syergie_ws/logs/*.json 2>/dev/null | head -3
# PASS: ada file JSON
```

**[ ] Item 13: rqt_graph menampilkan semua node**
```bash
ros2 node list | grep -E "bloom|row|spray|coverage|optical|rangefinder"
# PASS: semua 6 node muncul
```

**[ ] Item 14: verify_phase4.py lulus**
```bash
python3 ~/syergie_ws/src/syergie_bringup/scripts/verify_phase4.py
# PASS: "ALL PASS"
```

**[ ] Item 15: kill_sim.sh bekerja bersih**
```bash
~/syergie_ws/kill_sim.sh
sleep 3
pgrep -l "gz|arducopter|mavros|bloom|row|spray|coverage" 2>/dev/null | wc -l
# PASS: 0 (semua proses mati)
```

---

## Ringkasan Arsitektur Phase 4

```
GAZEBO HARMONIC
  │ /camera/front/image_raw ──────────► [row_detection_node]
  │                                          │
  │ /camera/down/image_raw ───────────► [optical_flow_node]
  │                                          │
  │ /rangefinder/scan_raw ────────────► [rangefinder_node]
  │                                          │
ArduPilot SITL ←──── MAVLink UDP ────── MAVROS2
  │
  │ /mavros/local_position/pose ──────► [bloom_detection_node]
  │                              └─────► [coverage_tracker_node]
  │
  │ /palm_nav/bloom_detected ◄─── bloom_detection_node
  │ /palm_nav/row_info       ◄─── row_detection_node
  │ /optical_flow/velocity   ◄─── optical_flow_node
  │ /rangefinder/range       ◄─── rangefinder_node
  │
  │ /palm_nav/spray_command ──────────► [spray_controller_node]
  │ /palm_nav/spray_done    ◄──────────  spray_controller_node
  │ /spray/cmd ─────────────────────────► Gazebo ParticleEmitter
  │
  │ /palm_nav/coverage_grid ◄──────────  coverage_tracker_node
  │ ~/syergie_ws/logs/*.json ◄──────────  coverage_tracker_node

Phase 5+ (FSM): palm_nav_fsm_node akan mengintegrasikan semua
subscriber/publisher di atas untuk misi otonom penuh.
```

---

*Dokumen selesai — Phase 0 hingga Phase 4.*
*Syergie Drone — Autonomous Palm Oil Pollinator | v1.0.0 | 2026*
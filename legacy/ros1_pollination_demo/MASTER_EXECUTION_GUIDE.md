# 🛠️ MASTER EXECUTION GUIDE — From Zero to Working Demo
### Date: February 10, 2026
### Hardware: Jetson Nano 4GB (B01) + 32GB SD Card
### Prerequisite: A flashed SD card with JetPack 4.6.x (L4T) booted at least once
### Companion Document: Read `ACTION_PLAN_SURVIVAL.md` for the "what." This document is the "how."

---

## TABLE OF CONTENTS

```
PHASE 0: THE "HANDSHAKE" — Getting SSH Working ........... Line ~30
  0.1  Method A: MicroUSB L4T Bridge (192.168.55.1) ..... Line ~50
  0.2  Method B: WiFi Hotspot from Laptop ............... Line ~120
  0.3  Method C: WiFi Hotspot from Phone ................ Line ~190
  0.4  Method D: Direct Ethernet (Fix the Broken Setup).. Line ~240
  0.5  Setting Up VS Code Remote-SSH .................... Line ~320
  0.6  Verifying Everything Works ....................... Line ~420

PHASE 1: SYSTEM PREP — The "32GB Survival" Setup ......... Line ~460
  1.1  Checking Disk Space (Know Where You Stand) ....... Line ~470
  1.2  The Great Purge (Removing Bloatware) ............. Line ~500
  1.3  Creating a 4GB Swap File ......................... Line ~590
  1.4  Setting Jetson to MAXN Performance Mode .......... Line ~650
  1.5  Installing ROS Noetic ............................ Line ~700
  1.6  Configuring ~/.bashrc ............................ Line ~900
  1.7  Installing Python Dependencies ................... Line ~970

PHASE 2: WORKSPACE CREATION — The Foundation .............. Line ~1020
  2.1  Creating the catkin_ws Workspace ................. Line ~1030
  2.2  Creating the sprayer_control Package ............. Line ~1060
  2.3  Creating the Custom Message ...................... Line ~1100
  2.4  Editing CMakeLists.txt ........................... Line ~1140
  2.5  Editing package.xml .............................. Line ~1240
  2.6  First Build + Verify ............................ Line ~1300

PHASE 3: DAILY EXECUTION ................................. Line ~1370
  Day 1: Camera Setup & Verification ................... Line ~1380
  Day 2: Detector Node — File Placement & Structure .... Line ~1500
  Day 3: Pixhawk Servo Setup & MAVROS Configuration .... Line ~1660
  Day 4: Full Integration Test ......................... Line ~1830
  Day 5: On-Drone Mounting & Battery Test .............. Line ~1930

APPENDIX A: Common Errors & Fixes ....................... Line ~2020
APPENDIX B: Quick Reference Command Card ............... Line ~2140
```

---

# ═══════════════════════════════════════════════════════════
# PHASE 0: THE "HANDSHAKE" — Getting SSH Working
# ═══════════════════════════════════════════════════════════

Your Ethernet from laptop to Jetson isn't working. That's OK — there are **four** ways to connect. We'll try them in order from easiest to hardest.

**What you need to understand first:**

SSH (Secure Shell) lets you type commands on the Jetson from your laptop's terminal. It's like a remote control. The Jetson doesn't need a monitor, keyboard, or mouse — it just needs a network connection to your laptop.

"Headless" means the Jetson has no monitor attached. All interaction is through SSH.

---

## 0.1 METHOD A: MicroUSB L4T Bridge (192.168.55.1) — EASIEST, TRY THIS FIRST

**What this is:** When you plug a MicroUSB cable into the Jetson's MicroUSB port (NOT the barrel jack, NOT the USB-A ports), the Jetson creates a virtual network adapter on your laptop. This adapter has a fixed IP address: `192.168.55.1` (Jetson) and `192.168.55.100` (your laptop). No WiFi, no Ethernet cable needed — just the MicroUSB cable.

**Requirements:**
- A MicroUSB data cable (not a charge-only cable — charge-only cables have no data wires)
- The MicroUSB port on the Jetson Nano (the one next to the barrel jack power connector)

**⚠️ IMPORTANT:** If you're powering the Jetson via the MicroUSB port (5V 2A), you're ALREADY using this port for power AND data. That works — the same cable carries both. But if you're powering via the barrel jack (5V 4A), you need to plug a SEPARATE MicroUSB cable into the MicroUSB port for the data bridge.

### Step-by-step (on your Windows Laptop):

**Step 1: Plug in the MicroUSB cable**

```
    Jetson Nano Board Layout:
    ═════════════════════════════════════

    ┌────────────────────────────────────┐
    │  [GPIO Pins]                       │
    │                                    │
    │  [Ethernet]  [USB-A] [USB-A]      │
    │              [USB-A] [USB-A]      │
    │                                    │
    │  [HDMI]  [DP]  [DC Barrel] [MicroUSB] ← THIS ONE
    │                              ▲
    └──────────────────────────────│─────┘
                                   │
                          Plug MicroUSB cable here
                          Connect other end to Laptop USB
```

**Step 2: Wait 30-60 seconds**

After plugging in, Windows might install a driver called "Remote NDIS based Internet Sharing Device" or "Linux USB Ethernet/RNDIS Gadget." You might see a notification in the bottom-right of your screen. Wait for it.

**Step 3: Check if the adapter appeared**

Open **PowerShell** on your Windows laptop and type:

```powershell
# Check if the RNDIS adapter exists
ipconfig | Select-String -Pattern "192.168.55"
```

You should see something like:
```
   IPv4 Address. . . . . . . . . . . : 192.168.55.100
```

If you DON'T see `192.168.55` in the output, try:

```powershell
# Show all network adapters — look for "RNDIS" or "Linux USB Ethernet"
ipconfig /all | Select-String -Pattern "RNDIS|Linux|USB Ethernet" -Context 0,10
```

If you see the adapter but it has a different IP (like 169.254.x.x), Windows auto-assigned an IP. You need to set it manually:

```powershell
# Open Network Connections GUI:
ncpa.cpl
```

1. Find the adapter named "Linux USB Ethernet/RNDIS Gadget" or similar
2. Right-click → Properties → Internet Protocol Version 4 (TCP/IPv4) → Properties
3. Select "Use the following IP address"
4. IP address: `192.168.55.100`
5. Subnet mask: `255.255.255.0`
6. Default gateway: (leave blank)
7. Click OK, OK

**Step 4: Ping the Jetson**

```powershell
# Ping the Jetson at its L4T bridge address
ping 192.168.55.1
```

If you see replies like `Reply from 192.168.55.1: bytes=32 time<1ms TTL=64`, **IT WORKS!** Skip to Step 5.

If you see "Request timed out" or "Destination host unreachable":
- Make sure the Jetson is powered on and has finished booting (green power LED solid, not blinking)
- Try a different MicroUSB cable (charge-only cables are VERY common and look identical)
- Try a different USB port on your laptop
- If still failing → skip to Method B (WiFi Hotspot)

**Step 5: SSH into the Jetson**

```powershell
# SSH into the Jetson (replace 'jetson' with your username if different)
ssh jetson@192.168.55.1
```

It will ask:
```
The authenticity of host '192.168.55.1' can't be established.
ECDSA key fingerprint is SHA256:xxxxxxxxxxxx.
Are you sure you want to continue connecting (yes/no)?
```

Type `yes` and press Enter. Then enter your password (the one you set during JetPack first boot).

**🎉 If you see `jetson@jetson-nano:~$` — YOU'RE IN! Skip to Section 0.5 (VS Code Setup).**

---

## 0.2 METHOD B: WiFi Hotspot from Your Laptop

**What this is:** You turn your laptop into a WiFi hotspot. The Jetson connects to that hotspot. They can now talk over WiFi.

**Requirements:**
- A USB WiFi dongle plugged into the Jetson (Jetson Nano does NOT have built-in WiFi)
  - OR an Intel AC8265 M.2 WiFi card installed inside the Jetson Nano
  - Common cheap dongles: TP-Link TL-WN725N (~$8), Edimax EW-7811Un
- You need a monitor + keyboard for the Jetson for the FIRST connection (to join the WiFi network). After that, it's headless.

**⚠️ No WiFi adapter on the Jetson?** Skip to Method C (Phone Hotspot via Ethernet) or Method D (Fix Ethernet).

### Step-by-step:

**Step 1: Create a hotspot on your Windows laptop**

```powershell
# Open Windows Settings → Network & Internet → Mobile hotspot
# Or use the quick command:
ms-settings:network-mobilehotspot
```

1. Turn on "Mobile hotspot"
2. Note down the **Network name** and **Password**
3. Set "Share my internet connection from" to your active internet (WiFi or Ethernet to router)

**Step 2: Connect the Jetson to your laptop's hotspot**

This step requires a monitor + keyboard on the Jetson (ONE TIME ONLY):

```bash
# ON THE JETSON (with monitor and keyboard):

# List available WiFi networks:
nmcli device wifi list

# Connect to your laptop's hotspot:
# Replace YOUR_HOTSPOT_NAME and YOUR_PASSWORD with actual values
nmcli device wifi connect "YOUR_HOTSPOT_NAME" password "YOUR_PASSWORD"

# Verify connection:
ip addr show wlan0
# Look for an IP like 192.168.137.x or 192.168.x.x

# Make it auto-connect on boot:
nmcli connection modify "YOUR_HOTSPOT_NAME" connection.autoconnect yes
```

**Step 3: Find the Jetson's IP address**

Still on the Jetson (with monitor):

```bash
# Show the IP assigned to the Jetson
hostname -I
# Output: 192.168.137.xxx   (or similar)
# WRITE THIS NUMBER DOWN. This is the Jetson's IP.
```

**Step 4: SSH from your laptop**

Back on your Windows laptop PowerShell:

```powershell
# Replace xxx with the actual number from Step 3
ssh jetson@192.168.137.xxx
```

**🎉 If you see `jetson@jetson-nano:~$` — YOU'RE IN! Skip to Section 0.5.**

**Step 5: (Optional) Set a static IP so it doesn't change**

On the Jetson (via SSH now):

```bash
# Set static IP for the hotspot connection
# This means the Jetson will ALWAYS be 192.168.137.50 on your hotspot
nmcli connection modify "YOUR_HOTSPOT_NAME" \
    ipv4.method manual \
    ipv4.addresses 192.168.137.50/24 \
    ipv4.gateway 192.168.137.1

# Restart the connection:
nmcli connection down "YOUR_HOTSPOT_NAME"
nmcli connection up "YOUR_HOTSPOT_NAME"

# Now from laptop, always use:
# ssh jetson@192.168.137.50
```

---

## 0.3 METHOD C: WiFi Hotspot from Phone

**What this is:** Same as Method B, but you use your phone's hotspot instead of laptop's. Both your laptop and Jetson connect to your phone.

This works if your laptop can't create a hotspot (some don't support it while connected to WiFi).

### Step-by-step:

**Step 1:** On your phone: Enable "WiFi Hotspot" / "Personal Hotspot"

**Step 2:** Connect the Jetson to the phone hotspot:

```bash
# ON THE JETSON (with monitor, one time):
nmcli device wifi connect "PHONE_HOTSPOT_NAME" password "PHONE_PASSWORD"
hostname -I
# Write down the IP address
```

**Step 3:** On your Windows laptop: Also connect to the phone hotspot WiFi.

**Step 4:** From laptop, SSH into Jetson using the IP from Step 2:

```powershell
ssh jetson@<JETSON_IP_FROM_STEP_2>
```

**⚠️ Note:** Phone hotspot has limited bandwidth. Good enough for SSH and file transfer. NOT good for streaming video.

---

## 0.4 METHOD D: Direct Ethernet (Fix the Broken Setup)

**What this is:** A direct Ethernet cable from laptop to Jetson. Your original plan that isn't working. Let's fix it.

### Common reasons it fails:

**Reason 1: IP address mismatch (MOST COMMON)**

Both devices need to be on the same subnet. The Jetson default Ethernet is usually set to DHCP (auto), and so is your laptop. When connected directly (no router), neither device gives the other an IP.

**Fix:** Set STATIC IPs on both sides.

On the Jetson (needs monitor first, or use MicroUSB SSH from Method A):

```bash
# Set static IP on the Jetson's Ethernet port
sudo nmcli connection modify "Wired connection 1" \
    ipv4.method manual \
    ipv4.addresses 192.168.1.10/24

# Bring it up
sudo nmcli connection up "Wired connection 1"

# Verify
ip addr show eth0
# Should show: inet 192.168.1.10/24
```

On your Windows laptop:

```powershell
# Open Network Connections
ncpa.cpl
```

1. Find your Ethernet adapter (the one with the cable to Jetson)
2. Right-click → Properties → Internet Protocol Version 4 (TCP/IPv4)
3. Select "Use the following IP address"
4. IP: `192.168.1.100`
5. Subnet: `255.255.255.0`
6. Gateway: (leave blank)
7. OK → OK

Now test:

```powershell
ping 192.168.1.10
```

**Reason 2: Wrong Ethernet cable**

A direct laptop-to-Jetson connection technically needs a "crossover" cable. However, most modern devices support Auto-MDIX (auto-detect), so a regular cable works. If you have an old laptop or NIC, try a crossover cable or go through a switch/router.

**Reason 3: Firewall blocking**

```powershell
# Temporarily disable Windows Firewall to test:
# (Re-enable after testing!)
netsh advfirewall set allprofiles state off

# Test:
ping 192.168.1.10

# Re-enable firewall:
netsh advfirewall set allprofiles state on

# If ping worked with firewall off, add a rule instead of disabling:
netsh advfirewall firewall add rule name="Allow SSH" dir=in action=allow protocol=TCP localport=22
```

**Reason 4: Ethernet adapter disabled or sleeping**

```powershell
# Check adapter status:
Get-NetAdapter | Where-Object {$_.InterfaceDescription -like "*Ethernet*"}

# If status is "Disabled", enable it:
Enable-NetAdapter -Name "Ethernet"

# Disable power saving on the adapter:
# Device Manager → Network Adapters → Your Ethernet → Properties →
# Power Management → Uncheck "Allow the computer to turn off this device"
```

---

## 0.5 SETTING UP VS CODE REMOTE-SSH

**What this does:** VS Code on your laptop connects to the Jetson via SSH. You edit files on the Jetson AS IF they were local. Copilot works inside the Jetson file system. Terminal in VS Code runs commands on the Jetson.

**This is the #1 productivity multiplier. Do this.**

### Step 1: Install the extension on your laptop

Open VS Code on your Windows laptop.

Press `Ctrl+Shift+X` (Extensions panel).

Search for: `Remote - SSH`

Install: **"Remote - SSH"** by Microsoft (Extension ID: `ms-vscode-remote.remote-ssh`)

Also install: **"Remote - SSH: Editing Configuration Files"** by Microsoft

### Step 2: Configure the SSH connection

Press `Ctrl+Shift+P` → type `Remote-SSH: Open SSH Configuration File` → select the first option (usually `C:\Users\YourName\.ssh\config`)

Add this block at the end of the file (use the IP that worked for you above):

```
# ═══ Jetson Nano ═══
# Change the HostName to whichever IP worked for you:
#   192.168.55.1    (if MicroUSB Method A worked)
#   192.168.137.50  (if WiFi Hotspot Method B/C worked)
#   192.168.1.10    (if Ethernet Method D worked)

Host jetson-nano
    HostName 192.168.55.1
    User jetson
    Port 22
    ForwardAgent yes
    ServerAliveInterval 60
    ServerAliveCountMax 3
```

Save the file (`Ctrl+S`).

### Step 3: Connect to the Jetson

1. Press `Ctrl+Shift+P` → type `Remote-SSH: Connect to Host`
2. Select `jetson-nano` from the list
3. A new VS Code window opens
4. It asks for your password (the Jetson's user password)
5. First connection takes 2-5 minutes — VS Code installs its server component on the Jetson
6. **IMPORTANT:** It will ask for the platform. Select **Linux**.

### Step 4: Open the project folder

Once connected:
1. File → Open Folder
2. Navigate to `/home/jetson/` (or wherever your project will live)
3. Click OK

### Step 5: Install extensions ON THE JETSON (Remote)

After connecting, VS Code runs in "remote" mode. Extensions need to be installed on the Jetson side:

Press `Ctrl+Shift+X` and install these on the Jetson (they'll show "Install in SSH: jetson-nano"):

- **Python** (ms-python.python) — for Python IntelliSense
- **GitHub Copilot** (GitHub.copilot) — if you have a subscription
- **GitHub Copilot Chat** (GitHub.copilot-chat) — chat interface

### Step 6: Open a terminal

Press `` Ctrl+` `` (backtick) to open a terminal. This terminal runs ON THE JETSON.

Test it:

```bash
# This runs on the Jetson, not your laptop:
uname -a
# Should show: Linux jetson-nano 4.9.xxx aarch64 ...

hostname
# Should show: jetson-nano (or whatever you named it)
```

**🎉 You now have a full VS Code development environment running on the Jetson, with Copilot, from your laptop. This is your workspace for the next 5 days.**

---

## 0.6 VERIFYING EVERYTHING WORKS

Run these checks on the Jetson (via SSH or VS Code terminal):

```bash
# ═══ CHECK 1: Who am I? ═══
whoami
# Expected: jetson (or your username)

# ═══ CHECK 2: What OS? ═══
cat /etc/os-release | head -5
# Expected: Ubuntu 18.04 (JetPack 4.6.x is based on Ubuntu 18.04)
# ⚠️ YES, Ubuntu 18.04. NOT 20.04. This matters for ROS installation.

# ═══ CHECK 3: How much disk space? ═══
df -h /
# Look at "Used" and "Avail" columns
# You want at least 8-10 GB free to install ROS + packages

# ═══ CHECK 4: How much RAM? ═══
free -h
# Total should be ~3.9 GB (some reserved by GPU)

# ═══ CHECK 5: Is CUDA available? ═══
nvcc --version
# Should show CUDA 10.2 (JetPack 4.6)
# If "command not found" → CUDA is installed but not in PATH. We'll fix later.

# ═══ CHECK 6: GPU info ═══
cat /proc/device-tree/model
# Should show: NVIDIA Jetson Nano Developer Kit
```

Write down the results. Specifically:
- **Free disk space:** `df -h /` → Avail column: _____ GB
- **Ubuntu version:** `cat /etc/os-release` → _____ (18.04 or 20.04)

**This determines which ROS installation path to follow.**

---

# ═══════════════════════════════════════════════════════════
# PHASE 1: SYSTEM PREP — The "32GB Survival" Setup
# ═══════════════════════════════════════════════════════════

Your 32GB SD card is tiny. After JetPack, you probably have 10-15 GB free. ROS Noetic needs ~3-5 GB. OpenCV, Python packages, your code, logs — another 2-3 GB. Swap file needs 4 GB. That leaves almost nothing.

**We need to be AGGRESSIVE about freeing space.**

---

## 1.1 CHECKING DISK SPACE (Know Where You Stand)

```bash
# How much total / used / available?
df -h /

# Example output:
# Filesystem      Size  Used Avail Use% Mounted on
# /dev/mmcblk0p1   29G   14G   14G  50% /
# 
# → 14 GB available. We can work with this.
# → If less than 8 GB: the purge below is CRITICAL.

# What's eating the most space?
sudo du -h --max-depth=1 / 2>/dev/null | sort -rh | head -20
# This shows the biggest directories. Common hogs:
#   /usr          → system packages, libraries
#   /var          → logs, cache, package manager
#   /home         → your files
#   /opt          → NVIDIA, CUDA
#   /snap         → snap packages (if any)
```

---

## 1.2 THE GREAT PURGE (Removing Bloatware)

**What we're removing:** Ubuntu Desktop comes with software you'll never use on a headless drone computer. LibreOffice alone is ~400 MB. Thunderbird mail, games, document viewers — all useless.

**⚠️ SAFETY NOTE:** Each command below removes specific packages. I'll explain what each one does. If you're nervous, run them ONE AT A TIME and check disk space after each.

```bash
# ════════════════════════════════════════════════════
# STEP 1: Remove LibreOffice (~400 MB)
# ════════════════════════════════════════════════════
# LibreOffice is a word processor / spreadsheet / presentation program.
# You're not writing documents on a drone. Remove it.
sudo apt-get purge -y libreoffice*
sudo apt-get autoremove -y
echo "=== LibreOffice removed ==="
df -h / | tail -1

# ════════════════════════════════════════════════════
# STEP 2: Remove Thunderbird email client (~100 MB)
# ════════════════════════════════════════════════════
# Email client. Useless on a drone.
sudo apt-get purge -y thunderbird*
sudo apt-get autoremove -y
echo "=== Thunderbird removed ==="
df -h / | tail -1

# ════════════════════════════════════════════════════
# STEP 3: Remove games and simple programs (~50 MB)
# ════════════════════════════════════════════════════
# Solitaire, mines, sudoku, etc.
sudo apt-get purge -y \
    aisleriot gnome-mines gnome-sudoku gnome-mahjongg \
    gnome-todo gnome-calendar gnome-characters \
    gnome-font-viewer gnome-screenshot gnome-logs \
    gnome-weather gnome-clocks gnome-maps \
    gnome-contacts gnome-documents \
    totem rhythmbox shotwell remmina \
    simple-scan cheese
sudo apt-get autoremove -y
echo "=== Desktop apps removed ==="
df -h / | tail -1

# ════════════════════════════════════════════════════
# STEP 4: Remove unnecessary documentation (~200 MB)
# ════════════════════════════════════════════════════
# Man pages and docs for removed packages.
sudo apt-get purge -y \
    libreoffice-common \
    ubuntu-docs \
    gnome-user-guide
sudo apt-get autoremove -y
echo "=== Docs removed ==="
df -h / | tail -1

# ════════════════════════════════════════════════════
# STEP 5: Clean the apt cache (~500 MB to 2 GB!)
# ════════════════════════════════════════════════════
# This is the biggest win. apt keeps downloaded .deb files in cache.
# They're never needed again after installation.
sudo apt-get clean
echo "=== apt cache cleaned ==="
df -h / | tail -1

# ════════════════════════════════════════════════════
# STEP 6: Remove old log files (~50-200 MB)
# ════════════════════════════════════════════════════
# System logs accumulate over time.
sudo journalctl --vacuum-size=50M
sudo rm -rf /var/log/*.gz /var/log/*.1 /var/log/*.old
echo "=== Old logs cleaned ==="
df -h / | tail -1

# ════════════════════════════════════════════════════
# STEP 7: Remove snap packages (if any exist)
# ════════════════════════════════════════════════════
# Some JetPack images have snaps. They waste space.
snap list 2>/dev/null
# If it shows any packages:
# sudo snap remove --purge <package_name>
# If snap itself is installed and you want it gone:
# sudo apt-get purge -y snapd
# sudo apt-get autoremove -y

# ════════════════════════════════════════════════════
# FINAL DISK SPACE CHECK:
# ════════════════════════════════════════════════════
echo ""
echo "════════════════════════════════════════"
echo "DISK SPACE AFTER PURGE:"
df -h /
echo "════════════════════════════════════════"
# You should have gained 1-3 GB from the purge.
# Target: at least 10 GB free.
```

**🛑 DO NOT REMOVE these (even if they look big):**
- `/usr/local/cuda*` — CUDA toolkit. You need this for GPU.
- `/usr/lib/aarch64-linux-gnu/tegra*` — NVIDIA GPU drivers.
- Anything in `/opt/nvidia/` — NVIDIA tools.
- `python3`, `python3-pip` — You need Python.
- `openssh-server` — This is how you're connected right now!

---

## 1.3 CREATING A 4GB SWAP FILE

**What is swap?** When your 4GB RAM fills up (and it WILL — compiling ROS and running YOLO will eat all of it), Linux normally crashes (OOM kill). A swap file tells Linux: "When RAM is full, overflow to this file on the SD card."

**It's slower than RAM** (SD card is ~50-100 MB/s vs RAM at ~25 GB/s), but it prevents crashes. Without this, `catkin_make` and YOLO inference will randomly kill processes.

**4 GB is the sweet spot.** It doubles your effective memory from 4GB to 8GB virtual.

```bash
# ════════════════════════════════════════════════════
# STEP 1: Check if you already have swap
# ════════════════════════════════════════════════════
free -h
# Look at the "Swap:" row.
# If it says "0B" for total → you have no swap. Continue below.
# If it shows 2G or more → you already have swap. Skip to Step 5 to resize if needed.

swapon --show
# If empty → no swap configured. Continue below.

# ════════════════════════════════════════════════════
# STEP 2: Create a 4GB swap file
# ════════════════════════════════════════════════════
# This creates a 4 GB file filled with zeros.
# It takes ~60-90 seconds on an SD card. Be patient.
sudo fallocate -l 4G /swapfile

# If fallocate doesn't work (some filesystems don't support it):
# sudo dd if=/dev/zero of=/swapfile bs=1M count=4096 status=progress

# ════════════════════════════════════════════════════
# STEP 3: Set correct permissions and format it
# ════════════════════════════════════════════════════
# Only root should read/write the swap file (security).
sudo chmod 600 /swapfile

# Format it as swap space:
sudo mkswap /swapfile

# ════════════════════════════════════════════════════
# STEP 4: Activate it NOW
# ════════════════════════════════════════════════════
sudo swapon /swapfile

# Verify it's active:
free -h
# Swap row should now show ~4.0G total.

swapon --show
# Should show: /swapfile file 4G 0B -2

# ════════════════════════════════════════════════════
# STEP 5: Make it permanent (survives reboot)
# ════════════════════════════════════════════════════
# Without this, the swap disappears after reboot.
# We add it to /etc/fstab (the file that tells Linux what to mount at boot).

# First, check if it's already there:
grep swapfile /etc/fstab

# If nothing printed, add it:
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Verify:
cat /etc/fstab | grep swap
# Should show: /swapfile none swap sw 0 0

# ════════════════════════════════════════════════════
# STEP 6: Tune the "swappiness" (IMPORTANT for performance)
# ════════════════════════════════════════════════════
# "Swappiness" controls how eagerly Linux uses swap.
# Default is 60 (use swap fairly often).
# For Jetson Nano, set it to 10 (only use swap when RAM is almost full).
# Higher values = more SD card wear and slower performance.

# Set it now:
sudo sysctl vm.swappiness=10

# Make it permanent:
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf

# ════════════════════════════════════════════════════
# FINAL VERIFICATION:
# ════════════════════════════════════════════════════
echo ""
echo "════════════════════════════════════════"
echo "SWAP STATUS:"
free -h
echo ""
echo "SWAP DETAIL:"
swapon --show
echo ""
echo "SWAPPINESS:"
cat /proc/sys/vm/swappiness
echo "════════════════════════════════════════"
# Expected:
#   Swap: 4.0Gi total
#   Swappiness: 10
```

---

## 1.4 SETTING JETSON TO MAXN PERFORMANCE MODE

**What this does:** The Jetson Nano has two power modes:
- **5W mode (Mode 1):** Only 2 CPU cores, lower clock speed. Saves power.
- **MAXN mode (Mode 0):** All 4 CPU cores, maximum clock speed. More power, more heat, MORE SPEED.

For development and demo, always use MAXN.

```bash
# ════════════════════════════════════════════════════
# Check current power mode:
# ════════════════════════════════════════════════════
sudo nvpmodel -q
# Expected output: "NV Power Mode: MAXN" or "NV Power Mode: 5W"

# ════════════════════════════════════════════════════
# Set to MAXN (Mode 0):
# ════════════════════════════════════════════════════
sudo nvpmodel -m 0

# ════════════════════════════════════════════════════
# Lock CPU clocks to maximum (until next reboot):
# ════════════════════════════════════════════════════
sudo jetson_clocks

# ════════════════════════════════════════════════════
# (Optional) Make jetson_clocks run on every boot:
# ════════════════════════════════════════════════════
# Create a systemd service:
sudo bash -c 'cat > /etc/systemd/system/jetson-clocks.service << EOF
[Unit]
Description=Maximize Jetson Nano Clock Speeds
After=nvpmodel.service

[Service]
Type=oneshot
ExecStart=/usr/bin/jetson_clocks
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF'

sudo systemctl daemon-reload
sudo systemctl enable jetson-clocks.service

echo "=== MAXN mode set. jetson_clocks will run on boot. ==="
```

---

## 1.5 INSTALLING ROS NOETIC

**Which version?** This depends on your Ubuntu version:

```bash
# CHECK YOUR UBUNTU VERSION FIRST:
cat /etc/os-release | grep VERSION_ID
```

### PATH A: If Ubuntu 20.04 (Focal) — Direct apt install

If your Jetson runs Ubuntu 20.04 (some custom JetPack images use 20.04), ROS Noetic installs directly from apt. This is the easy path.

```bash
# ════════════════════════════════════════════════════
# STEP 1: Setup keys and sources
# ════════════════════════════════════════════════════
sudo sh -c 'echo "deb http://packages.ros.org/ros/ubuntu $(lsb_release -sc) main" > /etc/apt/sources.list.d/ros-latest.list'

# Install curl if not present:
sudo apt-get install -y curl

# Add ROS key:
curl -s https://raw.githubusercontent.com/ros/rosdistro/master/ros.asc | sudo apt-key add -

# ════════════════════════════════════════════════════
# STEP 2: Install ROS Noetic (ros-base = minimal, saves ~1.5 GB vs desktop)
# ════════════════════════════════════════════════════
sudo apt-get update
sudo apt-get install -y ros-noetic-ros-base

# WHY ros-base instead of ros-desktop-full?
# ros-base:         ~1.5 GB — ROS core, rospy, roscpp, roslaunch, etc.
# ros-desktop:      ~3.0 GB — adds rviz, rqt, etc.
# ros-desktop-full: ~4.5 GB — adds Gazebo simulator (you don't need this)
#
# We install ros-base and ADD ONLY the specific packages we need.
# This saves 1.5-3 GB on your tiny 32GB card.

# ════════════════════════════════════════════════════
# STEP 3: Install ONLY the specific packages we need
# ════════════════════════════════════════════════════
sudo apt-get install -y \
    ros-noetic-usb-cam \
    ros-noetic-cv-bridge \
    ros-noetic-image-transport \
    ros-noetic-rqt-image-view \
    python3-rosdep \
    python3-rosinstall \
    python3-rosinstall-generator \
    python3-wstool \
    python3-catkin-tools

# ════════════════════════════════════════════════════
# STEP 4: Initialize rosdep
# ════════════════════════════════════════════════════
sudo rosdep init
rosdep update

# ════════════════════════════════════════════════════
# STEP 5: Verify installation
# ════════════════════════════════════════════════════
source /opt/ros/noetic/setup.bash
rosversion -d
# Expected: noetic

roscore &
# Wait 3 seconds, then:
rostopic list
# Expected: /rosout and /rosout_agg

# Kill roscore:
kill %1
# Or press Ctrl+C if it's in the foreground

echo "=== ROS Noetic installed successfully ==="
df -h / | tail -1
```

### PATH B: If Ubuntu 18.04 (Bionic) — You need ROS Melodic or a container

**⚠️ ROS Noetic does NOT natively support Ubuntu 18.04.** JetPack 4.6.x ships with Ubuntu 18.04.

You have three options:

**Option B1 (RECOMMENDED): Install ROS Melodic instead**

ROS Melodic is the LTS release for Ubuntu 18.04. It does EVERYTHING we need. The code in our project uses `rospy`, `std_msgs`, `cv_bridge` — all available in Melodic. The Python scripts work the same.

```bash
# ════════════════════════════════════════════════════
# ROS MELODIC INSTALLATION (for Ubuntu 18.04)
# ════════════════════════════════════════════════════

# STEP 1: Setup ROS repository (using modern gpg method)
# ════════════════════════════════════════════════════
sudo sh -c 'echo "deb http://packages.ros.org/ros/ubuntu $(lsb_release -sc) main" > /etc/apt/sources.list.d/ros-latest.list'

# Install curl and gnupg if not present:
sudo apt-get update
sudo apt-get install -y curl gnupg2 lsb-release

# Download and install the GPG key (NEW METHOD for Ubuntu 18.04+):
curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.asc | sudo apt-key add -

# If the above fails with "no valid OpenPGP data", try this alternative:
# sudo apt-key adv --keyserver 'hkp://keyserver.ubuntu.com:80' --recv-key C1CF6E31E6BADE8868B172B4F42ED6FBAB17C654

# Update package list:
sudo apt-get update

# ════════════════════════════════════════════════════
# STEP 2: Install ROS Melodic (ros-base = minimal)
# ════════════════════════════════════════════════════
sudo apt-get install -y ros-melodic-ros-base

# If you get "Unable to locate package ros-melodic-ros-base":
# 1. Check your Ubuntu version: lsb_release -a
#    If it's NOT 18.04, Melodic won't work. See Option B3 below.
# 2. Check if the repository was added: cat /etc/apt/sources.list.d/ros-latest.list
#    Should show: deb http://packages.ros.org/ros/ubuntu bionic main
# 3. Try: sudo apt-get update && apt-cache search ros-melodic
#    If nothing appears, the repository isn't configured correctly.

# ════════════════════════════════════════════════════
# STEP 3: Install specific ROS packages we need
# ════════════════════════════════════════════════════
sudo apt-get install -y \
    ros-melodic-usb-cam \
    ros-melodic-cv-bridge \
    ros-melodic-image-transport \
    ros-melodic-rqt-image-view \
    python-rosdep \
    python-rosinstall \
    python-catkin-tools

# ════════════════════════════════════════════════════
# STEP 4: Install Python 2 dependencies (RECOMMENDED)
# ════════════════════════════════════════════════════
# ⚠️ CRITICAL DECISION: Python 2 vs Python 3
#
# ROS Melodic was built for Python 2.7. While Python 3 support exists,
# it's INCOMPLETE (rospy, cv_bridge don't work out-of-the-box).
#
# For a 6-day demo deadline: USE PYTHON 2 (pragmatic, works immediately)
# For long-term: Upgrade to Ubuntu 20.04 + ROS Noetic (Python 3 native)

sudo apt-get install -y \
    python-opencv \
    python-serial \
    python-numpy

# Verify Python 2 works with ROS:
python2 -c "import rospy; print('✅ Python 2 + ROS Melodic works')"

echo "=== Using Python 2 for ROS Melodic (recommended) ==="
echo "All scripts will use #!/usr/bin/env python (not python3)"

# ════════════════════════════════════════════════════
# STEP 5: Initialize rosdep
# ════════════════════════════════════════════════════
sudo rosdep init 2>/dev/null || echo "rosdep already initialized"
rosdep update

# ════════════════════════════════════════════════════
# STEP 6: Verify installation
# ════════════════════════════════════════════════════

# ════════════════════════════════════════════════════
# STEP 4: Initialize rosdep
# ════════════════════════════════════════════════════
sudo rosdep init
rosdep update

# ════════════════════════════════════════════════════
# STEP 5: Source and verify
# ════════════════════════════════════════════════════
source /opt/ros/melodic/setup.bash

# Verify:
rosversion -d
# Expected: melodic

# Test Python 2 imports:
python2 -c "import rospy; print('✅ ROS Melodic + Python 2 working')"

echo "=== ROS Melodic installed successfully ==="
```

---

### 🔄 **RECOVERY PATH: If You Just Re-installed ROS Melodic**

**If you had ROS installation issues and just fixed them, you need to:**

1. **Change Python scripts from Python 3 to Python 2:**
   ```bash
   # Change shebang in all scripts:
   sed -i 's|#!/usr/bin/env python3|#!/usr/bin/env python|' \
       ~/catkin_ws/src/sprayer_control/scripts/*.py
   
   # Verify:
   head -1 ~/catkin_ws/src/sprayer_control/scripts/detector_node.py
   # Should show: #!/usr/bin/env python (not python3)
   ```

2. **Rebuild your catkin workspace:**
   ```bash
   cd ~/catkin_ws
   rm -rf build/ devel/  # Clean old build
   catkin_make           # Rebuild
   source devel/setup.bash
   ```

3. **Verify custom message:**
   ```bash
   rosmsg show sprayer_control/Detection
   # Should show the message definition
   ```

4. **Continue to Day 1, Step 1 (Camera Setup)** - Skip ahead to line ~1380 in this guide.

---

**Option B2: Build ROS Noetic from source on 18.04**

Possible but takes 2-4 HOURS to compile and uses ~5 GB of disk during build. NOT recommended on a 32GB card.

**Option B3: Use a Docker container with Ubuntu 20.04 + ROS Noetic**

Works but adds complexity. Docker images take 2-4 GB. Recommended only if you're experienced with Docker.

```bash
# Quick check — is Docker already installed?
docker --version
# If yes and you want to try this:
# sudo docker pull ros:noetic-ros-base
# sudo docker run -it --runtime nvidia --network host ros:noetic-ros-base bash
# But this adds complexity. Stick with Option B1 unless you have a reason.
```

**MY RECOMMENDATION:**

```
    IF Ubuntu 20.04 → Install ROS Noetic via apt (Path A). BEST CASE.
    IF Ubuntu 18.04 → Install ROS Melodic via apt (Option B1). WORKS FINE.
    
    Everything in our project works on BOTH Melodic and Noetic.
    The only difference is:
      Noetic:  /opt/ros/noetic/setup.bash,  uses Python 3 by default
      Melodic: /opt/ros/melodic/setup.bash,  uses Python 2 by default (fixable)
    
    In all commands below, I'll write:
      source /opt/ros/noetic/setup.bash
    If you installed Melodic, mentally replace "noetic" with "melodic".
```

---

## 1.6 CONFIGURING ~/.bashrc

**What is ~/.bashrc?** It's a script that runs every time you open a new terminal. We add lines to it so ROS is automatically set up in every terminal session.

```bash
# ════════════════════════════════════════════════════
# STEP 1: Backup the current .bashrc (safety!)
# ════════════════════════════════════════════════════
cp ~/.bashrc ~/.bashrc.backup.$(date +%Y%m%d)
# This creates a backup like: ~/.bashrc.backup.20260210
# If anything goes wrong, restore with: cp ~/.bashrc.backup.20260210 ~/.bashrc

# ════════════════════════════════════════════════════
# STEP 2: Add ROS and project environment setup
# ════════════════════════════════════════════════════
# We'll append to .bashrc. Each line is explained.

cat >> ~/.bashrc << 'BASHRC_END'

# ═══════════════════════════════════════════════════════
# JETSON NANO — ROS & DRONE PROJECT ENVIRONMENT
# Added: Feb 10, 2026
# ═══════════════════════════════════════════════════════

# 1. Source ROS Noetic (or Melodic — change "noetic" to "melodic" if needed)
#    This sets up all ROS commands (roscore, rosrun, rostopic, etc.)
source /opt/ros/noetic/setup.bash

# 2. Source your catkin workspace (after you create it in Phase 2)
#    This lets ROS find YOUR packages (sprayer_control)
#    It's OK if this file doesn't exist yet — it'll just print a warning
if [ -f ~/catkin_ws/devel/setup.bash ]; then
    source ~/catkin_ws/devel/setup.bash
fi

# 3. ROS Network Configuration
#    ROS_IP = this machine's IP (Jetson's IP)
#    ROS_MASTER_URI = where roscore is running (also this machine)
#    For single-machine setup (our case), both point to localhost.
export ROS_IP=127.0.0.1
export ROS_MASTER_URI=http://127.0.0.1:11311

# 4. CUDA PATH (needed for GPU operations)
#    JetPack installs CUDA but sometimes doesn't add it to PATH
export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH

# 5. Helpful aliases (shortcuts for common commands)
alias cb='cd ~/catkin_ws && catkin_make && source devel/setup.bash'
alias launch='roslaunch sprayer_control demo.launch'
alias topics='rostopic list'
alias det='rostopic echo /detection/result'
alias spray='rostopic echo /spray/status'
alias diskcheck='df -h / && echo "---" && free -h'
alias jetson_status='sudo nvpmodel -q && sudo jetson_clocks --show'

BASHRC_END

# ════════════════════════════════════════════════════
# STEP 3: Reload .bashrc so changes take effect NOW
# ════════════════════════════════════════════════════
source ~/.bashrc

# ════════════════════════════════════════════════════
# STEP 4: Verify
# ════════════════════════════════════════════════════
echo "ROS_DISTRO: $ROS_DISTRO"
echo "ROS_MASTER_URI: $ROS_MASTER_URI"
echo "CUDA: $(nvcc --version 2>/dev/null | grep release || echo 'not in PATH')"
which roscore
# Expected:
#   ROS_DISTRO: noetic (or melodic)
#   ROS_MASTER_URI: http://127.0.0.1:11311
#   CUDA: release 10.2 ...
#   /opt/ros/noetic/bin/roscore
```

---

## 1.7 INSTALLING PYTHON DEPENDENCIES

```bash
# ════════════════════════════════════════════════════
# Check Python version:
# ════════════════════════════════════════════════════
python3 --version
# Expected: Python 3.6.9 (Ubuntu 18.04) or Python 3.8.x (Ubuntu 20.04)

# ════════════════════════════════════════════════════
# Upgrade pip (the Python package installer):
# ════════════════════════════════════════════════════
python3 -m pip install --upgrade pip

# ════════════════════════════════════════════════════
# Install project dependencies:
# ════════════════════════════════════════════════════

# pyserial — for talking to ESP32 via USB serial
python3 -m pip install pyserial

# numpy — required by OpenCV (probably already installed with JetPack)
python3 -m pip install numpy

# OpenCV — IMPORTANT: JetPack usually pre-installs OpenCV with CUDA support.
# Check if it's already there BEFORE installing:
python3 -c "import cv2; print(f'OpenCV {cv2.__version__} — Build: {cv2.getBuildInformation().split(chr(10))[1]}')"

# If the above command works and shows a version → OpenCV is installed. DON'T reinstall.
# If it says "ModuleNotFoundError" → install it:
# python3 -m pip install opencv-python==4.5.5.64
#
# ⚠️ ONLY install via pip if JetPack's OpenCV is broken.
# The JetPack OpenCV has CUDA support. The pip version does NOT.
# Prefer JetPack's version.

# pymavlink — for future MAVLink communication with Pixhawk
# (not needed for Survival Mode demo, but install it now while we have time)
python3 -m pip install pymavlink

# ════════════════════════════════════════════════════
# Verify all imports work:
# ════════════════════════════════════════════════════
python3 << 'PYCHECK'
import sys
print(f"Python: {sys.version}")

try:
    import cv2
    print(f"✅ OpenCV: {cv2.__version__}")
except ImportError:
    print("❌ OpenCV: NOT INSTALLED")

try:
    import numpy as np
    print(f"✅ NumPy: {np.__version__}")
except ImportError:
    print("❌ NumPy: NOT INSTALLED")

try:
    import serial
    print(f"✅ pyserial: {serial.__version__}")
except ImportError:
    print("❌ pyserial: NOT INSTALLED")

try:
    import rospy
    print(f"✅ rospy: available")
except ImportError:
    print("⚠️  rospy: not importable outside ROS environment (normal if sourced)")

print("\nAll checks done.")
PYCHECK

echo ""
echo "════════════════════════════════════════"
echo "PHASE 1 COMPLETE — System is prepped!"
echo "════════════════════════════════════════"
diskcheck
```

---

# ═══════════════════════════════════════════════════════════
# PHASE 2: WORKSPACE CREATION — The Foundation
# ═══════════════════════════════════════════════════════════

---

## 2.1 CREATING THE catkin_ws WORKSPACE

**What is a catkin workspace?** It's a folder structure that ROS uses to build and find your code. Think of it like a "project directory" but with ROS conventions.

```bash
# ════════════════════════════════════════════════════
# STEP 1: Create the workspace directory structure
# ════════════════════════════════════════════════════
# ~/catkin_ws/        ← the workspace root
# ~/catkin_ws/src/    ← YOUR code goes here
# ~/catkin_ws/build/  ← (auto-generated by catkin_make)
# ~/catkin_ws/devel/  ← (auto-generated by catkin_make)

mkdir -p ~/catkin_ws/src

# ════════════════════════════════════════════════════
# STEP 2: Initialize the workspace (first build)
# ════════════════════════════════════════════════════
cd ~/catkin_ws

# This creates the build/ and devel/ folders:
catkin_make

# Source the workspace (so ROS knows about it):
source devel/setup.bash

# ════════════════════════════════════════════════════
# STEP 3: Verify the workspace
# ════════════════════════════════════════════════════
echo $ROS_PACKAGE_PATH
# Expected: /home/jetson/catkin_ws/src:/opt/ros/noetic/share
# This means ROS looks in YOUR src/ folder AND the ROS system folder.
```

---

## 2.2 CREATING THE sprayer_control PACKAGE

```bash
# ════════════════════════════════════════════════════
# STEP 1: Create the package
# ════════════════════════════════════════════════════
cd ~/catkin_ws/src

# catkin_create_pkg <name> <dependencies>
catkin_create_pkg sprayer_control std_msgs rospy sensor_msgs cv_bridge message_generation

# This creates:
# ~/catkin_ws/src/sprayer_control/
# ├── CMakeLists.txt    ← Build configuration (we'll edit this)
# ├── package.xml       ← Package metadata (we'll edit this)
# └── src/              ← (empty, we won't use this folder)

# ════════════════════════════════════════════════════
# STEP 2: Create the folder structure we need
# ════════════════════════════════════════════════════
cd ~/catkin_ws/src/sprayer_control

# Scripts folder — where our Python nodes live
mkdir -p scripts

# Message definitions — our custom Detection message
mkdir -p msg

# Launch files — for starting everything together
mkdir -p launch

# Config — for parameter files (HSV values, etc.)
mkdir -p config

# Verify:
find . -type d
# Should show:
# .
# ./src
# ./scripts
# ./msg
# ./launch
# ./config
```

---

## 2.3 CREATING THE CUSTOM MESSAGE

The `Detection.msg` file defines the data structure that the detector node publishes and the spray logic node subscribes to.

```bash
# ════════════════════════════════════════════════════
# Create the message file
# ════════════════════════════════════════════════════
cat > ~/catkin_ws/src/sprayer_control/msg/Detection.msg << 'EOF'
# Detection.msg — Custom ROS message for target detection results
# Package: sprayer_control
#
# Published by: detector_node.py
# Subscribed by: spray_logic_node.py

Header header
bool detected           # Is a target visible in this frame?
int32 cx                # Bounding box center X (pixels)
int32 cy                # Bounding box center Y (pixels)
int32 area              # Bounding box area in pixels² (w * h)
float32 confidence      # Detection confidence (0.0 - 1.0)
string position_hint    # "LEFT", "RIGHT", "CENTER", "TOO_FAR", "TOO_CLOSE", "NONE"
EOF

# Verify:
cat ~/catkin_ws/src/sprayer_control/msg/Detection.msg
echo ""
echo "✅ Detection.msg created"
```

---

## 2.4 EDITING CMakeLists.txt

This is the most error-prone step. `CMakeLists.txt` tells ROS how to build your package. The auto-generated file has most things commented out — we need to uncomment and edit specific sections.

**The safest approach: replace the entire file with a known-good version.**

```bash
# ════════════════════════════════════════════════════
# Backup the original:
# ════════════════════════════════════════════════════
cp ~/catkin_ws/src/sprayer_control/CMakeLists.txt \
   ~/catkin_ws/src/sprayer_control/CMakeLists.txt.original

# ════════════════════════════════════════════════════
# Write the correct CMakeLists.txt:
# ════════════════════════════════════════════════════
cat > ~/catkin_ws/src/sprayer_control/CMakeLists.txt << 'EOF'
cmake_minimum_required(VERSION 3.0.2)
project(sprayer_control)

## Find catkin and required ROS packages
find_package(catkin REQUIRED COMPONENTS
  std_msgs
  rospy
  sensor_msgs
  cv_bridge
  message_generation
)

## Declare our custom messages
add_message_files(
  FILES
  Detection.msg
)

## Generate messages with dependencies
generate_messages(
  DEPENDENCIES
  std_msgs
)

## Declare the catkin package
catkin_package(
  CATKIN_DEPENDS std_msgs rospy sensor_msgs cv_bridge message_runtime
)

## Include dirs
include_directories(
  ${catkin_INCLUDE_DIRS}
)

## Mark Python scripts as installable (optional but good practice)
catkin_install_python(PROGRAMS
  scripts/detector_node.py
  scripts/spray_logic_node.py
  scripts/hsv_tuner.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)
EOF

echo "✅ CMakeLists.txt written"
```

**Explanation of key lines:**
- `message_generation` in `find_package` → tells CMake we're defining custom messages
- `add_message_files` → registers `Detection.msg` for code generation
- `generate_messages` → generates Python/C++ bindings from the `.msg` file
- `message_runtime` in `catkin_package` → tells other packages they need the message runtime to use our messages
- `catkin_install_python` → marks our scripts for installation (optional but prevents warnings)

---

## 2.5 EDITING package.xml

```bash
# ════════════════════════════════════════════════════
# Backup the original:
# ════════════════════════════════════════════════════
cp ~/catkin_ws/src/sprayer_control/package.xml \
   ~/catkin_ws/src/sprayer_control/package.xml.original

# ════════════════════════════════════════════════════
# Write the correct package.xml:
# ════════════════════════════════════════════════════
cat > ~/catkin_ws/src/sprayer_control/package.xml << 'EOF'
<?xml version="1.0"?>
<package format="2">
  <name>sprayer_control</name>
  <version>1.0.0</version>
  <description>
    Autonomous sprayer control system for pollination drone.
    Part of the Synergie Drone project (new_plan_2_9).
    Detects yellow targets via camera, triggers sprayer via ESP32.
  </description>

  <maintainer email="karimn14@todo.todo">karimn14</maintainer>
  <license>MIT</license>

  <buildtool_depend>catkin</buildtool_depend>

  <!-- Build dependencies (needed to compile) -->
  <build_depend>std_msgs</build_depend>
  <build_depend>rospy</build_depend>
  <build_depend>sensor_msgs</build_depend>
  <build_depend>cv_bridge</build_depend>
  <build_depend>message_generation</build_depend>

  <!-- Runtime dependencies (needed to run) -->
  <exec_depend>std_msgs</exec_depend>
  <exec_depend>rospy</exec_depend>
  <exec_depend>sensor_msgs</exec_depend>
  <exec_depend>cv_bridge</exec_depend>
  <exec_depend>message_runtime</exec_depend>

  <!-- For Python 3 on ROS Melodic (uncomment if on Ubuntu 18.04): -->
  <!-- <exec_depend>python3-catkin-pkg-modules</exec_depend> -->
  <!-- <exec_depend>python3-rospkg-modules</exec_depend> -->

</package>
EOF

echo "✅ package.xml written"
```

---

## 2.6 FIRST BUILD + VERIFY

**This is the moment of truth.** If the build succeeds, your workspace is correctly set up.

```bash
# ════════════════════════════════════════════════════
# STEP 1: Build the workspace
# ════════════════════════════════════════════════════
cd ~/catkin_ws

# Build!
# This will:
# - Compile the message definitions (Detection.msg → Python class)
# - Register the package with ROS
# - Take 30-60 seconds on first build
catkin_make

# WHAT TO LOOK FOR:
# ✅ GOOD OUTPUT (last few lines):
#   [100%] Built target sprayer_control_generate_messages_py
#   [100%] Built target sprayer_control_generate_messages
#
# ❌ BAD OUTPUT (errors):
#   "Could not find a package configuration file provided by ..."
#   → Missing dependency. Run: sudo apt-get install ros-noetic-<missing_pkg>
#
#   "CMake Error: ... Detection.msg ..."
#   → Message file path wrong. Check: ls ~/catkin_ws/src/sprayer_control/msg/

# ════════════════════════════════════════════════════
# STEP 2: Source the workspace
# ════════════════════════════════════════════════════
source devel/setup.bash
# (.bashrc already does this automatically for new terminals)

# ════════════════════════════════════════════════════
# STEP 3: Verify the message was generated
# ════════════════════════════════════════════════════
rosmsg show sprayer_control/Detection

# Expected output:
# std_msgs/Header header
#   uint32 seq
#   time stamp
#   string frame_id
# bool detected
# int32 cx
# int32 cy
# int32 area
# float32 confidence
# string position_hint

# ════════════════════════════════════════════════════
# STEP 4: Verify ROS can find the package
# ════════════════════════════════════════════════════
rospack find sprayer_control
# Expected: /home/jetson/catkin_ws/src/sprayer_control

# ════════════════════════════════════════════════════
# STEP 5: Quick roscore test
# ════════════════════════════════════════════════════
# Start roscore in the background:
roscore &
ROSCORE_PID=$!

# Wait for it to start:
sleep 3

# List topics (should show default topics):
rostopic list
# Expected:
# /rosout
# /rosout_agg

# Kill roscore:
kill $ROSCORE_PID
wait $ROSCORE_PID 2>/dev/null

echo ""
echo "════════════════════════════════════════════════"
echo "✅ PHASE 2 COMPLETE — Workspace ready!"
echo "════════════════════════════════════════════════"
echo ""
echo "Package: sprayer_control"
echo "Location: $(rospack find sprayer_control)"
echo "Message: sprayer_control/Detection"
echo ""
echo "Next: Phase 3 — Daily Execution"
echo "════════════════════════════════════════════════"
```

---

# ═══════════════════════════════════════════════════════════
# PHASE 3: DAILY EXECUTION
# ═══════════════════════════════════════════════════════════

---

## 📅 DAY 1 (Feb 10): CAMERA SETUP & VERIFICATION

**Goal:** USB camera publishes frames via ROS at 25-30 FPS. You can see live video.

### Step 1: Plug in the Jete Webcam

Plug the Jete USB webcam into any USB port on the Jetson Nano.

```bash
# ════════════════════════════════════════════════════
# STEP 1: Check if Linux sees the camera
# ════════════════════════════════════════════════════
ls /dev/video*

# Expected: /dev/video0 (maybe also video1)
# If nothing appears:
#   - Unplug and re-plug the camera
#   - Try a different USB port
#   - Try: ls /dev/video*  again after 5 seconds

# More detail:
v4l2-ctl --list-devices 2>/dev/null || sudo apt-get install -y v4l2-utils && v4l2-ctl --list-devices

# This shows which camera is on which /dev/videoN device.
# Look for something like "USB Camera" or "Jete" → /dev/video0
```

### Step 2: Quick OpenCV test (no ROS)

```bash
# ════════════════════════════════════════════════════
# STEP 2: Test the camera with raw OpenCV (no ROS yet)
# ════════════════════════════════════════════════════
# This is a quick sanity check. If this works, the camera hardware is OK.

python3 << 'CAMTEST'
import cv2
import time

print("Opening camera...")
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("❌ FAILED: Cannot open camera /dev/video0")
    print("   Try: python3 -c \"import cv2; cap=cv2.VideoCapture(1); print(cap.isOpened())\"")
    exit(1)

# Set resolution
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# Grab 10 frames and measure FPS
start = time.time()
for i in range(10):
    ret, frame = cap.read()
    if not ret:
        print(f"❌ FAILED: Frame {i} grab failed")
        break

elapsed = time.time() - start
fps = 10 / elapsed if elapsed > 0 else 0

w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

print(f"✅ Camera works!")
print(f"   Resolution: {w}x{h}")
print(f"   Measured FPS: {fps:.1f}")
print(f"   Frame shape: {frame.shape}")

# Save a test frame (so you can verify the image is correct)
cv2.imwrite("/tmp/camera_test.jpg", frame)
print(f"   Test frame saved to /tmp/camera_test.jpg")

cap.release()
print("Done.")
CAMTEST

# ════════════════════════════════════════════════════
# View the test frame (from your laptop via VS Code):
# ════════════════════════════════════════════════════
# In VS Code Remote-SSH, navigate to /tmp/camera_test.jpg
# and click on it. VS Code can display JPEG images.
# OR download it:
#   On laptop PowerShell: scp jetson@192.168.55.1:/tmp/camera_test.jpg .
```

### Step 3: Install and test usb_cam (ROS camera driver)

```bash
# ════════════════════════════════════════════════════
# STEP 3: Install usb_cam (if not installed in Phase 1)
# ════════════════════════════════════════════════════
# Replace "noetic" with "melodic" if on Ubuntu 18.04
sudo apt-get install -y ros-noetic-usb-cam

# ════════════════════════════════════════════════════
# STEP 4: Start roscore (in one terminal)
# ════════════════════════════════════════════════════
# If using VS Code, click the "+" in the terminal panel to open a new terminal.

# TERMINAL 1:
roscore

# ════════════════════════════════════════════════════
# STEP 5: Start the camera node (in another terminal)
# ════════════════════════════════════════════════════

# TERMINAL 2:
rosrun usb_cam usb_cam_node \
    _video_device:=/dev/video0 \
    _image_width:=640 \
    _image_height:=480 \
    _framerate:=30 \
    _pixel_format:=mjpeg

# You should see output like:
# [ INFO] [xxxx]: using default camera info URL
# [ INFO] [xxxx]: Starting 'USB Camera' ...

# ════════════════════════════════════════════════════
# STEP 6: Verify frames are publishing (in a third terminal)
# ════════════════════════════════════════════════════

# TERMINAL 3:
rostopic hz /usb_cam/image_raw

# Expected output (updates every second):
# average rate: 30.001
#         min: 0.033s max: 0.034s std dev: 0.00010s window: 30
#
# PASS CRITERIA: Rate is 25-30 Hz.
# If rate is < 15 Hz → try _pixel_format:=yuyv instead of mjpeg

# Also check the topic exists:
rostopic list | grep usb_cam
# Expected: /usb_cam/image_raw and /usb_cam/camera_info

# ════════════════════════════════════════════════════
# STEP 7: Save a frame from ROS topic (verify it's real)
# ════════════════════════════════════════════════════
# This grabs one message from the topic and saves info about it:
rostopic echo /usb_cam/image_raw --noarr -n 1
# Shows: header, height, width, encoding, step, etc.
# Height should be 480, width 640, encoding "rgb8" or "bgr8"
```

### Step 4: Create and test the launch file

```bash
# ════════════════════════════════════════════════════
# STEP 8: Create the demo.launch file
# ════════════════════════════════════════════════════
cat > ~/catkin_ws/src/sprayer_control/launch/demo.launch << 'EOF'
<!-- demo.launch — Main launch file for Sprayer Control Demo -->
<!-- Architecture: OPTION A — Full Pixhawk Control (No ESP32) -->
<!-- Usage: roslaunch sprayer_control demo.launch -->
<!-- Override: roslaunch sprayer_control demo.launch camera_device:=/dev/video1 -->
<!-- Override: roslaunch sprayer_control demo.launch fcu_url:=/dev/ttyTHS1:921600 -->
<launch>

    <!-- ═══ ARGUMENTS ═══ -->
    <arg name="camera_device" default="/dev/video0" />
    <arg name="image_width"   default="640" />
    <arg name="image_height"  default="480" />
    <arg name="framerate"     default="30" />

    <!-- Pixhawk UART connection -->
    <arg name="fcu_url"       default="/dev/ttyTHS1:921600" />
    <arg name="gcs_url"       default="" />
    <arg name="tgt_system"    default="1" />
    <arg name="tgt_component" default="1" />

    <!-- Sprayer servo parameters -->
    <arg name="fan_pwm"         default="1800" />
    <arg name="feeder_pwm"      default="1650" />
    <arg name="fan_spool_time"  default="0.4" />
    <arg name="fan_shutdown_time" default="0.3" />

    <!-- ═══ MAVROS (MAVLink bridge to Pixhawk) ═══ -->
    <include file="$(find mavros)/launch/apm.launch">
        <arg name="fcu_url"       value="$(arg fcu_url)" />
        <arg name="gcs_url"       value="$(arg gcs_url)" />
        <arg name="tgt_system"    value="$(arg tgt_system)" />
        <arg name="tgt_component" value="$(arg tgt_component)" />
    </include>

    <!-- ═══ USB CAMERA NODE ═══ -->
    <node name="usb_cam" pkg="usb_cam" type="usb_cam_node" output="screen">
        <param name="video_device"   value="$(arg camera_device)" />
        <param name="image_width"    value="$(arg image_width)" />
        <param name="image_height"   value="$(arg image_height)" />
        <param name="framerate"      value="$(arg framerate)" />
        <param name="pixel_format"   value="mjpeg" />
        <param name="camera_name"    value="webcam" />
        <param name="io_method"      value="mmap" />
    </node>

    <!-- ═══ DETECTOR NODE ═══ -->
    <node name="detector" pkg="sprayer_control" type="detector_node.py" output="screen">
        <!-- HSV range for yellow (tune with hsv_tuner.py first) -->
        <param name="hsv_h_low"  value="20" />
        <param name="hsv_h_high" value="35" />
        <param name="hsv_s_low"  value="100" />
        <param name="hsv_s_high" value="255" />
        <param name="hsv_v_low"  value="100" />
        <param name="hsv_v_high" value="255" />
        <param name="min_contour_area" value="500" />
        <param name="center_tolerance" value="0.15" />
        <param name="close_area_threshold" value="15000" />
        <param name="far_area_threshold" value="2000" />
    </node>

    <!-- ═══ SPRAY LOGIC NODE (mavros servo control) ═══ -->
    <node name="spray_logic" pkg="sprayer_control" type="spray_logic_node.py" output="screen">
        <param name="spray_duration"     value="0.5" />
        <param name="cooldown_duration"  value="2.0" />
        <param name="alignment_hold_time" value="1.0" />
        <param name="detection_timeout"  value="2.0" />
        <param name="fan_spool_time"     value="$(arg fan_spool_time)" />
        <param name="fan_shutdown_time"  value="$(arg fan_shutdown_time)" />
        <param name="fan_pwm"            value="$(arg fan_pwm)" />
        <param name="feeder_pwm"         value="$(arg feeder_pwm)" />
    </node>

</launch>
EOF

echo "✅ demo.launch created"

# ════════════════════════════════════════════════════
# STEP 9: Test the launch file (camera only for now)
# ════════════════════════════════════════════════════
# Kill any running roscore first:
killall roscore rosmaster 2>/dev/null
sleep 2

# The launch file will start roscore automatically + all nodes.
# Detector and spray_logic nodes will fail (scripts don't exist yet) — that's OK.
# We just want to verify the camera launches correctly.
roslaunch sprayer_control demo.launch

# Expected:
# - mavros may fail (Pixhawk not connected yet) → EXPECTED on Day 1
# - usb_cam starts successfully
# - detector_node.py → error "No such file" → EXPECTED (we create it on Day 2)
# - spray_logic_node.py → error "No such file" → EXPECTED (we create it on Day 3)
#
# Press Ctrl+C to stop.
```

### Day 1 — Completion Checklist

```bash
# Run this checklist script:
echo "════════════════════════════════════════"
echo "DAY 1 CHECKLIST"
echo "════════════════════════════════════════"

echo -n "[ ] Camera device exists: "
ls /dev/video0 2>/dev/null && echo "✅" || echo "❌"

echo -n "[ ] OpenCV can grab frames: "
python3 -c "import cv2; c=cv2.VideoCapture(0); r,f=c.read(); print('✅' if r else '❌'); c.release()"

echo -n "[ ] usb_cam package installed: "
rospack find usb_cam 2>/dev/null && echo " ✅" || echo "❌"

echo -n "[ ] catkin_ws builds cleanly: "
cd ~/catkin_ws && catkin_make 2>&1 | tail -1

echo -n "[ ] Detection.msg is registered: "
rosmsg show sprayer_control/Detection 2>/dev/null | head -1 && echo " ✅" || echo "❌"

echo "════════════════════════════════════════"
```

---

## 📅 DAY 2 (Feb 11): DETECTOR NODE — File Placement & Template

**Goal:** Create the `detector_node.py` file in the correct location with the correct structure.

### Step 1: Create the detector_node.py file

**The full code is already written** in your repository at `ros_nodes/scripts/detector_node.py`. You need to copy it to the Jetson.

**Option A: If you cloned the repo on the Jetson:**

```bash
# If you cloned syergie_drone repo on the Jetson:
cp ~/syergie_drone/new_plan_2_9/ros_nodes/scripts/detector_node.py \
   ~/catkin_ws/src/sprayer_control/scripts/detector_node.py
```

**Option B: Create via VS Code Remote-SSH (recommended):**

Open VS Code (connected to Jetson via Remote-SSH). Create file at:
```
~/catkin_ws/src/sprayer_control/scripts/detector_node.py
```

Paste the full content from the `ros_nodes/scripts/detector_node.py` file in this repository.

**Option C: Download from GitHub directly on the Jetson:**

```bash
# If your repo is public or you have access:
cd ~/catkin_ws/src/sprayer_control/scripts

curl -o detector_node.py \
    "https://raw.githubusercontent.com/karimn14/syergie_drone/main/new_plan_2_9/ros_nodes/scripts/detector_node.py"

# Verify it downloaded:
head -5 detector_node.py
# Should show the shebang and docstring
```

**Option D: Create from scratch using this template:**

If none of the above work, create the file manually. Here's the template structure (you already have the full code in this repo — this is just so you understand the architecture):

```bash
cat > ~/catkin_ws/src/sprayer_control/scripts/detector_node.py << 'TEMPLATE'
#!/usr/bin/env python3
"""
detector_node.py — Yellow Ball Detection Node (ROS1)
=====================================================
This node:
1. Subscribes to /usb_cam/image_raw (camera frames)
2. Converts to HSV color space
3. Thresholds for yellow (configurable H, S, V ranges)
4. Finds the largest yellow contour
5. Computes center, area, and position hint (LEFT/RIGHT/CENTER)
6. Publishes Detection message to /detection/result
7. Publishes debug overlay to /detector/debug_image
"""

import rospy
import cv2
import numpy as np
from sensor_msgs.msg import Image
from cv_bridge import CvBridge, CvBridgeError
from sprayer_control.msg import Detection


class YellowBallDetector:
    def __init__(self):
        rospy.init_node('detector_node', anonymous=False)

        # ─── HSV Parameters (tune with hsv_tuner.py) ───
        self.hsv_lower = np.array([
            rospy.get_param('~hsv_h_low', 20),
            rospy.get_param('~hsv_s_low', 100),
            rospy.get_param('~hsv_v_low', 100),
        ])
        self.hsv_upper = np.array([
            rospy.get_param('~hsv_h_high', 35),
            rospy.get_param('~hsv_s_high', 255),
            rospy.get_param('~hsv_v_high', 255),
        ])

        self.min_area = rospy.get_param('~min_contour_area', 500)
        self.img_width = 640
        self.img_height = 480
        self.center_tolerance = rospy.get_param('~center_tolerance', 0.15)
        self.close_area = rospy.get_param('~close_area_threshold', 15000)
        self.far_area = rospy.get_param('~far_area_threshold', 2000)

        # ─── ROS Plumbing ───
        self.bridge = CvBridge()
        self.det_pub = rospy.Publisher('/detection/result', Detection, queue_size=1)
        self.debug_pub = rospy.Publisher('/detector/debug_image', Image, queue_size=1)
        self.image_sub = rospy.Subscriber(
            '/usb_cam/image_raw', Image, self.image_callback,
            queue_size=1, buff_size=2**24
        )

        rospy.loginfo("═══ Yellow Ball Detector Node Started ═══")

    def image_callback(self, msg):
        """Main processing callback — runs once per camera frame."""
        # TODO: Paste the full implementation from the repo
        # See: ros_nodes/scripts/detector_node.py in the project files
        pass

    def _detect_yellow(self, frame):
        """HSV threshold → morphology → largest contour → (cx,cy,area,conf,bbox)"""
        # TODO: Paste implementation
        pass

    def _get_position_hint(self, cx, area):
        """Classify target position: LEFT/RIGHT/CENTER/TOO_FAR/TOO_CLOSE"""
        # TODO: Paste implementation
        pass

    def _draw_debug_overlay(self, frame, detection, position_hint):
        """Draw bboxes, crosshairs, and status text on frame."""
        # TODO: Paste implementation
        pass


def main():
    try:
        detector = YellowBallDetector()
        rospy.spin()
    except rospy.ROSInterruptException:
        rospy.loginfo("Detector node shutting down.")


if __name__ == '__main__':
    main()
TEMPLATE
```

### Step 2: Fix line endings and make it executable

```bash
# ════════════════════════════════════════════════════
# STEP 1: FIX WINDOWS LINE ENDINGS FIRST (CRITICAL!)
# ════════════════════════════════════════════════════
# This MUST be done BEFORE changing the shebang, otherwise
# you'll change "python3\r" to "python\r" and the error persists!

# Install dos2unix if not present:
sudo apt-get install -y dos2unix

# Convert ALL Python files at once:
dos2unix ~/catkin_ws/src/sprayer_control/scripts/*.py

# Alternative if dos2unix fails:
# sed -i 's/\r$//' ~/catkin_ws/src/sprayer_control/scripts/*.py

# Verify the line endings are fixed (should NOT see \r):
head -1 ~/catkin_ws/src/sprayer_control/scripts/detector_node.py | od -c
# Look for the end of the line - should only see: \n
# Should NOT see: \r \n

# ════════════════════════════════════════════════════
# STEP 2: CHANGE SHEBANG TO PYTHON 2 (for ROS Melodic)
# ════════════════════════════════════════════════════
# Now that line endings are fixed, change python3 to python:
sed -i 's|#!/usr/bin/env python3|#!/usr/bin/env python|' \
    ~/catkin_ws/src/sprayer_control/scripts/*.py

# Verify the shebang:
head -1 ~/catkin_ws/src/sprayer_control/scripts/detector_node.py
# Should show: #!/usr/bin/env python (not python3)

# Double-check with od to ensure no \r at the end:
head -1 ~/catkin_ws/src/sprayer_control/scripts/detector_node.py | od -c
# Should end with: p y t h o n \n
# NOT: p y t h o n \r \n

# ════════════════════════════════════════════════════
# STEP 2.5: ADD PYTHON 2 ENCODING DECLARATION (for Unicode characters)
# ════════════════════════════════════════════════════
# Python 2 requires this if file contains any non-ASCII characters
# (em-dashes, smart quotes, etc. from copy-paste)
sed -i '2i# -*- coding: utf-8 -*-' \
    ~/catkin_ws/src/sprayer_control/scripts/*.py

# Verify it was added:
head -3 ~/catkin_ws/src/sprayer_control/scripts/detector_node.py
# Should show:
# #!/usr/bin/env python
# # -*- coding: utf-8 -*-
# """

# ════════════════════════════════════════════════════
# STEP 3: MAKE IT EXECUTABLE
# ════════════════════════════════════════════════════
chmod +x ~/catkin_ws/src/sprayer_control/scripts/*.py

# Verify:
ls -la ~/catkin_ws/src/sprayer_control/scripts/detector_node.py
# Should show: -rwxr-xr-x (the 'x' means executable)
```

### Step 3: Also create the HSV tuner (calibration tool)

```bash
# ════════════════════════════════════════════════════
# Copy or create hsv_tuner.py
# ════════════════════════════════════════════════════
# Same methods as above — copy from repo, download, or create.

# The HSV tuner from this repo is at:
# ros_nodes/scripts/hsv_tuner.py

# Place it at:
# ~/catkin_ws/src/sprayer_control/scripts/hsv_tuner.py

# Fix line endings + change to Python 2 + make executable:
dos2unix ~/catkin_ws/src/sprayer_control/scripts/hsv_tuner.py
sed -i 's|#!/usr/bin/env python3|#!/usr/bin/env python|' \
    ~/catkin_ws/src/sprayer_control/scripts/hsv_tuner.py
chmod +x ~/catkin_ws/src/sprayer_control/scripts/hsv_tuner.py
```

### Step 4: Rebuild and test

```bash
# ════════════════════════════════════════════════════
# Rebuild (to register the new scripts):
# ════════════════════════════════════════════════════
cd ~/catkin_ws && catkin_make && source devel/setup.bash

# ════════════════════════════════════════════════════
# Test the detector node:
# ════════════════════════════════════════════════════

# TERMINAL 1:
roscore

# TERMINAL 2 (camera):
rosrun usb_cam usb_cam_node _video_device:=/dev/video0 _image_width:=640 _image_height:=480

# TERMINAL 3 (detector):
rosrun sprayer_control detector_node.py

# TERMINAL 4 (monitor):
rostopic echo /detection/result

# ════════════════════════════════════════════════════
# TEST: Hold a yellow ball in front of the camera
# ════════════════════════════════════════════════════
# Terminal 4 should show:
#   detected: True
#   cx: 320     (roughly center-ish)
#   cy: 240
#   area: 5000  (depends on distance)
#   position_hint: "CENTER" or "LEFT" or "RIGHT"
#
# Move ball LEFT → position_hint: "LEFT"
# Move ball RIGHT → position_hint: "RIGHT"
# Move ball to center → position_hint: "CENTER"
# Remove ball → detected: False

# ════════════════════════════════════════════════════
# CHECK FPS of the detector:
# ════════════════════════════════════════════════════
rostopic hz /detection/result
# Expected: 25-30 Hz (same as camera)
# If < 15 Hz → detection is too slow, check CPU usage with: htop
```

### Day 2 — If HSV Detection Is Wrong

```bash
# ════════════════════════════════════════════════════
# Run the HSV tuner to find the right values:
# ════════════════════════════════════════════════════
# ⚠️ This needs a display. If headless, use X-forwarding:
#   From laptop: ssh -X jetson@192.168.55.1
#   Then run the tuner.
#
# OR: use VS Code Remote-SSH and forward the display
# OR: Save frames and tune on your laptop

# If you have X-forwarding working:
python3 ~/catkin_ws/src/sprayer_control/scripts/hsv_tuner.py

# If headless (no display):
# Grab a frame and tune offline:
python3 << 'GRAB'
import cv2
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
ret, frame = cap.read()
cv2.imwrite("/tmp/yellow_ball_sample.jpg", frame)
print("Saved /tmp/yellow_ball_sample.jpg — download and tune HSV on your laptop")
cap.release()
GRAB
# Then download: scp jetson@192.168.55.1:/tmp/yellow_ball_sample.jpg .
# Open in any image editor, use a color picker to find the HSV range of the yellow.
# H: typically 20-35 for yellow
# S: typically 80-255 (high saturation)
# V: typically 80-255 (bright)
```

---

## 📅 DAY 3 (Feb 12): PIXHAWK SERVO SETUP & MAVROS CONFIGURATION

**Goal:** Pixhawk AUX channels configured for sprayer. mavros installed. spray_logic_node.py sends DO_SET_SERVO commands to control EDF fan (AUX5) and MG996R servo (AUX6).

> **Architecture:** OPTION A — Full Pixhawk Control (No ESP32)
> The ESP32 and relay module have been removed from the BOM.
> All sprayer actuator control goes through Pixhawk AUX servo outputs
> via MAVLink DO_SET_SERVO commands sent by mavros.

### Step 1: Install mavros on the Jetson

```bash
# ════════════════════════════════════════════════════
# WHY: mavros is the ROS bridge to Pixhawk. It translates ROS messages
# into MAVLink protocol that the Pixhawk understands. Without mavros,
# we cannot send servo commands or receive telemetry.
# ════════════════════════════════════════════════════

# For ROS Melodic (Ubuntu 18.04):
sudo apt-get install -y ros-melodic-mavros ros-melodic-mavros-extras

# For ROS Noetic (Ubuntu 20.04):
# sudo apt-get install -y ros-noetic-mavros ros-noetic-mavros-extras

# ════════════════════════════════════════════════════
# Install GeographicLib datasets (required by mavros):
# ════════════════════════════════════════════════════
wget https://raw.githubusercontent.com/mavlink/mavros/master/mavros/scripts/install_geographiclib_datasets.sh
chmod +x install_geographiclib_datasets.sh
sudo ./install_geographiclib_datasets.sh
rm install_geographiclib_datasets.sh

# ════════════════════════════════════════════════════
# Verify mavros installed:
# ════════════════════════════════════════════════════
rospack find mavros
# Expected: /opt/ros/melodic/share/mavros (or noetic)

rospack find mavros_msgs
# Expected: /opt/ros/melodic/share/mavros_msgs

# Test the import our spray_logic_node needs:
python3 -c "from mavros_msgs.srv import CommandLong; print('✅ mavros_msgs.srv.CommandLong OK')"
# If this fails → see Appendix A "No module named rospy" section
```

### Step 2: Configure Pixhawk AUX channels (via Mission Planner)

```
    ═══════════════════════════════════════════════════════════════
    DO THIS ON YOUR WINDOWS LAPTOP (with Mission Planner)
    Connect Pixhawk via USB to your laptop
    ═══════════════════════════════════════════════════════════════

    The Pixhawk has 8 MAIN outputs (for flight motors) and
    6 AUX outputs. We need AUX5 and AUX6 for sprayer control.

    ArduPilot servo numbering:
      MAIN1-8  = SERVO1 to SERVO8  (flight motors, DO NOT TOUCH)
      AUX1     = SERVO9
      AUX2     = SERVO10
      AUX3     = SERVO11
      AUX4     = SERVO12
      AUX5     = SERVO13  ← EDF Fan ESC
      AUX6     = SERVO14  ← MG996R Continuous Rotation Servo

    ═══════════════════════════════════════════════════════════════
    STEP A: Set BRD_PWM_COUNT = 4
    ═══════════════════════════════════════════════════════════════
    In Mission Planner → Config → Full Parameter List:
      BRD_PWM_COUNT = 4

    WHY: By default, all 6 AUX outputs are reserved for PWM output
    controlled by ArduPilot's motor mixer. BRD_PWM_COUNT=4 means
    only AUX1-AUX4 are reserved for the mixer. AUX5 and AUX6 become
    "pass-through" channels that we can control via MAVLink commands.

    ═══════════════════════════════════════════════════════════════
    STEP B: Configure SERVO13 (AUX5 — EDF Fan ESC)
    ═══════════════════════════════════════════════════════════════
      SERVO13_FUNCTION = 0     (Disabled / pass-through)
      SERVO13_MIN      = 1000  (PWM for fan OFF / ESC idle)
      SERVO13_MAX      = 2000  (PWM maximum)
      SERVO13_TRIM     = 1000  (Default = OFF when no command sent)
      SERVO13_REVERSED = 0     (Normal direction)

    ═══════════════════════════════════════════════════════════════
    STEP C: Configure SERVO14 (AUX6 — MG996R Servo)
    ═══════════════════════════════════════════════════════════════
      SERVO14_FUNCTION = 0     (Disabled / pass-through)
      SERVO14_MIN      = 1000  (PWM minimum)
      SERVO14_MAX      = 2000  (PWM maximum)
      SERVO14_TRIM     = 1500  (Default = STOP — servo center deadband)
      SERVO14_REVERSED = 0     (Normal direction)

    ═══════════════════════════════════════════════════════════════
    STEP D: Click "Write Params" → Reboot Pixhawk
    ═══════════════════════════════════════════════════════════════
    After writing, power-cycle the Pixhawk to apply BRD_PWM_COUNT.

    ═══════════════════════════════════════════════════════════════
    STEP E: Wire the hardware
    ═══════════════════════════════════════════════════════════════
    Pixhawk AUX5 (3-pin header) → EDF Fan ESC signal wire
      - ESC power from battery (NOT from Pixhawk servo rail)
      - ESC signal wire (white/orange) → AUX5 signal pin
      - ESC ground wire (black/brown) → AUX5 ground pin

    Pixhawk AUX6 (3-pin header) → MG996R Servo
      - Servo power (red wire, 5-6V) from a dedicated BEC (NOT Pixhawk rail)
        ⚠️ MG996R draws up to 2.5A stall — Pixhawk's 5V rail cannot supply this!
        Use a 5V 3A BEC from the battery to power the servo rail.
      - Servo signal wire (orange/white) → AUX6 signal pin
      - Servo ground wire (brown/black) → AUX6 ground pin
      - ⚠️ Connect BEC ground to Pixhawk ground (common ground!)
```

### Step 3: Bench-test servo outputs from Mission Planner

```
    ═══════════════════════════════════════════════════════════════
    STILL ON YOUR LAPTOP (Mission Planner connected to Pixhawk)
    ═══════════════════════════════════════════════════════════════

    SAFETY WARNING:
    - Remove propellers if any are attached
    - Secure the EDF fan so it can't fly away
    - MG996R will spin — keep fingers clear

    1. Mission Planner → Setup → Servo/Relay tab
    2. Find Servo13 (AUX5) → set Output to 1400 → click "Set"
       → EDF fan should start spinning slowly
    3. Set Servo13 to 1600 → fan speeds up
    4. Set Servo13 to 1000 → fan stops
    5. Find Servo14 (AUX6) → set Output to 1650 → click "Set"
       → MG996R should rotate CW (feed direction)
    6. Set Servo14 to 1350 → servo rotates CCW (reverse)
    7. Set Servo14 to 1500 → servo stops

    If nothing happens:
    - Check BRD_PWM_COUNT is saved (must be 4, then reboot)
    - Check wiring (signal wire on correct AUX pin)
    - Check ESC is armed (some ESCs need throttle-low calibration)
    - Check servo is getting 5V power from BEC
```

### Step 4: Verify Pixhawk UART connection to Jetson

```bash
# ════════════════════════════════════════════════════
# WHY: mavros communicates with Pixhawk over serial UART.
# Pixhawk TELEM2 port → Jetson Nano UART (ttyTHS1).
# Make sure the wiring is correct and permission is granted.
# ════════════════════════════════════════════════════

# The TELEM2 port on Pixhawk connects to Jetson UART:
#   Pixhawk TELEM2 TX  → Jetson RX (Pin 10 on J41 header)
#   Pixhawk TELEM2 RX  → Jetson TX (Pin 8 on J41 header)
#   Pixhawk TELEM2 GND → Jetson GND (Pin 6 or 9 or 14)
#
# ⚠️ Voltage levels: Pixhawk TELEM2 is 3.3V, Jetson GPIO is 3.3V → SAFE
# DO NOT connect 5V to Jetson UART pins!

# Check that the UART device exists:
ls -la /dev/ttyTHS1
# Should exist. If "No such file" → wrong UART port.
# On Jetson Nano B01: /dev/ttyTHS1 is the 40-pin header UART.

# Grant serial port access:
sudo usermod -aG dialout $USER
sudo chmod 666 /dev/ttyTHS1

# ⚠️ If using USB connection instead of UART header:
# Connect Pixhawk USB to a Jetson USB-A port.
# The device will appear as /dev/ttyACM0.
# Use fcu_url:=/dev/ttyACM0:115200 in the launch file.

# ════════════════════════════════════════════════════
# DISABLE NVGETTY (Jetson console on ttyTHS1):
# ════════════════════════════════════════════════════
# By default, the Jetson runs a login console on ttyTHS1.
# This conflicts with mavros. Disable it:
sudo systemctl stop nvgetty
sudo systemctl disable nvgetty
# After reboot, ttyTHS1 will be free for mavros.
```

### Step 5: Test mavros connection to Pixhawk

```bash
# ════════════════════════════════════════════════════
# Quick mavros connection test (no camera or sprayer needed):
# ════════════════════════════════════════════════════

# TERMINAL 1:
roscore

# TERMINAL 2 (mavros):
roslaunch mavros apm.launch fcu_url:=/dev/ttyTHS1:921600
# (or fcu_url:=/dev/ttyACM0:115200 if using USB)

# Expected output (after a few seconds):
# "FCU: ArduPilot"
# "MAVROS started"
# "Got HEARTBEAT from ..."
# If you see "FCU: ArduPilot" → ✅ Pixhawk is talking to mavros!

# TERMINAL 3 (check topics):
rostopic list | grep mavros
# Should show many topics including:
# /mavros/state
# /mavros/battery
# /mavros/imu/data

# Check Pixhawk state:
rostopic echo /mavros/state -n 1
# Expected: connected: True, armed: False, mode: "STABILIZE" (or similar)

# ════════════════════════════════════════════════════
# Test DO_SET_SERVO from command line:
# ════════════════════════════════════════════════════
# WARNING: This will move the actual servo! Secure everything first.

# Fan ON (AUX5 / SERVO13 → PWM 1400):
rosservice call /mavros/cmd/command "{broadcast: false, command: 183, confirmation: 0, param1: 13, param2: 1400, param3: 0, param4: 0, param5: 0, param6: 0, param7: 0}"
# Expected: success: True

# Fan OFF:
rosservice call /mavros/cmd/command "{broadcast: false, command: 183, confirmation: 0, param1: 13, param2: 1000, param3: 0, param4: 0, param5: 0, param6: 0, param7: 0}"

# Feeder ON (AUX6 / SERVO14 → PWM 1650):
rosservice call /mavros/cmd/command "{broadcast: false, command: 183, confirmation: 0, param1: 14, param2: 1650, param3: 0, param4: 0, param5: 0, param6: 0, param7: 0}"

# Feeder STOP:
rosservice call /mavros/cmd/command "{broadcast: false, command: 183, confirmation: 0, param1: 14, param2: 1500, param3: 0, param4: 0, param5: 0, param6: 0, param7: 0}"

# If success: True → ✅ Pixhawk is accepting servo commands from mavros!
# If success: False → Check:
#   - BRD_PWM_COUNT=4 (was Pixhawk rebooted after setting this?)
#   - SERVO13_FUNCTION=0 and SERVO14_FUNCTION=0
#   - Pixhawk is not in a mode that overrides AUX outputs
```

### Step 6: Place the spray_logic_node.py file

Same process as Day 2's detector_node.py:

```bash
# ════════════════════════════════════════════════════
# Copy from repo (or download, or paste via VS Code):
# ════════════════════════════════════════════════════
# The full code is at: ros_nodes/scripts/spray_logic_node.py in this repo.
# ⚠️ This file has been COMPLETELY REWRITTEN for Pixhawk servo control.
# It uses mavros DO_SET_SERVO instead of ESP32 serial commands.
# Place it at: ~/catkin_ws/src/sprayer_control/scripts/spray_logic_node.py

# Fix line endings + change to Python 2 + make executable:
dos2unix ~/catkin_ws/src/sprayer_control/scripts/spray_logic_node.py
sed -i 's|#!/usr/bin/env python3|#!/usr/bin/env python|' \
    ~/catkin_ws/src/sprayer_control/scripts/spray_logic_node.py
chmod +x ~/catkin_ws/src/sprayer_control/scripts/spray_logic_node.py

# Rebuild:
cd ~/catkin_ws && catkin_make && source devel/setup.bash

# ════════════════════════════════════════════════════
# Test with a fake detection message (camera not needed):
# ════════════════════════════════════════════════════

# TERMINAL 1:
roscore

# TERMINAL 2 (mavros — Pixhawk must be connected):
roslaunch mavros apm.launch fcu_url:=/dev/ttyTHS1:921600

# TERMINAL 3 (spray logic):
rosrun sprayer_control spray_logic_node.py

# Expected startup output:
# "Waiting for mavros service: /mavros/cmd/command ..."
# "mavros command service connected"
# "Spray Logic Node Started (Pixhawk Servo Mode)"
# "Fan channel:    SERVO13 (AUX5)"
# "Feeder channel: SERVO14 (AUX6)"

# TERMINAL 4 (publish a fake detection to trigger spray):
# This simulates a "target detected, centered, close enough" message:
rostopic pub /detection/result sprayer_control/Detection \
    "header: {seq: 0, stamp: {secs: 0, nsecs: 0}, frame_id: ''}
detected: true
cx: 320
cy: 240
area: 8000
confidence: 0.9
position_hint: 'CENTER'" \
    -r 10
# -r 10 means publish at 10 Hz

# TERMINAL 5 (monitor):
rostopic echo /spray/status

# Expected: After ~1 second of continuous "CENTER" detections,
# spray_logic transitions:
#   IDLE → DETECTED → ALIGNED → SPRAY_FAN_SPOOL → SPRAY_ACTIVE → SPRAY_SHUTDOWN → COOLDOWN → IDLE
# You should see the EDF fan spin up, then the servo turn, then both stop!
# Status topic should show: MAVROS=OK

# Press Ctrl+C in Terminal 4 to stop fake detections.
```

### Day 3 — Completion Checklist

```bash
echo "════════════════════════════════════════"
echo "DAY 3 CHECKLIST"
echo "════════════════════════════════════════"

echo -n "[ ] mavros installed: "
rospack find mavros 2>/dev/null && echo " ✅" || echo "❌"

echo -n "[ ] mavros connects to Pixhawk: "
# (manual check — did 'Got HEARTBEAT' appear in mavros terminal?)
echo "(check mavros terminal)"

echo -n "[ ] BRD_PWM_COUNT=4 set: "
echo "(check via Mission Planner)"

echo -n "[ ] SERVO13 fan test via rosservice: "
echo "(did fan spin?)"

echo -n "[ ] SERVO14 servo test via rosservice: "
echo "(did servo rotate?)"

echo -n "[ ] spray_logic_node.py placed and executable: "
ls -la ~/catkin_ws/src/sprayer_control/scripts/spray_logic_node.py 2>/dev/null | grep -q 'x' && echo "✅" || echo "❌"

echo -n "[ ] Fake detection triggers spray sequence: "
echo "(did state machine cycle through SPRAY_FAN_SPOOL → SPRAY_ACTIVE → SPRAY_SHUTDOWN?)"

echo "════════════════════════════════════════"
```

---

## 📅 DAY 4 (Feb 13): FULL INTEGRATION TEST ("Table Test")

**Goal:** Everything runs together. Move yellow ball → sprayer fires automatically.

### Setup

```
    TABLE TEST RIG (No drone, no props, no danger):
    ═══════════════════════════════════════════════════

         Yellow Ball (on a stick or in your hand)
              🟡
              │     0.5 – 1.5 meters away
              │
         ┌────┼─────────────────────────────┐
         │    ▼                              │
         │   [Jete Webcam] → USB → [Jetson] │
         │                                   │
         │   [Jetson] ← UART → [Pixhawk]    │
         │                                   │
         │   [Pixhawk AUX5] → [EDF Fan ESC] │
         │   [Pixhawk AUX6] → [MG996R Servo]│
         │                                   │
         │   Power: 4S LiPo → BEC → Jetson  │
         │          4S LiPo → ESC → Fan     │
         │          5V BEC → Servo rail      │
         └───────────────────────────────────┘
         All powered. On a table. SAFE.
         ⚠️ Secure EDF fan (it blows hard!)
         ⚠️ Keep fingers away from MG996R
```

### Run the full system

```bash
# ════════════════════════════════════════════════════
# Kill any leftover ROS processes:
# ════════════════════════════════════════════════════
killall roscore rosmaster roslaunch 2>/dev/null
sleep 2

# ════════════════════════════════════════════════════
# Launch EVERYTHING:
# ════════════════════════════════════════════════════
# mavros + camera + detector + spray_logic all in one:
roslaunch sprayer_control demo.launch

# If Pixhawk is on USB instead of UART:
# roslaunch sprayer_control demo.launch fcu_url:=/dev/ttyACM0:115200

# This starts:
# 1. mavros (MAVLink bridge to Pixhawk)
# 2. usb_cam (camera)
# 3. detector_node (yellow ball detection)
# 4. spray_logic_node (state machine + Pixhawk servo control)

# ════════════════════════════════════════════════════
# Open monitoring terminals (new VS Code terminals):
# ════════════════════════════════════════════════════

# TERMINAL 2: Watch detections
rostopic echo /detection/result

# TERMINAL 3: Watch spray status
rostopic echo /spray/status

# TERMINAL 4: Check FPS
rostopic hz /detection/result
```

### Validation Tests

Run each test and record pass/fail:

```
    ╔═════╦═══════════════════════════════╦════════════════════════════╦═══════╗
    ║ #   ║ ACTION                        ║ EXPECTED RESULT            ║ PASS? ║
    ╠═════╬═══════════════════════════════╬════════════════════════════╬═══════╣
    ║ T1  ║ Ball at 1m, centered          ║ detected=True,             ║       ║
    ║     ║                               ║ position_hint=CENTER,      ║       ║
    ║     ║                               ║ Fan spools → servo feeds   ║       ║
    ║     ║                               ║ → spray after ~1.4s        ║       ║
    ╠═════╬═══════════════════════════════╬════════════════════════════╬═══════╣
    ║ T2  ║ Ball at 1m, LEFT of frame     ║ position_hint=LEFT,        ║       ║
    ║     ║                               ║ spray does NOT trigger     ║       ║
    ╠═════╬═══════════════════════════════╬════════════════════════════╬═══════╣
    ║ T3  ║ Ball at 1m, RIGHT of frame    ║ position_hint=RIGHT,       ║       ║
    ║     ║                               ║ spray does NOT trigger     ║       ║
    ╠═════╬═══════════════════════════════╬════════════════════════════╬═══════╣
    ║ T4  ║ Ball too far (small in frame) ║ position_hint=TOO_FAR,     ║       ║
    ║     ║                               ║ spray does NOT trigger     ║       ║
    ╠═════╬═══════════════════════════════╬════════════════════════════╬═══════╣
    ║ T5  ║ No ball visible               ║ detected=False,            ║       ║
    ║     ║                               ║ spray does NOT trigger     ║       ║
    ╠═════╬═══════════════════════════════╬════════════════════════════╬═══════╣
    ║ T6  ║ Ball centered → remove it     ║ Spray stops, fan clears    ║       ║
    ║     ║ during spray                  ║ tube, then COOLDOWN        ║       ║
    ╠═════╬═══════════════════════════════╬════════════════════════════╬═══════╣
    ║ T7  ║ Run for 10 minutes            ║ No crashes, no memory      ║       ║
    ║     ║ continuously                  ║ leaks, FPS stable ≥20     ║       ║
    ╠═════╬═══════════════════════════════╬════════════════════════════╬═══════╣
    ║ T8  ║ Kill mavros during spray      ║ spray_logic logs warning,  ║       ║
    ║     ║                               ║ detection continues,       ║       ║
    ║     ║                               ║ actuators stop (TRIM)      ║       ║
    ╚═════╩═══════════════════════════════╩════════════════════════════╩═══════╝
```

```bash
# ════════════════════════════════════════════════════
# Monitor memory usage during the 10-minute test:
# ════════════════════════════════════════════════════
# In a separate terminal:
watch -n 5 free -h
# If swap usage climbs steadily → possible memory leak. Note the rate.
# If swap usage stabilizes → normal. The system is stable.
```

---

## 📅 DAY 5 (Feb 14): ON-DRONE MOUNTING & BATTERY TEST

**Goal:** Mount everything on the F450 frame. Verify nothing breaks when running on battery power.

### Mounting Checklist

```bash
# ════════════════════════════════════════════════════
# BEFORE MOUNTING — Print this checklist:
# ════════════════════════════════════════════════════
echo "
MOUNTING CHECKLIST
═══════════════════════════════════════════════════

COMPONENTS TO MOUNT:
[ ] Jetson Nano (with carrier board)
[ ] Jete USB webcam
[ ] Pixhawk 2.4.8 (already mounted for flight)
[ ] EDF Fan + ESC (20A or 30A)
[ ] MG996R Continuous Rotation Servo + Auger tube
[ ] 5V 3A BEC for servo power (MG996R draws up to 2.5A!)
[ ] BEC/voltage regulator for Jetson (5V 4A)
[ ] Battery (4S LiPo)
[ ] Venturi sprayer tube assembly

CABLES TO SECURE:
[ ] USB: Webcam → Jetson (short cable, zip-tied)
[ ] UART: Pixhawk TELEM2 → Jetson ttyTHS1 (3-wire: TX, RX, GND)
[ ] Signal: Pixhawk AUX5 → EDF Fan ESC (3-pin servo cable)
[ ] Signal: Pixhawk AUX6 → MG996R Servo (3-pin servo cable)
[ ] Power: Battery → BEC → Jetson barrel jack (5V 4A)
[ ] Power: Battery → ESCs → Motors (existing)
[ ] Power: Battery → ESC → EDF Fan motor
[ ] Power: Battery → 5V BEC → Servo rail → MG996R

STRAIN RELIEF:
[ ] Loop each cable and zip-tie at BOTH ends
[ ] Webcam cable has slack (won't pull if frame flexes)
[ ] UART wires secured (vibration can disconnect Dupont pins)
[ ] Servo cables routed away from propeller arcs
[ ] No cable can touch a propeller arc

VIBRATION DAMPENING:
[ ] Jetson mounted on anti-vibration foam/gel pad
[ ] Camera mounted firmly (no wobble — zip ties tight)
[ ] All connectors pressed firmly in (won't vibrate loose)
[ ] Dupont UART connectors hot-glued or secured with tape

GROUND CONNECTIONS:
[ ] Pixhawk GND connected to Jetson GND (via UART cable)
[ ] Pixhawk GND connected to servo BEC GND (common ground)
[ ] ESC GND connected to Pixhawk AUX5 GND pin
[ ] All GNDs share a common reference (star ground at battery)

WEIGHT CHECK:
[ ] Weigh the complete drone with everything mounted
[ ] Total should be < 1500g for F450 with 2212 motors
"
```

### Battery Power Test

```bash
# ════════════════════════════════════════════════════
# STEP 1: Power everything from battery (NO laptop USB)
# ════════════════════════════════════════════════════
# Disconnect the Jetson from any laptop USB power.
# Connect the BEC output (5V 4A) to the Jetson barrel jack.
# Power on the battery.
# Wait 60 seconds for Jetson to boot.

# ════════════════════════════════════════════════════
# STEP 2: SSH into the Jetson (over WiFi or MicroUSB bridge)
# ════════════════════════════════════════════════════
ssh jetson@192.168.55.1
# (or whatever IP works for your setup)

# ════════════════════════════════════════════════════
# STEP 3: Launch the full system
# ════════════════════════════════════════════════════
roslaunch sprayer_control demo.launch

# ════════════════════════════════════════════════════
# STEP 4: Re-run the validation tests T1-T7 from Day 4
# ════════════════════════════════════════════════════
# PASS CRITERIA: Same results as on the table.
# Watch specifically for:
# - Brownouts (Jetson reboots → BEC can't supply enough current)
# - mavros disconnects (Pixhawk UART interrupted by vibration)
# - EDF fan ESC not arming (needs throttle-low at startup)
# - FPS drops (thermal throttling under the airframe)

# ════════════════════════════════════════════════════
# STEP 5: Run for 15 minutes on battery
# ════════════════════════════════════════════════════
# Monitor:
watch -n 10 "free -h; echo '---'; df -h /; echo '---'; uptime"

# After 15 minutes:
# - Check if FPS is still 25-30 Hz
# - Check if spray still works (re-test T1)
# - Check battery voltage (via Pixhawk telemetry or multimeter)
```

---

# ═══════════════════════════════════════════════════════════
# APPENDIX A: COMMON ERRORS & FIXES
# ═══════════════════════════════════════════════════════════

### Error: "no valid OpenPGP data found" (when adding ROS GPG key)

```bash
# CAUSE: Network issue, GitHub raw content blocked, or deprecated apt-key method.
# FIX 1: Use the alternative keyserver method:
sudo apt-key adv --keyserver 'hkp://keyserver.ubuntu.com:80' --recv-key C1CF6E31E6BADE8868B172B4F42ED6FBAB17C654

# Then:
sudo apt-get update

# FIX 2: Download the key file manually:
curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.asc -o /tmp/ros.asc
file /tmp/ros.asc  # Should show: "PGP public key block"
sudo apt-key add /tmp/ros.asc

# FIX 3: Check if your network blocks raw.githubusercontent.com:
ping raw.githubusercontent.com
# If "Name or service not known" → DNS/firewall issue. Try on different network.
```

### Error: "Unable to locate package ros-melodic-ros-base" (or ros-noetic)

```bash
# ════════════════════════════════════════════════════════════════════
# COMPREHENSIVE DEBUGGING FOR "UNABLE TO LOCATE PACKAGE" ERROR
# ════════════════════════════════════════════════════════════════════

# ═══ STEP 1: Verify your exact Ubuntu version ═══
lsb_release -a
# Look for: "Distributor ID: Ubuntu" and "Release: 18.04"
# If it says 18.04 → Melodic. If 20.04 → Noetic. If 16.04 → Kinetic (too old).
# Jetson Nano with JetPack 4.6.x should be 18.04.

# ═══ STEP 2: Check repository file contents ═══
cat /etc/apt/sources.list.d/ros-latest.list
# MUST show EXACTLY this line for Ubuntu 18.04:
# deb http://packages.ros.org/ros/ubuntu bionic main

# If it shows $(lsb_release -sc) or another placeholder instead of "bionic":
sudo rm /etc/apt/sources.list.d/ros-latest.list
echo "deb http://packages.ros.org/ros/ubuntu bionic main" | sudo tee /etc/apt/sources.list.d/ros-latest.list

# ═══ STEP 3: Verify GPG key is installed ═══
sudo apt-key list | grep -A 1 "ROS"
# Should show something like:
# pub   rsa4096 2019-05-30 [SC] [expires: 2025-05-28]
#       C1CF 6E31 E6BA DE88 68B1  72B4 F42E D6FB AB17 C654
# uid           [ unknown] Open Robotics <info@osrfoundation.org>

# If nothing appears, add the key again:
sudo apt-key adv --keyserver 'hkp://keyserver.ubuntu.com:80' --recv-key C1CF6E31E6BADE8868B172B4F42ED6FBAB17C654

# ═══ STEP 4: Clear apt cache and force update ═══
sudo rm -rf /var/lib/apt/lists/*
sudo apt-get clean
sudo apt-get update

# Watch the update output carefully! Look for:
# "Hit:1 http://packages.ros.org/ros/ubuntu bionic InRelease"
# OR
# "Get:1 http://packages.ros.org/ros/ubuntu bionic InRelease"
#
# ❌ BAD SIGNS:
# "Ign:1 http://packages.ros.org..." → Repository is being IGNORED
# "Err:1 http://packages.ros.org..." → Repository has an ERROR

# ═══ STEP 5: Test if the repository is accessible ═══
# Can you reach the ROS server from your Jetson?
ping -c 3 packages.ros.org
# If "Name or service not known" → DNS problem
# If "Network is unreachable" → Internet connection problem

# Try downloading the package index manually:
wget http://packages.ros.org/ros/ubuntu/dists/bionic/main/binary-arm64/Packages.gz
# If this fails → you can't reach the ROS servers (network/firewall issue)
# If it succeeds → the server is fine, problem is with apt configuration

# Clean up:
rm -f Packages.gz

# ═══ STEP 6: Check architecture ═══
dpkg --print-architecture
# Should show: arm64
# ROS Melodic supports: amd64, arm64, armhf
# Jetson Nano is arm64 (aarch64) → SUPPORTED

# ═══ STEP 7: Search for ANY ROS packages ═══
apt-cache search ros-melodic | head -20
# If this returns NOTHING → apt doesn't see the ROS repository at all.

# If empty, try searching the repository metadata directly:
apt-cache policy | grep -A 2 ros
# Should show something like:
#  500 http://packages.ros.org/ros/ubuntu bionic/main arm64 Packages

# ═══ STEP 8: Try updating with verbose output ═══
sudo apt-get update -o Debug::Acquire::http=true 2>&1 | grep ros
# This shows EXACTLY what apt is doing with the ROS repository.
# Look for errors or "Ignored" messages.

# ═══ STEP 9: Last resort - Manual verification ═══
# Check if the package actually exists on the ROS servers:
curl -I http://packages.ros.org/ros/ubuntu/dists/bionic/main/binary-arm64/Packages.gz
# Should return: HTTP/1.1 200 OK
# If 404 → the arm64 repository doesn't exist (highly unlikely)

# ═══ STEP 10: Nuclear option - Start fresh ═══
# If all above fails, completely remove and re-add everything:
sudo apt-key del C1CF6E31E6BADE8868B172B4F42ED6FBAB17C654
sudo rm /etc/apt/sources.list.d/ros-latest.list
sudo rm -rf /var/lib/apt/lists/*
sudo apt-get clean

# Re-add from scratch:
sudo sh -c 'echo "deb http://packages.ros.org/ros/ubuntu bionic main" > /etc/apt/sources.list.d/ros-latest.list'
sudo apt-key adv --keyserver 'hkp://keyserver.ubuntu.com:80' --recv-key C1CF6E31E6BADE8868B172B4F42ED6FBAB17C654
sudo apt-get update

# Now try ONE MORE TIME:
sudo apt-get install -y ros-melodic-ros-base

# ════════════════════════════════════════════════════════════════════
# IF STILL FAILING: Alternative Installation Methods
# ════════════════════════════════════════════════════════════════════

# WORKAROUND A: Use Ubuntu 18.04 mirrors instead of packages.ros.org
# Some networks block packages.ros.org. Try the mirror:
sudo sh -c 'echo "deb http://packages.ros.org/ros/ubuntu bionic main" > /etc/apt/sources.list.d/ros-latest.list'
# (Same URL, but we'll verify it's resolving correctly)

# WORKAROUND B: Use Docker with ROS pre-installed
# If apt is fundamentally broken, use Docker:
sudo docker pull arm64v8/ros:melodic-ros-base-bionic
# Then run ROS inside the container. (Advanced - adds complexity)

# WORKAROUND C: Build ROS from source (LAST RESORT - takes 3-4 hours)
# Only if you absolutely cannot get apt to work.
# See: http://wiki.ros.org/melodic/Installation/Source

# ════════════════════════════════════════════════════════════════════
# REPORT YOUR FINDINGS:
# ════════════════════════════════════════════════════════════════════
# After running the steps above, provide these outputs for further help:
echo "════════════════════════════════════════"
echo "DIAGNOSTIC REPORT:"
echo "════════════════════════════════════════"
echo ""
echo "1. Ubuntu version:"
lsb_release -a
echo ""
echo "2. Repository file:"
cat /etc/apt/sources.list.d/ros-latest.list
echo ""
echo "3. GPG keys (ROS related):"
sudo apt-key list | grep -A 2 -B 2 ROS
echo ""
echo "4. Architecture:"
dpkg --print-architecture
echo ""
echo "5. Can reach packages.ros.org:"
ping -c 2 packages.ros.org 2>&1 | head -5
echo ""
echo "6. ROS packages found by apt:"
apt-cache search ros-melodic | wc -l
echo "(Should be > 500 packages. If 0, repository is not accessible.)"
echo ""
echo "════════════════════════════════════════"
```

### Error: "Cannot connect to X server" (when running hsv_tuner or rqt_image_view)

```bash
# CAUSE: You're running a GUI program on a headless Jetson without X forwarding.
# FIX: SSH with X forwarding:
# From laptop: ssh -X jetson@192.168.55.1
# Then run the GUI program.

# On Windows, you need an X server. Install one:
# Option 1: VcXsrv (free): https://sourceforge.net/projects/vcxsrv/
#   Start VcXsrv with default settings before SSH.
#   In PowerShell: $env:DISPLAY="localhost:0"
# Option 2: Use MobaXterm instead of PowerShell for SSH (has built-in X server)
```

### Error: "Permission denied: '/dev/ttyUSB0'" or "/dev/ttyTHS1"

```bash
# CAUSE: Your user is not in the dialout group.
# FIX:
sudo usermod -aG dialout $USER
# Then LOG OUT and LOG BACK IN (close SSH, reconnect).
# Verify: groups | grep dialout
# For Jetson UART (ttyTHS1): also run: sudo chmod 666 /dev/ttyTHS1
```

### Error: "/usr/bin/env: 'python3\r': No such file or directory" OR "/usr/bin/env: 'python\r': ..."

```bash
# CAUSE: Windows line endings (CRLF) in the Python script.
# This happens when you create/edit files on Windows then copy to Linux.
# The \r (carriage return) character is invisible but breaks the shebang.

# ⚠️ CRITICAL ORDER: Fix line endings FIRST, THEN change python3→python
# If you do it backwards, you'll change "python3\r" to "python\r" (error persists!)

# ════════════════════════════════════════════════════
# FIX: Convert line endings FIRST, then change shebang
# ════════════════════════════════════════════════════

# Method 1: Use dos2unix (RECOMMENDED - cleaner)
sudo apt-get install -y dos2unix
dos2unix ~/catkin_ws/src/sprayer_control/scripts/*.py

# Method 2: Use sed (if dos2unix unavailable)
sed -i 's/\r$//' ~/catkin_ws/src/sprayer_control/scripts/*.py

# NOW change python3 to python (for ROS Melodic):
sed -i 's|#!/usr/bin/env python3|#!/usr/bin/env python|' \
    ~/catkin_ws/src/sprayer_control/scripts/*.py

# Make executable:
chmod +x ~/catkin_ws/src/sprayer_control/scripts/*.py

# ════════════════════════════════════════════════════
# VERIFY the fix (shows raw bytes):
# ════════════════════════════════════════════════════
head -1 ~/catkin_ws/src/sprayer_control/scripts/detector_node.py | od -c

# GOOD OUTPUT (ends with \n only):
# 0000000   #   !   /   u   s   r   /   b   i   n   /   e   n   v
# 0000020       p   y   t   h   o   n  \n
#
# BAD OUTPUT (ends with \r \n):
# 0000000   #   !   /   u   s   r   /   b   i   n   /   e   n   v
# 0000020       p   y   t   h   o   n  \r  \n   ← STILL HAS \r!

# Simple visual check (should look normal):
head -1 ~/catkin_ws/src/sprayer_control/scripts/detector_node.py
# Should show: #!/usr/bin/env python

# ════════════════════════════════════════════════════
# PREVENTION: Use VS Code Remote-SSH
# ════════════════════════════════════════════════════
# When creating/editing files in VS Code Remote-SSH (connected to Linux):
# - VS Code automatically uses LF (Unix line endings) ✅
# - The issue only happens if you:
#   a) Create files on Windows locally then SCP them, OR
#   b) Edit files with a Windows editor (Notepad++, etc.) then copy
```

### Error: "SyntaxError: Non-ASCII character '\xe2' in file ... but no encoding declared"

```bash
# FULL ERROR MESSAGE:
# SyntaxError: Non-ASCII character '\xe2' in file detector_node.py on line 4,
# but no encoding declared; see http://python.org/dev/peps/pep-0263/ for details

# ════════════════════════════════════════════════════
# CAUSE: Python 2 cannot handle Unicode characters without encoding declaration
# ════════════════════════════════════════════════════
# Common non-ASCII characters from copy-paste:
# - Smart quotes: " " (Unicode U+201C, U+201D) instead of regular "
# - Em-dashes: — (Unicode U+2014, hex \xe2\x80\x94) instead of regular -
# - Curly apostrophes: ' (Unicode U+2019) instead of regular '
# - Ellipsis: … (Unicode U+2026) instead of regular ...

# Python 3 handles these by default.
# Python 2 requires explicit encoding declaration at top of file.

# ════════════════════════════════════════════════════
# DIAGNOSTIC: Find the offending characters
# ════════════════════════════════════════════════════

# Show the exact line (error says "line 4"):
sed -n '4p' ~/catkin_ws/src/sprayer_control/scripts/detector_node.py

# Show raw bytes to see hidden Unicode:
sed -n '4p' ~/catkin_ws/src/sprayer_control/scripts/detector_node.py | od -c

# Look for these patterns in output:
# \342 \200 \224 = em-dash (—)
# \342 \200 \234 = left double quote (")
# \342 \200 \235 = right double quote (")
# \342 \200 \231 = right single quote (')

# Find ALL non-ASCII characters in the file:
grep --color='auto' -P -n "[\x80-\xFF]" \
    ~/catkin_ws/src/sprayer_control/scripts/detector_node.py

# ════════════════════════════════════════════════════
# FIX 1: Add encoding declaration (QUICK FIX - keeps Unicode)
# ════════════════════════════════════════════════════

cd ~/catkin_ws/src/sprayer_control/scripts/

# Add encoding declaration on line 2 (after shebang):
sed -i '2i# -*- coding: utf-8 -*-' *.py

# Verify it was added:
head -3 detector_node.py
# Should show:
# #!/usr/bin/env python
# # -*- coding: utf-8 -*-
# """

# Now try running:
rosrun sprayer_control detector_node.py

# ════════════════════════════════════════════════════
# FIX 2: Replace Unicode with ASCII (BETTER - cleaner)
# ════════════════════════════════════════════════════

# Replace em-dashes (—) with hyphens (-):
sed -i 's/—/-/g' ~/catkin_ws/src/sprayer_control/scripts/*.py

# Replace smart quotes with regular quotes:
sed -i "s/"/\"/g" ~/catkin_ws/src/sprayer_control/scripts/*.py
sed -i "s/"/\"/g" ~/catkin_ws/src/sprayer_control/scripts/*.py
sed -i "s/'/'/g" ~/catkin_ws/src/sprayer_control/scripts/*.py
sed -i "s/'/'/g" ~/catkin_ws/src/sprayer_control/scripts/*.py

# Replace ellipsis (…) with three dots (...):
sed -i 's/…/.../g' ~/catkin_ws/src/sprayer_control/scripts/*.py

# Verify all non-ASCII characters are gone:
grep --color='auto' -P -n "[\x80-\xFF]" *.py
# Should show: (no output = all clean)

# Now try running:
rosrun sprayer_control detector_node.py

# ════════════════════════════════════════════════════
# WHY THIS HAPPENS:
# ════════════════════════════════════════════════════
# - You copied code from a document/website with fancy formatting
# - Microsoft Word / Google Docs / Rich Text editors auto-replace:
#   - Regular quotes (") → Smart quotes ("")
#   - Hyphens (-) → Em-dashes (—)
#   - Three dots (...) → Ellipsis (…)
# - Python 2 source files MUST be pure ASCII unless you declare encoding

# ════════════════════════════════════════════════════
# PREVENTION:
# ════════════════════════════════════════════════════
# 1. Always use plain text editors (VS Code, nano, vim)
# 2. When copying code, use "Paste as Plain Text" (Ctrl+Shift+V)
# 3. If using VS Code Remote-SSH → file is created directly on Linux ✅
# 4. If you MUST paste from Word/Docs → run the sed replacements above
```

### Error: "No module named 'rospkg'" or "No module named 'catkin_pkg'"

```bash
# CAUSE: ROS Python 3 packages not installed (common on Melodic with Python 3).
# ROS Melodic defaults to Python 2, but our scripts use Python 3.

# FIX: Install Python 3 versions of ROS packages

# For ROS Melodic (Ubuntu 18.04):
sudo apt-get install -y \
    python3-rospkg \
    python3-catkin-pkg \
    python3-rosdep \
    python3-rosinstall \
    python3-rosinstall-generator

# For ROS Noetic (Ubuntu 20.04):
# These should already be installed, but if not:
sudo apt-get install -y \
    python3-rospkg \
    python3-catkin-pkg

# Verify:
python3 -c "import rospkg; print(f'rospkg version: {rospkg.__version__}')"
python3 -c "import catkin_pkg; print('catkin_pkg installed')"

# If still failing, check which Python is being used:
which python3
python3 --version

# Make sure you're sourcing the workspace:
source /opt/ros/melodic/setup.bash
source ~/catkin_ws/devel/setup.bash
```

### Error: "No module named 'rospy'"

```bash
# CAUSE: ROS environment not sourced, or Python can't find ROS packages.
# This is the most fundamental ROS import error.

# ════════════════════════════════════════════════════
# DIAGNOSTIC: Check if ROS is installed and sourced
# ════════════════════════════════════════════════════

# Step 1: Verify ROS is installed:
ls /opt/ros/
# Should show: melodic (or noetic)
# If "ls: cannot access '/opt/ros/': No such file or directory" → ROS NOT INSTALLED!

# Check if the setup.bash file exists:
ls -la /opt/ros/melodic/setup.bash
# If "No such file or directory" → ROS Melodic is NOT installed!

# Step 2: Check if ROS environment is sourced in current terminal:
echo $ROS_DISTRO
# Should show: melodic (or noetic)
# If EMPTY → ROS is NOT sourced in this terminal!

echo $PYTHONPATH
# Should show something like: /opt/ros/melodic/lib/python2.7/dist-packages
# If EMPTY → ROS Python path not set!

# ════════════════════════════════════════════════════
# FIX 0: If /opt/ros/melodic/setup.bash doesn't exist
# ════════════════════════════════════════════════════
# This means ROS is NOT installed, even if apt says it is.

# Check what's actually installed:
dpkg -l | grep ros-melodic

# If you see NOTHING or very few packages → apt install failed silently!
# Common cause: Repository not accessible during install.

# SOLUTION: Re-install ROS Melodic from scratch:

# Remove any partial installation:
sudo apt-get remove --purge ros-melodic-* -y
sudo apt-get autoremove -y

# Clear apt cache:
sudo rm -rf /var/lib/apt/lists/*
sudo apt-get clean
sudo apt-get update

# Re-install (this time WATCH for errors):
sudo apt-get install -y ros-melodic-ros-base

# WATCH THE OUTPUT! Look for:
# ✅ GOOD: "Setting up ros-melodic-ros-base..."
# ❌ BAD:  "E: Unable to locate package" → repository not configured
# ❌ BAD:  "E: Package ... has no installation candidate" → wrong Ubuntu version

# After successful install:
ls -la /opt/ros/melodic/setup.bash
# Should now exist!

# If STILL doesn't exist after install:
# Check: cat /etc/apt/sources.list.d/ros-latest.list
# Must show: deb http://packages.ros.org/ros/ubuntu bionic main
# Check: lsb_release -a
# Must show: Ubuntu 18.04 (bionic)

# ════════════════════════════════════════════════════
# FIX 1: Source ROS in the current terminal
# ════════════════════════════════════════════════════
source /opt/ros/melodic/setup.bash
source ~/catkin_ws/devel/setup.bash

# Verify:
echo $ROS_DISTRO
# Should now show: melodic

# Test rospy import:
python3 -c "import sys; print(sys.path)" | grep ros
# Should show ROS paths

# ════════════════════════════════════════════════════
# FIX 2: If still "No module named rospy" with Python 3
# ════════════════════════════════════════════════════
# Problem: ROS Melodic's Python 3 bindings may not be complete.
# You need to rebuild cv_bridge and other packages for Python 3.

# Option A: Install pre-built Python 3 packages (if available):
sudo apt-get update
sudo apt-get install -y \
    python3-catkin-pkg-modules \
    python3-rospkg-modules \
    python3-empy

# Option B: Check if rospy works with Python 2:
python2 -c "import rospy; print('Python 2 works')"
# If this works but Python 3 doesn't → ROS Melodic Python 3 incomplete

# Option C: Create a symbolic link workaround:
# First, find where rospy is installed:
find /opt/ros/melodic -name "rospy" -type d
# Usually: /opt/ros/melodic/lib/python2.7/dist-packages/rospy

# Check Python 3 dist-packages location:
python3 -c "import sys; print([p for p in sys.path if 'dist-packages' in p])"

# If Python 3 path exists, create symlink (CAREFUL - advanced):
# sudo ln -s /opt/ros/melodic/lib/python2.7/dist-packages/rospy \
#           /usr/local/lib/python3.6/dist-packages/rospy
# ⚠️ This is a HACK and may cause issues!

# ════════════════════════════════════════════════════
# FIX 3: Switch scripts to Python 2 (NOT RECOMMENDED)
# ════════════════════════════════════════════════════
# If Python 3 doesn't work with ROS Melodic, use Python 2:
# Edit the shebang in all scripts from:
#   #!/usr/bin/env python3
# To:
#   #!/usr/bin/env python
# 
# sed -i 's|#!/usr/bin/env python3|#!/usr/bin/env python|' \
#     ~/catkin_ws/src/sprayer_control/scripts/*.py
#
# Then install Python 2 dependencies:
# sudo apt-get install python-opencv python-serial
#
# ⚠️ Python 2 is DEPRECATED (EOL 2020). Only use as last resort.

# ════════════════════════════════════════════════════
# FIX 4: Use ROS Noetic instead (RECOMMENDED if possible)
# ════════════════════════════════════════════════════
# ROS Noetic natively supports Python 3.
# Requires Ubuntu 20.04.
# Check: lsb_release -a
# If Ubuntu 18.04 → you're stuck with Melodic or need to upgrade OS.

# ════════════════════════════════════════════════════
# VERIFICATION:
# ════════════════════════════════════════════════════
# After fixing, test ALL imports:
python3 << 'PYTEST'
import sys
print(f"Python: {sys.version}")
print(f"Python path: {sys.path}")

try:
    import rospy
    print("✅ rospy")
except ImportError as e:
    print(f"❌ rospy: {e}")

try:
    import rospkg
    print("✅ rospkg")
except ImportError as e:
    print(f"❌ rospkg: {e}")

try:
    import cv2
    print(f"✅ cv2 (OpenCV {cv2.__version__})")
except ImportError as e:
    print(f"❌ cv2: {e}")

try:
    from sensor_msgs.msg import Image
    print("✅ sensor_msgs")
except ImportError as e:
    print(f"❌ sensor_msgs: {e}")

try:
    from cv_bridge import CvBridge
    print("✅ cv_bridge")
except ImportError as e:
    print(f"❌ cv_bridge: {e}")
PYTEST
```

### Error: "No module named 'sprayer_control.msg'"

```bash
# CAUSE: You forgot to source the workspace, or catkin_make failed.
# FIX:
cd ~/catkin_ws && catkin_make && source devel/setup.bash
# Check: rosmsg show sprayer_control/Detection
```

### Error: "Unable to communicate with master!" (any ROS command)

```bash
# CAUSE: roscore is not running.
# FIX: Start roscore first:
roscore &
# Or use roslaunch (it starts roscore automatically).
```

### Error: "cv_bridge" import fails

```bash
# CAUSE: cv_bridge not installed, or Python version mismatch.
# FIX:
sudo apt-get install -y ros-noetic-cv-bridge
# (Replace "noetic" with "melodic" if on Ubuntu 18.04)

# If on Melodic with Python 3:
sudo apt-get install -y python3-catkin-pkg-modules python3-rospkg-modules
# And rebuild: cd ~/catkin_ws && catkin_make -DPYTHON_EXECUTABLE=/usr/bin/python3
```

### Error: "catkin_make" fails with "Could not find a package configuration file"

```bash
# CAUSE: A dependency is not installed.
# The error message tells you which one. Example:
# "Could not find a package configuration file provided by 'cv_bridge'"
# FIX:
sudo apt-get install -y ros-noetic-cv-bridge
# General pattern:
# sudo apt-get install -y ros-noetic-<PACKAGE_NAME_WITH_DASHES>
```

### Error: "Camera /dev/video0 not found"

```bash
# CAUSE: Camera not plugged in, or wrong device number.
# FIX:
ls /dev/video*
# If video0 doesn't exist:
#   - Unplug and re-plug the camera
#   - Try a different USB port
#   - Check dmesg: dmesg | tail -20
# If video1 exists instead of video0:
#   - Use: roslaunch sprayer_control demo.launch camera_device:=/dev/video1
```

### Error: Jetson freezes / reboots during catkin_make

```bash
# CAUSE: Out of memory. catkin_make compiling code uses lots of RAM.
# FIX: Make sure swap is active:
free -h
# If swap is 0: go back to Phase 1.3 and create the swap file.
# Also try limiting parallel build jobs:
catkin_make -j2
# (Default is -j4 on a 4-core CPU. -j2 uses less RAM.)
```

### Error: "Low disk space" warnings

```bash
# Check what's using space:
df -h /
sudo du -h --max-depth=1 / 2>/dev/null | sort -rh | head -15

# Clean apt cache:
sudo apt-get clean

# Clean old logs:
sudo journalctl --vacuum-size=50M

# Check for large files in /tmp:
du -h /tmp | sort -rh | head -10
# Remove stale test images:
rm -f /tmp/camera_test.jpg /tmp/yellow_ball_sample.jpg

# Check ROS log files (they grow over time):
du -h ~/.ros/log/
# Clean old logs:
rosclean purge -y
```

---

# ═══════════════════════════════════════════════════════════
# APPENDIX B: QUICK REFERENCE COMMAND CARD
# ═══════════════════════════════════════════════════════════

Print this and keep it next to your laptop.

```
╔══════════════════════════════════════════════════════════════════════╗
║                     DAILY COMMAND CHEAT SHEET                       ║
║             Architecture: Full Pixhawk Control (No ESP32)           ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  SSH IN:        ssh jetson@192.168.55.1                              ║
║                                                                      ║
║  FIX LINE ENDINGS & PYTHON 2 (run ONCE after copying files):        ║
║    dos2unix ~/catkin_ws/src/sprayer_control/scripts/*.py            ║
║    sed -i 's|#!/usr/bin/env python3|#!/usr/bin/env python|' \       ║
║        ~/catkin_ws/src/sprayer_control/scripts/*.py                 ║
║                                                                      ║
║  LAUNCH ALL:    roslaunch sprayer_control demo.launch                ║
║                 roslaunch sprayer_control demo.launch \              ║
║                     fcu_url:=/dev/ttyACM0:115200                    ║
║                                                                      ║
║  MONITOR:       rostopic echo /detection/result                     ║
║                 rostopic echo /spray/status                         ║
║                 rostopic hz /detection/result                       ║
║                 rostopic list                                       ║
║                 rostopic echo /mavros/state                         ║
║                                                                      ║
║  SERVO TEST (manual, via rosservice):                               ║
║    Fan ON:  rosservice call /mavros/cmd/command                     ║
║      "{command: 183, param1: 13, param2: 1400}"                     ║
║    Fan OFF: rosservice call /mavros/cmd/command                     ║
║      "{command: 183, param1: 13, param2: 1000}"                     ║
║    Feed ON: rosservice call /mavros/cmd/command                     ║
║      "{command: 183, param1: 14, param2: 1650}"                     ║
║    Feed OFF: rosservice call /mavros/cmd/command                    ║
║      "{command: 183, param1: 14, param2: 1500}"                     ║
║                                                                      ║
║  REBUILD:       cd ~/catkin_ws && catkin_make && source devel/setup.bash  ║
║  (shortcut):    cb   (alias from .bashrc)                           ║
║                                                                      ║
║  CAMERA TEST:   python3 -c "import cv2; c=cv2.VideoCapture(0);     ║
║                 r,f=c.read(); print(f'OK: {r}, {f.shape}')"        ║
║                                                                      ║
║  DISK SPACE:    df -h /                                             ║
║  RAM/SWAP:      free -h                                             ║
║  CPU/TEMP:      htop  (install: sudo apt-get install htop)          ║
║  GPU USAGE:     tegrastats (built-in Jetson tool)                   ║
║  POWER MODE:    sudo nvpmodel -q                                    ║
║  MAX PERF:      sudo nvpmodel -m 0 && sudo jetson_clocks            ║
║                                                                      ║
║  KILL ROS:      Ctrl+C in the roslaunch terminal                    ║
║  KILL ALL ROS:  killall roscore rosmaster roslaunch rosout 2>/dev/null║
║                                                                      ║
║  REBOOT:        sudo reboot                                        ║
║  SHUTDOWN:      sudo shutdown -h now                                ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

*Document Version: 2.0 | Date: Feb 17, 2025 | Architecture: Full Pixhawk Control (Option A)*
*"Every command is copy-paste. Every step explains why. You cannot break anything that a reboot won't fix."*

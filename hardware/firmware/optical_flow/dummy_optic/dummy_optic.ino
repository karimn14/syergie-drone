#include <Arduino.h>
#include <MAVLink.h>

// --- KONFIGURASI PIN SERIAL (Sesuaikan dengan Board ESP32-S3 Anda) ---
// Pada ESP32-S3 Freenove/XIAO, pin TX/RX default bisa dicek di pinout diagram.
// Contoh di bawah pakai pin custom:
#define RX_PIN 44 
#define TX_PIN 43 

HardwareSerial SerialMavlink(1); // Menggunakan UART 1

// --- VARIABEL OPTICAL FLOW ---
// Dalam implementasi nyata, nilai ini datang dari algoritma kamera Anda
int16_t flow_x_pixel = 0;
int16_t flow_y_pixel = 0;
uint8_t surface_quality = 0; // 0 = Buta, 255 = Kualitas Sempurna

// Timer untuk mengirim data (biasanya 10Hz - 50Hz)
unsigned long previousMillis = 0;
const long interval = 50; // 20Hz (kirim data tiap 50ms)

void setup() {
  Serial.begin(115200); // Untuk Debug ke Laptop
  
  // Inisialisasi Serial ke Pixhawk (Baudrate standar Telem biasanya 57600 atau 115200)
  // Pastikan baudrate ini SAMA dengan setting SERIALx_BAUD di Pixhawk
  SerialMavlink.begin(115200, SERIAL_8N1, RX_PIN, TX_PIN);
  
  Serial.println("MAVLink Optical Flow Sender Started");
}

void loop() {
  unsigned long currentMillis = millis();

  // --- SIMULASI DATA (Hapus bagian ini nanti jika algoritma visi sudah jadi) ---
  // Kita buat nilai 'bergoyang' sedikit untuk melihat grafik bergerak di Pixhawk
  flow_x_pixel = (int16_t)(sin(currentMillis / 1000.0) * 5.0); 
  flow_y_pixel = (int16_t)(cos(currentMillis / 1000.0) * 5.0);
  surface_quality = 200; // Pura-pura kualitas bagus
  // -------------------------------------------------------------------------

  if (currentMillis - previousMillis >= interval) {
    previousMillis = currentMillis;
    
    send_heartbeat();
    send_optical_flow(flow_x_pixel, flow_y_pixel, surface_quality);
    
    // Debug ke Serial Monitor Laptop
    Serial.printf("Sent Flow: X=%d Y=%d Qual=%d\n", flow_x_pixel, flow_y_pixel, surface_quality);
  }
}

void send_heartbeat() {
  mavlink_message_t msg;
  uint8_t buf[MAVLINK_MAX_PACKET_LEN];

  // System ID = 1 (Drone), Component ID = 100 (Kamera/Optical Flow)
  // MAV_TYPE_ONBOARD_CONTROLLER atau MAV_TYPE_CAMERA
  mavlink_msg_heartbeat_pack(1, 100, &msg, MAV_TYPE_CAMERA, MAV_AUTOPILOT_INVALID, MAV_MODE_PREFLIGHT, 0, MAV_STATE_ACTIVE);

  uint16_t len = mavlink_msg_to_send_buffer(buf, &msg);
  SerialMavlink.write(buf, len);
}

void send_optical_flow(int16_t flow_x_raw, int16_t flow_y_raw, uint8_t quality) {
  mavlink_message_t msg;
  uint8_t buf[MAVLINK_MAX_PACKET_LEN];
  
  uint64_t time_usec = micros(); // Waktu dalam mikros

  // --- PERBAIKAN LOGIKA DATA ---
  // Pesan OPTICAL_FLOW (ID 100) menggunakan satuan "Flow in pixels * 10".
  // Jadi kita tidak perlu konversi ke Radian di sini jika pakai pesan tipe ini.
  // Cukup kalikan pixel mentah dengan 10 sesuai standar MAVLink.
  int16_t flow_x_scaled = flow_x_raw * 10;
  int16_t flow_y_scaled = flow_y_raw * 10;

  // Pack pesan OPTICAL_FLOW
  // Signature fungsi ini membutuhkan argumen tambahan di library terbaru
  mavlink_msg_optical_flow_pack(
    1,                      // System ID
    100,                    // Component ID
    &msg,                   // Message container
    time_usec,              // Timestamp
    100,                    // Sensor ID
    flow_x_scaled,          // Flow X (int16_t: pixels * 10)
    flow_y_scaled,          // Flow Y (int16_t: pixels * 10)
    0.0f,                   // Flow X comp (m/s) - biarkan 0
    0.0f,                   // Flow Y comp (m/s) - biarkan 0
    quality,                // Quality (0-255)
    0.0f,                   // Ground Distance (float) - biarkan 0
    0.0f,                   // Flow Rate X (float) -> TAMBAHAN BARU (radian/s)
    0.0f                    // Flow Rate Y (float) -> TAMBAHAN BARU (radian/s)
  );

  uint16_t len = mavlink_msg_to_send_buffer(buf, &msg);
  SerialMavlink.write(buf, len);
}
/*
 * ╔═══════════════════════════════════════════════════════════════╗
 * ║  DEPRECATED — 2025-02-17                                     ║
 * ║                                                               ║
 * ║  This file is NO LONGER USED in the current architecture.     ║
 * ║  The project has pivoted to OPTION A: Full Pixhawk Control.   ║
 * ║                                                               ║
 * ║  Sprayer control is now handled by:                           ║
 * ║    - Pixhawk AUX5 (SERVO13) → EDF Fan ESC                    ║
 * ║    - Pixhawk AUX6 (SERVO14) → MG996R Continuous Servo        ║
 * ║    - MAVLink DO_SET_SERVO commands via mavros                 ║
 * ║    - ROS node: spray_logic_node.py                            ║
 * ║                                                               ║
 * ║  The ESP32 board is removed from the BOM.                     ║
 * ║  This file is kept for reference only.                        ║
 * ╚═══════════════════════════════════════════════════════════════╝
 */

/*
 * [ORIGINAL CODE BELOW — ARCHIVED]
 *
 * sprayer_controller.ino — ESP32-S3 Sprayer Relay Controller
 * =============================================================
 * Receives serial commands from Jetson Nano, drives a relay/MOSFET
 * to control the sprayer pump.
 *
 * Protocol:
 *   RX: "SPRAY_ON\n"   → Relay ON, respond "ACK_ON\n"
 *   RX: "SPRAY_OFF\n"  → Relay OFF, respond "ACK_OFF\n"
 *   RX: "PING\n"       → Respond "PONG\n"
 *
 * Safety:
 *   - Watchdog: If no SPRAY_ON refresh within WATCHDOG_TIMEOUT_MS → auto OFF
 *   - Max duration: If relay ON for > MAX_SPRAY_DURATION_MS → auto OFF
 *   - LED indicator: Built-in LED mirrors relay state
 *
 * Wiring:
 *   ESP32-S3 GPIO RELAY_PIN → Relay Module IN (or MOSFET Gate)
 *   Relay Module COM/NO → Sprayer Pump + Power Supply
 *
 * Board: ESP32-S3 DevKitC (or any ESP32 variant)
 * Serial: 115200 baud (USB CDC or UART)
 */

// ═══════════════════════════════════════════
// CONFIGURATION — Change these for your setup
// ═══════════════════════════════════════════

#define RELAY_PIN               4       // GPIO pin connected to relay module
#define LED_PIN                 2       // Built-in LED (varies by board; 2 for most ESP32)
#define BAUD_RATE               115200

#define WATCHDOG_TIMEOUT_MS     2000    // Auto-off if no command in 2 seconds
#define MAX_SPRAY_DURATION_MS   5000    // Max continuous spray: 5 seconds
#define SERIAL_BUFFER_SIZE      64      // Max command length

// For ESP32-S3 with USB CDC (native USB):
// Use Serial (USB CDC) — this is the default on most ESP32-S3 boards.
// If using UART pins (TX/RX), change to Serial1 or Serial2.
#define COMM_SERIAL             Serial

// ═══════════════════════════════════════════
// STATE
// ═══════════════════════════════════════════

bool relayState = false;
unsigned long lastCommandTime = 0;
unsigned long sprayStartTime = 0;
char serialBuffer[SERIAL_BUFFER_SIZE];
int bufferIndex = 0;

// ═══════════════════════════════════════════
// SETUP
// ═══════════════════════════════════════════

void setup() {
    // Initialize serial
    COMM_SERIAL.begin(BAUD_RATE);
    while (!COMM_SERIAL) {
        delay(10);  // Wait for serial connection (USB CDC)
    }

    // Initialize pins
    pinMode(RELAY_PIN, OUTPUT);
    pinMode(LED_PIN, OUTPUT);
    digitalWrite(RELAY_PIN, LOW);   // Relay OFF at startup
    digitalWrite(LED_PIN, LOW);

    // Clear buffer
    memset(serialBuffer, 0, SERIAL_BUFFER_SIZE);
    bufferIndex = 0;

    lastCommandTime = millis();

    COMM_SERIAL.println("ESP32_SPRAYER_READY");
    COMM_SERIAL.println("PONG");  // Auto-respond on boot (helps Jetson detect us)

    // Blink LED 3 times to indicate ready
    for (int i = 0; i < 3; i++) {
        digitalWrite(LED_PIN, HIGH);
        delay(100);
        digitalWrite(LED_PIN, LOW);
        delay(100);
    }
}

// ═══════════════════════════════════════════
// MAIN LOOP
// ═══════════════════════════════════════════

void loop() {
    // ─── Read Serial Commands ───
    while (COMM_SERIAL.available()) {
        char c = COMM_SERIAL.read();

        if (c == '\n' || c == '\r') {
            if (bufferIndex > 0) {
                serialBuffer[bufferIndex] = '\0';  // Null-terminate
                processCommand(String(serialBuffer));
                bufferIndex = 0;
                memset(serialBuffer, 0, SERIAL_BUFFER_SIZE);
            }
        } else {
            if (bufferIndex < SERIAL_BUFFER_SIZE - 1) {
                serialBuffer[bufferIndex++] = c;
            } else {
                // Buffer overflow — reset
                bufferIndex = 0;
                memset(serialBuffer, 0, SERIAL_BUFFER_SIZE);
            }
        }
    }

    // ─── Safety Watchdog ───
    if (relayState) {
        unsigned long now = millis();

        // Watchdog: No command received in time → auto OFF
        if (now - lastCommandTime > WATCHDOG_TIMEOUT_MS) {
            setRelay(false);
            COMM_SERIAL.println("SAFETY_OFF_WATCHDOG");
        }

        // Max duration: Spray too long → auto OFF
        if (now - sprayStartTime > MAX_SPRAY_DURATION_MS) {
            setRelay(false);
            COMM_SERIAL.println("SAFETY_OFF_MAXDURATION");
        }
    }

    delay(1);  // Small delay to prevent tight loop
}

// ═══════════════════════════════════════════
// COMMAND PROCESSING
// ═══════════════════════════════════════════

void processCommand(String cmd) {
    cmd.trim();  // Remove whitespace

    if (cmd == "SPRAY_ON") {
        setRelay(true);
        lastCommandTime = millis();
        if (!relayState) {
            sprayStartTime = millis();  // Record start time on first ON
        }
        sprayStartTime = (sprayStartTime == 0) ? millis() : sprayStartTime;
        COMM_SERIAL.println("ACK_ON");
    }
    else if (cmd == "SPRAY_OFF") {
        setRelay(false);
        lastCommandTime = millis();
        COMM_SERIAL.println("ACK_OFF");
    }
    else if (cmd == "PING") {
        lastCommandTime = millis();
        COMM_SERIAL.println("PONG");
    }
    else if (cmd == "STATUS") {
        lastCommandTime = millis();
        COMM_SERIAL.print("STATUS:");
        COMM_SERIAL.print(relayState ? "ON" : "OFF");
        COMM_SERIAL.print(":UPTIME:");
        COMM_SERIAL.println(millis() / 1000);
    }
    else {
        COMM_SERIAL.print("ERR_UNKNOWN:");
        COMM_SERIAL.println(cmd);
    }
}

// ═══════════════════════════════════════════
// RELAY CONTROL
// ═══════════════════════════════════════════

void setRelay(bool on) {
    relayState = on;
    digitalWrite(RELAY_PIN, on ? HIGH : LOW);
    digitalWrite(LED_PIN, on ? HIGH : LOW);

    if (on) {
        sprayStartTime = millis();
    } else {
        sprayStartTime = 0;
    }
}

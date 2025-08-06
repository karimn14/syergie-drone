// pwm_sprayer_control.ino – PWM-based spray actuation with feedback
#define SPRAY_PIN 9         // PWM pin
#define LED_PIN 13          // Status LED
#define FLOW_PIN A0         // Analog flow sensor
#define SPRAY_TIMEOUT 5000  // Safety timeout (ms)

unsigned long sprayStart = 0;
bool spraying = false;
int sprayCount = 0;

void setup() {
  pinMode(LED_PIN, OUTPUT);
  pinMode(SPRAY_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  Serial.begin(9600);
  while (!Serial);
}

void triggerSpray(int duration) {
  analogWrite(SPRAY_PIN, 255);
  digitalWrite(LED_PIN, HIGH);
  sprayStart = millis();
  spraying = true;
  sprayCount++;
  Serial.print("SPRAY_START,");
  Serial.println(duration);
}

void loop() {
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd.startsWith("S,")) {
      int duration = cmd.substring(2).toInt();
      if (duration > 0 && duration <= SPRAY_TIMEOUT) {
        triggerSpray(duration);
      } else {
        Serial.println("⚠️ Invalid spray duration");
      }
    } else {
      Serial.println("❌ Unknown command");
    }
  }
  if (spraying && millis() - sprayStart > SPRAY_TIMEOUT) {
    Serial.println("🛑 SPRAY TIMEOUT");
    analogWrite(SPRAY_PIN, 0);
    digitalWrite(LED_PIN, LOW);
    spraying = false;
  }
}

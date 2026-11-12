// electrostatic_gimbal_sprayer.ino – PWM + servo gimbal control
#include <Servo.h>
#define SPRAY_PIN 9
#define LED_PIN 13
#define GIMBAL_SERVO_PIN 10
#define FLOW_PIN A0
#define SPRAY_TIMEOUT 5000

Servo gimbal;
unsigned long sprayStart = 0;
bool spraying = false;
int sprayCount = 0;

void setup() {
  pinMode(LED_PIN, OUTPUT);
  pinMode(SPRAY_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  gimbal.attach(GIMBAL_SERVO_PIN);
  gimbal.write(90);  // Neutral position
  Serial.begin(9600);
  while (!Serial);
  Serial.println("🟢 Electrostatic Sprayer + Gimbal Ready");
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

void handleCommand() {
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
    } else if (cmd.startsWith("A,")) {
      int angle = cmd.substring(2).toInt();
      if (angle >= 0 && angle <= 180) {
        gimbal.write(angle);
        Serial.print("GIMBAL_SET,");
        Serial.println(angle);
      } else {
        Serial.println("⚠️ Invalid gimbal angle");
      }
    } else {
      Serial.println("❌ Unknown command");
    }
  }
}

void monitorTimeout() {
  if (spraying && millis() - sprayStart > SPRAY_TIMEOUT) {
    Serial.println("🛑 SPRAY TIMEOUT");
    analogWrite(SPRAY_PIN, 0);
    digitalWrite(LED_PIN, LOW);
    spraying = false;
  }
}

void loop() {
  handleCommand();
  monitorTimeout();
}

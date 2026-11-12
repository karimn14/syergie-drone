// sprayer_control_dual_mode.ino – Relay or servo selectable
#include <Servo.h>
#define SPRAY_PIN 9
#define LED_PIN 13
#define GIMBAL_SERVO_PIN 10
#define MODE_SERVO_PIN 2
#define FLOW_PIN A0
#define SPRAY_TIMEOUT 5000

Servo gimbal;
unsigned long sprayStart = 0;
bool spraying = false;
int sprayCount = 0;
bool mode_servo = false;

void setup() {
  pinMode(LED_PIN, OUTPUT);
  pinMode(SPRAY_PIN, OUTPUT);
  pinMode(MODE_SERVO_PIN, INPUT_PULLUP);
  digitalWrite(LED_PIN, LOW);
  gimbal.attach(GIMBAL_SERVO_PIN);
  gimbal.write(90);
  Serial.begin(9600);
  while (!Serial);
  Serial.println("🟢 Dual Mode Sprayer Ready");
}

void triggerSpray(int duration) {
  if (mode_servo) {
    analogWrite(SPRAY_PIN, 255);
  } else {
    digitalWrite(SPRAY_PIN, HIGH);
  }
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
    if (mode_servo) {
      analogWrite(SPRAY_PIN, 0);
    } else {
      digitalWrite(SPRAY_PIN, LOW);
    }
    digitalWrite(LED_PIN, LOW);
    spraying = false;
    Serial.println("🛑 SPRAY TIMEOUT");
  }
}

void loop() {
  mode_servo = (digitalRead(MODE_SERVO_PIN) == LOW);
  handleCommand();
  monitorTimeout();
}

// sensor_feedback_sprayer.ino – Closed-loop spray with flow sensor feedback and error detection
#define SPRAY_PIN 9
#define LED_PIN 13
#define FLOW_PIN A0
#define SPRAY_TIMEOUT 5000
#define ERROR_LED_PIN 12

unsigned long sprayStart = 0;
bool spraying = false;
int sprayCount = 0;
float flowSum = 0;
int flowSamples = 0;
bool errorState = false;

void setup() {
  pinMode(LED_PIN, OUTPUT);
  pinMode(SPRAY_PIN, OUTPUT);
  pinMode(ERROR_LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  digitalWrite(ERROR_LED_PIN, LOW);
  Serial.begin(9600);
  while (!Serial);
  Serial.println("🟢 Sensor Feedback Sprayer Ready");
}

void triggerSpray(int duration) {
  analogWrite(SPRAY_PIN, 255);
  digitalWrite(LED_PIN, HIGH);
  sprayStart = millis();
  spraying = true;
  sprayCount++;
  flowSum = 0;
  flowSamples = 0;
  errorState = false;
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
    } else {
      Serial.println("❌ Unknown command");
    }
  }
}

void monitorFlow() {
  if (spraying) {
    int flow = analogRead(FLOW_PIN);
    flowSum += flow;
    flowSamples++;
    if (flow < 10) {
      errorState = true;
      digitalWrite(ERROR_LED_PIN, HIGH);
      Serial.println("❌ Flow sensor error!");
    }
  }
}

void monitorTimeout() {
  if (spraying && millis() - sprayStart > SPRAY_TIMEOUT) {
    analogWrite(SPRAY_PIN, 0);
    digitalWrite(LED_PIN, LOW);
    spraying = false;
    float avgFlow = (flowSamples > 0) ? flowSum / flowSamples : 0;
    Serial.print("SPRAY_END,AVG_FLOW,");
    Serial.println(avgFlow);
    if (errorState) {
      Serial.println("❌ Spray ended with error");
    }
    digitalWrite(ERROR_LED_PIN, LOW);
  }
}

void loop() {
  handleCommand();
  monitorFlow();
  monitorTimeout();
}

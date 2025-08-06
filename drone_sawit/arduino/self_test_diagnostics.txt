// self_test_diagnostics.ino – Hardware self-test and diagnostics
#define SPRAY_PIN 9
#define LED_PIN 13
#define FLOW_PIN A0
#define ERROR_LED_PIN 12

void setup() {
  pinMode(LED_PIN, OUTPUT);
  pinMode(SPRAY_PIN, OUTPUT);
  pinMode(ERROR_LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  digitalWrite(ERROR_LED_PIN, LOW);
  Serial.begin(9600);
  while (!Serial);
  Serial.println("🟢 Running self-test...");
  // Test LED
  digitalWrite(LED_PIN, HIGH);
  delay(200);
  digitalWrite(LED_PIN, LOW);
  // Test spray pin
  analogWrite(SPRAY_PIN, 255);
  delay(200);
  analogWrite(SPRAY_PIN, 0);
  // Test flow sensor
  int flow = analogRead(FLOW_PIN);
  Serial.print("Flow sensor reading: ");
  Serial.println(flow);
  // Test error LED
  digitalWrite(ERROR_LED_PIN, HIGH);
  delay(200);
  digitalWrite(ERROR_LED_PIN, LOW);
  Serial.println("🟢 Self-test complete.");
}

void loop() {
  // No main logic; self-test runs on boot
}

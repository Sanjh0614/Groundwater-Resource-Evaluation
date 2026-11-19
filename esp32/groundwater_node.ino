// ESP32 DevKit V1 + DFRobot Gravity analog water pressure sensor + 0.96" I2C OLED
// Libraries: Adafruit SSD1306, Adafruit GFX
#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

const char* WIFI_SSID = "YOUR_WIFI";
const char* WIFI_PASS = "YOUR_PASSWORD";
const char* API_URL   = "http://192.168.1.50:8000/api/readings"; // backend PC's LAN IP (or https URL if deployed)
const char* API_KEY   = "D0bnBX8MxpZsLVJCH862SoQmI3zIiLjW8xfzJC6ulcw";
const char* DEVICE_ID = "node-1";

const int   SENSOR_PIN = 34;       // ADC1 pin (ADC2 does not work while Wi-Fi is on)
const float DIVIDER    = 1.5;      // 10k/20k divider -> multiply back. Use 1.0 if the sensor output stays under 3.3 V
const unsigned long SEND_MS = 10000;

// Two-point calibration: note the sensor voltage with an empty and a full column, then edit these.
const float V_EMPTY = 0.50, CM_EMPTY = 0.0;
const float V_FULL  = 0.55, CM_FULL  = 100.0;

Adafruit_SSD1306 oled(128, 64, &Wire, -1);

float readVoltage() {              // average 64 samples to tame ESP32 ADC noise
  uint32_t mv = 0;
  for (int i = 0; i < 64; i++) { mv += analogReadMilliVolts(SENSOR_PIN); delay(2); }
  return (mv / 64.0f / 1000.0f) * DIVIDER;
}

float voltageToCm(float v) {
  float cm = CM_EMPTY + (v - V_EMPTY) * (CM_FULL - CM_EMPTY) / (V_FULL - V_EMPTY);
  return cm < 0 ? 0 : cm;
}

void show(float cm, float v, bool sent) {
  oled.clearDisplay();
  oled.setTextColor(SSD1306_WHITE);
  oled.setTextSize(1); oled.setCursor(0, 0);  oled.print("Water level");
  oled.setTextSize(3); oled.setCursor(0, 16); oled.printf("%.1f", cm);
  oled.setTextSize(1); oled.print(" cm");
  oled.setCursor(0, 50);
  oled.printf("%.3fV  WiFi:%s  %s", v, WiFi.status() == WL_CONNECTED ? "ok" : "--", sent ? "sent" : "");
  oled.display();
}

void setup() {
  Serial.begin(115200);
  analogSetPinAttenuation(SENSOR_PIN, ADC_11db);
  oled.begin(SSD1306_SWITCHCAPVCC, 0x3C);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
}

void loop() {
  static unsigned long last = 0;
  float v = readVoltage(), cm = voltageToCm(v);
  bool sent = false;

  if (millis() - last >= SEND_MS) {
    last = millis();
    if (WiFi.status() == WL_CONNECTED) {
      char body[160];
      snprintf(body, sizeof(body), "{\"device_id\":\"%s\",\"water_level_cm\":%.2f,\"voltage\":%.4f}", DEVICE_ID, cm, v);
      HTTPClient http;
      http.begin(API_URL);
      http.addHeader("Content-Type", "application/json");
      http.addHeader("X-API-Key", API_KEY);
      int code = http.POST(body);
      Serial.printf("POST %s -> %d\n", body, code);
      sent = (code == 201);
      http.end();
    } else {
      WiFi.reconnect();
    }
  }
  show(cm, v, sent);
  delay(500);
}

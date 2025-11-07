// #include <WiFi.h>
// #include <WebServer.h>
// #include <Adafruit_NeoPixel.h>
// #include <ArduinoJson.h>

// #include <Wire.h>
// #include <Adafruit_MCP23X17.h>
// #include <Adafruit_PN532.h>

// // ======= USTAWIENIA SIECI =======
// const char* WIFI_SSID = "Winiar-góra";
// const char* WIFI_PASS = "Uranium-235!";

// // ===== KONFIG LED =====
// #define LED_PIN   5
// #define N_LEDS    300
// #define LED_TYPE  NEO_GRB
// #define LED_KHZ   NEO_KHZ800

// // ===== KONFIG I2C / ESP32 =====
// #define SDA_PIN 21   // <- ZMIEŃ jeśli używasz innych pinów I²C
// #define SCL_PIN 22

// // ===== KONFIG MCP23017 (matryca 15x20) =====
// Adafruit_MCP23X17 mcpRows;
// Adafruit_MCP23X17 mcpCols1;
// Adafruit_MCP23X17 mcpCols2;
// Adafruit_MCP23X17 mcpCols3;

// // (addr, pin)
// const uint8_t colPins[20][2] = {
//   {0x21, 0}, {0x21, 1}, {0x21, 2}, {0x21, 3}, {0x21, 4}, {0x21, 5}, {0x21, 6},
//   {0x22, 0}, {0x22, 1}, {0x22, 2}, {0x22, 3}, {0x22, 4}, {0x22, 5}, {0x22, 6},
//   {0x23, 0}, {0x23, 1}, {0x23, 2}, {0x23, 3}, {0x23, 4}, {0x23, 5}
// };
// const uint8_t rowPins[15][2] = {
//   {0x20, 0}, {0x20, 1}, {0x20, 2}, {0x20, 3}, {0x20, 4}, {0x20, 5}, {0x20, 6}, {0x20, 7},
//   {0x20, 8}, {0x20, 9}, {0x20, 10}, {0x20, 11}, {0x20, 12}, {0x20, 13}, {0x20, 14}
// };

// // ===== PN532 (I²C) =====
// // Używamy konstrukcji I²C z Adafruit_PN532 przy wykorzystaniu globalnego Wire
// #define PN532_IRQ   -1
// #define PN532_RESET -1
// Adafruit_PN532 nfc(PN532_IRQ, PN532_RESET);


// // ===== GLOBALNE =====
// Adafruit_NeoPixel strip(N_LEDS, LED_PIN, LED_TYPE + LED_KHZ);
// WebServer server(80);

// // ────────────────────────────────── HELPERS ─────────────────────────────────
// Adafruit_MCP23X17 &getMCP(uint8_t addr) {
//   switch (addr) {
//     case 0x20: return mcpRows;
//     case 0x21: return mcpCols1;
//     case 0x22: return mcpCols2;
//     case 0x23: return mcpCols3;
//     default:   return mcpRows; // fallback
//   }
// }

// inline void allColumnsHigh() {
//   for (uint8_t i = 0; i < 20; i++) {
//     getMCP(colPins[i][0]).digitalWrite(colPins[i][1], HIGH);
//   }
// }

// inline void setColumnLow(uint8_t col) {
//   getMCP(colPins[col][0]).digitalWrite(colPins[col][1], LOW);
// }

// // ─────────────────────────────── ENDPOINTY LED ──────────────────────────────
// void handleOff() {
//   strip.clear();
//   strip.show();
//   server.send(200, "application/json", "{\"ok\":true,\"message\":\"all off\"}");
// }

// void handleSet() {
//   if (!server.hasArg("plain")) {
//     server.send(400, "application/json", "{\"ok\":false,\"error\":\"no body\"}");
//     return;
//   }

//   DynamicJsonDocument doc(16 * 1024);
//   DeserializationError err = deserializeJson(doc, server.arg("plain"));
//   if (err) {
//     String msg = String("{\"ok\":false,\"error\":\"json parse error: ") + err.c_str() + "\"}";
//     server.send(400, "application/json", msg);
//     return;
//   }

//   if (!doc.containsKey("leds") || !doc["leds"].is<JsonArray>()) {
//     server.send(400, "application/json", "{\"ok\":false,\"error\":\"missing leds array\"}");
//     return;
//   }

//   JsonArray arr = doc["leds"].as<JsonArray>();
//   uint32_t applied = 0;

//   for (JsonVariant v : arr) {
//     if (!v.is<JsonObject>()) continue;
//     JsonObject o = v.as<JsonObject>();

//     if (!o.containsKey("i") || !o.containsKey("rgb")) continue;

//     int idx1 = o["i"].as<int>(); // 1-bazowo
//     if (idx1 < 1 || idx1 > N_LEDS) continue;
//     int idx0 = idx1 - 1;

//     JsonArray rgb = o["rgb"].as<JsonArray>();
//     if (rgb.size() < 3) continue;

//     int r = rgb[0].as<int>();
//     int g = rgb[1].as<int>();
//     int b = rgb[2].as<int>();

//     auto ok = [](int x){ return x >= 0 && x <= 255; };
//     if (!ok(r) || !ok(g) || !ok(b)) continue;

//     strip.setPixelColor(idx0, strip.Color(r, g, b));
//     applied++;
//   }

//   strip.show();
//   String resp = String("{\"ok\":true,\"applied\":") + applied + "}";
//   server.send(200, "application/json", resp);
// }

// // ─────────────────────────────── SKANOWANIE ─────────────────────────────────
// // Funkcja blokująca: pinguje PN532 i skanuje matrycę aż coś znajdzie.
// bool scanBlocking(JsonDocument &outDoc) {
//   // przygotowanie wyjścia
//   outDoc.clear();

//   // pętla aż do zdarzenia
//   for (;;) {
//     // 1) Spróbuj odczytać NFC
//     {
//       uint8_t uid[7] = {0};
//       uint8_t uidLength = 0;
//       // timeout ~50ms, nie blokuje na długo
//       uint8_t success = nfc.readPassiveTargetID(PN532_MIFARE_ISO14443A, uid, &uidLength, 50);
//       if (success && uidLength > 0) {
//         outDoc["ok"] = true;
//         outDoc["type"] = "nfc";
//         JsonArray juid = outDoc.createNestedArray("uid");
//         char hexbuf[3];
//         String hexstr;
//         for (uint8_t i = 0; i < uidLength; i++) {
//           juid.add(uid[i]);
//           sprintf(hexbuf, "%02X", uid[i]);
//           if (i) hexstr += ":";
//           hexstr += hexbuf;
//         }
//         outDoc["uid_hex"] = hexstr;

//         // Dodatkowe info gdy dostępne
//         uint8_t atqa_answer[2] = {0};
//         uint8_t sak = 0;
//         if (nfc.inListPassiveTarget()) {
//           // nie wszystkie wersje/tryby dadzą tu dane – pole opcjonalne
//           outDoc["sak"] = (int)sak; // placeholder jeśli biblioteka nie zwróci
//         }

//         return true;
//       }
//     }

//     // 2) Skan kolumn -> wierszy
//     allColumnsHigh();
//     for (uint8_t col = 0; col < 20; col++) {
//       setColumnLow(col); // aktywna kolumna = LOW

//       // czytaj wszystkie wiersze
//       for (uint8_t row = 0; row < 15; row++) {
//         if (mcpRows.digitalRead(rowPins[row][1]) == LOW) {
//           // prosty debounce
//           delay(5);
//           if (mcpRows.digitalRead(rowPins[row][1]) == LOW) {
//             outDoc["ok"]  = true;
//             outDoc["type"] = "key";
//             outDoc["col"] = (int)(col + 1); // 1-bazowo
//             outDoc["row"] = (int)(row + 1);
//             // przywróć kolumnę
//             getMCP(colPins[col][0]).digitalWrite(colPins[col][1], HIGH);
//             return true;
//           }
//         }
//       }

//       // przywróć kolumnę
//       getMCP(colPins[col][0]).digitalWrite(colPins[col][1], HIGH);

//       // daj oddech WiFi/Watchdogowi
//       delay(1);
//       yield();
//     }

//     // utrzymaj responsywność, ale pętla jest blokująca
//     delay(1);
//     yield();
//   }

//   // unreachable
//   // return false;
// }

// // ───────────────────────────── ENDPOINT /scan_board ─────────────────────────
// void handleScanBoard() {
//   // Uwaga: to endpoint blokujący aż do zdarzenia (klawisz/karta).
//   // Jeśli chcesz mieć twardy limit czasu, dodaj tu licznik iteracji/czasu.

//   DynamicJsonDocument resp(1024);

//   bool ok = scanBlocking(resp);
//   if (!ok) {
//     server.send(500, "application/json", "{\"ok\":false,\"error\":\"scan failed\"}");
//     return;
//   }

//   String out;
//   serializeJson(resp, out);
//   server.send(200, "application/json", out);
// }

// // ────────────────────────────────── WiFi ────────────────────────────────────
// void connectWiFi() {
//   WiFi.mode(WIFI_STA);
//   WiFi.begin(WIFI_SSID, WIFI_PASS);
//   Serial.print("Łączenie z WiFi");
//   while (WiFi.status() != WL_CONNECTED) {
//     delay(500);
//     Serial.print(".");
//   }
//   Serial.println();
//   Serial.print("Połączono. IP: ");
//   Serial.println(WiFi.localIP());
// }

// // ────────────────────────────────── SETUP ───────────────────────────────────
// void setup() {
//   Serial.begin(115200);

//   // LED strip
//   strip.begin();
//   strip.clear();
//   strip.show();

//   // I²C
//   Wire.begin(SDA_PIN, SCL_PIN); // 400kHz dla stabilnej pracy

//   // MCP23017
//   mcpRows.begin_I2C(0x20, &Wire);
//   mcpCols1.begin_I2C(0x21, &Wire);
//   mcpCols2.begin_I2C(0x22, &Wire);
//   mcpCols3.begin_I2C(0x23, &Wire);

//   // Kolumny = OUTPUT HIGH (nieaktywne)
//   for (uint8_t i = 0; i < 20; i++) {
//     auto &mcp = getMCP(colPins[i][0]);
//     mcp.pinMode(colPins[i][1], OUTPUT);
//     mcp.digitalWrite(colPins[i][1], HIGH);
//   }

//   // Wiersze = INPUT_PULLUP
//   for (uint8_t i = 0; i < 15; i++) {
//     mcpRows.pinMode(rowPins[i][1], INPUT_PULLUP);
//   }

//   // PN532
//   nfc.begin();     // użyje Wire zdefiniowanego wyżej
//   uint32_t versiondata = nfc.getFirmwareVersion();
//   if (!versiondata) {
//     Serial.println("Nie wykryto PN532 (sprawdź zasilanie/okablowanie/I2C addr).");
//   } else {
//     Serial.print("PN532 OK, ver: 0x"); Serial.println(versiondata, HEX);
//     nfc.SAMConfig(); // konfiguracja do pasywnego odczytu kart
//   }

//   // WiFi + HTTP
//   connectWiFi();

//   server.on("/off", HTTP_GET, handleOff);
//   server.on("/set", HTTP_POST, handleSet);
//   server.on("/scan_board", HTTP_GET, handleScanBoard);

//   server.onNotFound([](){
//     server.send(404, "application/json", "{\"ok\":false,\"error\":\"not found\"}");
//   });

//   server.begin();
//   Serial.println("HTTP server wystartował.");
// }

// void loop() {
//   server.handleClient();
// }

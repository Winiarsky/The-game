#include <Adafruit_NeoPixel.h>

namespace {

constexpr uint8_t LED_PIN = 5;
constexpr uint16_t LED_COUNT = 600;

// Dla WS2815 zwykle działa GRB + 800 kHz.
// Jeśli kolory wyjdą pomieszane, sprawdź wariant NEO_RGB.
constexpr neoPixelType LED_TYPE = NEO_GRB + NEO_KHZ800;

// Jeden aktywny LED naraz, szybki przebieg po całym łańcuchu.
constexpr uint8_t LED_R = 0;
constexpr uint8_t LED_G = 64;
constexpr uint8_t LED_B = 0;
constexpr uint16_t STEP_DELAY_MS = 12;

Adafruit_NeoPixel strip(LED_COUNT, LED_PIN, LED_TYPE);

void showSinglePixel(uint16_t index) {
  strip.clear();
  strip.setPixelColor(index, strip.Color(LED_R, LED_G, LED_B));
  strip.show();
}

}  // namespace

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("ws2815_chase_start");

  strip.begin();
  strip.clear();
  strip.show();
}

void loop() {
  for (uint16_t ledIndex = 0; ledIndex < LED_COUNT; ++ledIndex) {
    showSinglePixel(ledIndex);
    delay(STEP_DELAY_MS);
  }
}

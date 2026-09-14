#include <Arduino.h>
#include <Wire.h>
#include <esp_system.h>
#include "board_mcp_io.h"

// Strict v2: discovery PING, then HELLO and context-bound JSON commands.
namespace {

void settleColumn(unsigned us) { delayMicroseconds(us); }
board_v2::Matrix<TwoWire> matrix(Wire, settleColumn);

// Serial.print can block when USB is slow. Enqueue complete frames and drain
// only available UART space. Event retransmission remains in the controller.
class SerialOutput {
 public:
  bool enqueue(const char *line, size_t size) {
    if (size + 1 > sizeof(bytes_) - count_) return false;
    for (size_t i = 0; i < size; ++i) push(line[i]);
    push('\n');
    return true;
  }
  void pump() {
    int available = Serial.availableForWrite();
    unsigned budget = 128;
    while (available-- > 0 && count_ && budget--) {
      if (Serial.write(static_cast<uint8_t>(bytes_[head_])) != 1) break;
      head_ = (head_ + 1) % sizeof(bytes_);
      --count_;
    }
  }
 private:
  char bytes_[4096]{};
  size_t head_ = 0, count_ = 0;
  void push(char ch) {
    bytes_[(head_ + count_) % sizeof(bytes_)] = ch;
    ++count_;
  }
};

SerialOutput output;
bool initMatrix(void *) { return matrix.init(); }
bool scanMatrix(void *, const board_v2::Mask &mask, board_v2::Mask &pressed) {
  return matrix.scan(mask, pressed);
}
bool sendFrame(void *, const char *line, size_t size) { return output.enqueue(line, size); }
void releaseMatrix(void *) { matrix.release(); }
uint32_t readMicros(void *) { return micros(); }
board_v2::Controller controller({nullptr, initMatrix, scanMatrix, sendFrame, releaseMatrix, readMicros});

}  // namespace

void setup() {
  Serial.begin(115200);
  Wire.begin(21, 22);
  Wire.setClock(400000);
  Wire.setTimeOut(20);
  char boot[17];
  snprintf(boot, sizeof(boot), "%08lx%08lx", static_cast<unsigned long>(esp_random()),
           static_cast<unsigned long>(esp_random()));
  controller.begin(boot, millis());
}

void loop() {
  output.pump();
  unsigned budget = 128;
  while (Serial.available() > 0 && budget--) {
    controller.receive(static_cast<char>(Serial.read()), millis());
  }
  controller.tick(millis());
  output.pump();
  delay(1);
}

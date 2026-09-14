#pragma once

#include "board_protocol_v2.h"

namespace board_v2 {

// MCP23017 BANK=0, SEQOP=0; physical map retained from the original sketch.
// All I2C operations are checked; a failed read never becomes 0xffff/released.
template <class Bus>
class Matrix {
 public:
  explicit Matrix(Bus &bus, void (*settle)(unsigned)) : bus_(bus), settle_(settle) {}

  bool init() {
    // Set output latches BEFORE switching pins to outputs.
    if (!release()) return false;
    for (uint8_t addr = 0x20; addr <= 0x23; ++addr) {
      if (!write16(addr, 0x0a, 0)) return false;  // IOCON, sequential BANK=0
      const uint16_t directions = addr < 0x22 ? 0xffff : (addr == 0x22 ? 0 : 0xfff0);
      const uint16_t pullups = addr < 0x22 ? 0xffff : 0;
      if (!write16(addr, 0x00, directions) || !write16(addr, 0x0c, pullups)) return false;
      uint16_t actual = 0;
      if (!read16(addr, 0x00, actual) || actual != directions ||
          !read16(addr, 0x0c, actual) || actual != pullups) return false;
    }
    return release();
  }

  bool release() {
    const bool a = write16(0x22, 0x14, 0xffff);
    const bool b = write16(0x23, 0x14, 0xffff);
    return a && b;
  }

  bool scan(const Mask &mask, Mask &pressed) {
    pressed = Mask{};
    for (unsigned col = 0; col < 20; ++col) {
      const uint32_t bits = mask.cols[col];
      if (!bits) continue;
      const uint8_t addr = col < 16 ? 0x22 : 0x23;
      const unsigned pin = col < 16 ? col : col - 16;
      if (!write16(addr, 0x14, static_cast<uint16_t>(0xffffu & ~(1u << pin)))) return scanFailed();
      settle_(120);
      uint16_t a = 0xffff, b = 0xffff;
      bool ok = true;
      if (bits & 0xffff) ok = read16(0x20, 0x12, a);
      if (ok && (bits & 0x3fff0000)) ok = read16(0x21, 0x12, b);
      const bool restored = write16(addr, 0x14, 0xffff);
      if (!ok || !restored) return scanFailed();
      pressed.cols[col] = (~(uint32_t(a) | (uint32_t(b) << 16))) & bits;
    }
    return true;
  }

 private:
  Bus &bus_;
  void (*settle_)(unsigned);
  bool scanFailed() { release(); return false; }

  bool write16(uint8_t addr, uint8_t reg, uint16_t value) {
    bus_.beginTransmission(addr);
    bus_.write(reg);
    bus_.write(static_cast<uint8_t>(value));
    bus_.write(static_cast<uint8_t>(value >> 8));
    return bus_.endTransmission() == 0;
  }
  bool read16(uint8_t addr, uint8_t reg, uint16_t &value) {
    bus_.beginTransmission(addr);
    bus_.write(reg);
    if (bus_.endTransmission(false) != 0) return false;
    if (bus_.requestFrom(addr, uint8_t(2)) != 2 || bus_.available() < 2) return false;
    const int low = bus_.read(), high = bus_.read();
    if (low < 0 || high < 0) return false;
    value = static_cast<uint16_t>(low | (high << 8));
    return true;
  }
};

}  // namespace board_v2

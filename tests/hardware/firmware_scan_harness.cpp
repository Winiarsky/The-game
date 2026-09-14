#include <cassert>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>
#include "board_mcp_io.h"

struct FakeWire {
  uint8_t registers[4][256]{};
  bool touched[20][30]{};
  bool failed = false, shortRead = false;
  unsigned reads = 0, writes = 0;
  uint8_t address = 0, selected[4]{};
  std::vector<uint8_t> outgoing, incoming;
  size_t readIndex = 0;
  void beginTransmission(uint8_t addr) { address = addr; outgoing.clear(); }
  size_t write(uint8_t byte) { outgoing.push_back(byte); return 1; }
  int endTransmission(bool = true) {
    if (failed) return 2;
    assert(address >= 0x20 && address <= 0x23 && !outgoing.empty());
    const unsigned chip = address - 0x20;
    selected[chip] = outgoing[0];
    if (outgoing.size() > 1) {
      ++writes;
      for (size_t i = 1; i < outgoing.size(); ++i)
        registers[chip][static_cast<uint8_t>(outgoing[0] + i - 1)] = outgoing[i];
    }
    return 0;
  }
  bool active(unsigned col) const {
    const unsigned chip = col < 16 ? 2 : 3, bit = col < 16 ? col : col - 16;
    const uint16_t latch = registers[chip][0x14] | (uint16_t(registers[chip][0x15]) << 8);
    return (latch & (uint16_t(1) << bit)) == 0;
  }
  int requestFrom(uint8_t addr, uint8_t count) {
    assert(count == 2);
    if (failed) return 0;
    ++reads;
    const unsigned chip = addr - 0x20;
    const uint8_t reg = selected[chip];
    uint16_t value = registers[chip][reg] | (uint16_t(registers[chip][reg + 1]) << 8);
    if (chip < 2 && reg == 0x12) {
      value = 0xffff;
      for (unsigned col = 0; col < 20; ++col) {
        if (!active(col)) continue;
        for (unsigned bit = 0; bit < 16; ++bit) {
          const unsigned row = chip * 16 + bit;
          if (row < 30 && touched[col][row]) value &= ~(uint16_t(1) << bit);
        }
      }
    }
    incoming = {static_cast<uint8_t>(value), static_cast<uint8_t>(value >> 8)};
    if (shortRead) incoming.pop_back();
    readIndex = 0;
    return static_cast<int>(incoming.size());
  }
  int available() const { return static_cast<int>(incoming.size() - readIndex); }
  int read() { return readIndex < incoming.size() ? incoming[readIndex++] : -1; }
};

void settle(unsigned us) { assert(us == 120); }

void testMatrix() {
  FakeWire wire;
  board_v2::Matrix<FakeWire> matrix(wire, settle);
  assert(matrix.init());
  board_v2::Mask full, pressed;
  for (auto &bits : full.cols) bits = board_v2::kFullRows;
  wire.reads = wire.writes = 0;
  assert(matrix.scan(full, pressed) && pressed.empty());
  assert(wire.reads == 40 && wire.writes == 40);
  for (unsigned col = 0; col < 20; ++col) {
    for (unsigned row = 0; row < 30; ++row) {
      wire.touched[col][row] = true;
      board_v2::Mask mask;
      mask.cols[col] = uint32_t(1) << row;
      wire.reads = wire.writes = 0;
      assert(matrix.scan(mask, pressed));
      assert(pressed.cols[col] == mask.cols[col]);
      assert(wire.reads == 1 && wire.writes == 2);
      for (unsigned c = 0; c < 20; ++c) assert(!wire.active(c));
      assert(matrix.scan(full, pressed) && pressed.cols[col] == mask.cols[col]);
      wire.touched[col][row] = false;
    }
  }
  board_v2::Mask panel;
  panel.cols[19] = 14;
  wire.touched[0][0] = wire.touched[19][7] = true;
  wire.reads = 0;
  assert(matrix.scan(panel, pressed) && pressed.empty() && wire.reads == 1);
  wire.touched[19][1] = wire.touched[19][2] = true;
  assert(matrix.scan(panel, pressed) && pressed.cols[19] == 6);
  wire.shortRead = true;
  assert(!matrix.scan(panel, pressed));
  for (unsigned c = 0; c < 20; ++c) assert(!wire.active(c));
  wire.shortRead = false;
  wire.failed = true;
  assert(!matrix.init() && !matrix.scan(panel, pressed));
  wire.failed = false;
  assert(matrix.init());
  board_v2::Mask empty;
  wire.reads = wire.writes = 0;
  assert(matrix.scan(empty, pressed) && pressed.empty());
  assert(wire.reads == 0 && wire.writes == 0);
  std::cout << "600 cells; masked bulk reads; checked I2C OK\n";
}

struct Harness {
  FakeWire wire;
  board_v2::Matrix<FakeWire> matrix{wire, settle};
  bool blocked = false;
  static bool init(void *data) { return static_cast<Harness *>(data)->matrix.init(); }
  static bool scan(void *data, const board_v2::Mask &mask, board_v2::Mask &pressed) {
    return static_cast<Harness *>(data)->matrix.scan(mask, pressed);
  }
  static bool send(void *data, const char *line, size_t size) {
    if (static_cast<Harness *>(data)->blocked) return false;
    std::cout.write(line, static_cast<std::streamsize>(size));
    std::cout << '\n';
    return true;
  }
  static void release(void *data) { static_cast<Harness *>(data)->matrix.release(); }
};

int main(int argc, char **) {
  std::cout.setf(std::ios::unitbuf);
  if (argc > 1) { testMatrix(); return 0; }
  Harness harness;
  board_v2::Controller controller({&harness, Harness::init, Harness::scan, Harness::send, Harness::release});
  uint32_t now = 0;
  controller.begin("a18b920000000001", now);
  std::string line;
  while (std::getline(std::cin, line)) {
    if (line.rfind("@tick ", 0) == 0) {
      const unsigned duration = static_cast<unsigned>(std::stoul(line.substr(6)));
      assert(duration <= 60000);
      for (unsigned i = 0; i < duration; ++i) controller.tick(++now);
    } else if (line.rfind("@time ", 0) == 0) {
      now = static_cast<uint32_t>(std::stoul(line.substr(6)));
    } else if (line.rfind("@contact ", 0) == 0) {
      std::istringstream values(line.substr(9));
      unsigned col, row, down;
      values >> col >> row >> down;
      assert(col < 20 && row < 30);
      harness.wire.touched[col][row] = down != 0;
    } else if (line == "@short_read") harness.wire.shortRead = true;
    else if (line == "@i2c_error") harness.wire.failed = true;
    else if (line == "@recover") harness.wire.failed = harness.wire.shortRead = false;
    else if (line == "@block") harness.blocked = true;
    else if (line == "@unblock") harness.blocked = false;
    else if (line.rfind("@bytes ", 0) == 0) {
      for (char c : line.substr(7)) controller.receive(c, now);
    } else {
      for (char c : line) controller.receive(c, now);
      controller.receive('\n', now);
    }
  }
}

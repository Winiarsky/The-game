#include <Wire.h>
#include <Adafruit_MCP23X17.h>

namespace {

constexpr char PROTOCOL_NAME[] = "board_scan_usb_v1";
constexpr unsigned long SERIAL_BAUD = 115200;

constexpr uint8_t SDA_PIN = 21;
constexpr uint8_t SCL_PIN = 22;

constexpr uint8_t BOARD_ROWS = 30;
constexpr uint8_t BOARD_COLS = 20;

constexpr uint16_t SCAN_SETTLE_US = 120;
constexpr uint16_t PRESS_DEBOUNCE_MS = 25;
constexpr uint16_t RELEASE_DEBOUNCE_MS = 25;

// Zalecane adresy MCP23017:
// 0x20 -> wiersze 0..15   (A2=0 A1=0 A0=0)
// 0x21 -> wiersze 16..29  (A2=0 A1=0 A0=1)
// 0x22 -> kolumny 0..15   (A2=0 A1=1 A0=0)
// 0x23 -> kolumny 16..19  (A2=0 A1=1 A0=1)
constexpr uint8_t MCP_ROWS_A_ADDR = 0x20;
constexpr uint8_t MCP_ROWS_B_ADDR = 0x21;
constexpr uint8_t MCP_COLS_A_ADDR = 0x22;
constexpr uint8_t MCP_COLS_B_ADDR = 0x23;

struct PinRef {
  uint8_t addr;
  uint8_t pin;
};

struct CellRef {
  int8_t row = -1;
  int8_t col = -1;

  bool valid() const {
    return row >= 0 && col >= 0;
  }
};

Adafruit_MCP23X17 mcpRowsA;
Adafruit_MCP23X17 mcpRowsB;
Adafruit_MCP23X17 mcpColsA;
Adafruit_MCP23X17 mcpColsB;

const PinRef ROW_PINS[BOARD_ROWS] = {
  {MCP_ROWS_A_ADDR, 0},  {MCP_ROWS_A_ADDR, 1},  {MCP_ROWS_A_ADDR, 2},  {MCP_ROWS_A_ADDR, 3},
  {MCP_ROWS_A_ADDR, 4},  {MCP_ROWS_A_ADDR, 5},  {MCP_ROWS_A_ADDR, 6},  {MCP_ROWS_A_ADDR, 7},
  {MCP_ROWS_A_ADDR, 8},  {MCP_ROWS_A_ADDR, 9},  {MCP_ROWS_A_ADDR, 10}, {MCP_ROWS_A_ADDR, 11},
  {MCP_ROWS_A_ADDR, 12}, {MCP_ROWS_A_ADDR, 13}, {MCP_ROWS_A_ADDR, 14}, {MCP_ROWS_A_ADDR, 15},
  {MCP_ROWS_B_ADDR, 0},  {MCP_ROWS_B_ADDR, 1},  {MCP_ROWS_B_ADDR, 2},  {MCP_ROWS_B_ADDR, 3},
  {MCP_ROWS_B_ADDR, 4},  {MCP_ROWS_B_ADDR, 5},  {MCP_ROWS_B_ADDR, 6},  {MCP_ROWS_B_ADDR, 7},
  {MCP_ROWS_B_ADDR, 8},  {MCP_ROWS_B_ADDR, 9},  {MCP_ROWS_B_ADDR, 10}, {MCP_ROWS_B_ADDR, 11},
  {MCP_ROWS_B_ADDR, 12}, {MCP_ROWS_B_ADDR, 13},
};

const PinRef COL_PINS[BOARD_COLS] = {
  {MCP_COLS_A_ADDR, 0},  {MCP_COLS_A_ADDR, 1},  {MCP_COLS_A_ADDR, 2},  {MCP_COLS_A_ADDR, 3},
  {MCP_COLS_A_ADDR, 4},  {MCP_COLS_A_ADDR, 5},  {MCP_COLS_A_ADDR, 6},  {MCP_COLS_A_ADDR, 7},
  {MCP_COLS_A_ADDR, 8},  {MCP_COLS_A_ADDR, 9},  {MCP_COLS_A_ADDR, 10}, {MCP_COLS_A_ADDR, 11},
  {MCP_COLS_A_ADDR, 12}, {MCP_COLS_A_ADDR, 13}, {MCP_COLS_A_ADDR, 14}, {MCP_COLS_A_ADDR, 15},
  {MCP_COLS_B_ADDR, 0},  {MCP_COLS_B_ADDR, 1},  {MCP_COLS_B_ADDR, 2},  {MCP_COLS_B_ADDR, 3},
};

CellRef lastCandidate;
unsigned long candidateSinceMs = 0;

bool activePressed = false;
CellRef activeCell;
bool boardReady = false;

Adafruit_MCP23X17 &mcpForAddress(uint8_t addr) {
  switch (addr) {
    case MCP_ROWS_A_ADDR:
      return mcpRowsA;
    case MCP_ROWS_B_ADDR:
      return mcpRowsB;
    case MCP_COLS_A_ADDR:
      return mcpColsA;
    case MCP_COLS_B_ADDR:
      return mcpColsB;
    default:
      return mcpRowsA;
  }
}

bool sameCell(const CellRef &a, const CellRef &b) {
  return a.row == b.row && a.col == b.col;
}

String sanitizeCommand(const String &raw) {
  String cleaned;
  cleaned.reserve(raw.length());
  for (size_t i = 0; i < raw.length(); ++i) {
    const char ch = raw[i];
    if (ch >= 'a' && ch <= 'z') {
      cleaned += static_cast<char>(ch - 32);
      continue;
    }
    if (ch >= 'A' && ch <= 'Z') {
      cleaned += ch;
      continue;
    }
    if (ch >= '0' && ch <= '9') {
      cleaned += ch;
      continue;
    }
    if (ch == '_' || ch == '-') {
      cleaned += ch;
    }
  }
  return cleaned;
}

void writeBootLine(const char *stage) {
  Serial.print("{\"event\":\"boot\",\"stage\":\"");
  Serial.print(stage);
  Serial.print("\",\"protocol\":\"");
  Serial.print(PROTOCOL_NAME);
  Serial.println("\"}");
}

void writeJsonInfoLine(const char *eventName) {
  Serial.print("{\"event\":\"");
  Serial.print(eventName);
  Serial.print("\",\"protocol\":\"");
  Serial.print(PROTOCOL_NAME);
  Serial.print("\",\"rows\":");
  Serial.print(BOARD_ROWS);
  Serial.print(",\"cols\":");
  Serial.print(BOARD_COLS);
  Serial.print(",\"rows_addr\":[32,33],\"cols_addr\":[34,35]}");
  Serial.println();
}

void writeJsonCellLine(const char *eventName, const CellRef &cell) {
  Serial.print("{\"event\":\"");
  Serial.print(eventName);
  Serial.print("\",\"protocol\":\"");
  Serial.print(PROTOCOL_NAME);
  Serial.print("\",\"row\":");
  Serial.print(cell.row);
  Serial.print(",\"col\":");
  Serial.print(cell.col);
  Serial.print(",\"row_1b\":");
  Serial.print(cell.row + 1);
  Serial.print(",\"col_1b\":");
  Serial.print(cell.col + 1);
  Serial.print(",\"ts_ms\":");
  Serial.print(millis());
  Serial.println("}");
}

void allColumnsHigh() {
  for (uint8_t col = 0; col < BOARD_COLS; ++col) {
    const PinRef &pin = COL_PINS[col];
    mcpForAddress(pin.addr).digitalWrite(pin.pin, HIGH);
  }
}

void activateColumn(uint8_t col) {
  const PinRef &pin = COL_PINS[col];
  mcpForAddress(pin.addr).digitalWrite(pin.pin, LOW);
}

CellRef scanBoard() {
  CellRef found;

  allColumnsHigh();
  for (uint8_t col = 0; col < BOARD_COLS; ++col) {
    activateColumn(col);
    delayMicroseconds(SCAN_SETTLE_US);

    for (uint8_t row = 0; row < BOARD_ROWS; ++row) {
      const PinRef &pin = ROW_PINS[row];
      if (mcpForAddress(pin.addr).digitalRead(pin.pin) == LOW) {
        found.row = static_cast<int8_t>(row);
        found.col = static_cast<int8_t>(col);
        allColumnsHigh();
        return found;
      }
    }

    const PinRef &pin = COL_PINS[col];
    mcpForAddress(pin.addr).digitalWrite(pin.pin, HIGH);
  }

  return found;
}

void configureRows() {
  for (uint8_t row = 0; row < BOARD_ROWS; ++row) {
    const PinRef &pin = ROW_PINS[row];
    auto &mcp = mcpForAddress(pin.addr);
    mcp.pinMode(pin.pin, INPUT_PULLUP);
  }
}

void configureColumns() {
  for (uint8_t col = 0; col < BOARD_COLS; ++col) {
    const PinRef &pin = COL_PINS[col];
    auto &mcp = mcpForAddress(pin.addr);
    mcp.pinMode(pin.pin, OUTPUT);
    mcp.digitalWrite(pin.pin, HIGH);
  }
}

bool initMcp(Adafruit_MCP23X17 &mcp, uint8_t addr) {
  Serial.print("{\"event\":\"boot\",\"stage\":\"mcp_probe\",\"addr\":");
  Serial.print(addr);
  Serial.println("}");
  if (!mcp.begin_I2C(addr, &Wire)) {
    Serial.print("{\"event\":\"fatal\",\"message\":\"MCP init failed\",\"addr\":");
    Serial.print(addr);
    Serial.println("}");
    return false;
  }
  return true;
}

void handleSerialCommand(String command) {
  const String cleaned = sanitizeCommand(command);
  if (cleaned.length() == 0) {
    return;
  }

  if (cleaned.indexOf("PING") >= 0) {
    writeJsonInfoLine("pong");
    return;
  }

  if (cleaned.indexOf("STATUS") >= 0 || cleaned.indexOf("INFO") >= 0) {
    writeJsonInfoLine("status");
    return;
  }

  Serial.print("{\"event\":\"error\",\"message\":\"unknown command\",\"command\":\"");
  Serial.print(cleaned);
  Serial.println("\"}");
}

void pollSerialCommands() {
  static String buffer;
  while (Serial.available() > 0) {
    const char ch = static_cast<char>(Serial.read());
    if (ch == '\0') {
      buffer = "";
      continue;
    }
    if (ch == '\n' || ch == '\r') {
      if (buffer.length() > 0) {
        handleSerialCommand(buffer);
        buffer = "";
      }
      continue;
    }
    if (static_cast<unsigned char>(ch) < 32 || static_cast<unsigned char>(ch) > 126) {
      continue;
    }
    buffer += ch;
    if (buffer.length() > 64) {
      buffer = "";
    }
  }
}

}  // namespace

void setup() {
  Serial.begin(SERIAL_BAUD);
  delay(1000);
  writeBootLine("serial_ready");

  Wire.begin(SDA_PIN, SCL_PIN);
  Wire.setClock(400000);
  writeBootLine("wire_ready");

  const bool ok =
      initMcp(mcpRowsA, MCP_ROWS_A_ADDR) &&
      initMcp(mcpRowsB, MCP_ROWS_B_ADDR) &&
      initMcp(mcpColsA, MCP_COLS_A_ADDR) &&
      initMcp(mcpColsB, MCP_COLS_B_ADDR);

  if (!ok) {
    writeBootLine("halt_after_mcp_error");
    return;
  }

  configureRows();
  configureColumns();
  allColumnsHigh();
  boardReady = true;
  writeBootLine("board_ready");

  writeJsonInfoLine("ready");
}

void loop() {
  pollSerialCommands();
  if (!boardReady) {
    delay(250);
    return;
  }

  const CellRef sample = scanBoard();
  const unsigned long nowMs = millis();

  if (!sameCell(sample, lastCandidate)) {
    lastCandidate = sample;
    candidateSinceMs = nowMs;
  }

  if (!activePressed) {
    if (sample.valid() && (nowMs - candidateSinceMs) >= PRESS_DEBOUNCE_MS) {
      activePressed = true;
      activeCell = sample;
      writeJsonCellLine("press", activeCell);
    }
    delay(2);
    return;
  }

  if (sameCell(sample, activeCell)) {
    delay(2);
    return;
  }

  if (!sample.valid()) {
    if ((nowMs - candidateSinceMs) >= RELEASE_DEBOUNCE_MS) {
      writeJsonCellLine("release", activeCell);
      activePressed = false;
      activeCell = CellRef();
    }
    delay(2);
    return;
  }

  if ((nowMs - candidateSinceMs) >= PRESS_DEBOUNCE_MS) {
    writeJsonCellLine("release", activeCell);
    activeCell = sample;
    writeJsonCellLine("press", activeCell);
  }

  delay(2);
}

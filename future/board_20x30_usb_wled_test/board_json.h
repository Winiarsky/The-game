#pragma once

#include <cstddef>
#include <cstdint>
#include <cstring>

namespace board_v2 {

// Bounded command grammar: objects, arrays, plain ASCII strings and uint32.
// No allocation, coercion, escapes, duplicate keys or partial-line execution.
// This deliberately accepts only the JSON subset used by the wire contract.
class CommandJson {
 public:
  enum Kind { Object, Array, String, Number };
  struct Token {
    Kind kind = Object;
    uint16_t begin = 0, end = 0, next = 0;
    uint32_t number = 0;
  };
  static constexpr size_t kTokens = 192;
  Token tokens[kTokens]{};
  const char *text = nullptr;
  size_t count = 0;

  bool parse(const char *input) {
    text = input;
    count = pos_ = 0;
    if (!value(0) || tokens[0].kind != Object) return false;
    space();
    return text[pos_] == '\0';
  }

  bool equals(size_t index, const char *expected) const {
    return index < count && tokens[index].kind == String &&
           std::strlen(expected) == static_cast<size_t>(tokens[index].end - tokens[index].begin) &&
           std::strncmp(text + tokens[index].begin, expected,
                        tokens[index].end - tokens[index].begin) == 0;
  }

  int field(const char *key) const {
    for (size_t i = 1; i < tokens[0].next;) {
      const size_t val = i + 1;
      if (equals(i, key)) return static_cast<int>(val);
      i = tokens[val].next;
    }
    return -1;
  }

  bool string(const char *key, const char *expected) const {
    const int index = field(key);
    return index >= 0 && equals(static_cast<size_t>(index), expected);
  }

  bool uintValue(const char *key, uint32_t &out) const {
    const int index = field(key);
    if (index < 0 || tokens[index].kind != Number) return false;
    out = tokens[index].number;
    return true;
  }

  bool hexString(size_t index, size_t length) const {
    if (index >= count || tokens[index].kind != String ||
        static_cast<size_t>(tokens[index].end - tokens[index].begin) != length) return false;
    for (size_t i = tokens[index].begin; i < tokens[index].end; ++i) {
      const char ch = text[i];
      if (!((ch >= '0' && ch <= '9') || (ch >= 'a' && ch <= 'f'))) return false;
    }
    return true;
  }

  bool copyHex(const char *key, char *out, size_t length) const {
    const int index = field(key);
    if (index < 0 || !hexString(static_cast<size_t>(index), length)) return false;
    std::memcpy(out, text + tokens[index].begin, length);
    out[length] = '\0';
    return true;
  }

  bool only(const char *const *keys, size_t keyCount) const {
    size_t seen = 0;
    for (size_t i = 1; i < tokens[0].next; i = tokens[i + 1].next) {
      bool found = false;
      for (size_t k = 0; k < keyCount; ++k) found = found || equals(i, keys[k]);
      if (!found) return false;
      ++seen;
    }
    return seen == keyCount;
  }

 private:
  size_t pos_ = 0;
  void space() {
    while (text[pos_] == ' ' || text[pos_] == '\t' || text[pos_] == '\r') ++pos_;
  }
  bool value(unsigned depth) {
    space();
    if (depth > 3 || count == kTokens) return false;
    const size_t index = count++;
    Token &token = tokens[index];
    token = Token{};
    const char ch = text[pos_];
    if (ch == '"') {
      token.kind = String;
      token.begin = static_cast<uint16_t>(++pos_);
      while (text[pos_] != '"') {
        const unsigned char c = static_cast<unsigned char>(text[pos_]);
        if (c < 32 || c > 126 || c == '\\') return false;
        ++pos_;
      }
      token.end = static_cast<uint16_t>(pos_++);
    } else if (ch >= '0' && ch <= '9') {
      token.kind = Number;
      if (ch == '0' && text[pos_ + 1] >= '0' && text[pos_ + 1] <= '9') return false;
      uint64_t number = 0;
      do {
        number = number * 10 + static_cast<unsigned>(text[pos_++] - '0');
        if (number > UINT32_MAX) return false;
      } while (text[pos_] >= '0' && text[pos_] <= '9');
      token.number = static_cast<uint32_t>(number);
    } else if (ch == '{' || ch == '[') {
      token.kind = ch == '{' ? Object : Array;
      const char end = ch == '{' ? '}' : ']';
      ++pos_;
      space();
      if (text[pos_] != end) {
        while (true) {
          if (token.kind == Object) {
            const size_t key = count;
            if (!value(depth + 1) || tokens[key].kind != String) return false;
            for (size_t prev = index + 1; prev < key; prev = tokens[prev + 1].next) {
              const size_t len = tokens[key].end - tokens[key].begin;
              if (len == static_cast<size_t>(tokens[prev].end - tokens[prev].begin) &&
                  std::strncmp(text + tokens[key].begin, text + tokens[prev].begin, len) == 0)
                return false;
            }
            space();
            if (text[pos_++] != ':') return false;
          }
          if (!value(depth + 1)) return false;
          space();
          if (text[pos_] == end) break;
          if (text[pos_] != ',') return false;
          ++pos_;
        }
      }
      ++pos_;
    } else {
      return false;
    }
    token.next = static_cast<uint16_t>(count);
    return true;
  }
};

}  // namespace board_v2

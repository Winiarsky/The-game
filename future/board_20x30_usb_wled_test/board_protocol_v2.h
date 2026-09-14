#pragma once

#include "board_json.h"
#include <cstdarg>
#include <cstdio>
#include <initializer_list>

namespace board_v2 {

constexpr char kFirmware[] = "board_scan_protocol_v2_2";
constexpr char kMapping[] = "mcp20_21_rows_mcp22_23_cols_20x30_v1";
constexpr size_t kFrameSize = 2048;
constexpr uint32_t kFullRows = 0x3fffffff;
constexpr uint32_t kDebounceMs = 25;

struct Mask {
  uint32_t cols[20]{};
  bool empty() const {
    for (uint32_t bits : cols) if (bits != 0) return false;
    return true;
  }
  bool contains(unsigned col, unsigned row) const {
    return col < 20 && row < 30 && (cols[col] & (uint32_t(1) << row)) != 0;
  }
};

struct Hardware {
  void *data;
  bool (*init)(void *);
  bool (*scan)(void *, const Mask &, Mask &);
  bool (*send)(void *, const char *, size_t);
  void (*release)(void *);
  uint32_t (*micros)(void *) = nullptr;
};

// Stack-free formatting storage is owned by Controller, not Arduino String.
struct Frame {
  char data[kFrameSize + 1]{};
  size_t size = 0;
  bool valid = true;
  void clear() { size = 0; data[0] = '\0'; valid = true; }
  void add(const char *format, ...) {
    if (!valid) return;
    va_list args;
    va_start(args, format);
    const int n = vsnprintf(data + size, sizeof(data) - size, format, args);
    va_end(args);
    if (n < 0 || static_cast<size_t>(n) >= sizeof(data) - size) { valid = false; return; }
    size += static_cast<size_t>(n);
  }
};

class Controller {
 public:
  explicit Controller(Hardware hardware) : hw_(hardware) {}

  void begin(const char *boot, uint32_t now) {
    std::memcpy(boot_, boot, 17);
    ready_ = hw_.init(hw_.data);
    now_ = lastStatus_ = now;
    if (!ready_) faultCode_ = "i2c_error";
    info();
  }

  // At most a bounded number of bytes should be fed between scan ticks.
  void receive(char ch, uint32_t now) {
    now_ = now;
    expirePartial(now);
    lastByte_ = now;
    if (ch == '\n') {
      if (!discard_ && length_ != 0) {
        if (rx_[length_ - 1] == '\r') --length_;
        rx_[length_] = '\0';
        handleLine();
      }
      length_ = 0;
      discard_ = false;
      return;
    }
    if (discard_) return;
    const unsigned char c = static_cast<unsigned char>(ch);
    if ((c < 32 && ch != '\t' && ch != '\r') || c > 126) {
      discard_ = true;
      invalid("invalid_frame");
      return;
    }
    // The optional CR belongs to CRLF, not the 2048-byte JSON budget.
    if (length_ >= kFrameSize && !(length_ == kFrameSize && ch == '\r')) {
      discard_ = true;
      invalid("frame_too_long");
      return;
    }
    rx_[length_++] = ch;
  }

  void tick(uint32_t now) {
    now_ = now;
    expirePartial(now);
    if (open_ && elapsed(now, lastHost_) >= 5000) {
      fail("host_timeout");
      open_ = false;
    }
    if (open_ && eventCount_ && elapsed(now, ackProgress_) >= 2000) fail("ack_timeout");
    if (replyPending_ && hw_.send(hw_.data, reply_, std::strlen(reply_))) replyPending_ = false;
    if (!replyPending_ && ready_ && (state_ == Waiting || state_ == Scanning)) sample();
    if (open_ && !replyPending_) sendEvents();
    if (elapsed(now, lastStatus_) >= 1000) {
      lastStatus_ = now;
      if (open_) status(0, false);
      else info();
    }
  }

 private:
  enum State { Idle, Waiting, Scanning, Completed, Fault };
  struct Event {
    uint32_t seq = 0, at = 0, sentAt = 0;
    uint8_t col = 0, row = 0;
    bool final = false, sent = false;
  };
  Hardware hw_;
  CommandJson json_;
  Frame tx_;
  char boot_[17]{}, session_[17]{};
  char rx_[kFrameSize + 1]{}, lastCommand_[kFrameSize + 1]{}, reply_[kFrameSize + 1]{};
  size_t length_ = 0;
  bool discard_ = false, ready_ = false, open_ = false, stream_ = false;
  State state_ = Idle;
  Mask mask_, finish_, held_;
  Event events_[32]{};
  unsigned eventHead_ = 0, eventCount_ = 0;
  uint32_t now_ = 0, lastByte_ = 0, lastStatus_ = 0, lastHost_ = 0;
  uint32_t lastId_ = 0, context_ = 0, seq_ = 0, acked_ = 0, sentSeq_ = 0;
  uint32_t ackProgress_ = 0, releaseSince_ = 0, candidateSince_ = 0;
  uint32_t lastInvalid_ = 0, i2cErrors_ = 0;
  bool invalidSent_ = false, clearSeen_ = false, readyAnnounced_ = false;
  bool replyPending_ = false;
  uint32_t scanUs_ = 0, scanMaxUs_ = 0;
  int candidate_ = -1;
  const char *faultCode_ = nullptr;

  static uint32_t elapsed(uint32_t now, uint32_t then) { return now - then; }
  const char *stateName() const {
    switch (state_) {
      case Waiting: return "waiting_release";
      case Scanning: return "scanning";
      case Completed: return "completed";
      case Fault: return "fault";
      default: return "idle";
    }
  }
  bool emit() { return tx_.valid && hw_.send(hw_.data, tx_.data, tx_.size); }
  void base(const char *type) {
    tx_.clear();
    tx_.add("{\"v\":2,\"type\":\"%s\",\"boot\":\"%s\",\"session\":\"%s\"", type, boot_, session_);
  }
  void addState() {
    tx_.add(",\"context\":");
    if (context_) tx_.add("%lu", static_cast<unsigned long>(context_));
    else tx_.add("null");
    tx_.add(",\"state\":\"%s\",\"ready\":%s", stateName(), ready_ ? "true" : "false");
  }
  void addMask(const Mask &mask) {
    tx_.add("[");
    bool first = true;
    for (unsigned col = 0; col < 20; ++col) {
      if (!mask.cols[col]) continue;
      tx_.add("%s[%u,\"%08lx\"]", first ? "" : ",", col,
              static_cast<unsigned long>(mask.cols[col]));
      first = false;
    }
    tx_.add("]");
  }
  void info() {
    tx_.clear();
    tx_.add("{\"v\":2,\"type\":\"info\",\"protocol\":\"board_scan_usb_v2\","
            "\"firmware\":\"%s\",\"boot\":\"%s\",\"mapping_id\":\"%s\","
            "\"cols\":20,\"rows\":30,\"ready\":%s,\"max_frame\":2048,"
            "\"event_capacity\":32,\"capabilities\":[\"mask\",\"single\",\"stream\",\"finish\",\"ack\"]}",
            kFirmware, boot_, kMapping, ready_ ? "true" : "false");
    emit();
  }
  void status(uint32_t id, bool cache) {
    base("status");
    if (id) tx_.add(",\"id\":%lu", static_cast<unsigned long>(id));
    addState();
    tx_.add(",\"seq\":%lu,\"ack\":%lu,\"queued\":%u,\"i2c_errors\":%lu,\"scan_us\":%lu,\"scan_max_us\":%lu,\"held\":",
            static_cast<unsigned long>(seq_), static_cast<unsigned long>(acked_), eventCount_,
            static_cast<unsigned long>(i2cErrors_), static_cast<unsigned long>(scanUs_),
            static_cast<unsigned long>(scanMaxUs_));
    addMask(held_);
    if (faultCode_) tx_.add(",\"fault\":\"%s\"", faultCode_);
    tx_.add("}");
    if (cache) cacheReply(); else emit();
  }
  void cacheReply() {
    if (!tx_.valid) return;
    std::memcpy(reply_, tx_.data, tx_.size + 1);
    replyPending_ = !emit();
  }
  void error(const char *code, uint32_t id = 0, bool cache = false) {
    base("error");
    if (id) tx_.add(",\"id\":%lu", static_cast<unsigned long>(id));
    tx_.add(",\"code\":\"%s\"", code);
    addState();
    tx_.add("}");
    if (cache) cacheReply(); else emit();
  }
  void invalid(const char *code) {
    if (!invalidSent_ || elapsed(now_, lastInvalid_) >= 250) {
      lastInvalid_ = now_;
      invalidSent_ = true;
      error(code);
    }
  }
  void expirePartial(uint32_t now) {
    if (length_ && !discard_ && elapsed(now, lastByte_) >= 1000) {
      discard_ = true;
      invalid("invalid_frame");
    }
  }
  void resetInput() {
    state_ = Idle;
    mask_ = Mask{};
    finish_ = Mask{};
    held_ = Mask{};
    eventHead_ = eventCount_ = 0;
    seq_ = acked_ = sentSeq_ = 0;
    candidate_ = -1;
    clearSeen_ = readyAnnounced_ = false;
    hw_.release(hw_.data);
  }
  void fail(const char *code) {
    resetInput();
    state_ = Fault;
    faultCode_ = code;
    if (std::strcmp(code, "i2c_error") == 0) { ready_ = false; ++i2cErrors_; }
    if (open_) {
      base("fault");
      tx_.add(",\"code\":\"%s\"", code);
      addState();
      tx_.add("}");
      emit();
    }
  }
  bool readMask(const char *name, Mask &out) {
    const int index = json_.field(name);
    if (index < 0 || json_.tokens[index].kind != CommandJson::Array) return false;
    int previous = -1;
    for (size_t i = static_cast<size_t>(index) + 1; i < json_.tokens[index].next; i = json_.tokens[i].next) {
      const auto &pair = json_.tokens[i];
      if (pair.kind != CommandJson::Array || pair.next != i + 3 ||
          json_.tokens[i + 1].kind != CommandJson::Number || !json_.hexString(i + 2, 8)) return false;
      const uint32_t col = json_.tokens[i + 1].number;
      if (col >= 20 || static_cast<int>(col) <= previous) return false;
      uint32_t bits = 0;
      for (size_t k = json_.tokens[i + 2].begin; k < json_.tokens[i + 2].end; ++k) {
        const char c = json_.text[k];
        bits = (bits << 4) | static_cast<unsigned>(c <= '9' ? c - '0' : c - 'a' + 10);
      }
      if (bits == 0 || bits > kFullRows) return false;
      out.cols[col] = bits;
      previous = static_cast<int>(col);
    }
    return true;
  }
  bool schema(const char *type) {
    static const char *const common[] = {"v", "type", "boot", "session", "id"};
    static const char *const stop[] = {"v", "type", "boot", "session", "id", "context"};
    static const char *const ack[] = {"v", "type", "boot", "session", "context", "seq"};
    static const char *const input[] = {"v", "type", "boot", "session", "id", "context", "mode", "mask", "finish"};
    if (std::strcmp(type, "SET_INPUT") == 0) return json_.only(input, 9);
    if (std::strcmp(type, "STOP") == 0) return json_.only(stop, 6);
    if (std::strcmp(type, "ACK") == 0) return json_.only(ack, 6);
    return json_.only(common, 5);
  }
  void handleLine() {
    if (std::strcmp(rx_, "PING") == 0) {
      info();
      return;
    }
    if (!json_.parse(rx_)) { invalid("invalid_frame"); return; }
    uint32_t version = 0, id = 0;
    if (!json_.uintValue("v", version) || version != 2) { invalid("unsupported_version"); return; }
    if (!json_.string("boot", boot_)) { invalid("wrong_boot"); return; }
    char session[17]{};
    if (!json_.copyHex("session", session, 16)) { invalid("invalid_frame"); return; }
    const char *type = nullptr;
    for (const char *name : {"HELLO", "SET_INPUT", "STOP", "PING", "ACK"})
      if (json_.string("type", name)) type = name;
    if (!type) { invalid("invalid_frame"); return; }
    const bool hello = std::strcmp(type, "HELLO") == 0;
    const bool ack = std::strcmp(type, "ACK") == 0;
    if (!hello && (!open_ || std::strcmp(session, session_) != 0)) { invalid("wrong_session"); return; }
    if (!ack && (!json_.uintValue("id", id) || id == 0)) { invalid("invalid_frame"); return; }
    if (hello && std::strcmp(session, session_) != 0) {
      if (id != 1 || !schema(type)) { invalid("invalid_frame"); return; }
      resetInput();
      context_ = lastId_ = 0;
      reply_[0] = lastCommand_[0] = '\0';
      replyPending_ = false;
      std::memcpy(session_, session, 17);
      open_ = true;
      if (!ready_) ready_ = hw_.init(hw_.data);
      faultCode_ = ready_ ? nullptr : "i2c_error";
      state_ = ready_ ? Idle : Fault;
    } else if (hello && !open_) { invalid("wrong_session"); return; }
    if (ack) { acknowledge(); return; }
    if (id < lastId_) { error("stale_request", id); return; }
    if (id == lastId_) {
      if (std::strcmp(rx_, lastCommand_) != 0) { error("id_conflict", id); return; }
      lastHost_ = now_;
      replyPending_ = !hw_.send(hw_.data, reply_, std::strlen(reply_));
      return;
    }
    lastId_ = id;
    std::memcpy(lastCommand_, rx_, std::strlen(rx_) + 1);
    uint32_t requestedContext = 0;
    if (std::strcmp(type, "SET_INPUT") == 0 && json_.uintValue("context", requestedContext) &&
        requestedContext > 0 && requestedContext <= context_) {
      error("stale_context", id, true);
      return;
    }
    if (!schema(type)) {
      if (std::strcmp(type, "SET_INPUT") == 0) resetInput();
      error("invalid_frame", id, true);
      return;
    }
    if (hello) {
      lastHost_ = now_;
      base("hello");
      tx_.add(",\"id\":%lu,\"protocol\":\"board_scan_usb_v2\",\"firmware\":\"%s\","
              "\"mapping_id\":\"%s\",\"rows\":30,\"cols\":20,\"max_frame\":2048,\"event_capacity\":32",
              static_cast<unsigned long>(id), kFirmware, kMapping);
      addState();
      tx_.add("}");
      cacheReply();
    } else if (std::strcmp(type, "PING") == 0) {
      lastHost_ = now_;
      status(id, true);
    } else if (std::strcmp(type, "SET_INPUT") == 0) {
      setInput(id);
    } else {
      stop(id);
    }
  }
  void setInput(uint32_t id) {
    uint32_t context = 0;
    if (!json_.uintValue("context", context) || context == 0) {
      resetInput(); error("invalid_frame", id, true); return;
    }
    if (context <= context_) { error("stale_context", id, true); return; }
    Mask mask, finish;
    const bool stream = json_.string("mode", "stream");
    bool valid = stream || json_.string("mode", "single");
    valid = readMask("mask", mask) && readMask("finish", finish) && valid;
    for (unsigned col = 0; col < 20; ++col) valid = valid && ((finish.cols[col] & ~mask.cols[col]) == 0);
    if (!stream && !finish.empty()) valid = false;
    resetInput();
    context_ = context;
    if (!valid) { error("invalid_mask", id, true); return; }
    if (!ready_) { state_ = Fault; error("not_ready", id, true); return; }
    mask_ = mask;
    finish_ = finish;
    stream_ = stream;
    faultCode_ = nullptr;
    state_ = mask.empty() ? Idle : Waiting;
    lastHost_ = now_;
    base("input_set");
    tx_.add(",\"id\":%lu", static_cast<unsigned long>(id));
    addState();
    tx_.add("}");
    cacheReply();
  }
  void stop(uint32_t id) {
    uint32_t context = 0;
    if (!json_.uintValue("context", context) || context == 0) { error("invalid_frame", id, true); return; }
    if (context != context_) { error("stale_context", id, true); return; }
    resetInput();
    lastHost_ = now_;
    base("stopped");
    tx_.add(",\"id\":%lu", static_cast<unsigned long>(id));
    addState();
    tx_.add("}");
    cacheReply();
  }
  void acknowledge() {
    uint32_t context = 0, seq = 0;
    if (!schema("ACK") || !json_.uintValue("context", context) || !json_.uintValue("seq", seq) || seq == 0) {
      invalid("invalid_frame"); return;
    }
    if (context != context_) { invalid("stale_context"); return; }
    if (seq > sentSeq_) { invalid("invalid_ack"); return; }
    lastHost_ = now_;
    if (seq <= acked_) return;
    acked_ = seq;
    ackProgress_ = now_;
    while (eventCount_ && events_[eventHead_].seq <= seq) {
      eventHead_ = (eventHead_ + 1) % 32;
      --eventCount_;
    }
  }
  void sample() {
    Mask sample;
    const uint32_t started = hw_.micros ? hw_.micros(hw_.data) : 0;
    const bool ok = hw_.scan(hw_.data, mask_, sample);
    if (hw_.micros) {
      scanUs_ = hw_.micros(hw_.data) - started;
      if (scanUs_ > scanMaxUs_) scanMaxUs_ = scanUs_;
    }
    if (!ok) { fail("i2c_error"); return; }
    held_ = sample;
    unsigned count = 0;
    int cell = -1;
    for (unsigned col = 0; col < 20; ++col) {
      for (unsigned row = 0; row < 30; ++row) {
        if (!sample.contains(col, row)) continue;
        ++count;
        cell = static_cast<int>(col * 30 + row);
      }
    }
    if (state_ == Waiting) {
      if (count) clearSeen_ = false;
      else if (!clearSeen_) { clearSeen_ = true; releaseSince_ = now_; }
      else if (elapsed(now_, releaseSince_) >= kDebounceMs) {
        state_ = Scanning;
        candidate_ = -1;
        if (open_ && !readyAnnounced_) {
          readyAnnounced_ = true;
          base("input_ready"); addState(); tx_.add("}"); emit();
        }
      }
      return;
    }
    if (count > 1) {
      state_ = Waiting; clearSeen_ = false; candidate_ = -1;
      return;
    }
    if (count == 0) { candidate_ = -1; return; }
    if (candidate_ != cell) { candidate_ = cell; candidateSince_ = now_; return; }
    if (elapsed(now_, candidateSince_) < kDebounceMs) return;
    const unsigned col = static_cast<unsigned>(cell / 30), row = static_cast<unsigned>(cell % 30);
    const bool final = !stream_ || finish_.contains(col, row);
    if (eventCount_ == 32) { fail("event_overflow"); return; }
    if (seq_ == UINT32_MAX) { fail("sequence_exhausted"); return; }
    if (!eventCount_) ackProgress_ = now_;
    Event &event = events_[(eventHead_ + eventCount_) % 32];
    event = Event{};
    event.seq = ++seq_; event.at = now_;
    event.col = static_cast<uint8_t>(col); event.row = static_cast<uint8_t>(row);
    event.final = final;
    ++eventCount_;
    state_ = final ? Completed : Waiting;
    candidate_ = -1;
    clearSeen_ = false;
  }
  bool sendEvent(Event &event) {
    base("press");
    tx_.add(",\"context\":%lu,\"seq\":%lu,\"col\":%u,\"row\":%u,\"final\":%s,\"uptime_ms\":%lu}",
            static_cast<unsigned long>(context_), static_cast<unsigned long>(event.seq),
            event.col, event.row, event.final ? "true" : "false", static_cast<unsigned long>(event.at));
    if (!emit()) return false;
    event.sent = true;
    event.sentAt = now_;
    if (event.seq > sentSeq_) sentSeq_ = event.seq;
    return true;
  }
  void sendEvents() {
    for (unsigned n = 0; n < eventCount_; ++n) {
      Event &event = events_[(eventHead_ + n) % 32];
      if (!event.sent && !sendEvent(event)) return;
    }
    if (eventCount_) {
      Event &oldest = events_[eventHead_];
      if (oldest.sent && elapsed(now_, oldest.sentAt) >= 250) sendEvent(oldest);
    }
  }
};

}  // namespace board_v2

#include <assert.h>
#include <stdio.h>
#include <string.h>

#include "../chips/dfplayer-mock.chip.c"

static uart_config_t registered_uart;
static timer_config_t registered_timer;
static uint8_t transmitted[DFPLAYER_FRAME_SIZE];
static uint32_t transmitted_count;
static uint32_t scheduled_micros;
static uint32_t timer_start_count;
static uint32_t timer_stop_count;
static bool fake_timer_pending;

void timer_start_ns_d(timer_t timer, double nanos, bool repeat) {
  (void)timer;
  (void)nanos;
  (void)repeat;
}

double get_sim_nanos_d(void) {
  return 0.0;
}

pin_t pin_init(const char *name, uint32_t mode) {
  (void)mode;
  if (strcmp(name, "RX") == 0) return 10;
  if (strcmp(name, "TX") == 0) return 11;
  assert(!"unexpected mock pin");
  return NO_PIN;
}

uint32_t attr_init(const char *name, uint32_t default_value) {
  assert(strcmp(name, "completionDelayMs") == 0);
  assert(default_value == 2000);
  return 1;
}

uint32_t attr_read(uint32_t attr) {
  assert(attr == 1);
  return 2000;
}

uart_dev_t uart_init(const uart_config_t *config) {
  registered_uart = *config;
  return 7;
}

timer_t timer_init(const timer_config_t *config) {
  registered_timer = *config;
  return 9;
}

void timer_start(const timer_t timer, uint32_t micros, bool repeat) {
  assert(timer == 9);
  assert(!repeat);
  scheduled_micros = micros;
  ++timer_start_count;
  fake_timer_pending = true;
}

void timer_stop(const timer_t timer) {
  assert(timer == 9);
  ++timer_stop_count;
  fake_timer_pending = false;
}

bool uart_write(uart_dev_t uart, uint8_t *buffer, uint32_t count) {
  assert(uart == 7);
  assert(count == DFPLAYER_FRAME_SIZE);
  memcpy(transmitted, buffer, count);
  transmitted_count = count;
  return true;
}

static void update_frame_checksum(uint8_t frame[DFPLAYER_FRAME_SIZE]) {
  uint16_t checksum = frame_checksum(frame);
  frame[7] = (uint8_t)(checksum >> 8);
  frame[8] = (uint8_t)checksum;
}

static void make_frame(uint8_t command, uint16_t parameter, uint8_t frame[DFPLAYER_FRAME_SIZE]) {
  frame[0] = 0x7E;
  frame[1] = 0xFF;
  frame[2] = 0x06;
  frame[3] = command;
  frame[4] = 0;
  frame[5] = (uint8_t)(parameter >> 8);
  frame[6] = (uint8_t)parameter;
  frame[9] = 0xEF;
  update_frame_checksum(frame);
}

static void send_frame(const uint8_t frame[DFPLAYER_FRAME_SIZE]) {
  for (uint8_t i = 0; i < DFPLAYER_FRAME_SIZE; ++i) {
    registered_uart.rx_data(registered_uart.user_data, frame[i]);
  }
}

static void test_protocol_commands_and_validation(void) {
  uint8_t frame[DFPLAYER_FRAME_SIZE];
  make_frame(0x12, 1, frame);
  frame[8] ^= 0x01; // invalid checksum
  send_frame(frame);
  assert(current_track == 0);
  assert(!completion_pending);

  make_frame(0x12, 1, frame);
  frame[0] = 0x00; // invalid header
  send_frame(frame);
  assert(current_track == 0);

  make_frame(0x12, 1, frame);
  frame[2] = 0x05; // malformed length
  send_frame(frame);
  assert(current_track == 0);

  make_frame(0x12, 1, frame);
  frame[9] = 0x00; // invalid terminator
  send_frame(frame);
  assert(current_track == 0);

  make_frame(0x06, 3, frame);
  send_frame(frame);
  assert(current_volume == 3);

  make_frame(0x06, 0x0104, frame); // big-endian high byte must not be treated as volume
  send_frame(frame);
  assert(current_volume == 3);

  make_frame(0x99, 1, frame); // valid frame, unsupported command
  send_frame(frame);
  assert(current_volume == 3);
  assert(current_track == 0);

  make_frame(0x12, 0x0101, frame); // high parameter byte makes track invalid
  send_frame(frame);
  assert(current_track == 0);
  assert(!completion_pending);
}

static void test_payload_header_does_not_restart_candidate(void) {
  uint8_t frame[DFPLAYER_FRAME_SIZE];
  make_frame(0x06, 4, frame);
  frame[4] = 0x7E; // a payload byte is not a new frame until the candidate is invalid
  update_frame_checksum(frame);
  assert(valid_frame(frame));
  send_frame(frame);
  assert(current_volume == 4);
  assert(received_count == 0);
}

static void test_truncated_prefix_recovers_valid_play_frame(void) {
  const uint8_t truncated_prefix[] = {0x7E, 0xFF, 0x06, 0x12, 0x00};
  for (uint8_t i = 0; i < sizeof(truncated_prefix); ++i) {
    registered_uart.rx_data(registered_uart.user_data, truncated_prefix[i]);
  }
  assert(received_count == sizeof(truncated_prefix));
  assert(current_track == 0);

  uint8_t frame[DFPLAYER_FRAME_SIZE];
  make_frame(0x12, 3, frame);
  send_frame(frame);
  assert(current_track == 3);
  assert(last_track == 3);
  assert(completion_pending);
  assert(fake_timer_pending);

  make_frame(0x16, 0, frame);
  send_frame(frame);
  assert(current_track == 0);
  assert(!completion_pending);
  assert(!fake_timer_pending);
}

static void test_fragmented_play_completion_and_checksum(void) {
  uint8_t frame[DFPLAYER_FRAME_SIZE];
  make_frame(0x12, 1, frame);
  for (uint8_t i = 0; i < 4; ++i) {
    registered_uart.rx_data(registered_uart.user_data, frame[i]);
  }
  assert(current_track == 0); // fragmented prefix is not parsed prematurely
  for (uint8_t i = 4; i < DFPLAYER_FRAME_SIZE; ++i) {
    registered_uart.rx_data(registered_uart.user_data, frame[i]);
  }

  assert(current_track == 1);
  assert(last_track == 1);
  assert(completion_pending);
  assert(fake_timer_pending);
  assert(scheduled_micros == 2000000UL);

  transmitted_count = 0;
  fake_timer_pending = false; // the one-shot timer has fired
  registered_timer.callback(registered_timer.user_data);
  const uint8_t expected[DFPLAYER_FRAME_SIZE] = {
    0x7E, 0xFF, 0x06, 0x3D, 0x00, 0x00, 0x01, 0xFE, 0xBD, 0xEF
  };
  assert(transmitted_count == DFPLAYER_FRAME_SIZE);
  assert(memcmp(transmitted, expected, sizeof(expected)) == 0);
  assert(valid_frame(transmitted));
  assert(last_completed_track == 1);
  assert(current_track == 0);
  assert(!completion_pending);
  assert(!fake_timer_pending);
}

static void test_stop_cancels_completion_and_is_idempotent(void) {
  uint8_t frame[DFPLAYER_FRAME_SIZE];
  make_frame(0x12, 2, frame);
  send_frame(frame);
  assert(current_track == 2);
  assert(completion_pending);
  assert(fake_timer_pending);

  transmitted_count = 0;
  make_frame(0x16, 0, frame);
  send_frame(frame);
  assert(current_track == 0);
  assert(!completion_pending);
  assert(!fake_timer_pending);
  uint32_t starts_after_stop = timer_start_count;
  uint32_t stops_after_stop = timer_stop_count;

  // A callback racing with Stop is harmless after cancellation.
  registered_timer.callback(registered_timer.user_data);
  assert(transmitted_count == 0);
  assert(timer_start_count == starts_after_stop);

  send_frame(frame); // repeated Stop remains harmless
  assert(current_track == 0);
  assert(!completion_pending);
  assert(timer_stop_count > stops_after_stop);
}

static void test_supported_tracks_complete_and_invalid_tracks_are_rejected(void) {
  uint8_t frame[DFPLAYER_FRAME_SIZE];
  assert(AUDIO_MAX_TRACK == 7U);

  for (uint8_t track = AUDIO_FIRST_CUE_TRACK; track <= AUDIO_MAX_TRACK; ++track) {
    make_frame(0x12, track, frame);
    send_frame(frame);
    assert(current_track == track);
    assert(last_track == track);
    assert(completion_pending);
    assert(fake_timer_pending);
    assert(scheduled_micros == 2000000UL);

    transmitted_count = 0;
    fake_timer_pending = false;
    registered_timer.callback(registered_timer.user_data);
    assert(transmitted_count == DFPLAYER_FRAME_SIZE);
    assert(valid_frame(transmitted));
    assert(transmitted[3] == DFPLAYER_EVENT_PLAY_FINISHED);
    assert(transmitted[6] == track);
    assert(last_completed_track == track);
    assert(current_track == 0);
    assert(!completion_pending);
    assert(!fake_timer_pending);
  }

  // Track 5 remains a supported existing file; 6 and 7 also finish normally.
  assert(last_completed_track == AUDIO_MAX_TRACK);
  for (uint16_t invalid_track = 0U; invalid_track <= AUDIO_MAX_TRACK + 1U;
       invalid_track += AUDIO_MAX_TRACK + 1U) {
    make_frame(0x12, invalid_track, frame);
    send_frame(frame);
    assert(current_track == 0);
    assert(last_track == AUDIO_MAX_TRACK);
    assert(!completion_pending);
    assert(!fake_timer_pending);
  }

  make_frame(0x12, 0x0101U, frame); // high parameter byte remains invalid
  send_frame(frame);
  assert(current_track == 0);
  assert(last_track == AUDIO_MAX_TRACK);
  assert(!completion_pending);
}

int main(void) {
  chip_init();
  assert(registered_uart.baud_rate == 9600);
  assert(registered_uart.rx == 10);
  assert(registered_uart.tx == 11);
  assert(registered_uart.rx_data != NULL);
  assert(registered_timer.callback != NULL);

  test_protocol_commands_and_validation();
  test_payload_header_does_not_restart_candidate();
  test_truncated_prefix_recovers_valid_play_frame();
  test_fragmented_play_completion_and_checksum();
  test_stop_cancels_completion_and_is_idempotent();
  test_supported_tracks_complete_and_invalid_tracks_are_rejected();
  puts("DFPlayer mock protocol tests passed");
  return 0;
}

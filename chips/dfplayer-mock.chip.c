#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#include "wokwi-api.h"
#include "../audio_track_config.h"

#define DFPLAYER_FRAME_SIZE 10
#define DFPLAYER_EVENT_PLAY_FINISHED 0x3D

static uart_dev_t dfplayer_uart;
static timer_t completion_timer;
static uint32_t completion_delay_attribute;
static uart_config_t uart_config;
static timer_config_t timer_config;
static uint8_t received_frame[DFPLAYER_FRAME_SIZE];
static uint8_t received_count;
static uint8_t event_frame[DFPLAYER_FRAME_SIZE];
static uint8_t current_volume;
static uint8_t current_track;
static uint8_t last_track;
static uint8_t last_completed_track;
static uint8_t pending_track;
static bool completion_pending;

static uint16_t frame_checksum(const uint8_t frame[DFPLAYER_FRAME_SIZE]) {
  uint16_t sum = 0;
  for (uint8_t i = 1; i <= 6; ++i) sum = (uint16_t)(sum + frame[i]);
  return (uint16_t)(0U - sum);
}

static bool valid_frame(const uint8_t frame[DFPLAYER_FRAME_SIZE]) {
  if (frame[0] != 0x7E || frame[1] != 0xFF || frame[2] != 0x06 || frame[9] != 0xEF) {
    return false;
  }
  uint16_t actual = ((uint16_t)frame[7] << 8) | frame[8];
  return actual == frame_checksum(frame);
}

static void encode_frame(uint8_t command, uint16_t parameter, uint8_t frame[DFPLAYER_FRAME_SIZE]) {
  frame[0] = 0x7E;
  frame[1] = 0xFF;
  frame[2] = 0x06;
  frame[3] = command;
  frame[4] = 0x00; // no ACK requested by DFRobotDFPlayerMini
  frame[5] = (uint8_t)(parameter >> 8);
  frame[6] = (uint8_t)parameter;
  uint16_t checksum = frame_checksum(frame);
  frame[7] = (uint8_t)(checksum >> 8);
  frame[8] = (uint8_t)checksum;
  frame[9] = 0xEF;
}

static void cancel_completion(void) {
  timer_stop(completion_timer);
  completion_pending = false;
  pending_track = 0;
}

static void schedule_completion(uint8_t track) {
  cancel_completion();
  pending_track = track;
  completion_pending = true;
  uint32_t delay_ms = attr_read(completion_delay_attribute);
  if (delay_ms == 0) delay_ms = 1;
  timer_start(completion_timer, delay_ms * 1000UL, false);
}

static void on_completion_timer(void *user_data) {
  (void)user_data;
  if (!completion_pending || pending_track == 0 || current_track != pending_track) return;

  encode_frame(DFPLAYER_EVENT_PLAY_FINISHED, pending_track, event_frame);
  if (!uart_write(dfplayer_uart, event_frame, DFPLAYER_FRAME_SIZE)) {
    timer_start(completion_timer, 1000, false);
    return;
  }
  last_completed_track = pending_track;
  current_track = 0;
  pending_track = 0;
  completion_pending = false;
}

static void handle_command(const uint8_t frame[DFPLAYER_FRAME_SIZE]) {
  uint16_t parameter = ((uint16_t)frame[5] << 8) | frame[6];
  switch (frame[3]) {
    case 0x06: // volume(0..30)
      if (frame[5] == 0 && frame[6] <= 30) current_volume = frame[6];
      break;

    case 0x12: // playMp3Folder(1..AUDIO_MAX_TRACK)
      if (frame[5] == 0 && frame[6] >= AUDIO_FIRST_CUE_TRACK && frame[6] <= AUDIO_MAX_TRACK) {
        cancel_completion();
        current_track = frame[6];
        last_track = current_track;
        schedule_completion(current_track);
      }
      break;

    case 0x16: // stop()
      if (parameter == 0) {
        cancel_completion();
        current_track = 0;
      }
      break;

    default:
      // Valid but unsupported DFPlayer commands have no modeled effect.
      break;
  }
}

static void retain_candidate_suffix(void) {
  uint8_t start = 1;
  while (start < DFPLAYER_FRAME_SIZE && received_frame[start] != 0x7E) ++start;

  if (start == DFPLAYER_FRAME_SIZE) {
    received_count = 0;
    return;
  }

  received_count = (uint8_t)(DFPLAYER_FRAME_SIZE - start);
  memmove(received_frame, received_frame + start, received_count);
}

static void on_uart_rx(void *user_data, uint8_t byte) {
  (void)user_data;
  if (received_count == 0) {
    if (byte == 0x7E) received_frame[received_count++] = byte;
    return;
  }

  received_frame[received_count++] = byte;
  if (received_count == DFPLAYER_FRAME_SIZE) {
    if (valid_frame(received_frame)) {
      handle_command(received_frame);
      received_count = 0;
    } else {
      // Only inspect for another header after this full candidate has failed.
      // A 0x7E in a valid frame's payload must not restart parsing prematurely.
      retain_candidate_suffix();
    }
  }
}

void chip_init(void) {
  current_volume = 0;
  current_track = 0;
  last_track = 0;
  last_completed_track = 0;
  pending_track = 0;
  completion_pending = false;
  received_count = 0;
  completion_delay_attribute = attr_init("completionDelayMs", 2000);

  uart_config.user_data = NULL;
  uart_config.rx = pin_init("RX", INPUT);
  uart_config.tx = pin_init("TX", INPUT_PULLUP);
  uart_config.baud_rate = 9600;
  uart_config.rx_data = on_uart_rx;
  uart_config.write_done = NULL;
  memset(uart_config.reserved, 0, sizeof(uart_config.reserved));
  dfplayer_uart = uart_init(&uart_config);

  timer_config.user_data = NULL;
  timer_config.callback = on_completion_timer;
  memset(timer_config.reserved, 0, sizeof(timer_config.reserved));
  completion_timer = timer_init(&timer_config);
}

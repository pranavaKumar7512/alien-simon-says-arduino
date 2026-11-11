#ifndef AUDIO_TRACK_CONFIG_H
#define AUDIO_TRACK_CONFIG_H

#include <stdbool.h>
#include <stdint.h>

#define AUDIO_FIRST_CUE_TRACK 1U
#define AUDIO_LAST_CUE_TRACK 4U
#define AUDIO_GAME_OVER_LOSS_TRACK 5U
#define AUDIO_MAX_TRACK AUDIO_GAME_OVER_LOSS_TRACK

static inline uint8_t gameOverAudioTrack(bool playerLost, uint8_t randomTrack) {
  if (playerLost) return AUDIO_GAME_OVER_LOSS_TRACK;
  return randomTrack >= AUDIO_FIRST_CUE_TRACK && randomTrack <= AUDIO_LAST_CUE_TRACK
      ? randomTrack
      : AUDIO_FIRST_CUE_TRACK;
}

#endif

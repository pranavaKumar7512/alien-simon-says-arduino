#ifndef AUDIO_TRACK_CONFIG_H
#define AUDIO_TRACK_CONFIG_H

#include <stdbool.h>
#include <stdint.h>

// Files on the card, in /mp3, played by number with playMp3Folder(n). Each name must
// start with its 4-digit track number; the text after it is only a label.
//   1 0001-button1.mp3  2 0002-button2.mp3  3 0003-button3.mp3  4 0004-button4.mp3
//   5 0005-spare.mp3 (unused)  6 0006-celebration.mp3  7 0007-losing.mp3
#define AUDIO_FIRST_CUE_TRACK 1U
#define AUDIO_LAST_CUE_TRACK 4U
#define AUDIO_ROUND_CELEBRATION_TRACK 6U
#define AUDIO_GAME_OVER_LOSS_TRACK 7U
#define AUDIO_MAX_TRACK AUDIO_GAME_OVER_LOSS_TRACK

static inline uint8_t gameOverAudioTrack(bool playerLost, uint8_t randomTrack) {
  if (playerLost) return AUDIO_GAME_OVER_LOSS_TRACK;
  return randomTrack >= AUDIO_FIRST_CUE_TRACK && randomTrack <= AUDIO_LAST_CUE_TRACK
      ? randomTrack
      : AUDIO_FIRST_CUE_TRACK;
}

#endif

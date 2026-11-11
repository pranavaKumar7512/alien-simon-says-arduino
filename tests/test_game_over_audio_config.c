#include <assert.h>
#include <stdint.h>
#include <stdio.h>

#include "../audio_track_config.h"

int main(void) {
  assert(AUDIO_FIRST_CUE_TRACK == 1U);
  assert(AUDIO_LAST_CUE_TRACK == 4U);
  assert(AUDIO_GAME_OVER_LOSS_TRACK == 5U);
  assert(AUDIO_MAX_TRACK == AUDIO_GAME_OVER_LOSS_TRACK);
  assert(gameOverAudioTrack(true, 3U) == AUDIO_GAME_OVER_LOSS_TRACK);
  assert(gameOverAudioTrack(false, 3U) == 3U);
  assert(gameOverAudioTrack(false, 1U) == 1U);
  assert(gameOverAudioTrack(false, 0U) == AUDIO_FIRST_CUE_TRACK);
  assert(gameOverAudioTrack(false, 5U) == AUDIO_FIRST_CUE_TRACK);
  puts("Game Over audio track selection tests passed");
  return 0;
}

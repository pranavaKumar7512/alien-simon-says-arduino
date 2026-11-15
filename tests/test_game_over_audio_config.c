#include <assert.h>
#include <stdint.h>
#include <stdio.h>

#include "../audio_track_config.h"

int main(void) {
  assert(AUDIO_FIRST_CUE_TRACK == 1U);
  assert(AUDIO_LAST_CUE_TRACK == 4U);
  assert(AUDIO_ROUND_CELEBRATION_TRACK == 6U);
  assert(AUDIO_GAME_OVER_LOSS_TRACK == 7U);
  assert(AUDIO_MAX_TRACK == 7U);
  assert(AUDIO_MAX_TRACK == AUDIO_GAME_OVER_LOSS_TRACK);

  for (uint8_t cueTrack = AUDIO_FIRST_CUE_TRACK; cueTrack <= AUDIO_LAST_CUE_TRACK; ++cueTrack) {
    assert(gameOverAudioTrack(false, cueTrack) == cueTrack);
  }
  assert(gameOverAudioTrack(true, AUDIO_FIRST_CUE_TRACK) == AUDIO_GAME_OVER_LOSS_TRACK);
  assert(gameOverAudioTrack(true, AUDIO_LAST_CUE_TRACK) == AUDIO_GAME_OVER_LOSS_TRACK);
  assert(gameOverAudioTrack(false, 0U) == AUDIO_FIRST_CUE_TRACK);
  assert(gameOverAudioTrack(false, 5U) == AUDIO_FIRST_CUE_TRACK);
  assert(gameOverAudioTrack(false, AUDIO_ROUND_CELEBRATION_TRACK) == AUDIO_FIRST_CUE_TRACK);
  assert(gameOverAudioTrack(false, AUDIO_GAME_OVER_LOSS_TRACK) == AUDIO_FIRST_CUE_TRACK);
  assert(gameOverAudioTrack(false, UINT8_MAX) == AUDIO_FIRST_CUE_TRACK);
  puts("Game audio track selection tests passed");
  return 0;
}

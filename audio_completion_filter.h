#ifndef AUDIO_COMPLETION_FILTER_H
#define AUDIO_COMPLETION_FILTER_H

#include <stdbool.h>
#include <stdint.h>

static inline bool audioCompletionMatches(uint16_t eventTrack,
                                          uint8_t activeTrack,
                                          bool audioRunning,
                                          bool gameOver) {
  return audioRunning && !gameOver && activeTrack != 0 && eventTrack == activeTrack;
}

#endif

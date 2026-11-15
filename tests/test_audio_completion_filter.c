#include <assert.h>
#include <stdio.h>

#include "../audio_completion_filter.h"

int main(void) {
  assert(audioCompletionMatches(1, 1, true, false));
  assert(audioCompletionMatches(4, 4, true, false));
  assert(audioCompletionMatches(6, 6, true, false));
  assert(audioCompletionMatches(7, 7, true, false));
  assert(!audioCompletionMatches(6, 7, true, false));
  assert(!audioCompletionMatches(7, 6, true, false));
  assert(!audioCompletionMatches(1, 2, true, false));
  assert(!audioCompletionMatches(0, 1, true, false));
  assert(!audioCompletionMatches(1, 0, true, false));
  assert(!audioCompletionMatches(1, 1, false, false));
  assert(!audioCompletionMatches(1, 1, true, true)); // stale Game Over event for same track
  puts("Audio completion filter tests passed");
  return 0;
}

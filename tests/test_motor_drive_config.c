#include <assert.h>
#include <stdio.h>
#include <stdint.h>

#include "../alien-simon-says/motor_drive_config.h"

int main(void) {
  // Off during the servo lead and from the hard cap onward, even with no audio event.
  for (uint32_t t = 0; t < MOTOR_START_LEAD_MS; t++) assert(motorDriveDuty(t) == 0U);
  assert(motorDriveDuty(MOTOR_MAX_RUN_MS) == 0U);
  assert(motorDriveDuty(MOTOR_MAX_RUN_MS + 1000UL) == 0U);
  assert(!motorRunExpired(MOTOR_MAX_RUN_MS - 1UL));
  assert(motorRunExpired(MOTOR_MAX_RUN_MS));

  // Duty never exceeds the cap and the ramp is monotonic, ending at the cap.
  uint8_t last = 0U;
  for (uint32_t t = 0; t < MOTOR_MAX_RUN_MS; t++) {
    uint8_t d = motorDriveDuty(t);
    assert(d <= MOTOR_DUTY_MAX);
    assert(d >= last);
    last = d;
  }
  assert(last == MOTOR_DUTY_MAX);
  assert(motorDriveDuty(MOTOR_START_LEAD_MS + MOTOR_RAMP_MS) == MOTOR_DUTY_MAX);
  assert(motorDriveDuty(MOTOR_START_LEAD_MS + MOTOR_RAMP_MS / 2UL) > 0U);

  // The cap is shorter than the loss reaction's 7 s audio failsafe.
  assert(MOTOR_MAX_RUN_MS < 7000UL);
  puts("Motor drive config tests passed");
  return 0;
}

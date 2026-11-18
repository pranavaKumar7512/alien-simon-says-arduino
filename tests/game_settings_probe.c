// Probe used by test_game_settings.py: prints the effective value of every
// exposed setting. Compile with -DNO_SETTINGS to see the headers' own defaults.
#include <stdio.h>
#ifndef NO_SETTINGS
#include "../alien-simon-says/game_settings.h"
#endif
#include "../alien-simon-says/motor_drive_config.h"
#include "../alien-simon-says/player_led_feedback.h"
#include "../alien-simon-says/servo_celebration_config.h"

int main(void) {
  printf("MOTOR_START_LEAD_MS=%lu\n", (unsigned long)MOTOR_START_LEAD_MS);
  printf("MOTOR_RAMP_MS=%lu\n", (unsigned long)MOTOR_RAMP_MS);
  printf("MOTOR_MAX_RUN_MS=%lu\n", (unsigned long)MOTOR_MAX_RUN_MS);
  printf("MOTOR_DUTY_MAX=%u\n", (unsigned)MOTOR_DUTY_MAX);
  printf("PLAYER_LED_BRIGHTNESS=%u\n", (unsigned)PLAYER_LED_BRIGHTNESS);
  printf("SERVO_GAME_OVER_EXTEND_ANGLE=%u\n", (unsigned)SERVO_GAME_OVER_EXTEND_ANGLE);
  printf("SERVO_GAME_OVER_HOLD_MS=%lu\n", (unsigned long)SERVO_GAME_OVER_HOLD_MS);
  printf("SERVO_GAME_OVER_RETRACT_ALLOWANCE_MS=%lu\n",
         (unsigned long)SERVO_GAME_OVER_RETRACT_ALLOWANCE_MS);
  return 0;
}

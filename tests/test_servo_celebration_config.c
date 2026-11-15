#include <assert.h>
#include <stdio.h>

#include "../servo_celebration_config.h"

static uint16_t pulseTrace[2];
static uint8_t pulseTraceCount = 0;

static void recordServoPulse(uint16_t ticks) {
  assert(pulseTraceCount < 2U);
  pulseTrace[pulseTraceCount++] = ticks;
}

int main(void) {
#if defined(WOKWI_SIM)
  const uint8_t extendAngle = 180U;
#else
  const uint8_t extendAngle = 90U;
#endif

  // A successful round (or technical Game Over) must never extend the servo.
  assert(!servoWriteGameOverTargetIfLost(false, extendAngle, recordServoPulse));
  assert(pulseTraceCount == 0U);

  // The loss path emits exactly one extension target.
  assert(servoWriteGameOverTargetIfLost(true, extendAngle, recordServoPulse));
  assert(pulseTraceCount == 1U);
  assert(pulseTrace[0] == servoAngleToPulseTicks(extendAngle));
  assert(!servoWriteGameOverTargetIfLost(true, extendAngle, 0));
  assert(pulseTraceCount == 1U);

  assert(SERVO_PWM_CPU_HZ == 16000000UL);
  assert(SERVO_PWM_PRESCALER == 8UL);
  assert(SERVO_TIMER_TICKS_PER_US == 2U);
  assert(SERVO_PWM_FRAME_TICKS == 40000UL);
  assert(SERVO_PWM_FRAME_US == 20000UL);
  assert(SERVO_PWM_TOP_TICKS == 39999UL);
  assert(SERVO_DEFAULT_MIN_PULSE_US == 700U);
  assert(SERVO_DEFAULT_MAX_PULSE_US == 2300U);
  assert(servoAngleToPulseTicks(0U) == 1400U);   // 700 us * 2 Timer1 ticks/us
  assert(servoAngleToPulseTicks(90U) == 3000U);  // 1500 us * 2 Timer1 ticks/us
  assert(servoAngleToPulseTicks(180U) == 4600U); // 2300 us * 2 Timer1 ticks/us
  assert(servoAngleToPulseTicks(255U) == 4600U); // Angles above 180 degrees clamp.

  for (uint16_t angle = 0U; angle < 256U; ++angle) {
    const uint8_t boundedAngle = angle > 180U ? 180U : (uint8_t)angle;
    const uint16_t ticks = servoAngleToPulseTicks((uint8_t)angle);
    const uint32_t expectedPulseUs = SERVO_DEFAULT_MIN_PULSE_US +
        ((uint32_t)(SERVO_DEFAULT_MAX_PULSE_US - SERVO_DEFAULT_MIN_PULSE_US) *
         boundedAngle) / 180UL;
    assert(ticks == expectedPulseUs * SERVO_TIMER_TICKS_PER_US);
    assert(ticks >= SERVO_DEFAULT_MIN_PULSE_US * SERVO_TIMER_TICKS_PER_US);
    assert(ticks <= SERVO_DEFAULT_MAX_PULSE_US * SERVO_TIMER_TICKS_PER_US);
  }

#if defined(WOKWI_SIM)
  assert(SERVO_GAME_OVER_EXTEND_ANGLE == 180U);
  assert(SERVO_GAME_OVER_RETRACT_ANGLE == 0U);
  assert(SERVO_GAME_OVER_HOLD_MS == 3000UL);
  assert(SERVO_GAME_OVER_RETRACT_ALLOWANCE_MS == 3000UL);
  puts("Wokwi game-over servo config tests passed");
#else
  assert(SERVO_GAME_OVER_EXTEND_ANGLE == 90U);
  assert(SERVO_GAME_OVER_RETRACT_ANGLE == 0U);
  assert(SERVO_GAME_OVER_HOLD_MS == 1000UL);
  assert(SERVO_GAME_OVER_RETRACT_ALLOWANCE_MS == 1000UL);
  puts("Physical game-over servo config tests passed");
#endif
  return 0;
}

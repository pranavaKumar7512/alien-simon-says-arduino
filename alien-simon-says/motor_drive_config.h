#ifndef MOTOR_DRIVE_CONFIG_H
#define MOTOR_DRIVE_CONFIG_H

#include <stdint.h>

// Conservative first-power limits for the FIT0458 6 V motor on the shared 5 V rail.
// These bound motor current; they are not a verified supply or safety rating.
#define MOTOR_START_LEAD_MS 150UL   // servo extends first, so inrush peaks do not stack
#define MOTOR_RAMP_MS 300UL         // soft start from 0 to MOTOR_DUTY_MAX
#define MOTOR_MAX_RUN_MS 2500UL     // hard cap per loss, independent of audio length
#define MOTOR_DUTY_MAX 128U         // 50% of analogWrite range; raise only after bench tests

#if MOTOR_DUTY_MAX > 255
#error "MOTOR_DUTY_MAX exceeds analogWrite range"
#endif
#if MOTOR_START_LEAD_MS + MOTOR_RAMP_MS > MOTOR_MAX_RUN_MS
#error "Motor lead plus ramp must fit inside the run cap"
#endif

// PWM duty for M1A given milliseconds since the motor was commanded on.
// 0 before the lead delay and from the run cap onward.
static inline uint8_t motorDriveDuty(uint32_t sinceStartMs) {
  if (sinceStartMs < MOTOR_START_LEAD_MS || sinceStartMs >= MOTOR_MAX_RUN_MS) return 0U;
  uint32_t ramped = sinceStartMs - MOTOR_START_LEAD_MS;
  if (ramped >= MOTOR_RAMP_MS) return (uint8_t)MOTOR_DUTY_MAX;
  return (uint8_t)(((uint32_t)MOTOR_DUTY_MAX * (ramped + 1UL)) / MOTOR_RAMP_MS);
}

static inline uint8_t motorRunExpired(uint32_t sinceStartMs) {
  return sinceStartMs >= MOTOR_MAX_RUN_MS ? 1U : 0U;
}

#endif

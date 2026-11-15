#ifndef SERVO_GAME_OVER_CONFIG_H
#define SERVO_GAME_OVER_CONFIG_H

#if defined(WOKWI_SIM)
#define SERVO_GAME_OVER_EXTEND_ANGLE 180U
#define SERVO_GAME_OVER_RETRACT_ANGLE 0U
#define SERVO_GAME_OVER_HOLD_MS 3000UL
#define SERVO_GAME_OVER_RETRACT_ALLOWANCE_MS 3000UL
#else
#define SERVO_GAME_OVER_EXTEND_ANGLE 90U
#define SERVO_GAME_OVER_RETRACT_ANGLE 0U
#define SERVO_GAME_OVER_HOLD_MS 1000UL
#define SERVO_GAME_OVER_RETRACT_ALLOWANCE_MS 1000UL
#endif

#include <stdbool.h>
#include <stdint.h>

#define SERVO_DEFAULT_MIN_PULSE_US 700U
#define SERVO_DEFAULT_MAX_PULSE_US 2300U
#define SERVO_PWM_CPU_HZ 16000000UL
#define SERVO_PWM_PRESCALER 8UL
#define SERVO_TIMER_TICKS_PER_US 2U
#define SERVO_PWM_FRAME_TICKS 40000UL
#define SERVO_PWM_FRAME_US (SERVO_PWM_FRAME_TICKS * SERVO_PWM_PRESCALER / (SERVO_PWM_CPU_HZ / 1000000UL))
#define SERVO_PWM_TOP_TICKS (SERVO_PWM_FRAME_TICKS - 1UL)

static inline uint16_t servoAngleToPulseTicks(uint8_t angle) {
  if (angle > 180U) angle = 180U;
  const uint32_t pulseUs = SERVO_DEFAULT_MIN_PULSE_US +
    ((uint32_t)(SERVO_DEFAULT_MAX_PULSE_US - SERVO_DEFAULT_MIN_PULSE_US) * angle) / 180UL;
  return (uint16_t)(pulseUs * SERVO_TIMER_TICKS_PER_US);
}

typedef void (*ServoPulseWriter)(uint16_t ticks);

static inline uint8_t servoWriteGameOverTargetIfLost(bool playerLost, uint8_t angle,
                                                      ServoPulseWriter writePulse) {
  if (!playerLost || writePulse == 0) return 0;
  writePulse(servoAngleToPulseTicks(angle));
  return 1;
}

#endif

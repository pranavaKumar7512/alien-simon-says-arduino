#ifndef MOTOR_LOSS_REACTION_H
#define MOTOR_LOSS_REACTION_H

#include <stdbool.h>
#include <stdint.h>

#define MOTOR_LOSS_FAILSAFE_MS 7000UL

typedef enum {
  MOTOR_LOSS_IDLE = 0,
  MOTOR_LOSS_PLAYING,
  MOTOR_LOSS_RETURNING,
  MOTOR_LOSS_READY
} MotorLossPhase;

typedef struct {
  MotorLossPhase phase;
  uint32_t startedAt;
  uint32_t retractedAt;
  bool restartQueued;
} MotorLossReaction;

typedef struct {
  bool stopAudio;
  bool driveMotor;
  bool stopMotor;
  bool extendServo;
  bool retractServo;
  bool startGame;
} MotorLossActions;

static inline MotorLossActions motorLossNoActions(void) {
  MotorLossActions actions = {false, false, false, false, false, false};
  return actions;
}

static inline void motorLossReset(MotorLossReaction *reaction) {
  if (reaction == 0) return;
  reaction->phase = MOTOR_LOSS_IDLE;
  reaction->startedAt = 0U;
  reaction->retractedAt = 0U;
  reaction->restartQueued = false;
}

static inline MotorLossActions motorLossBegin(MotorLossReaction *reaction,
                                               uint32_t now,
                                               bool playerLost,
                                               bool audioReady) {
  MotorLossActions actions = motorLossNoActions();
  if (reaction == 0) return actions;
  motorLossReset(reaction);
  if (!playerLost) return actions;

  if (!audioReady) {
    reaction->phase = MOTOR_LOSS_RETURNING;
    reaction->retractedAt = now;
    actions.stopMotor = true;
    actions.retractServo = true;
    return actions;
  }

  reaction->phase = MOTOR_LOSS_PLAYING;
  reaction->startedAt = now;
  actions.driveMotor = true;
  actions.extendServo = true;
  return actions;
}

static inline MotorLossActions motorLossComplete(MotorLossReaction *reaction,
                                                  uint16_t eventTrack,
                                                  uint8_t lossTrack,
                                                  uint32_t now,
                                                  bool *accepted) {
  MotorLossActions actions = motorLossNoActions();
  if (accepted != 0) *accepted = false;
  if (reaction == 0 || reaction->phase != MOTOR_LOSS_PLAYING ||
      eventTrack != lossTrack) return actions;

  if (accepted != 0) *accepted = true;
  reaction->phase = MOTOR_LOSS_RETURNING;
  reaction->retractedAt = now;
  actions.stopMotor = true;
  actions.retractServo = true;
  return actions;
}

static inline MotorLossActions motorLossFail(MotorLossReaction *reaction,
                                              uint32_t now) {
  MotorLossActions actions = motorLossNoActions();
  if (reaction == 0 || reaction->phase != MOTOR_LOSS_PLAYING) return actions;
  reaction->phase = MOTOR_LOSS_RETURNING;
  reaction->retractedAt = now;
  actions.stopAudio = true;
  actions.stopMotor = true;
  actions.retractServo = true;
  return actions;
}

static inline MotorLossActions motorLossService(MotorLossReaction *reaction,
                                                 uint32_t now,
                                                 uint32_t returnAllowanceMs) {
  MotorLossActions actions = motorLossNoActions();
  if (reaction == 0) return actions;

  if (reaction->phase == MOTOR_LOSS_PLAYING &&
      (uint32_t)(now - reaction->startedAt) >= MOTOR_LOSS_FAILSAFE_MS) {
    return motorLossFail(reaction, now);
  }

  if (reaction->phase == MOTOR_LOSS_RETURNING &&
      (uint32_t)(now - reaction->retractedAt) >= returnAllowanceMs) {
    reaction->phase = MOTOR_LOSS_READY;
    if (reaction->restartQueued) {
      reaction->restartQueued = false;
      actions.startGame = true;
    }
  }
  return actions;
}

static inline MotorLossActions motorLossQueueRestart(MotorLossReaction *reaction,
                                                       uint32_t now) {
  MotorLossActions actions = motorLossNoActions();
  if (reaction == 0) return actions;
  reaction->restartQueued = true;
  if (reaction->phase == MOTOR_LOSS_PLAYING) {
    reaction->phase = MOTOR_LOSS_RETURNING;
    reaction->retractedAt = now;
    actions.stopAudio = true;
    actions.stopMotor = true;
    actions.retractServo = true;
  } else if (reaction->phase == MOTOR_LOSS_READY) {
    reaction->restartQueued = false;
    actions.startGame = true;
  }
  return actions;
}

// PWM/PWM inputs: 10 drives forward, 01 reverses; equal inputs (00 or 11) brake.
static inline void mdd3aForwardInputs(uint8_t *m1a, uint8_t *m1b) {
  if (m1a != 0) *m1a = 1U;
  if (m1b != 0) *m1b = 0U;
}

static inline void mdd3aStopInputs(uint8_t *m1a, uint8_t *m1b) {
  if (m1a != 0) *m1a = 0U;
  if (m1b != 0) *m1b = 0U;
}

static inline void mdd3aBrakeInputs(uint8_t *m1a, uint8_t *m1b) {
  if (m1a != 0) *m1a = 1U;
  if (m1b != 0) *m1b = 1U;
}

static inline bool mdd3aInputsStopped(uint8_t m1a, uint8_t m1b) {
  return m1a == 0U && m1b == 0U;
}

static inline bool mdd3aInputsBrake(uint8_t m1a, uint8_t m1b) {
  return (m1a != 0U) == (m1b != 0U);
}

static inline void mdd3aBridgeOutputs(uint8_t m1a, uint8_t m1b,
                                      uint8_t *outA, uint8_t *outB) {
  // Logic-level model: each bridge output follows its input.
  if (outA != 0) *outA = m1a != 0U ? 1U : 0U;
  if (outB != 0) *outB = m1b != 0U ? 1U : 0U;
}

#endif

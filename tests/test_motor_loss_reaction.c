#include <assert.h>
#include <stdio.h>
#include <stdint.h>

#include "../audio_completion_filter.h"
#include "../audio_track_config.h"
#include "../alien-simon-says/motor_loss_reaction.h"

static void test_only_the_new_loss_track_can_complete_the_reaction(void) {
  MotorLossReaction reaction;
  motorLossReset(&reaction);
  MotorLossActions actions = motorLossBegin(&reaction, 100U, true, true);
  assert(reaction.phase == MOTOR_LOSS_PLAYING);
  assert(actions.driveMotor && actions.extendServo);
  assert(!actions.stopMotor && !actions.retractServo && !actions.stopAudio);
  assert(AUDIO_GAME_OVER_LOSS_TRACK == 7U); // the physical SD card holds only tracks 6 and 7
  assert(AUDIO_ROUND_CELEBRATION_TRACK != AUDIO_GAME_OVER_LOSS_TRACK);
  assert(gameOverAudioTrack(true, 3U) == AUDIO_GAME_OVER_LOSS_TRACK);
  assert(audioCompletionMatches(AUDIO_GAME_OVER_LOSS_TRACK,
                                AUDIO_GAME_OVER_LOSS_TRACK, true, false));

  bool accepted = true;
  actions = motorLossComplete(&reaction, AUDIO_ROUND_CELEBRATION_TRACK,
                              AUDIO_GAME_OVER_LOSS_TRACK, 200U, &accepted);
  assert(!accepted);
  assert(reaction.phase == MOTOR_LOSS_PLAYING);
  assert(!actions.stopMotor && !actions.retractServo);

  // The DFPlayer event has no request ID: a delayed same-track event is
  // indistinguishable from a current completion and is intentionally accepted.
  actions = motorLossComplete(&reaction, AUDIO_GAME_OVER_LOSS_TRACK,
                              AUDIO_GAME_OVER_LOSS_TRACK, 600U, &accepted);
  assert(accepted);
  assert(reaction.phase == MOTOR_LOSS_RETURNING);
  assert(actions.stopMotor && actions.retractServo);
  assert(!actions.stopAudio);
}

static void test_completion_waits_only_for_servo_return_allowance(void) {
  MotorLossReaction reaction;
  motorLossReset(&reaction);
  (void)motorLossBegin(&reaction, 500U, true, true);
  bool accepted = false;
  (void)motorLossComplete(&reaction, AUDIO_GAME_OVER_LOSS_TRACK,
                          AUDIO_GAME_OVER_LOSS_TRACK, 5500U, &accepted);
  assert(accepted);
  assert(motorLossService(&reaction, 6499U, 1000U).startGame == false);
  assert(reaction.phase == MOTOR_LOSS_RETURNING);
  MotorLossActions actions = motorLossService(&reaction, 6500U, 1000U);
  assert(reaction.phase == MOTOR_LOSS_READY);
  assert(!actions.startGame);
}

static void test_audio_error_and_failed_initialization_fail_safe(void) {
  MotorLossReaction reaction;
  motorLossReset(&reaction);
  MotorLossActions actions = motorLossBegin(&reaction, 1000U, true, true);
  assert(actions.driveMotor && actions.extendServo);
  actions = motorLossFail(&reaction, 1200U);
  assert(reaction.phase == MOTOR_LOSS_RETURNING);
  assert(actions.stopAudio && actions.stopMotor && actions.retractServo);
  assert(!actions.driveMotor && !actions.extendServo);

  motorLossReset(&reaction);
  actions = motorLossBegin(&reaction, 2000U, true, false);
  assert(reaction.phase == MOTOR_LOSS_RETURNING);
  assert(!actions.driveMotor && !actions.extendServo);
  assert(actions.stopMotor && actions.retractServo);
  assert(!actions.stopAudio);
  actions = motorLossService(&reaction, 2999U, 1000U);
  assert(reaction.phase == MOTOR_LOSS_RETURNING && !actions.startGame);
  actions = motorLossService(&reaction, 3000U, 1000U);
  assert(reaction.phase == MOTOR_LOSS_READY && !actions.startGame);
}

static void test_watchdog_is_absolute_and_wrap_safe(void) {
  MotorLossReaction reaction;
  motorLossReset(&reaction);
  (void)motorLossBegin(&reaction, 1000U, true, true);
  MotorLossActions actions = motorLossService(&reaction,
      1000U + MOTOR_LOSS_FAILSAFE_MS - 1U, 1000U);
  assert(reaction.phase == MOTOR_LOSS_PLAYING);
  assert(!actions.stopAudio && !actions.stopMotor && !actions.retractServo);
  actions = motorLossService(&reaction, 1000U + MOTOR_LOSS_FAILSAFE_MS, 1000U);
  assert(reaction.phase == MOTOR_LOSS_RETURNING);
  assert(actions.stopAudio && actions.stopMotor && actions.retractServo);

  motorLossReset(&reaction);
  const uint32_t start = UINT32_MAX - 3000U;
  (void)motorLossBegin(&reaction, start, true, true);
  actions = motorLossService(&reaction, start + MOTOR_LOSS_FAILSAFE_MS - 1U, 1000U);
  assert(reaction.phase == MOTOR_LOSS_PLAYING);
  assert(!actions.stopMotor);
  actions = motorLossService(&reaction, start + MOTOR_LOSS_FAILSAFE_MS, 1000U);
  assert(reaction.phase == MOTOR_LOSS_RETURNING);
  assert(actions.stopAudio && actions.stopMotor && actions.retractServo);
}

static void test_start_interrupts_and_waits_for_return_allowance(void) {
  MotorLossReaction reaction;
  motorLossReset(&reaction);
  (void)motorLossBegin(&reaction, 100U, true, true);
  MotorLossActions actions = motorLossQueueRestart(&reaction, 250U);
  assert(reaction.phase == MOTOR_LOSS_RETURNING);
  assert(actions.stopAudio && actions.stopMotor && actions.retractServo);
  assert(!actions.startGame);
  actions = motorLossService(&reaction, 1249U, 1000U);
  assert(!actions.startGame);
  actions = motorLossService(&reaction, 1250U, 1000U);
  assert(reaction.phase == MOTOR_LOSS_READY);
  assert(actions.startGame);

  actions = motorLossQueueRestart(&reaction, 1300U);
  assert(actions.startGame);
  assert(!actions.stopMotor && !actions.retractServo);
}

static void test_non_loss_game_over_does_not_start_motor_reaction(void) {
  MotorLossReaction reaction;
  motorLossReset(&reaction);
  MotorLossActions actions = motorLossBegin(&reaction, 100U, false, true);
  assert(reaction.phase == MOTOR_LOSS_IDLE);
  assert(!actions.driveMotor && !actions.extendServo && !actions.retractServo);
  assert(gameOverAudioTrack(false, AUDIO_LAST_CUE_TRACK) == AUDIO_LAST_CUE_TRACK);
  assert(gameOverAudioTrack(false, AUDIO_LAST_CUE_TRACK) != AUDIO_GAME_OVER_LOSS_TRACK);
}

static void test_mdd3a_pwm_pwm_truth_table_and_brake_outputs(void) {
  uint8_t a = 0U;
  uint8_t b = 0U;
  uint8_t outA = 9U;
  uint8_t outB = 9U;
  mdd3aStopInputs(&a, &b);
  assert(a == 0U && b == 0U && mdd3aInputsStopped(a, b));
  assert(mdd3aInputsBrake(a, b)); // 00 brakes; it is not coast.
  mdd3aBridgeOutputs(a, b, &outA, &outB);
  assert(outA == 0U && outB == 0U);

  mdd3aForwardInputs(&a, &b);
  assert(a == 1U && b == 0U && !mdd3aInputsBrake(a, b));
  mdd3aBridgeOutputs(a, b, &outA, &outB);
  assert(outA == 1U && outB == 0U);

  mdd3aBridgeOutputs(0U, 1U, &outA, &outB);
  assert(outA == 0U && outB == 1U);
  assert(!mdd3aInputsBrake(0U, 1U));

  mdd3aBrakeInputs(&a, &b);
  assert(a == 1U && b == 1U && mdd3aInputsBrake(a, b));
  assert(!mdd3aInputsStopped(a, b));
  mdd3aBridgeOutputs(a, b, &outA, &outB);
  assert(outA == 1U && outB == 1U);
}

int main(void) {
  test_only_the_new_loss_track_can_complete_the_reaction();
  test_completion_waits_only_for_servo_return_allowance();
  test_audio_error_and_failed_initialization_fail_safe();
  test_watchdog_is_absolute_and_wrap_safe();
  test_start_interrupts_and_waits_for_return_allowance();
  test_non_loss_game_over_does_not_start_motor_reaction();
  test_mdd3a_pwm_pwm_truth_table_and_brake_outputs();
  puts("Motor loss reaction tests passed");
  return 0;
}

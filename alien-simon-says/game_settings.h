// =====================================================================
//  GAME SETTINGS - the one file you edit to tune the game.
//
//  HOW TO CHANGE A SETTING
//    1. Edit a value below and save this file.
//    2. Compile and upload the sketch again. The Uno cannot read this
//       file while running, so nothing changes until you re-upload.
//
//  RULES
//    - Keep the number and its suffix (U / UL) exactly as written.
//    - Values outside the allowed range stop the compile with an error.
//    - Pins, wiring, EEPROM layout, track numbers and LCD text are NOT
//      here on purpose: changing them can break the game or the hardware.
//    - Wokwi simulator runs use the same values except the servo, which
//      keeps its own simulator values. The automatic Wokwi test scenarios
//      assume the defaults below, so restore them before running those.
// =====================================================================
#ifndef GAME_SETTINGS_H
#define GAME_SETTINGS_H

// ---------------------------------------------------------------------
//  MOTOR (FIT0458 on the MDD3A driver, runs when the player loses)
//  The motor shares the 5 V supply with the strips and servo. Raise
//  power or run time only after bench tests, and never without a fuse.
// ---------------------------------------------------------------------
// Delay after the servo starts moving before the motor starts (ms).
// Keeps the servo and motor current peaks apart.
#define MOTOR_START_LEAD_MS 150UL
// Soft-start time from stopped to full power (ms). Longer = gentler.
#define MOTOR_RAMP_MS 300UL
// Hard stop: the motor never runs longer than this per loss (ms).
// Must be below 7000 and at least LEAD + RAMP.
#define MOTOR_MAX_RUN_MS 2500UL
// Motor power, 1-255. 128 = 50 %, 64 = 25 %, 255 = 100 %.
#define MOTOR_DUTY_MAX 128U

// ---------------------------------------------------------------------
//  LEDs
// ---------------------------------------------------------------------
// Brightness of the four player strips, 0-255. 64 = about 25 %.
// Higher values draw more current from the shared 5 V supply.
#define PLAYER_LED_BRIGHTNESS 64U

// ---------------------------------------------------------------------
//  SERVO (real rig only; the Wokwi simulator keeps its own values)
// ---------------------------------------------------------------------
#if !defined(WOKWI_SIM)
// Game Over arm position, 0-180 degrees. Raise in small steps and check
// the linkage first; the real travel is not confirmed by this number.
#define SERVO_GAME_OVER_EXTEND_ANGLE 90U
// Time the arm stays out (ms).
#define SERVO_GAME_OVER_HOLD_MS 1000UL
// Time allowed for the arm to return before the game continues (ms).
#define SERVO_GAME_OVER_RETRACT_ALLOWANCE_MS 1000UL
#endif

// ---------------------------------------------------------------------
//  AUDIO
// ---------------------------------------------------------------------
// MP3 module volume, 0-30. Start low on a real speaker.
#define SETTING_AUDIO_VOLUME 3U

// ---------------------------------------------------------------------
//  TIMING (all in milliseconds)
// ---------------------------------------------------------------------
// How long each colour of the sequence stays lit.
#define SETTING_SEQUENCE_CUE_MS 2000U
// Dark pause between sequence colours.
#define SETTING_CUE_GAP_MS 180U
// How long a pressed colour's strip stays dark as button feedback.
#define SETTING_BUTTON_FEEDBACK_DARK_MS 500U
// Shortest time the GAME OVER screen stays up.
#define SETTING_GAME_OVER_MIN_MS 3000UL
// How long each idle score page (YOUR / BEST) shows before switching.
#define SETTING_SCORE_PAGE_MS 3000UL

// ---------------------------------------------------------------------
//  Range checks: a bad value stops the compile instead of misbehaving.
// ---------------------------------------------------------------------
#if MOTOR_DUTY_MAX < 1 || MOTOR_DUTY_MAX > 255
#error "MOTOR_DUTY_MAX must be 1-255"
#endif
#if MOTOR_START_LEAD_MS + MOTOR_RAMP_MS > MOTOR_MAX_RUN_MS
#error "MOTOR_START_LEAD_MS + MOTOR_RAMP_MS must not exceed MOTOR_MAX_RUN_MS"
#endif
#if MOTOR_MAX_RUN_MS >= 7000
#error "MOTOR_MAX_RUN_MS must stay below the 7000 ms loss failsafe"
#endif
#if MOTOR_RAMP_MS < 1
#error "MOTOR_RAMP_MS must be at least 1"
#endif
#if PLAYER_LED_BRIGHTNESS > 255
#error "PLAYER_LED_BRIGHTNESS must be 0-255"
#endif
#if !defined(WOKWI_SIM)
#if SERVO_GAME_OVER_EXTEND_ANGLE > 180
#error "SERVO_GAME_OVER_EXTEND_ANGLE must be 0-180"
#endif
#if SERVO_GAME_OVER_HOLD_MS < 1 || SERVO_GAME_OVER_RETRACT_ALLOWANCE_MS < 1
#error "Servo hold and retract allowance must be at least 1 ms"
#endif
#endif
#if SETTING_AUDIO_VOLUME > 30
#error "SETTING_AUDIO_VOLUME must be 0-30"
#endif
#if SETTING_SEQUENCE_CUE_MS < 1 || SETTING_CUE_GAP_MS < 1
#error "Cue length and gap must be at least 1 ms"
#endif
#if SETTING_SEQUENCE_CUE_MS > 60000
#error "SETTING_SEQUENCE_CUE_MS is too long (max 60000)"
#endif
#if SETTING_GAME_OVER_MIN_MS < 1 || SETTING_SCORE_PAGE_MS < 1
#error "Game Over minimum and score page time must be at least 1 ms"
#endif

#endif

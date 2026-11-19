#include "wokwi-api.h"

// Visual-only: M1A/M1B are mirrored onto M1_OUT_A/M1_OUT_B so the motor chip can animate.
// No bridge, current, supply voltage, or the real board's truth table is modeled (the datasheet
// was not readable). Pin names follow the board's M1A/M1B inputs, logic GND, VB+/VB- supply, and
// motor-1 output terminals.
typedef struct {
  pin_t in_a, in_b, out_a, out_b;
} state_t;

static state_t s;

static void on_pin(void *ud, pin_t pin, uint32_t value) {
  (void)ud;
  pin_write(pin == s.in_a ? s.out_a : s.out_b, value);
}

void chip_init(void) {
  s.in_a = pin_init("M1A", INPUT);
  s.in_b = pin_init("M1B", INPUT);
  s.out_a = pin_init("M1_OUT_A", OUTPUT_LOW);
  s.out_b = pin_init("M1_OUT_B", OUTPUT_LOW);
  pin_watch_config_t cfg = {.user_data = 0, .edge = BOTH, .pin_change = on_pin};
  pin_watch(s.in_a, &cfg);
  pin_watch(s.in_b, &cfg);
}

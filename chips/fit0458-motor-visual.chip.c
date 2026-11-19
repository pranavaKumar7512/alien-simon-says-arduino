#include "wokwi-api.h"

// Visual-only animation: a spoked rotor spins while a motor lead is driven (high or PWM-toggling)
// and the other lead is not. MOTOR_PLUS active = clockwise, MOTOR_MINUS active = counter-clockwise.
// No torque, load, stall, speed-vs-duty or current is modeled; the spin rate is a fixed cosmetic
// value. The encoder leads are intentionally absent because the firmware does not use the encoder.

#define W 64
#define H 64
#define FRAME_US 33000
#define PWM_HOLD_NS 6000000ULL  // a lead with an edge in the last 6 ms counts as PWM-driven
#define SPIN_RAD_PER_FRAME 0.25f

typedef struct {
  pin_t plus, minus;
  bool plus_level, minus_level;
  uint64_t plus_edge, minus_edge;
  buffer_t fb;
  float angle;
  uint32_t px[W * H];
} state_t;

static state_t s;

static float wrap(float a) {
  while (a > 3.14159265f) a -= 6.2831853f;
  while (a < -3.14159265f) a += 6.2831853f;
  return a;
}
static float fsin(float a) {
  a = wrap(a);
  float a2 = a * a;
  return a * (1.0f - a2 / 6.0f * (1.0f - a2 / 20.0f * (1.0f - a2 / 42.0f * (1.0f - a2 / 72.0f))));
}
static float fcos(float a) { return fsin(a + 1.5707963f); }

static void plot(int x, int y, uint32_t c) {
  if (x >= 0 && x < W && y >= 0 && y < H) s.px[y * W + x] = c;
}

static void draw(void) {
  const uint32_t bg = 0xFF2A2A2A, ring = 0xFF9A9A9A, hub = 0xFF3C8CFF, blade = 0xFFE0E0E0, mark = 0xFF3030FF;
  for (int i = 0; i < W * H; i++) s.px[i] = bg;
  const int cx = W / 2, cy = H / 2, R = 28;
  for (int a = 0; a < 360; a++) {  // outer ring
    float r = a * 0.0174533f;
    plot(cx + (int)(R * fcos(r) + 0.5f), cy + (int)(R * fsin(r) + 0.5f), ring);
  }
  for (int k = 0; k < 4; k++) {  // four spokes, one tipped red so direction is visible
    float r = s.angle + k * 1.5707963f;
    float c = fcos(r), sn = fsin(r);
    for (int t = 3; t <= R - 2; t++) {
      int x = cx + (int)(t * c + 0.5f), y = cy + (int)(t * sn + 0.5f);
      uint32_t col = (k == 0 && t > R - 9) ? mark : blade;
      plot(x, y, col); plot(x + 1, y, col); plot(x, y + 1, col);
    }
  }
  for (int y = -3; y <= 3; y++)
    for (int x = -3; x <= 3; x++)
      if (x * x + y * y <= 10) plot(cx + x, cy + y, hub);
  buffer_write(s.fb, 0, s.px, sizeof(s.px));
}

static void on_pin(void *ud, pin_t pin, uint32_t value) {
  (void)ud;
  uint64_t now = get_sim_nanos();
  if (pin == s.plus) { s.plus_level = value; s.plus_edge = now; }
  else { s.minus_level = value; s.minus_edge = now; }
}

static void on_frame(void *ud) {
  (void)ud;
  uint64_t now = get_sim_nanos();
  bool p = s.plus_level || (s.plus_edge && now - s.plus_edge < PWM_HOLD_NS);
  bool m = s.minus_level || (s.minus_edge && now - s.minus_edge < PWM_HOLD_NS);
  if (p && !m) s.angle = wrap(s.angle + SPIN_RAD_PER_FRAME);
  else if (m && !p) s.angle = wrap(s.angle - SPIN_RAD_PER_FRAME);
  draw();
}

void chip_init(void) {
  s.plus = pin_init("MOTOR_PLUS", INPUT);
  s.minus = pin_init("MOTOR_MINUS", INPUT);
  uint32_t w = W, h = H;
  s.fb = framebuffer_init(&w, &h);
  pin_watch_config_t cfg = {.user_data = 0, .edge = BOTH, .pin_change = on_pin};
  pin_watch(s.plus, &cfg);
  pin_watch(s.minus, &cfg);
  timer_config_t t = {.user_data = 0, .callback = on_frame};
  timer_start(timer_init(&t), FRAME_US, true);
  draw();
}

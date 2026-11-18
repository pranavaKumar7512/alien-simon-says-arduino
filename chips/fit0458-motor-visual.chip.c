#include "wokwi-api.h"

// Label marker only: no motion, load, stall, or current is modeled. The encoder leads are
// intentionally absent because the firmware does not use the encoder.
void chip_init(void) {
}

#include "PulseWave.hpp"

#include <cmath>
#include <cstdio>

PulseWave::PulseWave()
  : period(0.0), duty(0.0), enabled(0), envelope(1.0)
{
}

void PulseWave :: setPeriod(double p) {
  // TODO: this will do strange things if time isn't zero, because the
  // relative position within the period will change. Think about
  // whether we care.
  period = p;
}

void PulseWave :: setDuty(float d) {
  duty = d;
}

void PulseWave :: setEnabled(bool e) {
  enabled = e;
}

float PulseWave :: sample(double time)
{
  if (!period) {
    return 0.0;
  }
  float phase = fmod(((time - (0.125 * period)) / period), 1.0);
  if (phase < 0.0) {
    phase += 1.0;
  }
  float out = (phase < duty) ? envelope : 0.0;
  return out;
}

// Note: not guaranteed to print entire state
void PulseWave::printState(void) {
  const char *enabledStr = enabled ? "enabled" : "disabled";
  float frequency = 1.0 / period;
  printf("Pulse wave channel %d: %s, duty %f, period %f (%f Hz)\n",
         // dummy channel number below
         -1, enabledStr, duty, period, frequency);
}

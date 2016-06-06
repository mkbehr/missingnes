#include "PulseWave.hpp"

#include <cmath>
#include <cstdio>

PulseWave::PulseWave()
  : divider(0), duty(0.0), enabled(0), envelope(1.0), startTime(0.0)
{
}

void PulseWave::reset(double t) {
  startTime = t;
  envelope = 1.0;
}

void PulseWave::setDivider(unsigned int d) {
  divider = d;
}

void PulseWave::setDuty(float d) {
  duty = d;
}

void PulseWave::setEnabled(bool e) {
  enabled = e;
}

double PulseWave::period() {
  return (divider + 2) * PERIOD_INCREMENT;
}

float PulseWave::sample(double time)
{
  double prd = period();
  if (prd < MINIMUM_PERIOD) {
    return 0.0;
  }
  float phase = fmod(((time - startTime - (0.125 * prd)) / prd), 1.0);
  if (phase < 0.0) {
    phase += 1.0;
  }
  float out = (phase < duty) ? envelope : 0.0;
  return out;
}

// Note: not guaranteed to print entire state
void PulseWave::printState(void) {
  const char *enabledStr = enabled ? "enabled" : "disabled";
  float frequency = 1.0 / period();
  printf("Pulse wave channel %d: %s, duty %f, divider %d (%f Hz)\n",
         // dummy channel number below
         -1, enabledStr, duty, divider, frequency);
}

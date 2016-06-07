#include "PulseWave.hpp"

#include <cmath>
#include <cstdio>

PulseWave::PulseWave(double sampleRate)
  : divider(0), duty(0.0), enabled(0), envelope(1.0), time(0.0),
    sweepLastActed(0.0), sweepEnabled(0), sweepDivider(0), sweepShift(0),
    duration(-1.0),
    sampleRate(sampleRate)
{
}

void PulseWave::reset(void) {
  time = 0.0;
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

void PulseWave::setDuration(float d) {
  duration = d;
}

void PulseWave::updateSweep(bool _enabled, unsigned int _divider,
                            unsigned int _shift, bool _negate) {
  sweepEnabled = _enabled;
  sweepDivider = _divider;
  sweepShift = _shift;
  sweepNegate = _negate;
  sweepReset();
}

void PulseWave::sweepReset() {
  sweepLastActed = 0.0;
  // Note: resetting the sweep unit does not reset the divider.
}

// TODO: sweep-setting functions

double PulseWave::frameCounterPeriod() {
  // TODO account for 4-step vs. 5-step modes
  return 18641.0 / (CPU_FREQUENCY / 2.0);
}

double PulseWave::period() {
  return (divider + 2) * PERIOD_INCREMENT;
}

double PulseWave::sweepPeriod() {
  // sweep unit is clocked twice per frame-counter period
  return (sweepDivider + 1) * frameCounterPeriod() / 2.0;
}

void PulseWave::sweepAct() {
  sweepLastActed += sweepPeriod();
    if (sweepEnabled) {
      int dividerDelta = divider >> sweepShift;
      // TODO: If the divider would go outside [MINIMUM_DIVIDER,
      // MAXIMUM_DIVIDER], this should actually silence the channel
      // but leave the divider unchanged. Uh, it also may be that we
      // silence the channel before actually ticking, but as soon as
      // we see that on our /next/ tick we will go outside the range.
      if (sweepNegate) {
        // TODO: If we are pulse channel 1, then we are actually
        // adding the one's complement instead of the two's
        // complement, so subtract one from dividerDelta. (But what
        // happens if dividerDelta is zero - are we actually
        // increasing the divider then???)

        // dividerDelta <= divider, so this will never underflow
        divider -= dividerDelta;
      } else {
        // not the correct check (divider should actually never exceed
        // MAXIMUM_DIVIDER), but prevents overflow
        if (divider <= MAXIMUM_DIVIDER) {
          divider += dividerDelta;
        }
      }
    }
}

float PulseWave::tick()
{
  if (sweepPeriod() - (time - sweepLastActed) <= TIME_PRECISION) {
    sweepAct();
  }
  double prd = period();
  float phase = fmod(((time - (0.125 * prd)) / prd), 1.0);
  if (phase < 0.0) {
    phase += 1.0;
  }
  float out = (phase < duty) ? envelope : 0.0;
  if ((divider < MINIMUM_DIVIDER) || (divider > MAXIMUM_DIVIDER)) {
    out = 0.0;
  }
  if (!enabled) {
    out = 0.0;
  }
  if ((duration >= 0) && (time >= duration)) {
    out = 0.0;
  }
  time += 1.0 / sampleRate;
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

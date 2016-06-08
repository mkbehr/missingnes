#include "PulseWave.hpp"

#include <cmath>
#include <cstdio>

PulseWave::PulseWave(double sampleRate)
  : divider(0), duty(0.0), enabled(0), time(0.0),
    sweepLastActed(0.0), sweepEnabled(0), sweepDivider(0), sweepShift(0),
    duration(-1.0),
    envelopeCounter(ENVELOPE_MAX), envelopeLoop(0), envelopeConstant(1),
    envelopeTimerReload(ENVELOPE_MAX),
    sampleRate(sampleRate)
{
}

void PulseWave::reset(void) {
  time = 0.0;
  sweepLastActed = 0.0;
  envelopeLastActed = 0.0;
  envelopeCounter = ENVELOPE_MAX;
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

void PulseWave::updateEnvelope(bool loop, bool constant,
                               unsigned char timerReload) {
  // Note: this does not reset the envelope. reset() does that, which
  // is called by writing to 0x4003 or 0x4007 (length counter load,
  // timer high bits)
  envelopeLoop = loop;
  envelopeConstant = constant;
  envelopeTimerReload = timerReload;
}

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

float PulseWave::envelopePeriod() {
  // envelope is clocked four times per frame-counter period
  return (envelopeTimerReload + 1) * frameCounterPeriod() / 4.0;
}

void PulseWave::envelopeAct() {
  envelopeLastActed += envelopePeriod();
  if (envelopeCounter > 0) {
    envelopeCounter--;
  } else if (envelopeLoop) {
    envelopeCounter = ENVELOPE_MAX;
  }
}

float PulseWave::envelope() {
  unsigned char envelope_n =
    envelopeConstant ? envelopeTimerReload : envelopeCounter;
  return ((float) envelope_n) / ((float) ENVELOPE_MAX);
}

float PulseWave::tick()
{
  if (sweepPeriod() - (time - sweepLastActed) <= TIME_PRECISION) {
    sweepAct();
  }
  if (envelopePeriod() - (time - envelopeLastActed) <= TIME_PRECISION) {
    envelopeAct();
  }
  double prd = period();
  float phase = fmod(((time - (0.125 * prd)) / prd), 1.0);
  if (phase < 0.0) {
    phase += 1.0;
  }
  float out = (phase < duty) ? envelope() : 0.0;
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

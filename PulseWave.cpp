#include "PulseWave.hpp"

#include <cassert>
#include <cmath>
#include <cstdio>

PulseWave::PulseWave(float sampleRate)
  : divider(0), duty(0.0), enabled(0), time(0.0),
    sweepEnabled(0), sweepDividerReload(0), sweepDivider(0), sweepShift(0),
    lengthCounterValue(0), lengthCounterHalt(0), frameCounterMode(0),
    envelopeCounter(ENVELOPE_MAX), envelopeLoop(0), envelopeConstant(1),
    envelopeDivider(0), envelopeDividerReload(ENVELOPE_MAX),
    sampleRate(sampleRate)
{
}

void PulseWave::reset(void) {
  // reset phase, reload length conuter, reset envelope.
  time = 0.0;
  envelopeDivider = envelopeDividerReload;
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

void PulseWave::setLengthCounterHalt(bool h) {
  lengthCounterHalt = h;
}

void PulseWave::setLengthCounter(unsigned int c) {
  lengthCounterValue = c;
}

void PulseWave::updateSweep(bool _enabled, unsigned int _divider,
                            unsigned int _shift, bool _negate) {
  sweepEnabled = _enabled;
  sweepDividerReload = _divider;
  sweepShift = _shift;
  sweepNegate = _negate;
  sweepReset();
}

void PulseWave::sweepReset() {
  sweepDivider = sweepDividerReload;
  // Note: resetting the sweep unit does not reset the divider.
}

void PulseWave::updateEnvelope(bool loop, bool constant,
                               unsigned char timerReload) {
  // Note: this does not reset the envelope. reset() does that, which
  // is called by writing to 0x4003 or 0x4007 (length counter load,
  // timer high bits)
  envelopeLoop = loop;
  envelopeConstant = constant;
  envelopeDividerReload = timerReload;
}

float PulseWave::period() {
  return (divider + 2) * PULSE_PERIOD_INCREMENT;
}

void PulseWave::sweepAct() {
  if (sweepDivider) {
    sweepDivider--;
    return;
  }
  sweepDivider = sweepDividerReload;
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
      if (divider <= PULSE_MAXIMUM_DIVIDER) {
        divider += dividerDelta;
      }
    }
  }
}

void PulseWave::envelopeAct() {
  if (envelopeDivider) {
    envelopeDivider--;
    return;
  }
  envelopeDivider = envelopeDividerReload;
  if (envelopeCounter > 0) {
    envelopeCounter--;
  } else if (envelopeLoop) {
    envelopeCounter = ENVELOPE_MAX;
  }
}

unsigned char PulseWave::envelope() {
  unsigned char out = envelopeConstant ?
    envelopeDividerReload : envelopeCounter;
  assert((out >= 0) &&
         (out <= ENVELOPE_MAX));
  return out;
}

void PulseWave::lengthCounterAct() {
  if ((!lengthCounterHalt) && (lengthCounterValue > 0)) {
    lengthCounterValue--;
  }
  if (!enabled) {
    // TODO check to see whether this is exactly the right behavior
    lengthCounterValue = 0;
  }
}

void PulseWave::updateFrameCounter(bool mode) {
  frameCounterMode = mode;
}

void PulseWave::frameCounterQuarterFrame() {
  sweepAct();
}

void PulseWave::frameCounterHalfFrame() {
  lengthCounterAct();
  envelopeAct();
  sweepAct();
}

unsigned char PulseWave::tick()
{
  float prd = period();
  float phase = fmod(((time - (0.125 * prd)) / prd), 1.0);
  if (phase < 0.0) {
    phase += 1.0;
  }
  float out = (phase < duty) ? envelope() : 0.0;
  if ((divider < PULSE_MINIMUM_DIVIDER) || (divider > PULSE_MAXIMUM_DIVIDER)) {
    out = 0;
  }
  if (!enabled) {
    out = 0;
  }
  if (!lengthCounterValue) {
    out = 0;
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

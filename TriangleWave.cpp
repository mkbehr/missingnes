#include "TriangleWave.hpp"

#include <cassert>
#include <cmath>
#include <cstdio>

// TODO make sure to initialize everything here
TriangleWave::TriangleWave(float sampleRate)
  : enabled(0), divider(0),
    sequenceIndex(TRIANGLE_WAVE_SEQUENCE_START),
    time(0.0),
    linearCounterHalt(0), lengthCounterHalt(0),
    linearCounterInit(0), linearCounterValue(0),
    lengthCounterValue(0),
    linearCounterLastActed(0.0), lengthCounterLastActed(0.0),
    sequencerLastActed(0.0),
    sampleRate(sampleRate)
{
}

void TriangleWave::setEnabled(bool e) {
  enabled = e;
}

void TriangleWave::setDivider(unsigned int d) {
  sequencerLastActed = time; // DEBUG
  divider = d;
}

void TriangleWave::setLinearCounterInit(unsigned int c) {
  // Note: AFAICT, this should not affect the actual duration of the
  // wave until we write to 0x400b, which will also call linearCounterReload
  linearCounterInit = c;
}

void TriangleWave::setTimerHalts(bool h) {
  linearCounterHalt = h;
  lengthCounterHalt = h;
}

void TriangleWave::setLengthCounter(unsigned int c) {
  lengthCounterValue = c;
}

unsigned char TriangleWave::envelope() {
  // Envelope has a 32-element sequence: it counts down from 15 to 0,
  // then up from 0 to 15
  unsigned char out;
  if (sequenceIndex < 16) {
    out = 15 - sequenceIndex;
  } else {
    out = sequenceIndex - 16;
  }
  assert((out >= 0) &&
         (out <= ENVELOPE_MAX));
  return out;
}

void TriangleWave::updateFrameCounter(bool mode) {
  frameCounterMode = mode;
  // In 5-step mode, clock everything immediately. In 4-step mode,
  // don't. (Not sure the 4-step mode behavior is exactly correct.)

  // TODO: Make sure this is robust to timing errors; currently, we
  // might tick in the middle of this.
  if (mode) {
    linearCounterLastActed = time - linearCounterPeriod();
    lengthCounterLastActed = time - lengthCounterPeriod();
    sequencerLastActed = time - sequencerPeriod();
  } else {
    linearCounterLastActed = time;
    lengthCounterLastActed = time;
    sequencerLastActed = time;
  }
}

float TriangleWave::frameCounterPeriod() {
  return (frameCounterMode ?
          FRAME_COUNTER_5STEP_LENGTH :
          FRAME_COUNTER_4STEP_LENGTH)
    / (CPU_FREQUENCY / 2.0);
}

float TriangleWave::linearCounterPeriod() {
  return frameCounterPeriod() / 4.0;
}

void TriangleWave::linearCounterAct() {
  linearCounterLastActed += linearCounterPeriod();
  if ((!linearCounterHalt) && (linearCounterValue > 0)) {
    linearCounterValue--;
  }
}

void TriangleWave::linearCounterReload() {
  // In the NES, this would cause the linear counter to be set to its
  // initial value the next time it was clocked. Instead, we'll just
  // set it to its initial vlaue plus one.

  // FIXME: This behavior isn't quite right, because the NES will set
  // the value to its initial value even when the linear counter
  // control bit (linearCounterHalt) is set. We'll instead leave it
  // sitting around at the initial value plus one.
  linearCounterValue = linearCounterInit + 1;
}

float TriangleWave::lengthCounterPeriod() {
  return frameCounterPeriod() / 2.0;
}

void TriangleWave::lengthCounterAct() {
  lengthCounterLastActed += lengthCounterPeriod();
  if ((!lengthCounterHalt) && (lengthCounterValue > 0)) {
    lengthCounterValue--;
  }
  if (!enabled) {
    lengthCounterValue = 0;
  }
}

float TriangleWave::sequencerPeriod() {
  return (divider + 1) / CPU_FREQUENCY;
}

void TriangleWave::sequencerAct() {
  sequencerLastActed += sequencerPeriod();
  // When the triangle wave is silenced, it doesn't jump to 0: it just
  // keeps outputting what it's been outputting
  if (!silent()) {
    sequenceIndex = (sequenceIndex + 1) % TRIANGLE_WAVE_SEQUENCE_LENGTH;
  }
}

bool TriangleWave::silent() {
  // The channel is silent if the channel is inactive, if either
  // counter has expired, or if the divider is below its minimum
  // value. (In real hardware, if the divider is below its minimum
  // value, the output will just jump to about 7.5 and make a popping
  // sound, but I'm okay just silencing instead.)
  return ( (!enabled) ||
           (linearCounterValue == 0) ||
           (lengthCounterValue == 0) ||
           (divider < TRIANGLE_MINIMUM_DIVIDER));
}

unsigned char TriangleWave::tick() {
  if (linearCounterPeriod() - (time - linearCounterLastActed)
      <= TIME_PRECISION) {
    linearCounterAct();
  }
  if (lengthCounterPeriod() - (time - lengthCounterLastActed)
      <= TIME_PRECISION) {
    lengthCounterAct();
  }
  if (sequencerPeriod() - (time - sequencerLastActed)
      <= TIME_PRECISION) {
    sequencerAct();
  }
  unsigned char out = envelope();
  time += 1.0 / sampleRate;
  return out;
}

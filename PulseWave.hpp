#ifndef PULSE_WAVE_H
#define PULSE_WAVE_H

#include "nesconstants.hpp"

// For a timer value of t, the period is:
// (t + 2) * CPU_CYCLES_PER_WAVEFORM_CYCLE / CPU_FREQUENCY

const float PERIOD_INCREMENT = CPU_CYCLES_PER_WAVEFORM_CYCLE / CPU_FREQUENCY;

// For t of 8 or higher, the pulse wave is played; for t of 7 or
// lower, it is silenced. Set the minimum period in between so we
// don't hit floating-point errors.
const float MINIMUM_PERIOD = ((7.5 + 2) * PERIOD_INCREMENT);

const unsigned int MINIMUM_DIVIDER = 8;
const unsigned int MAXIMUM_DIVIDER = 0x7ff;

const float TIME_PRECISION = 1e-8;

const unsigned char ENVELOPE_MAX = 0xf;

class PulseWave {

public:

  PulseWave(float sampleRate);
  void reset();
  void setDivider(unsigned int divider);
  void setDuty(float duty);
  void setEnabled(bool);
  void setDuration(float duration);

  void updateSweep(bool enabled, unsigned int divider,
                   unsigned int shift, bool negate);
  void sweepReset();

  void updateEnvelope(bool loop, bool constant,
                      unsigned char timerReload);

  float tick();

  void printState(void);

protected:

  float frameCounterPeriod();

  float period();
  float sweepPeriod();
  void sweepAct();
  float envelopePeriod();
  void envelopeAct();
  float envelope();

  const float sampleRate;

  unsigned int divider;
  float duty;
  bool enabled;
  float time;
  float duration;

  bool envelopeLoop;
  bool envelopeConstant;
  // Note: the timer reload also specifies the envelope in constant mode
  unsigned char envelopeTimerReload;
  float envelopeLastActed;
  unsigned char envelopeCounter;

  float sweepLastActed;
  bool sweepEnabled;
  unsigned int sweepDivider;
  unsigned int sweepShift;
  bool sweepNegate;

};
#endif

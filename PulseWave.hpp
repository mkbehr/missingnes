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

const double TIME_PRECISION = 1e-8;

class PulseWave {

public:

  PulseWave(double sampleRate);
  void reset();
  void setDivider(unsigned int divider);
  void setDuty(float duty);
  void setEnabled(bool);
  void setDuration(float duration);

  void updateSweep(bool enabled, unsigned int divider,
                   unsigned int shift, bool negate);
  void sweepReset();

  float tick();

  void printState(void);

protected:

  // TODO these should probably all be floats

  double frameCounterPeriod();

  double period();
  double sweepPeriod();
  void sweepAct();

  const double sampleRate;

  unsigned int divider;
  float duty;
  float envelope;
  bool enabled;
  float time;
  float duration;

  double sweepLastActed;
  bool sweepEnabled;
  unsigned int sweepDivider;
  unsigned int sweepShift;
  bool sweepNegate;

};
#endif

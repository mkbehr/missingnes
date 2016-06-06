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

class PulseWave {

public:

  PulseWave();
  void reset(double);
  void setDivider(unsigned int divider);
  // void setPeriod(double period);
  void setDuty(float duty);
  void setEnabled(bool);

  void setSweepEnabled(bool);
  void setSweepPeriod(float);

  float sample(double);

  void printState(void);

protected:

  double period();

  unsigned int divider;
  float duty;
  float envelope;
  bool enabled;
  float startTime;
  bool sweepEnabled;


};
#endif

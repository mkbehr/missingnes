#ifndef PULSE_WAVE_H
#define PULSE_WAVE_H

#include "nesconstants.hpp"

// For a timer value of t, the period is:
// (t + 2) * CPU_CYCLES_PER_PULSE_CYCLE / CPU_FREQUENCY

const int CPU_CYCLES_PER_PULSE_CYCLE = 16;
const float PULSE_PERIOD_INCREMENT = CPU_CYCLES_PER_PULSE_CYCLE / CPU_FREQUENCY;

const unsigned int PULSE_MINIMUM_DIVIDER = 8;
const unsigned int PULSE_MAXIMUM_DIVIDER = 0x7ff;

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

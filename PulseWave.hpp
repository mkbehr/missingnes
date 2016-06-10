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
  void setLengthCounterHalt(bool halt);
  void setLengthCounter(unsigned int c);

  void updateSweep(bool enabled, unsigned int divider,
                   unsigned int shift, bool negate);
  void sweepReset();

  void updateEnvelope(bool loop, bool constant,
                      unsigned char timerReload);

  void updateFrameCounter(bool mode);
  void frameCounterQuarterFrame();
  void frameCounterHalfFrame();

  unsigned char tick();

  void printState(void);

protected:

  float period();
  void sweepAct();
  void envelopeAct();
  void lengthCounterAct();
  unsigned char envelope();

  const float sampleRate;

  unsigned int divider;
  float duty;
  bool enabled;
  float time;

  bool lengthCounterHalt;
  int lengthCounterValue;

  bool envelopeLoop;
  bool envelopeConstant;
  // Note: the timer reload also specifies the envelope in constant mode
  unsigned char envelopeDividerReload;
  unsigned char envelopeDivider;
  unsigned char envelopeCounter;

  bool sweepEnabled;
  unsigned int sweepDividerReload;
  unsigned int sweepDivider;
  unsigned int sweepShift;
  bool sweepNegate;

  bool frameCounterMode;

};
#endif

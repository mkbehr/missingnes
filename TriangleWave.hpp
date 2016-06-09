#ifndef TRIANGLE_WAVE_H
#define TRIANGLE_WAVE_H

#include "nesconstants.hpp"

const int TRIANGLE_WAVE_SEQUENCE_LENGTH = 32;
// start with output 0 so there's no popping sound
const int TRIANGLE_WAVE_SEQUENCE_START = 15;

const int TRIANGLE_MINIMUM_DIVIDER = 2;

class TriangleWave {

public:
  TriangleWave(float sampleRate);
  void setEnabled(bool enabled);
  void setDivider(unsigned int divider);
  void setLinearCounterInit(unsigned int c);
  void setTimerHalts(bool halt);
  void setLengthCounter(unsigned int c);
  void linearCounterReload();

  void updateFrameCounter(bool mode);

  unsigned char tick();

protected:
  const float sampleRate;

  bool enabled;
  unsigned int divider;
  unsigned int sequenceIndex;
  float time;

  // these two bits are actually the same bit in the NES
  bool linearCounterHalt; // a.k.a. linear counter control bit
  bool lengthCounterHalt;

  int linearCounterInit;
  int linearCounterValue;
  int lengthCounterValue;

  float frameCounterPeriod();
  float linearCounterPeriod();
  float lengthCounterPeriod();
  float sequencerPeriod();

  void linearCounterAct();
  void lengthCounterAct();
  void sequencerAct();

  float linearCounterLastActed;
  float lengthCounterLastActed;
  float sequencerLastActed;

  bool silent();

  unsigned char envelope();

  bool frameCounterMode;
};

#endif

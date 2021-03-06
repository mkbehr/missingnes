#ifndef APU_H
#define APU_H

#include <cstdlib>
#include <string>
#include <vector>

#include "portaudio.h"

#include "PulseWave.hpp"
#include "TriangleWave.hpp"

const int N_PULSE_WAVES = 2;

const float SAMPLE_RATE = 44100.0;

const float PULSE_MIX_COEFFICIENT = 0.00752;
const float TRIANGLE_MIX_COEFFICIENT = 0.00851;
const float NOISE_MIX_COEFFICIENT = 0.00494;
const float DMC_MIX_COEFFICIENT = 0.00335;

class APU {
public:
  APU(float sampleRate);
  ~APU();
  void apuInit();
  float tick();
  void updateFrameCounter(bool);
  void frameCounterQuarterFrame();
  void frameCounterHalfFrame();
  // pulse wave interface
  void resetPulse(unsigned int);
  void setPulseDivider(unsigned int, unsigned int);
  void setPulseEnabled(unsigned int, bool);
  void setPulseDuty(unsigned int, float);
  void setPulseLengthCounterHalt(unsigned int, bool);
  void setPulseLengthCounter(unsigned int, unsigned int);
  void setPulseDuration(unsigned int, float);
  void updatePulseSweep(unsigned int pulse_n,
                        bool enabled, unsigned int divider,
                        unsigned int shift, bool negate);
  void updatePulseEnvelope(unsigned int pulse_n,
                           bool loop, bool constant,
                           unsigned char timerReload);

  float lastSample;

  std::vector<PulseWave> pulses;
  TriangleWave triangle;

protected:
  float time;
  float sampleRate;
  float timeStep;

  bool frameCounterMode;

  PaStream *stream;
};

#endif

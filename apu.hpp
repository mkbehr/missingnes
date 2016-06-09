#ifndef APU_H
#define APU_H

#include <cstdlib>
#include <string>
#include <vector>

#include "portaudio.h"

#include "PulseWave.hpp"
#include "TriangleWave.hpp"

const int N_PULSE_WAVES = 2;
const int N_SOURCES = 3; // currently: pulse x2, triangle

const float SAMPLE_RATE = 44100.0;

class APU {
public:
  APU(float sampleRate);
  ~APU();
  void apuInit();
  float tick();
  void updateFrameCounter(bool);
  // pulse wave interface
  void resetPulse(unsigned int);
  void setPulseDivider(unsigned int, unsigned int);
  void setPulseEnabled(unsigned int, bool);
  void setPulseDuty(unsigned int, float);
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

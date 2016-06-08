#ifndef APU_H
#define APU_H

#include <cstdlib>
#include <string>
#include <vector>

#include "portaudio.h"

#include "PulseWave.hpp"

const int N_PULSE_WAVES = 2;
const int N_SOURCES = 2;

const double SAMPLE_RATE = 44100.0;

class APU {
public:
  APU(double sampleRate);
  ~APU();
  void apuInit();
  float tick();
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
  // TODO more interface functions

  float lastSample;

protected:
  std::vector<PulseWave> pulses;
  double time;
  double sampleRate;
  double timeStep;

  PaStream *stream;
};

#endif

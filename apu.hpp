#ifndef APU_H
#define APU_H

#include <cstdlib>
#include <string>

#include "portaudio.h"

#include "PulseWave.hpp"

const int N_PULSE_WAVES = 2;
const int N_SOURCES = 2;

const double SAMPLE_RATE = 44100.0;

class APU {
public:
  APU(double);
  ~APU();
  void apuInit();
  float tick();
  void resetPulse(unsigned int);
  void setPulseDivider(unsigned int, unsigned int);
  void setPulseEnabled(unsigned int, bool);
  void setPulseDuty(unsigned int, float);
  // TODO more interface functions

  float lastSample;

protected:
  PulseWave pulses[N_PULSE_WAVES];
  double time;
  double sampleRate;
  double timeStep;

  PaStream *stream;
};

#endif

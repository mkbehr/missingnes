#ifndef APU_H
#define APU_H

#include <cstdlib>
#include <string>
#include <thread>
#include <mutex>

#include "PulseWave.hpp"

const int N_PULSE_WAVES = 2;

const stk::StkFloat SAMPLE_RATE = 44100.0;

class APU {
public:
  APU();
  ~APU();
  void apuInit();
  stk::StkFloat tick();
  void setPulsePeriod(int, stk::StkFloat);
  void setPulseEnabled(int, bool);
  // TODO more interface functions

  bool terminating;

  std::mutex audioMutex;

protected:
  // to keep things simple, we'll only work with one pulse wave for now
  PulseWave pulse;

  std::thread audioThread;

};

#endif

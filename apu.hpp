#ifndef APU_H
#define APU_H

#include <cstdlib>
#include <string>
#include <thread>
#include <mutex>

#include "PulseWave.hpp"

const int N_PULSE_WAVES = 2;
const int N_SOURCES = 2;

const stk::StkFloat SAMPLE_RATE = 44100.0;

class APU {
public:
  APU();
  ~APU();
  void apuInit();
  stk::StkFloat tick();
  void setPulsePeriod(unsigned int, stk::StkFloat);
  void setPulseEnabled(unsigned int, bool);
  void setPulseDuty(unsigned int, stk::StkFloat);
  // TODO more interface functions

  bool terminating;



protected:
  PulseWave pulses[N_PULSE_WAVES];

  std::thread audioThread;
  std::mutex audioMutex;

};

#endif

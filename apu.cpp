#include <stdexcept>
#include <string>

#include "apu.hpp"

#include "stk/RtWvOut.h"

APU::APU(void)
  : terminating(0) {
}

APU::~APU(void) {
  terminating = 1;
  audioThread.join();
}

void audioRun(APU *apu) {
  stk::RtWvOut *dac = 0;
  try {
    dac = new stk::RtWvOut(1);
  }
  catch (stk::StkError &e) {
    std::cerr << "Error creating audio output device:\n";
    e.printMessage();
    exit(1);
  }

  while (!(apu->terminating)) {
    stk::StkFloat tickValue = apu->tick();
    // This can apparently throw an StkError, but I don't know when
    // or why, so we'll happily crash in that case
    try {
      dac->tick(tickValue);
    } catch (stk::StkError &e) {
      std::cerr << "Error outputting audio:\n";
      e.printMessage();
      exit(1);
    }
  }
  delete dac;
  return;
}

void APU::apuInit(void) {
  // Using stk::RtWvOut, at least for now. However, the documentation
  // says "This class should not be used when low-latency is desired."
  // It doesn't elaborate or suggest an alternative, so I'll look into
  // that once I get something working to start with.
  stk::Stk::setSampleRate(SAMPLE_RATE);
  stk::Stk::showWarnings(true);

  audioThread = std::thread(audioRun, this);
}

stk::StkFloat APU::tick(void) {
  std::lock_guard<std::mutex> lock(audioMutex);

  stk::StkFloat out = 0.0;
  for (int pulse_i = 0; pulse_i < N_PULSE_WAVES; pulse_i++) {
    out += pulses[pulse_i].tick();
  }
  out /= N_SOURCES;
  return out;
}

void APU::setPulsePeriod(unsigned int pulse_n, stk::StkFloat period) {
  if (pulse_n >= N_PULSE_WAVES) {
    throw std::range_error(
      std::string("setPulsePeriod: bad pulse channel: ") +
      std::to_string(pulse_n));
    exit(1);
  }
  std::lock_guard<std::mutex> lock(audioMutex);
  pulses[pulse_n].setPeriod(period);
}

void APU::setPulseEnabled(unsigned int pulse_n, bool enabled) {
  if (pulse_n >= N_PULSE_WAVES) {
    throw std::range_error(
      std::string("setPulseEnabled: bad pulse channel: ")
      + std::to_string(pulse_n));
    exit(1);
  }
  std::lock_guard<std::mutex> lock(audioMutex);
  pulses[pulse_n].setEnabled(enabled);
}

void APU::setPulseDuty(unsigned int pulse_n, stk::StkFloat duty) {
  if (pulse_n >= N_PULSE_WAVES) {
    throw std::range_error(
      std::string("setPulsePeriod: bad pulse channel: ") +
      std::to_string(pulse_n));
    exit(1);
  }
  std::lock_guard<std::mutex> lock(audioMutex);
  pulses[pulse_n].setDuty(duty);
}

// ctypes interface

extern "C" {

  APU *ex_initAPU(void) {
    APU *out = new APU();
    out->apuInit();
    return out;
  }

  void ex_setPulsePeriod(APU *apu, unsigned int pulse_n, float period) {
    apu->setPulsePeriod(pulse_n, (stk::StkFloat) period);
  }

  void ex_setPulseEnabled(APU *apu, unsigned int pulse_n, unsigned char enabled) {
    apu->setPulseEnabled(pulse_n, enabled);
  }

  void ex_setPulseDuty(APU *apu, unsigned int pulse_n, float duty) {
    apu->setPulseDuty(pulse_n, (stk::StkFloat) duty);
  }

}

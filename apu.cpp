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
    apu->audioMutex.lock();
    stk::StkFloat tickValue = apu->tick();
    if (tickValue > 1.0) {
      printf("Big tick value: %f\n", tickValue);
    }
    apu->audioMutex.unlock();
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
  // TODO get mutex

  // TODO eventually mix sources
  return pulse.tick();
}

void APU::setPulsePeriod(int pulse_n, stk::StkFloat period) {
  // Currently only dealing with pulse channel 2 (index 1)
  if (pulse_n != 1) {
    return;
  }
  std::lock_guard<std::mutex> lock(audioMutex);
  pulse.setPeriod(period);
}

void APU::setPulseEnabled(int pulse_n, bool enabled) {
  // Currently only dealing with pulse channel 2 (index 1)
  if (pulse_n != 1) {
    return;
  }
  std::lock_guard<std::mutex> lock(audioMutex);
  pulse.setEnabled(enabled);
}

// ctypes interface

extern "C" {

  APU *ex_initAPU(void) {
    APU *out = new APU();
    out->apuInit();
    return out;
  }

  void ex_setPulsePeriod(APU *apu, int pulse_n, float period) {
    apu->setPulsePeriod(pulse_n, (stk::StkFloat) period);
  }

  void ex_setPulseEnabled(APU *apu, int pulse_n, unsigned char enabled) {
    apu->setPulseEnabled(pulse_n, enabled);
  }

}

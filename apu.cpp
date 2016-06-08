#include <stdexcept>
#include <string>

#include "apu.hpp"

void checkPaError(PaError err) {
  if (err != paNoError) {
    fprintf(stderr, "PortAudio error: %s\n", Pa_GetErrorText(err));
    exit(1);
  }
}

static int apuCallback (const void *inputBuffer, void *outputBuffer,
                        unsigned long framesPerBuffer,
                        const PaStreamCallbackTimeInfo* timeInfo,
                        PaStreamCallbackFlags statusFlags,
                        void *userData ) {
  APU *apu = (APU *) userData;
  float *out = (float *) outputBuffer;
  (void) inputBuffer; /* Prevent unused variable warning. */

  for(int i = 0; i < framesPerBuffer; i++) {
    *out++ = apu->lastSample;
    *out++ = apu->lastSample;
    apu->tick();
  }
  return 0;
}

APU::APU(double sampleRate)
  : time(0), sampleRate(sampleRate), timeStep(1.0/sampleRate),
    pulses(std::vector<PulseWave>(2, PulseWave(SAMPLE_RATE)))
{
}

APU::~APU(void) {
  PaError err = Pa_StopStream(stream);
  checkPaError(err);

  err = Pa_Terminate();
  checkPaError(err);
}

void APU::apuInit(void) {


  PaError err = Pa_Initialize();
  checkPaError(err);


  err = Pa_OpenDefaultStream(
    &stream,
    0,                /* no input channels */
    2,                /* stereo output */
    paFloat32,        /* 32 bit floating point output */
    (int) sampleRate, /* sample rate */
    256,              /* frames per buffer */
    apuCallback,      /* callback */
    this);            /* pointer passed to callback */
  checkPaError(err);

  err = Pa_StartStream(stream);
  checkPaError(err);

}

// Computes one sample. Returns the sample, and also stores it in the
// lastSample member. Automatically advances the stored time.
float APU::tick(void) {
  float out = 0.0;
  for (int pulse_i = 0; pulse_i < N_PULSE_WAVES; pulse_i++) {
    out += pulses[pulse_i].tick();
  }
  out /= N_SOURCES;
  lastSample = out;
  time += timeStep;
  return out;
}

void APU::resetPulse(unsigned int pulse_n) {
  if (pulse_n >= N_PULSE_WAVES) {
    throw std::range_error(
      std::string("resetPulse: bad pulse channel: ") +
      std::to_string(pulse_n));
    exit(1);
  }
  pulses[pulse_n].reset();
}

void APU::setPulseDivider(unsigned int pulse_n, unsigned int divider) {
  if (pulse_n >= N_PULSE_WAVES) {
    throw std::range_error(
      std::string("setPulseDivider: bad pulse channel: ") +
      std::to_string(pulse_n));
    exit(1);
  }
  pulses[pulse_n].setDivider(divider);
}

void APU::setPulseEnabled(unsigned int pulse_n, bool enabled) {
  if (pulse_n >= N_PULSE_WAVES) {
    throw std::range_error(
      std::string("setPulseEnabled: bad pulse channel: ")
      + std::to_string(pulse_n));
    exit(1);
  }
  pulses[pulse_n].setEnabled(enabled);
}

void APU::setPulseDuty(unsigned int pulse_n, float duty) {
  if (pulse_n >= N_PULSE_WAVES) {
    throw std::range_error(
      std::string("setPulseDuty: bad pulse channel: ") +
      std::to_string(pulse_n));
    exit(1);
  }
  pulses[pulse_n].setDuty(duty);
}

void APU::setPulseDuration(unsigned int pulse_n, float duration) {
  if (pulse_n >= N_PULSE_WAVES) {
    throw std::range_error(
      std::string("setPulseDuration: bad pulse channel: ") +
      std::to_string(pulse_n));
    exit(1);
  }
  pulses[pulse_n].setDuration(duration);
}

void APU::updatePulseSweep(unsigned int pulse_n,
                           bool enabled, unsigned int divider,
                           unsigned int shift, bool negate) {
  if (pulse_n >= N_PULSE_WAVES) {
    throw std::range_error(
      std::string("updatePulseSweep: bad pulse channel: ") +
      std::to_string(pulse_n));
    exit(1);
  }
  pulses[pulse_n].updateSweep(enabled, divider, shift, negate);
}

// ctypes interface

extern "C" {

  APU *ex_initAPU(void) {
    APU *out = new APU(SAMPLE_RATE);
    out->apuInit();
    return out;
  }

  void ex_resetPulse(APU *apu, unsigned int pulse_n) {
    apu->resetPulse(pulse_n);
  }

  void ex_setPulseDivider(APU *apu, unsigned int pulse_n, unsigned int divider) {
    apu->setPulseDivider(pulse_n, divider);
  }

  void ex_setPulseEnabled(APU *apu, unsigned int pulse_n, unsigned char enabled) {
    apu->setPulseEnabled(pulse_n, enabled);
  }

  void ex_setPulseDuty(APU *apu, unsigned int pulse_n, float duty) {
    apu->setPulseDuty(pulse_n, duty);
  }

  void ex_setPulseDuration(APU *apu, unsigned int pulse_n, float duration) {
    apu->setPulseDuration(pulse_n, duration);
  }

  void ex_updatePulseSweep(APU *apu, unsigned int pulse_n,
                           unsigned char enabled, unsigned int divider,
                           unsigned int shift, unsigned char negate) {
    apu->updatePulseSweep(pulse_n,
                          (bool) enabled, divider,
                          shift, (bool) negate);
  }

}
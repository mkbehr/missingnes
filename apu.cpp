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

APU::APU(float sampleRate)
  : time(0), sampleRate(sampleRate), timeStep(1.0/sampleRate),
    frameCounterMode(0),
    pulses(std::vector<PulseWave>(2, PulseWave(sampleRate))),
    triangle(TriangleWave(sampleRate))
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
// lastSample member. Automatically advances the stored time. Mixes
// sources using a linear approximation of the NES's mixer. Returns a
// value between 0.0 and 1.0, so that zero outputs match (and there's
// no popping sound on startup and shutdown). Does not currently
// simulate the high-pass and low-pass filters that the NES appliles
// after DAC conversion.
float APU::tick(void) {
  float out = 0.0;
  // Using linear approximation for mixing: see
  // http://wiki.nesdev.com/w/index.php/APU_Mixer
  for (int pulse_i = 0; pulse_i < N_PULSE_WAVES; pulse_i++) {
    out += pulses[pulse_i].tick() * PULSE_MIX_COEFFICIENT;
  }
  out += triangle.tick() * TRIANGLE_MIX_COEFFICIENT;
  //out = (out * 2.0) - 1.0;
  lastSample = out;
  time += timeStep;
  return out;
}

void APU::updateFrameCounter(bool mode) {
  frameCounterMode = mode;
  for (int i = 0; i < N_PULSE_WAVES; i++) {
    pulses.at(i).updateFrameCounter(mode);
  }
  triangle.updateFrameCounter(mode);
}

void APU::resetPulse(unsigned int pulse_n) {
  pulses.at(pulse_n).reset();
}

void APU::setPulseDivider(unsigned int pulse_n, unsigned int divider) {
  pulses.at(pulse_n).setDivider(divider);
}

void APU::setPulseEnabled(unsigned int pulse_n, bool enabled) {
  pulses.at(pulse_n).setEnabled(enabled);
}

void APU::setPulseDuty(unsigned int pulse_n, float duty) {
  pulses.at(pulse_n).setDuty(duty);
}

void APU::setPulseDuration(unsigned int pulse_n, float duration) {
  pulses.at(pulse_n).setDuration(duration);
}

void APU::updatePulseSweep(unsigned int pulse_n,
                           bool enabled, unsigned int divider,
                           unsigned int shift, bool negate) {
  pulses.at(pulse_n).updateSweep(enabled, divider, shift, negate);
}

void APU::updatePulseEnvelope(unsigned int pulse_n,
                              bool loop, bool constant,
                              unsigned char timerReload) {
  pulses.at(pulse_n).updateEnvelope(loop, constant, timerReload);
}

// ctypes interface

extern "C" {

  APU *ex_initAPU(void) {
    APU *out = new APU(SAMPLE_RATE);
    out->apuInit();
    return out;
  }

  void ex_updateFrameCounter(APU *apu, unsigned char mode) {
    apu->updateFrameCounter((bool) mode);
  }

  // pulse wave interface

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

  void ex_updatePulseEnvelope(APU *apu, unsigned int pulse_n,
                              unsigned char loop, unsigned char constant,
                              unsigned char timerReload) {
    apu->updatePulseEnvelope(pulse_n, (bool) loop, (bool) constant, timerReload);
  }


  // triangle wave interface

  void ex_setTriangleEnabled(APU *apu, unsigned char enabled) {
    apu->triangle.setEnabled((bool) enabled);
  }

  void ex_setTriangleDivider(APU *apu, unsigned int divider) {
    apu->triangle.setDivider(divider);
  }

  void ex_setTriangleLinearCounterInit(APU *apu, unsigned int c) {
    apu->triangle.setLinearCounterInit(c);
  }

  void ex_setTriangleTimerHalts(APU *apu, unsigned char halt) {
    apu->triangle.setTimerHalts((bool) halt);
  }

  void ex_setTriangleLengthCounter(APU *apu, unsigned int c) {
    apu->triangle.setLengthCounter(c);
  }

  void ex_triangleLinearCounterReload(APU *apu) {
    apu->triangle.linearCounterReload();
  }
}

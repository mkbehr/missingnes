#include "portaudio.h"

#include "PulseWave.hpp"

#include <cstdio>
#include <cstdlib>
#include <string>

// Default: testing with first pitch in Donkey Kong:
// divider 427 (260.747815 Hz), 50% duty
const float TEST_DUTY = 0.5;
const unsigned int TEST_DIVIDER = 427;

const int SAMPLE_RATE = 44100;

const int DURATION = 3;

inline void checkPaError(PaError err) {
  if (err != paNoError) {
    fprintf(stderr, "PortAudio error: %s\n", Pa_GetErrorText(err));
    exit(1);
  }
}

typedef struct
{
  double t;
  float out;
}
paTestData;

static paTestData sdata;

static PulseWave pulse;

static int patestCallback( const void *inputBuffer, void *outputBuffer,
                           unsigned long framesPerBuffer,
                           const PaStreamCallbackTimeInfo* timeInfo,
                           PaStreamCallbackFlags statusFlags,
                           void *userData )
{
    paTestData *data = (paTestData*)userData;
    float *out = (float*)outputBuffer;
    unsigned int i;
    (void) inputBuffer; /* Prevent unused variable warning. */

    for( i=0; i<framesPerBuffer; i++ )
    {
      *out++ = data->out;
      *out++ = data->out;
      data->out = pulse.sample((data->t));
      data->t += ((double)1.0/(double)SAMPLE_RATE);
    }
    return 0;
}

int main(int argc, char **argv) {

  unsigned int divider = TEST_DIVIDER;
  if (argc >= 2) {
    divider = std::stoi(argv[1]);
  }
  float duty = TEST_DUTY;
  if (argc >= 3) {
    duty = std::stof(argv[2]);
  }


  pulse.setDivider(divider);
  pulse.setDuty(duty);
  pulse.setEnabled(1);

  sdata.t = 0.0;

  PaError err = Pa_Initialize();
  checkPaError(err);


  PaStream *stream;

  err = Pa_OpenDefaultStream( &stream,
                              0,          /* no input channels */
                              2,          /* stereo output */
                              paFloat32,  /* 32 bit floating point output */
                              SAMPLE_RATE,
                              256,        /* frames per buffer, i.e. the number
                                             of sample frames that PortAudio will
                                             request from the callback. Many apps
                                             may want to use
                                             paFramesPerBufferUnspecified, which
                                             tells PortAudio to pick the best,
                                             possibly changing, buffer size.*/
                              patestCallback, /* this is your callback function */
                              &sdata ); /*This is a pointer that will be passed to
                                         your callback*/
  checkPaError(err);

  err = Pa_StartStream( stream );
  checkPaError(err);

  Pa_Sleep(DURATION*1000);

  err = Pa_StopStream( stream );
  checkPaError(err);

  err = Pa_Terminate();
  checkPaError(err);
}

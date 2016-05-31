#include "stk/RtWvOut.h"
#include <cstdlib>
#include <string>

#include "PulseWave.hpp"

using namespace stk;

int main(int argc, char **argv)
{
  // Default: testing with first pitch in Donkey Kong:
  // 261.357039 Hz, 50% duty
  float frequency = 261.357039;
  if (argc >= 2) {
    frequency = std::stof(argv[1]);
  }
  float duty = 0.5;
  if (argc >= 3) {
    duty = std::stof(argv[2]);
  }

  // Set the global sample rate before creating class instances.
  Stk::setSampleRate( 44100.0 );
  Stk::showWarnings( true );
  int nFrames = 100000;

  PulseWave pulse;
  pulse.setPeriod(1.0/frequency);
  pulse.setDuty(duty);
  RtWvOut *dac = 0;
  try {
    // Define and open the default realtime output device for one-channel playback
    dac = new RtWvOut( 1 );
  }
  catch ( StkError & ) {
    exit( 1 );
  }
  for ( int i=0; i<nFrames; i++ ) {
    try {
      dac->tick( pulse.tick() );
     }
    catch ( StkError & ) {
      goto cleanup;
    }
  }
 cleanup:
  delete dac;
  return 0;
}

#include "PulseWave.hpp"

using namespace stk;

PulseWave::PulseWave(void)
  // arbitrary default for period
  : time_(0.0), rate_(1.0), duty_(0.5), enabled_(0)
{
  Stk::addSampleRateAlert(this);
}

PulseWave::~PulseWave() {
  Stk::removeSampleRateAlert(this);
}

void PulseWave :: sampleRateChanged( StkFloat newRate, StkFloat oldRate )
{
  if ( !ignoreSampleRateChange_ )
    this->setRate( oldRate * rate_ / newRate );
}

void PulseWave :: reset( void )
{
  time_ = 0.0;
  lastFrame_[0] = 0;
}

void PulseWave :: setRate(StkFloat rate) {
  rate_ = rate;
}

void PulseWave :: setPeriod( StkFloat period )
{
  // TODO: this will do strange things if time isn't zero, because the
  // relative position within the period will change. Think about
  // whether we care.
  this->setRate(PULSE_PERIOD / (period * Stk::sampleRate()));
}

void PulseWave :: setDuty(StkFloat duty) {
  duty_ = duty;
}

void PulseWave :: addTime( StkFloat time )
{
  // Add an absolute time in samples.
  time_ += time;
}

void PulseWave :: setEnabled(bool enabled) {
  enabled_ = enabled;
}

StkFloat PulseWave :: tick( void )
{
  while ( time_ < 0.0 ) {
    time_ += PULSE_PERIOD;
  }
  while ( time_ >= PULSE_PERIOD ) {
    time_ -= PULSE_PERIOD;
  }

  // TODO: there's a 1/8 period offset because that's how the NES
  // hardware works. Implement that.
  lastFrame_[0] =
    (time_ / PULSE_PERIOD) < (1.0 - duty_) ? 1.0 : 0.0;
  if (!enabled_) {
    lastFrame_[0] = 0.0;
  }
  time_ += rate_;
  return lastFrame_[0];
}

StkFrames& PulseWave :: tick( StkFrames& frames, unsigned int channel )
{
  StkFloat *samples = &frames[channel];
  StkFloat tmp = 0.0;

  unsigned int hop = frames.channels();
  for ( unsigned int i=0; i<frames.frames(); i++, samples += hop ) {
    while ( time_ < 0.0 ) {
      time_ += PULSE_PERIOD;
    }
    while ( time_ >= PULSE_PERIOD ) {
      time_ -= PULSE_PERIOD;
    }
    // TODO: there's a 1/8 period offset because that's how the NES
    // hardware works. Implement that.
    tmp = (time_ / PULSE_PERIOD) < (1.0 - duty_) ? 1.0 : 0.0;
    if (!enabled_) {
      tmp = 0.0;
    }
    *samples = tmp;
    time_ += rate_;
  }

  lastFrame_[0] = tmp;
  return frames;
}

// Note: not guaranteed to print entire state
void PulseWave::printState(void) {
  const char *enabledStr = enabled_ ? "enabled" : "disabled";
  float frequency = rate_ * Stk::sampleRate() / PULSE_PERIOD;;
  printf("Pulse wave channel %d: %s, duty %f, rate %f (%f Hz)\n",
         // dummy channel number below
         -1, enabledStr, (float) duty_, (float) rate_, frequency);
}

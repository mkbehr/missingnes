#ifndef PULSE_WAVE_H
#define PULSE_WAVE_H

#include "stk/Generator.h"

const stk::StkFloat PULSE_PERIOD = 1.0;

class PulseWave : public stk::Generator {

public:

  PulseWave( void );
  ~PulseWave( void );
  void reset( void );
  void setRate(stk::StkFloat rate);
  void setPeriod(stk::StkFloat period);
  void setDuty(stk::StkFloat duty);
  void addTime( stk::StkFloat time );
  void setEnabled(bool);
  stk::StkFloat lastOut( void ) const { return lastFrame_[0]; };
  stk::StkFloat tick( void );
  stk::StkFrames& tick( stk::StkFrames& frames, unsigned int channel = 0 );

  void printState(void);

protected:

  void sampleRateChanged( stk::StkFloat newRate, stk::StkFloat oldRate );

  stk::StkFloat rate_;
  stk::StkFloat time_;
  stk::StkFloat duty_;

  bool enabled_;

};
#endif

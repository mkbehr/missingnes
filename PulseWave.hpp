#ifndef PULSE_WAVE_H
#define PULSE_WAVE_H

class PulseWave {

public:

  PulseWave();
  void setPeriod(double period);
  void setDuty(float duty);
  void setEnabled(bool);
  float sample(double);

  void printState(void);

protected:

  double period;
  float duty;
  float envelope;
  bool enabled;

};
#endif

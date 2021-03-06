#ifndef NES_CONSTANTS_H
#define NES_CONSTANTS_H

const float CPU_FREQUENCY = 1.789773e6;

const unsigned char ENVELOPE_MAX = 0xf;

// not an NES-specificconstant, but still useful across multiple files
const float TIME_PRECISION = 1e-8;

const int FRAME_COUNTER_4STEP_LENGTH = 14915;
const int FRAME_COUNTER_5STEP_LENGTH = 18641;

#endif

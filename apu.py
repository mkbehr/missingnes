import sys

APU_FRAME_COUNTER_WARN = False
APU_WARN = False
APU_INFO = True

APU_STATUS = 0x4015
APU_FRAME_COUNTER = 0x4017

CHANNEL_ADDRESS_RANGE = 4

PULSE_1_BASE = 0x4000
PULSE_2_BASE = 0x4004
TRIANGLE_BASE = 0x4008
NOISE_BASE = 0x400c
DMC_BASE = 0x4010

PULSE_1_STATUS_MASK = 0x1
PULSE_2_STATUS_MASK = 0x2
TRIANGLE_STATUS_MASK = 0x4
NOISE_STATUS_MASK = 0x8
DMC_STATUS_MASK = 0x10

PULSE_ENVELOPE_DIVIDER_MASK = 0xf
PULSE_ENVELOPE_DIVIDER_OFFSET = 0
PULSE_CONSTANT_ENVELOPE_MASK = 0x10
PULSE_CONSTANT_ENVELOPE_OFFSET = 4
PULSE_LENGTH_HALT_MASK = 0x20
PULSE_LENGTH_HALT_OFFSET = 5
PULSE_DUTY_MASK = 0xc0
PULSE_DUTY_OFFSET = 6

PULSE_SWEEP_SHIFT_MASK = 0x7
PULSE_SWEEP_SHIFT_OFFSET = 0
PULSE_SWEEP_NEGATE_MASK = 0x8
PULSE_SWEEP_PERIOD_MASK = 0x70
PULSE_SWEEP_PERIOD_OFFSET = 4
PULSE_SWEEP_ENABLE_MASK = 0x80

PULSE_TIMER_LOW_VALUE_MASK = 0xff
PULSE_TIMER_HIGH_VALUE_MASK = 0x700
PULSE_TIMER_HIGH_VALUE_OFFSET = 8

PULSE_TIMER_HIGH_INPUT_MASK = 0x7
PULSE_LC_LOAD_MASK = 0xf8
PULSE_LC_LOAD_OFFSET = 3

PULSE_LC_TABLE = [10, 254, 20, 2,
                  40, 4, 80, 6,
                  160, 8, 60, 10,
                  14, 12, 26, 14,
                  12, 16, 24, 18,
                  48, 20, 96, 22,
                  192, 24, 72, 26,
                  16, 28, 32, 30]

class PulseChannel(object):

    # The pulse channel outputs a square wave. Seems to work roughly like this:

    # - The square wave is defined by a period, a duty, and an
    #   envelope. Period is determined by the timer and duty is
    #   determined by its own setting. Envelope has to do with the
    #   envelope flags somehow? Duty is constant, I think. Period may
    #   be modified by the sweep unit. Envelope may be modified
    #   according to the envelope divider. Sweep unit and envelope
    #   divider are clocked by the APU frame counter, which clocks
    #   every other CPU cycle. That should be quick enough that we'll
    #   need to pass the state of those things to the audio code. So
    #   the overall output from here to the C++ code should be:
    #   period, duty, envelope, sweep unit state, envelope divider
    #   state.



    def __init__(self, apu, channelID):
        self.apu = apu
        self.channelID = channelID
        self.enabled = False
        # TODO ensure these defaults are right
        self.envelopeDivider = 0
        self.constantEnvelope = True
        self.lengthCounterHalt = True
        self.duty = 0
        self.timer = 0
        self.lengthCounter = 0
        # sweep unit
        self.sweepEnabled = False
        self.sweepDividerPeriod = 1
        self.sweepNegate = 0
        self.sweepShift = 0
        self.sweepReload = False

    def setEnabled(self, enabled):
        self.enabled = enabled
        if not enabled:
            self.lengthCounter = 0
            # TODO ensure that the channel is immediately silenced

    def write(self, register, val):
        # register should be between 0 and 3 inclusive, and val should be an integer
        if register == 0: # Duty, length counter halt, envelope settings
            self.envelopeDivider = (val & PULSE_ENVELOPE_DIVIDER_MASK) >> PULSE_ENVELOPE_DIVIDER_OFFSET
            self.constantEnvelope = bool(val & PULSE_CONSTANT_ENVELOPE_MASK)
            self.lengthCounterHalt = bool(val & PULSE_LENGTH_HALT_MASK)
            self.duty = (val & PULSE_DUTY_MASK) >> PULSE_DUTY_OFFSET
            if APU_INFO:
                print >> sys.stderr, \
                    "Frame %d: APU pulse %d: divider %d, constant envelope %d, length counter halt %d, duty %d" % \
                    (self.apu.cpu.ppu.frame, self.channelID,
                     self.envelopeDivider, self.constantEnvelope, self.lengthCounterHalt, self.duty)
        elif register == 1: # Sweep unit
            self.sweepReload = True
            self.sweepShift = (val & PULSE_SWEEP_SHIFT_MASK) >> PULSE_SWEEP_SHIFT_OFFSET
            self.sweepNegate = bool(val & PULSE_SWEEP_NEGATE_MASK)
            self.sweepPeriod = 1 + ((val & PULSE_SWEEP_PERIOD_MASK) >> PULSE_SWEEP_PERIOD_OFFSET)
            self.sweepEnable = bool(val & PULSE_SWEEP_ENABLE_MASK)
            if APU_INFO:
                if self.sweepEnable:
                    print >> sys.stderr, \
                    "Frame %d: APU pulse %d sweep enabled: shift %d, negate %d, period %d" % \
                        (self.apu.cpu.ppu.frame, self.channelID,
                         self.sweepShift, self.sweepNegate, self.sweepPeriod)
                else:
                    print >> sys.stderr, \
                    "Frame %d: APU pulse %d sweep disabled" \
                    % (self.apu.cpu.ppu.frame, self.channelID)
        elif register == 2: # Timer low
            self.timer = (self.timer & PULSE_TIMER_HIGH_VALUE_MASK) + val
        elif register == 3: # Length counter load, timer high
            self.timer = (self.timer & PULSE_TIMER_LOW_VALUE_MASK) + \
                         ((val & PULSE_TIMER_HIGH_INPUT_MASK) << PULSE_TIMER_HIGH_VALUE_OFFSET)
            if self.enabled:
                lengthCounterIndex = (val & PULSE_LC_LOAD_MASK) >> PULSE_LC_LOAD_OFFSET
                self.lengthCounter = PULSE_LC_TABLE[lengthCounterIndex]
                # TODO If I'm reading the nesdev wiki's page on the
                # APU length counter right, this should also restart
                # the envelope and reset the phase.
        else:
            raise RuntimeError("Unrecognized pulse channel register")

class APU(object):

    def __init__(self, cpu):
        self.cpu = cpu
        self.pulse1 = PulseChannel(self, 1)
        self.pulse2 = PulseChannel(self, 2)
        self.triangleEnabled = False
        self.noiseEnabled = False
        self.dmcEnabled = False

    def write(self, address, val):
        if address == APU_STATUS:
            self.setStatus(ord(val))
        elif address == APU_FRAME_COUNTER:
            if APU_FRAME_COUNTER_WARN:
                print >> sys.stderr, \
                    "Frame %d: ignoring APU frame counter write: 0b%s" % \
                    (self.cpu.ppu.frame, "{0:08b}".format(ord(val)))
        elif PULSE_1_BASE <= address < (PULSE_1_BASE + CHANNEL_ADDRESS_RANGE):
            self.pulse1.write(address - PULSE_1_BASE, ord(val))
        elif PULSE_2_BASE <= address < (PULSE_2_BASE + CHANNEL_ADDRESS_RANGE):
            self.pulse2.write(address - PULSE_2_BASE, ord(val))
        elif TRIANGLE_BASE <= address < (TRIANGLE_BASE + CHANNEL_ADDRESS_RANGE):
            if APU_WARN:
                print >> sys.stderr, \
                    "Frame %d: ignoring write to APU triangle wave register 0x%04x: %02x" % \
                    (self.cpu.ppu.frame, address, ord(val))
        elif NOISE_BASE <= address < (NOISE_BASE + CHANNEL_ADDRESS_RANGE):
            if APU_WARN:
                print >> sys.stderr, \
                    "Frame %d: ignoring write to APU noise register 0x%04x: %02x" % \
                    (self.cpu.ppu.frame, address, ord(val))
        elif DMC_BASE <= address < (DMC_BASE + CHANNEL_ADDRESS_RANGE):
            if APU_WARN:
                print >> sys.stderr, \
                    "Frame %d: ignoring write to APU noise register 0x%04x: %02x" % \
                    (self.cpu.ppu.frame, address, ord(val))
        else:
            raise RuntimeError(
                "Frame %d: write to invalid APU register 0x%04x: %02x" %
                (self.cpu.ppu.frame, address, ord(val)))

    def setStatus(self, statusByte):
        # TODO: ensure that this:
        # - Silences disabled channels and sets their length counter to 0
        # - Clears the DMC interrupt flag
        # - Does whatever DMC logic it needs to do depending on the DMC bit
        self.pulse1.setEnabled(bool(statusByte & PULSE_1_STATUS_MASK))
        self.pulse2.setEnabled(bool(statusByte & PULSE_1_STATUS_MASK))
        self.triangleEnabled = bool(statusByte & TRIANGLE_STATUS_MASK)
        self.noiseEnabled = bool(statusByte & NOISE_STATUS_MASK)
        self.dmcEnabled = bool(statusByte & DMC_STATUS_MASK)
        if APU_INFO:
            channels = []
            if self.pulse1.enabled:
                channels += ["pulse wave 1"]
            if self.pulse2.enabled:
                channels += ["pulse wave 2"]
            if self.triangleEnabled:
                channels += ["triangle wave"]
            if self.noiseEnabled:
                channels += ["noise"]
            if self.dmcEnabled:
                channels += ["DMC"]
            if channels:
                print >> sys.stderr, "Frame %d: APU channels enabled: %s" % \
                    (self.cpu.ppu.frame, ", ".join(channels))
            else:
                print >> sys.stderr, "Frame %d: APU channels enabled: none" % \
                    self.cpu.ppu.frame

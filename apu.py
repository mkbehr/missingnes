import sys
import ctypes
from ctypes import CDLL, c_void_p, c_uint, c_float, c_ubyte

# TODO: note when an APU cycle starts, react (and print info)
# accordingly

APU_FRAME_COUNTER_WARN = False
APU_WARN = False
APU_INFO = False

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

FRAME_COUNTER_IRQ_INHIBIT_MASK = 0x40
FRAME_COUNTER_MODE_MASK = 0x80
FRAME_COUNTER_MODE_OFFSET = 7

PULSE_ENVELOPE_DIVIDER_MASK = 0xf
PULSE_ENVELOPE_DIVIDER_OFFSET = 0
PULSE_CONSTANT_ENVELOPE_MASK = 0x10
PULSE_CONSTANT_ENVELOPE_OFFSET = 4
PULSE_LENGTH_HALT_MASK = 0x20
PULSE_LENGTH_HALT_OFFSET = 5
PULSE_DUTY_MASK = 0xc0
PULSE_DUTY_OFFSET = 6

PULSE_DUTY_TABLE = [0.125, 0.25, 0.5, 0.75]

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

CPU_FREQUENCY = 1.789773e6
CPU_CYCLES_PER_WAVEFORM_CYCLE = 16

APU_FREQUENCY = CPU_FREQUENCY / 2.0
APU_CYCLES_PER_4STEP_FRAME = 14915
APU_CYCLES_PER_5STEP_FRAME = 18641

class CAPU(object):

    def __init__(self):
        libapu = CDLL("libapu.so")

        libapu.ex_initAPU.restype = c_void_p

        libapu.ex_resetPulse.argtypes = \
        [c_void_p, c_uint]

        libapu.ex_setPulseDivider.argtypes = \
        [c_void_p, c_uint, c_uint]

        libapu.ex_setPulseEnabled.argtypes = \
        [c_void_p, c_uint, c_ubyte]

        libapu.ex_setPulseDuty.argtypes = \
        [c_void_p, c_uint, c_float]

        libapu.ex_setPulseDuration.argtypes = \
        [c_void_p, c_uint, c_float]

        libapu.ex_updatePulseSweep.argtypes = \
        [c_void_p, c_uint, c_ubyte, c_uint, c_uint, c_ubyte]

        self.libapu = libapu

        self.apu_p = libapu.ex_initAPU()

    def resetPulse(self, pulse_n):
        self.libapu.ex_resetPulse(self.apu_p, pulse_n)

    def setPulseDivider(self, pulse_n, divider):
        self.libapu.ex_setPulseDivider(self.apu_p, pulse_n, divider)

    def setPulseEnabled(self, pulse_n, enabled):
        self.libapu.ex_setPulseEnabled(self.apu_p, pulse_n, enabled)

    def setPulseDuty(self, pulse_n, duty):
        self.libapu.ex_setPulseDuty(self.apu_p, pulse_n, duty)

    def setPulseDuration(self, pulse_n, duration):
        self.libapu.ex_setPulseDuration(self.apu_p, pulse_n, duration)

    def updatePulseSweep(self, pulse_n, enabled, divider, shift, negate):
        self.libapu.ex_updatePulseSweep(self.apu_p, pulse_n,
                                        enabled, divider, shift, negate)


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
        self.apu.capu.setPulseEnabled(self.channelID, enabled)

    def getPeriod(self):
        return ((self.timer + 2) * CPU_CYCLES_PER_WAVEFORM_CYCLE
                / CPU_FREQUENCY)

    def write(self, register, val):
        # register should be between 0 and 3 inclusive, and val should be an integer
        if register == 0: # Duty, length counter halt, envelope settings
            self.envelopeDivider = (val & PULSE_ENVELOPE_DIVIDER_MASK) >> PULSE_ENVELOPE_DIVIDER_OFFSET
            self.constantEnvelope = bool(val & PULSE_CONSTANT_ENVELOPE_MASK)
            self.lengthCounterHalt = bool(val & PULSE_LENGTH_HALT_MASK)
            self.duty = (val & PULSE_DUTY_MASK) >> PULSE_DUTY_OFFSET
            dutyFloat = PULSE_DUTY_TABLE[self.duty]
            self.apu.capu.setPulseDuty(self.channelID, dutyFloat)
            self.updateDuration()
            if APU_INFO:
                print >> sys.stderr, \
                    "Frame %d: APU pulse %d: divider %d, constant envelope %d, length counter halt %d, duty %d" % \
                    (self.apu.cpu.ppu.frame, self.channelID,
                     self.envelopeDivider, self.constantEnvelope, self.lengthCounterHalt, self.duty)
        elif register == 1: # Sweep unit
            self.sweepReload = True # This may not do anything right now
            self.sweepShift = (val & PULSE_SWEEP_SHIFT_MASK) >> PULSE_SWEEP_SHIFT_OFFSET
            self.sweepNegate = bool(val & PULSE_SWEEP_NEGATE_MASK)
            self.sweepPeriod = 1 + ((val & PULSE_SWEEP_PERIOD_MASK) >> PULSE_SWEEP_PERIOD_OFFSET)
            self.sweepEnable = bool(val & PULSE_SWEEP_ENABLE_MASK)
            self.apu.capu.updatePulseSweep(self.channelID, self.sweepEnable,
                                           self.sweepPeriod, self.sweepShift,
                                           int(self.sweepNegate))
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
        elif register == 2: # Timer low (note: does not reset phase or envelope)
            self.timer = (self.timer & PULSE_TIMER_HIGH_VALUE_MASK) + val
            self.apu.capu.setPulseDivider(self.channelID, self.timer)
            if APU_INFO:
                if self.timer < 8:
                    freq_string = "silent"
                else:
                    freq_string = "%f Hz" % \
                                  (CPU_FREQUENCY / (CPU_CYCLES_PER_WAVEFORM_CYCLE * (self.timer + 2)))
                print >> sys.stderr, \
                    "Frame %d: APU pulse %d timer %d after low bits (%s)" \
                    % (self.apu.cpu.ppu.frame, self.channelID,
                       self.timer, freq_string)
        elif register == 3: # Length counter load, timer high
            self.timer = (self.timer & PULSE_TIMER_LOW_VALUE_MASK) + \
                         ((val & PULSE_TIMER_HIGH_INPUT_MASK) << PULSE_TIMER_HIGH_VALUE_OFFSET)
            self.apu.capu.setPulseDivider(self.channelID, self.timer)
            if self.enabled:
                lengthCounterIndex = (val & PULSE_LC_LOAD_MASK) >> PULSE_LC_LOAD_OFFSET
                self.lengthCounter = PULSE_LC_TABLE[lengthCounterIndex]
                self.updateDuration()
                # As a side effect, this restarts the envelope and
                # resets the phase.
                self.apu.capu.resetPulse(self.channelID)
            if APU_INFO:
                # not printing length counter info for now
                if self.timer < 8:
                    freq_string = "silent"
                else:
                    freq_string = "%f Hz" % \
                                  (CPU_FREQUENCY / (CPU_CYCLES_PER_WAVEFORM_CYCLE * (self.timer + 2)))
                # Length counter is clocked by the frame counter,
                # twice per APU frame. The duration of an APU frame
                # depends on the sequencer mode, which is set by the
                # frame counter.

                # TODO: In the five-step sequence, the frame counter
                # clocks things at uneven intervals. That might matter somewhere.
                duration = self.lengthCounter * self.apu.frameDuration() / 2.0
                print >> sys.stderr, \
                    "Frame %d: APU pulse %d timer %d after high bits (%s); length counter %d (%fs)" \
                    % (self.apu.cpu.ppu.frame, self.channelID,
                       self.timer, freq_string, self.lengthCounter, duration)
        else:
            raise RuntimeError("Unrecognized pulse channel register")

    def updateDuration(self):
        # TODO: Fix to more accurately reflect NES behavior. This sets
        # a duration, but there should actually be a length counter
        # that counts down unless lengthCounterHalt is set.
        if self.lengthCounterHalt:
            duration = -1.0 # infinite duration
        else:
            duration = self.lengthCounter * self.apu.frameDuration() / 2.0
        self.apu.capu.setPulseDuration(self.channelID, duration)


class APU(object):

    def __init__(self, cpu):
        self.cpu = cpu
        self.pulse1 = PulseChannel(self, 0)
        self.pulse2 = PulseChannel(self, 1)
        self.triangleEnabled = False
        self.noiseEnabled = False
        self.dmcEnabled = False
        self.fcMode = 0
        self.fcIRQInhibit = False

        self.capu = CAPU()

    def write(self, address, val):
        if address == APU_STATUS:
            self.setStatus(ord(val))
        elif address == APU_FRAME_COUNTER:
            self.fcMode = (ord(val) & FRAME_COUNTER_MODE_MASK) >> FRAME_COUNTER_MODE_OFFSET
            self.fcIRQInhibit = not bool(ord(val) & FRAME_COUNTER_IRQ_INHIBIT_MASK)
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

    def frameDuration(self):
        if not self.fcMode:
            return APU_CYCLES_PER_4STEP_FRAME / APU_FREQUENCY
        else:
            return APU_CYCLES_PER_5STEP_FRAME / APU_FREQUENCY
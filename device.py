from collections import deque
from util import NamedDescriptor, NamedMeta, configable
from math import sin, floor, pi, log10
from numbers import Number

_tau = 2*pi

class SpaceTimeContinuumError (Exception):
  pass

class Signal (metaclass=NamedMeta):
  """
  Signals normally operate over [-1,1]. A subclass may change this.
  """

  #last_t = -1
  #last_samp = None

  def __call__ (self, t):
    """
    Sample this signal at time index t. Each call to sample must be with a
    larger value for t.
    """
    #if t <= self.last_t:
      #raise SpaceTimeContinuumError(
        #"We're moving back in time! Last t = {}, now = {}".format(
          #self.last_t, t))

    #samp = self._sample(t)
    #self.last_t = t
    #self.last_samp = samp
    #return samp
    pass

class Const (Signal):
  def __init__ (self, val):
    self.val = val if val is not None else 0

  def __call__ (self, t):
    return self.val

def asInput (input, type=None, const_type=Const, **kwargs):
  if not isinstance(input, Signal):
    if const_type is None:
      # TODO: This None -> 0 conversion is hacky
      if input is None:
        input = 0
      return input
    else:
      input = const_type(input)

  if type and not isinstance(input, type):
    input = type(input, **kwargs)

  return input

class Input (NamedDescriptor):
  def __init__ (self, type=None, const_type=Const, **kwargs):
    self.type = type
    self.const_type = const_type
    self.kwargs = kwargs

  def __set__ (self, instance, value):
    super().__set__(instance, asInput(value, self.type,
                                      const_type=self.const_type,
                                      **self.kwargs))

class FrequencySignal (Signal):
  """
  Frequency channels operate over [0,11000]
  """
  input = Input()

  def __init__ (self, input):
    self.input = input

  def __call__ (self, t):
    return (self._input(t)+1)*5500

class ConstFrequency (Const, FrequencySignal):
  def __init__ (self, val):
    if isinstance(val, Number) and  -1 <= val <= 1:
      val = (val+1)*5500
    super().__init__(val)

class TriggerSignal (Signal):
  """
  Outputs a sample of 1 for one sample when the input signal crosses the
  threshold. Only after the input signal has dropped below the threshold will
  the TriggerSignal be ready to be triggered again.
  """
  input = Input()
  thresh = Input()

  def __init__ (self, input, thresh=0.5):
    self.input = input
    self.thresh = thresh
    self.hot = False

  def __call__ (self, t):
    samp = self.input(t)
    thresh = self.thresh(t)

    if not self.hot and samp >= thresh:
      self.hot = True
      return 1

    if self.hot and samp < thresh:
      self.hot = False

    return 0

class Trigger (TriggerSignal):
  def __init__ (self):
    self.firing = False

  def fire (self):
    self.firing = True

  def __call__ (self, t):
    if self.firing:
      self.firing = False
      return 1
    return 0

class GateSignal (Signal):
  """
  Outputs a sample of 1 if the input signal is >= the threshold, otherwise the
  output is 0.
  """
  input = Input()
  thresh = Input()

  def __init__ (self, input, thresh=0.5):
    self.input = input
    self.thresh = thresh

  def __call__ (self, t):
    return 0 if self.input(t) < self.thresh(t) else 1

class Gate (GateSignal):
  def __init__ (self):
    self.open = 0

  def on (self):
    self.open = 1

  def off (self):
    self.open = 0

  def __call__ (self, t):
    return self.open

class PositiveSignal (Signal):
  input = Input()

  def __init__ (self, input):
    self.input = input

  def __call__ (self, t):
    return (self._input(t) + 1)/2

class LinearRamp (Signal):
  def __init__ (self, t_start, dur):
    self.t_start = t_start
    self.dur = dur

  def __call__ (self, t):
    if t < self.t_start:
      return -1
      #return 0
    if t > self.t_start + self.dur:
      return 1

    return (t - self.t_start) / self.dur * 2 - 1
    #return (t - self.t_start) / self.dur

class PolyRamp (Signal):
  def __init__ (self, t_start, dur, power=2):
    self.t_start = t_start
    self.dur = dur
    self.power = power

  def __call__ (self, t):
    if t < self.t_start:
      return -1
    if t > self.t_start + self.dur:
      return 1

    return ((t - self.t_start)/self.dur)**self.power * 2 - 1

class ExpRamp (Signal):
  def __init__ (self, t_start, dur):
    self.t_start = t_start
    self.dur = dur

  def __call__ (self, t):
    if t < self.t_start:
      return -1
    if t > self.t_start + self.dur:
      return 1

    return (10**((t - self.t_start)/self.dur) - 1)/9 * 2 - 1

class LogRamp (Signal):
  def __init__ (self, t_start, dur):
    self.t_start = t_start
    self.dur = dur

  def __call__ (self, t):
    if t < self.t_start:
      return -1
    if t > self.t_start + self.dur:
      return 1

    return log10(((t - self.t_start)/self.dur)*9 + 1) * 2 - 1


class ADSREnvelope (PositiveSignal):
  A = Input()
  D = Input()
  S = Input()
  R = Input()
  trigger = Input(TriggerSignal)
  gate = Input(GateSignal)

  def __init__ (self, A=None, D=None, S=None, R=None, trigger=None,
                gate=None):
    self.A = A
    self.D = D
    self.S = S
    self.R = R
    self.trigger = trigger
    self.gate = gate

    self.start_A = None
    self.start_R = None
    self.last_samp = 0
    self.last_t = -1/DEFAULT_SAMPLERATE


  def __call__ (self, t):
    trigger = self._trigger(t)
    gate = self._gate(t)
    if trigger:
      self.start_A = t
      self.start_R = None

    samp = 0
    S = self._S(t)
    if gate:
      A = self._A(t)
      D = self._D(t)
      start_D = self.start_A + A
      start_S = start_D + D
      if self.start_A <= t < start_D:
        # Attack
        samp = (self.last_samp +
                (1 - self.last_samp)/(self.start_A + A - t)*(t - self.last_t))
      elif start_D <= t < start_S:
        # Decay
        samp = 1 - (t - start_D)*(1-S)/D
      else:
        # Sustain
        samp = S
    elif self.last_samp:
      # Release...
      if not self.start_R:
        self.start_R = t

      R = self._R(t)
      if self.start_R <= t < self.start_R + R:
        samp = (self.last_samp -
                self.last_samp/(self.start_R + R - t)*(t - self.last_t))

    self.last_samp = samp
    self.last_t = t
    return samp

def p2f (p):
  """
  Pitch signal is defined in the range [-1,1].
  """
  #return 11000**((p+1)/2)
  #return (p+1)*11000
  return (p+1)*5500

def f2p (f):
  """
  #Frequency signal is defined in the range [0,22000]
  Frequency signal is defined in the range [0,11000]
  """
  #return 2*math.log(f, 11000) - 1
  #return f/11000 - 1
  return f/5500 - 1

class PhasedSignal (Signal):
  #freq = Input(FrequencySignal, const_type=ConstFrequency)
  freq = Input(FrequencySignal, const_type=None)

  def __init__ (self, freq=None):
    self.freq = freq
    self.pa = 0
    self.last_t = 0

  def __call__ (self, t):
    dt = t - self.last_t
    self.last_t = t
    f = self._freq
    if callable(f):
      f = f(t)
    df = floor(dt*f * 2.0**24)
    self.pa = (self.pa + df) & 0xFFFFFF
    return self._phase[self.pa >> 14]

class Sine (PhasedSignal):
  _phase = [sin(_tau*p/1024) for p in range(1024)]

class Saw (PhasedSignal):
  _phase = [1 - 2*p/1024 for p in range(1024)]

class Square (PhasedSignal):
  _phase = [1 if p/1024 < 1/2 else -1 for p in range(1024)]

class Triangle (PhasedSignal):
  _phase = [2*abs(Saw._phase[(p - 256) % 1024]) - 1 for p in range(1024)]

class Amp (Signal):
  input = Input()
  ratio = Input(PositiveSignal)

  def __init__ (self, ratio, input):
    self.ratio = ratio
    self.input = input

  def __call__ (self, t):
    return self._ratio(t) * self._input(t)

def Mult (factor, carrier):

  class Mult (type(carrier)):
    left = Input()
    right = Input()

    def __init__ (self, left, right):
      self.left = left
      self.right = right

    def __call__ (self, t):
      return self._left(t) * self._right(t)

  return Mult(factor, carrier)

class Bias (Signal):
  input = Input()
  offset = Input()

  def __init__ (self, offset, input):
    self.offset = offset
    self.input = input

  def __call__ (self, t):
    return self._offset(t) + self._input(t)

class Sequence (Signal):
  def __init__ (self, steps=[]):
    self.steps = iter(steps)
    self.until = -1

    self.trigger = Trigger()
    self.gate = Gate()

  def __call__ (self, t):
    if t > self.until:
      try:
        next_value, dur = next(self.steps)
        print('Sequence:', next_value, dur)
        self.until = t + dur
      except StopIteration:
        next_value = None
        self.until = -1

      if next_value is None:
        self.gate.off()
        # Keep our previous self.value
      else:
        self.trigger.fire()
        self.gate.on()
        self.value = next_value

    return self.value

class FrequencySequence (Sequence, FrequencySignal):
  pass

def Synth (steps=[], oscillator=Sine, modifier=None,
           A=0.1, D=0.1, S=0.5, R=0.1):
  sequencer = FrequencySequence(steps)
  freq_input = sequencer
  if callable(modifier):
    freq_input = modifier(freq_input)
  oscillator = oscillator(freq_input)
  envelope = ADSREnvelope(A, D, S, R, sequencer.trigger, sequencer.gate)
  return Amp(envelope, oscillator)

def AMSynth (input, factor=2):
  carrier = Sine(input)
  modulator = Sine(Mult(factor, input))
  return Amp(modulator, carrier)

def RMSynth (input, freq=50):
  carrier = Sine(input)
  modulator = Sine(freq)
  return Mult(modulator, carrier)

@configable
def Vibrato (input, freq=6, cents=50):
  modulator = Bias(1, Mult(0.0005946*cents, Sine(freq)))
  return Mult(modulator, input)

def Mixer (synths):
  numSamps = len(synths)
  def output (t):
    return sum(synth(t) for synth in synths)/numSamps

  return output


def Sampler (input, sample_rate, dur=None):
  sample_dur = 1/sample_rate
  t = 0

  while True:
    yield input(t)

    t += sample_dur

    if dur and t > dur:
      break

CHANNELS = 1
DEFAULT_SAMPLERATE = 44100//2

def play (input, dur):
  import alsaaudio
  from util import chunk

  out = alsaaudio.PCM()
  out.setchannels(CHANNELS)
  out.setformat(alsaaudio.PCM_FORMAT_S16_LE)
  SAMPLERATE = out.setrate(DEFAULT_SAMPLERATE)
  print(SAMPLERATE)
  ALSAPERIOD = out.setperiodsize(SAMPLERATE//4)

  total = 0
  for bs in chunk(Sampler(input, SAMPLERATE, dur), ALSAPERIOD*CHANNELS):
    wrote = out.write(bs)
    total += wrote
    print(wrote, total)
    if wrote != ALSAPERIOD:
      print("Huh? Only wrote {}/{}".format(wrote, ALSAPERIOD))

  print('Closing...')
  out.close()

def write (input, dur, filename='out.wav'):
  import wave, array
  from util import byte_array

  bytes = byte_array(Sampler(input, DEFAULT_SAMPLERATE, dur))
  #bytes = array.array('f', Sampler(input, DEFAULT_SAMPLERATE*2, dur))

  #f = wave.open(filename, 'w')
  #f.setnchannels(CHANNELS)
  #f.setsampwidth(2)
  #f.setframerate(DEFAULT_SAMPLERATE)
  #f.setcomptype('NONE', 'not compressed')
  #f.setnframes(len(bytes))
  #f.writeframesraw(bytes)
  #print(f._datawritten, f._nframeswritten)
  #f.close()

  with open(filename + '.raw', 'wb') as rf:
    rf.write(bytes)

def generate (input, dur):
  """ For profiling. """
  return list(Sampler(input, DEFAULT_SAMPLERATE, dur))

def random_walk ():
  import random
  freq = 440

  while True:
    if random.random() < 1/5:
      yield (None, 0.25)
    else:
      yield (freq, 0.25)
      steps = random.randint(-12, 12)
      freq *= 2**(steps/12)



if __name__ == '__main__':
  synth = Synth(modifier=Vibrato(freq=3.2), A=0.13, D=0.03, S=0.5, R=0.5,
    steps = (
    (440, 0.25),
    (440 * 2**(2/12), 0.25),
    (440 * 2**(3/12), 0.25),
    (None, 1.25),
    (220, 0.25),
    (220 * 2**(2/12), 0.25),
    (220 * 2**(3/12), 0.25),
  ))
  play(synth, 4)


  #rw = random_walk()
  #synth.steps = iter([next(rw) for x in range(40)] + [(None, 0.5)])
  #write(synth, 10.5)

  #import guitar_wave
  #class Guitar (PhasedSignal):
    #_phase = guitar_wave.data

  #from music import PianoRoll
  #import tabreader
  #synths = [Synth(steps=PianoRoll(33, n), oscillator=Guitar(), A=0.03, D=0.05,
                  #R=0.05)
            #for n in tabreader.read(tabreader.ex_tabs)]
  #play(Mixer(synths), 10) #38)

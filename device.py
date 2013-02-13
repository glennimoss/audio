from collections import deque
from util import NamedDescriptor, NamedMeta
from math import sin, floor, pi
_tau = 2*pi

class Input (NamedDescriptor):
  def __init__ (self, type=None):
    self.type = type

  def __set__ (self, instance, value):
    if not isinstance(value, Signal):
      value = Const(value)
    if self.type and not isinstance(value, self.type):
      value = self.type(value)
    super().__set__(instance, value)

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

class FrequencySignal (Signal):
  """
  Frequency channels operate over [0,11000]
  """
  input = Input()

  def __init__ (self, input):
    self.input = input
    self.convert = not (
      (isinstance(self.input, Const) and self.input.val > 1) or
      (isinstance(self.input, FrequencySignal)))
      #self._sample = input._sample
      #self.__call__ = input.__call__

  def __call__ (self, t):
    if self.convert:
      return (self.input(t)+1)*5500
    return self.input(t)

class Const (Signal):
  def __init__ (self, val):
    self.val = val

  def __call__ (self, t):
    return self.val

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
  thresh = Thresh()

  def __init__ (self, input, thresh=0.5):
    self.input = input
    self.thresh = thresh

  def __call__ (self, t):
    return 0 if self.input(t) < self.thresh(t) else 1

class Gate (GateSignal):
  def __init__ (self):
    self.open = False

  def on (self):
    self.open = True

  def off (self):
    self.open = False

  def __call__ (self, t):
    return self.open*1


class ADSREnvelope (Signal):
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
    self.last_samp = None


  def __call__ (self, t):
    trigger = self.trigger(t)
    gate = self.gate(t)
    if trigger:
      self.start_A = t
      #self.start_D = t + self.A(t)
      #self.start_S = self.start_D + self.D(t)

    samp = None
    if gate:
      A = self.A(t)
      D = self.D(t)
      start_D = self.startA + A
      start_S = start_D + D
      if self.start_A <= t < start_D:
        # Attack
        samp = (t - self.start_A) / A
      elif start_D <= t < start_S:
        # Decay
        samp = 1 - (t - start_D) / D
      else:
        # Sustain
        samp = self.S
    elif self.last_samp is not None:
      # Release...
      if not self.start_R:
        self.start_R = t

      R = self.R(t)
      if self.start_R <= t < self.start_R + R:
        samp = self.S * (1 - (t - self.start_R) / R)

    self.last_samp = samp
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
  freq = Input(FrequencySignal)

  def __init__ (self, pitch=None):
    self.freq = pitch
    self.pa = 0
    self.last_t = 0

  def __call__ (self, t):
    dt = t - self.last_t
    self.last_t = t
    f = self._freq(t)
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
  ratio = Input()

  def __init__ (self, ratio, input):
    self.ratio = ratio
    self.input = input

  def __call__ (self, t):
    return self._ratio(t) * self._input(t)

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
    self.steps = deque(steps)
    self.until = 0
    self._next_step()

  def _next_step (self):
    self.input, dur = self.steps.popleft()
    self.until += dur

  def append (self, input, dur):
    self.steps.append((input, dur))

  def extend (self, steps)
    self.steps.extend(steps)

  def __call__ (self, t):
    if t > self.until:
      self._next_step()

    return self.input(t)

class Synth (Sequence):
  oscillator = Input()
  envelope = Input()

  def __init__ (self, oscillator=Sine):
    self.oscillator = oscillator
    self.env_trigger = Trigger()
    self.env_gate = Gate()
    self.envelope = ADSREnvelope(100, 100, 0.8, 100, self.env_trigger,
                                 self.env_gate)
    self.output = Amp(self.envelope, self.seq)

  def __call__ (self, t):
    self.oscillator


def Sampler (input, sample_rate, dur=None):
  sample_dur = 1/sample_rate
  t = 0

  while True:
    yield input(t)

    t += sample_dur

    if dur and t > dur:
      break

CHANNELS = 1
DEFAULT_SAMPLERATE = 44100

def play (input, dur):
  import alsaaudio
  from util import chunk

  out = alsaaudio.PCM()
  out.setchannels(CHANNELS)
  out.setformat(alsaaudio.PCM_FORMAT_S16_LE)
  SAMPLERATE = out.setrate(DEFAULT_SAMPLERATE)
  print(SAMPLERATE)
  ALSAPERIOD = out.setperiodsize(int(SAMPLERATE/4))

  total = 0
  for bs in chunk(Sampler(input, SAMPLERATE, dur), ALSAPERIOD*CHANNELS):
    wrote = out.write(bs)
    total += wrote
    print(wrote, total)
    if wrote != ALSAPERIOD:
      print("Huh? Only wrote {}/{}".format(wrote, ALSAPERIOD))

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
  return list(Sampler(input, DEFAULT_SAMPLERATE, dur))


if __name__ == '__main__':
  #print([x for x in Sampler(Sine(Const(f2p(440))),
  #play(Sine(Const(f2p(440))), 2)
  #play(Sine(Saw(Const(f2p(1/2)))), 2)
  #write(Sine(Saw(Const(f2p(1/2)))), 2)
  #play(Sine(lambda t: t - 1 ), 2)
  #write(Sine(Saw(Const(f2p(1/10)))), 10)
  #write(Sine(lambda t: math.floor((t/5-1)*10)/10 ), 10)
  #play(Sine(lambda t: t/5 - 1 ), 10)
  #play(Saw(lambda t: math.floor((t/5-1)*10)/10.0 ), 10)
  #write(Sine(lambda t: 22000**(t/10) ), 10)
  #write(Sine(Const(f2p(20000))), 2)

  #play(Sequence((
    #(Sine(f2p(440)), 2),
    #(Const(0), 2),
  #)), 4)

  #play(Sine(Bias(-0.95, Amp(0.005, Square(2)))), 2)
  #play(Sine(60), 2)
  play(Amp(Bias(0.5, Amp(0.25, Sine(2))), Sequence((
    (Triangle(220), 2),
    (Sine(220), 2),
  ))), 4)


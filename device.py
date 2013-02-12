import math
_tau = 2*math.pi

"""
All inputs and outputs should be [-1, 1]
"""

class InputSignal:
  n = 0

  def __init__ (self):
    self.varname = '_sig{}'.format(InputSignal.n)
    InputSignal.n += 1

  def __get__ (self, instance, owner):
    return getattr(instance, self.varname)

  def __set__ (self, instance, value):
    if not isinstance(value, Signal):
      value = Const(value)
    setattr(instance, self.varname, value)

class FrequencySignal (InputSignal):

  def __get__ (self, instance, owner):
    return lambda t: p2f(getattr(instance, self.varname)(t))

class SpaceTimeContinuumError (Exception):
  pass

class Signal:
  last_t = -1
  last_samp = None

  def sample (self, t):
    """
    Sample this signal at time index t. Each call to sample must be with a
    larger value for t.
    """
    if t <= self.last_t:
      import pdb;pdb.set_trace()
      raise SpaceTimeContinuumError(
        "We're moving back in time! Last t = {}, now = {}".format(
          self.last_t, t))

    samp = self._sample(t)
    self.last_t = t
    self.last_samp = samp
    return samp

  def __call__ (self, t):
    return self.sample(t)


class Const (Signal):
  def __init__ (self, val):
    self.val = val

  def _sample (self, t):
    return self.val

class TriggerSignal (Signal):
  """
  Outputs a sample of 1 for one sample when the input signal crosses the
  threshold. Only after the input signal has dropped below the threshold will
  the TriggerSignal be ready to be triggered again.
  """

  def __init__ (self, input, thresh):
    self.input = input
    self.thresh = thresh
    self.hot = False

  def _sample (self, t):
    samp = self.input(t)

    if not self.hot and samp >= self.thresh:
      self.hot = True
      return 1

    if self.hot and samp < self.thresh:
      self.hot = False

    return 0


class GateSignal (Signal):
  """
  Outputs a sample of 1 if the input signal is >= the threshold, otherwise the
  output is 0.
  """

  def __init__ (self, input, thresh):
    self.input = input
    self.thresh = thresh

  def _sample(self, t):
    return 0 if self.input(t) < self.thresh else 1



class ADSREnvelope (Signal):
  def __init__ (self, A=None, D=None, S=None, R=None, trigger=None,
                trigger_thresh=0.5, gate=None, gate_thresh=0.5):
    self.A = A
    self.D = D
    self.S = S
    self.R = R
    self.trigger = TriggerSignal(trigger, trigger_thresh)
    self.gate = GateSignal(gate, gate_thresh)

    self.start_A = None
    self.start_D = None
    self.start_S = None
    self.start_R = None

  def _sample (self, t):
    trigger = self.trigger(t)
    gate = self.gate(t)
    if trigger:
      self.start_A = t
      self.start_D = t + self.A
      self.start_S = self.start_D + self.D

    if gate:
      if self.start_A <= t < self.start_D:
        # Attack
        return (t - self.start_A) / self.A
      elif self.start_D <= t < self.start_S:
        # Decay
        return 1 - (t - self.start_D)/self.D
      else:
        # Sustain
        return self.S
    elif self.last_samp:
      # Release...
      if not self.start_R:
        self.start_R = t

      if self.start_R <= t < self.start_R + self.R:
        return self.S * (1 - (t - self.start_R)/self.R)

    return 0

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
  freq = FrequencySignal()

  def __init__ (self, pitch=None):
    self.freq = pitch
    self.pa = 0

  def _sample (self, t):
    dt = t - self.last_t
    f = self.freq(t)
    self.pa = (self.pa + dt*f) % 1

    return self._phase(self.pa)


  def _phase (self, p):
    """ Amplitude [-1,1] at phase [0,1] for this waveform. """
    pass

class Sine (PhasedSignal):
  def _phase (self, p):
    return math.sin(_tau*p)

class Saw (PhasedSignal):
  def _phase (self, p):
    return 1 - 2*p

class Square (PhasedSignal):
  def _phase (self, p):
    return 1 if p < 1/2 else -1

class Triangle (Saw):
  def _phase (self, p):
    return 2*abs(super()._phase((p - 1/4) % 1)) - 1

class Amp (Signal):
  input = InputSignal()
  ratio = InputSignal()

  def __init__ (self, ratio, input):
    self.ratio = ratio
    self.input = input

  def _sample (self, t):
    return self.ratio(t) * self.input(t)

class Bias (Signal):
  input = InputSignal()
  offset = InputSignal()

  def __init__ (self, offset, input):
    self.offset = offset
    self.input = input

  def _sample (self, t):
    return self.offset(t) + self.input(t)

class Sequence (Signal):
  def __init__ (self, steps):
    self.steps = iter(steps)
    self.start = 0
    self._next_step()

  def _next_step (self):
    self.input, self.dur = next(self.steps)

  def _sample (self, t):
    if t > self.start + self.dur:
      self._next_step()
      self.start = t

    return self.input(t)


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
  play(Amp(Bias(0.5, Amp(0.25, Square(f2p(2)))), Sequence((
    (Triangle(f2p(220)), 2),
    (Sine(f2p(220)), 2),
  ))), 4)
  #print([p2f(x) for x in Sampler(Sine(Const(1)), 4, 2)])

import math
from util import cimethod

SAMPLERATE = 0
SAMPLEDUR = 0

_clamp = lambda x,l,h: min(max(l,x), h)
_tau = 2*math.pi

class Silence:

  @staticmethod
  def gen (dur):
    """
    A generator of data for this sound at a given freqency and samplerate for
    the specified duration.

    freq -> Note frequency.
    dur -> Duration in seconds
    samplerate -> Sample points generated per second of duration.
    """

    for _ in range(int(SAMPLERATE * dur)):
      yield 0

class PeriodicWave:

  @classmethod
  def _sample (cls, t):
    return 0

  @classmethod
  def one_period (cls):
    return [cls._sample(t) for t in (0,0.125,0.25,0.375,0.5,0.625,0.75,0.875,1)]

  @cimethod
  def gen (cls, freq, dur):
    period = int(SAMPLERATE / freq)
    data = [cls._sample(i/period) for i in range(period)]
    for i in range(int(SAMPLERATE * dur)):
      yield data[i % period]

class SineWave (PeriodicWave):
  @classmethod
  def _sample (cls, t):
    return math.sin(_tau*t)
#print('SineWave', SineWave().one_period())

class SquareWave (PeriodicWave):
  def __init__ (self, duty=0.5):
    self.duty = _clamp(duty, 0, 1)

  #def gen (self, freq, dur):
    #return PeriodicWave.gen(self, freq, dur)

  def _sample (self, t):
    return (t <= self.duty) - (t > self.duty)

#print('SquareWave', SquareWave().one_period())

class SawtoothWave (PeriodicWave):
  @classmethod
  def _sample (cls, t):
    t = (t - 0.5) % 1
    return 2 * t - 1
#print('SawtoothWave', SawtoothWave().one_period())

class TriangleWave (SawtoothWave):
  @classmethod
  def _sample (cls, t):
    t = (t + 0.25) % 1
    return 2*abs(super()._sample(t)) - 1
#print('TriangleWave', TriangleWave().one_period())


class Envelope:
  def __init__ (self, attack, decay, sustain, release):
    """
    sound: Sound object to envelop.
    attack: in millis
    decay: in millis
    sustain: [0,1] ration to amplitude
    release: in millis
    """
    self.attack = attack
    self.decay = decay
    self.sustain = sustain
    self.release = release

  def gen (self, sound, freq, dur):
    decay_idx = self.attack + self.decay
    release_idx = dur*1000 - self.release
    idx = 0
    for samp in sound.gen(freq, dur):
      if idx < self.attack:
        factor = idx/self.attack
      elif idx < decay_idx:
        factor = 1 - (idx - self.attack)/self.decay*(1 - self.sustain)
      elif idx < release_idx:
        factor = self.sustain
      else:
        factor = self.sustain - (idx - release_idx)/self.release*self.sustain

      yield samp*factor
      idx += SAMPLEDUR

class FMSynth (PeriodicWave):
  def __init__ (self, I, H):
    self.I = I
    self.H = H

  def _sample (self, t):
    return math.sin(_tau*t + self.I*math.sin(_tau*self.H*t))

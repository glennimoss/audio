import sys, wave, math, struct, random, array, re, alsaaudio
from itertools import *

DEFAULT_SAMPLERATE = 44100
DEFAULT_ALSAPERIOD = 320

tau = 2*math.pi

clamp = lambda x,l,h: min(max(l,x), h)
int16 = lambda f: int(f * 32767)

A4 = 440.0
dist_A4 = {
  'C': -9,
  'D': -7,
  'E': -5,
  'F': -4,
  'G': -2,
  'A': 0,
  'B': 2,
}
note_re = re.compile(r'([ABCDEFG])(#*|b*)(\d+)')

def freq (note):
  m = note_re.match(note)
  scale, accidental, octave = m.groups()
  octave = int(octave)

  halfs = dist_A4[scale] + (octave - 4)*12 + (-1 if accidental.startswith('b') else 1)*len(accidental)
  return A4 * 2**(halfs/12)

class Sound:

  def __init__ (self, data=None, samplerate=DEFAULT_SAMPLERATE):
    self.samplerate = samplerate
    self.data = data

  def for_ (self, sec):
    return islice(cycle(self.data), int(sec*self.samplerate))

class PeriodicWave (Sound):

  def __init__ (self, note='A4', amp=0.5, **kwargs):
    super().__init__(**kwargs)
    self.freq = freq(note)
    self.amp = clamp(float(amp), 0, 1)

    period = int(self.samplerate / self.freq)
    self.data = [int16(self._sample(i/period)) for i in range(period)]

  def _sample (self, t):
    return 0

  def one_period (self):
    return [self._sample(t) for t in (0,0.125,0.25,0.375,0.5,0.625,0.75,0.875,1)]

  def synthesize (self, ):
    pass

class SineWave (PeriodicWave):
  def _sample (self, t):
    return self.amp * math.sin(tau*t)
print('SineWave', SineWave().one_period())

class SquareWave (PeriodicWave):
  def __init__ (self, duty=0.5, **kwargs):
    self.duty = clamp(duty, 0, 1)
    super().__init__(**kwargs)

  def _sample (self, t):
    return self.amp * (t <= self.duty) - self.amp * (t > self.duty)
print('SquareWave', SquareWave().one_period())

class SawtoothWave (PeriodicWave):
  def _sample (self, t):
    t = (t - 0.5) % 1
    return 2*self.amp * t - self.amp
print('SawtoothWave', SawtoothWave().one_period())

class TriangleWave (SawtoothWave):
  def _sample (self, t):
    t = (t + 0.25) % 1
    return 2*abs(super()._sample(t)) - self.amp
print('TriangleWave', TriangleWave().one_period())


CHANNELS = 2
samples = array.array('h')
for samp in chain(SineWave().for_(0.5),
                  SquareWave().for_(0.5),
                  SawtoothWave().for_(0.5),
                  TriangleWave().for_(0.5),
                 ):
  samples.extend([samp]*CHANNELS)

samples.extend([0] * (DEFAULT_ALSAPERIOD - (len(samples) %
                                            DEFAULT_ALSAPERIOD))*CHANNELS)

"""
samples = array.array('h', chain(SineWave().for_(0.5),
                                 SquareWave().for_(0.5),
                                 SawtoothWave().for_(0.5),
                                 TriangleWave().for_(0.5),
                                ))
"""

out = alsaaudio.PCM()
out.setchannels(CHANNELS)
out.setformat(alsaaudio.PCM_FORMAT_S16_LE)
out.setperiodsize(DEFAULT_ALSAPERIOD)

print("about to write", len(samples), len(samples)//CHANNELS)
i = 0
while i < len(samples):
  wrote = out.write(samples[i:]) #i+DEFAULT_ALSAPERIOD*CHANNELS])
  print(wrote)
  i += wrote*CHANNELS

#print(len(samples), out.write(samples))
print("written")

out.close()
print("closed")

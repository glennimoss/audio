import sys, wave, math, struct, random, array, re, alsaaudio, operator
from itertools import islice
from music import *
import sounds, tabreader
from sounds import *

_CHANNELS = 1
_DEFAULT_SAMPLERATE = 44100


_int16 = lambda f: int(f * 32767)

class Patch:

  def __init__ (self, input, filter):
    pass

def Player (tempo, sound, env, notes):
  """
  Tempo is in bars/min. Whereas 120bpm usually means 120 quarter notes per
  minute, we would say 40 bars/min. This makes tempo independent of time
  signature.
  """
  beat = 60 / tempo
  for pitch, size in notes:
    dur = beat * size

    for sample in (env.gen(sound, pitch, dur) if pitch else Silence.gen(dur)):
      yield sample

def MultiPlayer (tempo, sound, env, musics):
  for samples in zip(*(Player(tempo, sound, env, notes) for notes in musics)):
    yield sum(samples)/len(samples)



class Mixer:

  def __init__ (self, *args):
    self.inputs = []
    for arg in args:
      try:
        input, weight = arg
        self.inputs.append((input, weight))
      except ValueError:
        self.inputs.append((arg, 1))

  def add (self, input, weight=1):
    self.inputs.append((input, weight))

  def __iter__ (self):
    weighted_samples = []
    for input, weight in self.inputs:
      weighted_samples.append(samp*weight for samp in input)

    for samps in zip(*weighted_samples):
      yield sum(samps)/len(samps)


def chunk(iter, size):
  a = array.array('h', (0 for x in range(size)))

  while True:

    i = -1
    for i, samp in enumerate(islice(iter, size)):
      a[i] = _int16(samp)

    if i == -1:
      break

    if i < size -1:
      for i in range(i+1, size):
        a[i] = 0

    yield a

  #for i in iter:
    #a.extend([_int16(i)]*_CHANNELS)

    #if len(a) == size:
      #yield a
      #a = array.array('h')
  #if len(a):
    #yield a


def gensound (tempo=33, I=0, H=1, sound=None):
  if sound is None:
    sound = FMSynth(I, H)
  env = Envelope(25, 25, .4, 25)
  return MultiPlayer(tempo, sound, env,
                     [PianoRoll(n) for n in tabreader.read(tabreader.ex_tabs)])

def play (data=None, **kwargs):
  if data is None:
    data = gensound(**kwargs)

  out = alsaaudio.PCM()
  out.setchannels(_CHANNELS)
  out.setformat(alsaaudio.PCM_FORMAT_S16_LE)
  sounds.SAMPLERATE = out.setrate(_DEFAULT_SAMPLERATE)
  sounds.SAMPLEDUR = 1/sounds.SAMPLERATE * 1000
  _ALSAPERIOD = out.setperiodsize(int(sounds.SAMPLERATE/4))
  #print(sounds.SAMPLERATE, _ALSAPERIOD)

  wroten = []
  for bs in chunk(data, _ALSAPERIOD*_CHANNELS):
    wrote = out.write(bs)
    wroten.append(wrote)
    if wrote != _ALSAPERIOD:
      print("WTF? only wrote", wrote, "/", _ALSAPERIOD)

  #print("written", wroten)

  out.close()
  #print("closed")

def write (filename="out", data=None, **kwargs):
  if data is None:
    data = gensound(**kwargs)

  f = wave.open(filename + ".wav", 'w')
  f.setnchannels(_CHANNELS)
  f.setsampwidth(2)
  f.setframerate(sounds.SAMPLERATE)
  f.setcomptype('NONE', 'not compressed')

  bytes = array.array('h',(_int16(s) for s in data))
  f.writeframes(bytes)
  f.close()

if __name__ == '__main__':
  play()

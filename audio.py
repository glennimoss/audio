import sys, wave, math, struct, random, array, re, alsaaudio, operator
from itertools import islice
from music import *
import sounds
from sounds import *

_CHANNELS = 1
_DEFAULT_SAMPLERATE = 44100
_DEFAULT_ALSAPERIOD = int(_DEFAULT_SAMPLERATE/4)
_ALSAPERIOD = None


_int16 = lambda f: int(f * 32767)

class Patch:

  def __init__ (self, input, filter):
    pass

class Filter:
  def sample (self, input):
    for samp in input:
      yield self._sample(samp)

  def _sample (self, samp):
    return samp

class Volume (Filter):
  def __init__ (self, vol):
    self.vol = vol

  def _sample (self, samp):
    return samp * self.vol



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


def play(tempo=33, I=0, H=1, sound=None):
  global _ALSAPERIOD
  out = alsaaudio.PCM() #mode=alsaaudio.PCM_NONBLOCK)
  out.setchannels(_CHANNELS)
  out.setformat(alsaaudio.PCM_FORMAT_S16_LE)
  sounds.SAMPLERATE = out.setrate(_DEFAULT_SAMPLERATE)
  sounds.SAMPLEDUR = 1/sounds.SAMPLERATE * 1000
  _ALSAPERIOD = out.setperiodsize(_DEFAULT_ALSAPERIOD)
  print(sounds.SAMPLERATE, _ALSAPERIOD)


  """
  |--------|--------|----|
  |       O|        |    |
  |------O-|------O.|---O|
  |     O  |  O...  | O. |
  |----O---|O.----O.|O--O|
  |   O    |  O...  | O. |
  |--O-----|O.----O.|O--O|
  | O      |  O...  | O. |
  |O-------|O.------|O---|
  """

  """
  E4|--------|--------|--------|--------|--------|--------|--------|:--------------:|
  B4|--------|--------|--------|--------|--------|--------|--------|:0 -0-0-0 -----:|
  G3|--------|4---4 -2|--------|4   4 -2|--------|4 --4 -2|--------|:4 -4-4-4 -----:|
  D3|-------2|4---4 -2|-------2|4   4 -2|-------2|4 --4 -2|-------2|:4 -2-2-2 -----:|
  A3|-----04-|2---2 -0|-----04-|2   2 -0|-----04-|2 --2 -0|-----04-|:2 -0-0-2 --040:|
  E2|---04---|------4-|---04---|------4-|---04---|------2-|---04---|:-------0 24---:|
  """
  #music = PianoRoll("/8 E F G A5 B5 C5 D5 E5 /4 [E G B] [F A C]/2 [G B D]")
  #music1 = PianoRoll("/8 E F G A5 B5 C5 D5 E5 /4 E F/2  G")
  #music2 = PianoRoll("/8 ; ; ; ;  ;  ;  ;  ;  /4 G A5/2 B5")
  #music3 = PianoRoll("/8 ; ; ; ;  ;  ;  ;  ;  /4 B C5/2 D5")

  #music = PianoRoll("B A G A B B B/2 A A A/2 B D5 D5/2 B A G A B B B B A A B A G/1")
  music1 = PianoRoll("/8 E2 G#2 , A3 C#3 , E3 B3/4 ; ,, B3/4 , G#2 A3 ;/4 " * 1 +
                    "E2 G#2 , A3 C#3 , E3 " +
                    "B3/4 ; A3 ; A3 ; E2/4 F#2 G#2 A3 C#3 A3 " * 4
                   )
  music2 = PianoRoll("/8 ; ; , ; ; , ; F#3/4 ; ,, F#3/4 , ; E3 ;/4 " * 1 +
                    "; ; , ; ; , ; " +
                    "F#3/4 ; E3 ; E3 ; B3/4 ; ; ; ; ; " * 4
                   )
  music3 = PianoRoll("/8 ; ; , ; ; , ; B4/4 ; ,, B4/4 , ; A4 ;/4 " * 1 +
                    "; ; , ; ; , ; " +
                    "B4/4 ; A4 ; A4 ; E3/4 ; ; ; ; ; " * 4
                   )
  env = Envelope(100, 25, .4, 25)
  #synth1 = Volume(0.5).sample(Player(tempo, SquareWave(), env, music1))
  #synth2 = Volume(0.5).sample(Player(tempo, SquareWave(), env, music2))
  #synth3 = Volume(0.5).sample(Player(tempo, SquareWave(), env, music3))
  #mixed = Mixer(synth1, synth2, synth3)

  if sound is None:
    sound = FMSynth(I, H)
  import tabreader
  mixed = MultiPlayer(tempo, sound, env,
                      [PianoRoll(n) for n in tabreader.read(tabreader.ex_tabs)])
  #mixed = MultiPlayer(tempo, SquareWave(), env,
                      #[PianoRoll(n) for n in tabreader.read(mytab)])

  #samples = array.array('h')
  #for samp in mixed:
    #samples.extend([_int16(samp)]*_CHANNELS)

  #samples.extend([0] * (_ALSAPERIOD - (len(samples) %
                                              #_ALSAPERIOD))*_CHANNELS)

  #numSamps = len(samples)//_CHANNELS
  #alsaPeriods = numSamps/_ALSAPERIOD
  #print("about to write {} ints, {} samples, {} periods for {}s".format(
    #len(samples), numSamps, alsaPeriods, numSamps/_SAMPLERATE))
  i = 0
  wroten = []
  blocked = 0
  for bs in chunk(mixed, _ALSAPERIOD*_CHANNELS):
    #wrote = out.write(samples[i:i+_ALSAPERIOD*_CHANNELS])
    wrote = out.write(bs)
    if wrote > 0:
      if blocked < 0:
        wroten.append(blocked)
        blocked = 0
      wroten.append(wrote)
      i += wrote*_CHANNELS
    else:
      blocked -= 1

  #print(len(samples), out.write(samples))
  print("written")
  print(wroten)

  out.close()
  print("closed")

mytab = """
E4|--------|
B4|-------0|
G3|------0 |
D3|----0   |
A3|--0     |
E2|0       |
"""

if __name__ == '__main__':
  play()

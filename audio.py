import sys, wave, math, struct, random, array, re, alsaaudio, operator
from itertools import islice
from music import *
import sounds, tabreader
from sounds import *
from util import chunk

_CHANNELS = 1
_DEFAULT_SAMPLERATE = 44100


def Player (sound, env, notes):
  """
  Tempo is in bars/min. Whereas 120bpm usually means 120 quarter notes per
  minute, we would say 40 bars/min. This makes tempo independent of time
  signature.
  """
  for pitch, dur in notes:
    for sample in (env.gen(sound, pitch, dur) if pitch else Silence.gen(dur)):
      yield sample

def MultiPlayer (sound, env, musics):
  for samples in zip(*(Player(sound, env, notes) for notes in musics)):
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


def gensound (tempo=33, I=1, H=1, sound=None):
  if sound is None:
    sound = FMSynth(I, H)
  env = Envelope(25, 25, .4, 25)
  return MultiPlayer(sound, env, [PianoRoll(tempo, n)
                                  for n in tabreader.read(tabreader.ex_tabs)])

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

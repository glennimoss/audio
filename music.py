import re
from fractions import Fraction

_A4 = 440.0
_dist_A = {
  ';': None, # Rest
  'A': 0,
  'B': 2,
  'C': 3,
  'D': 5,
  'E': 7,
  'F': 8,
  'G': 10,
}
_semitones = ['A',
              'Bb',
              'B',
              'C',
              'C#',
              'D',
              'Eb',
              'E',
              'F',
              'F#',
              'G',
              'G#',
             ]


_pitch_re = re.compile(r'^([ABCDEFG;])(#*|b*)(\d+)?$')


def to_dotted (frac):
  suffix = []
  #print("     {:5} = {:5}".format(frac, frac))
  while frac.numerator > 1 and frac.numerator % 2:
    subnote = Fraction(1,frac.denominator)
    frac -= subnote
    #print("   - {:5} = {:5}".format(subnote, frac))
    if frac.denominator * 2 == subnote.denominator:
      suffix.insert(0, '.')
    elif frac.denominator * 4 == subnote.denominator:
      suffix.insert(0, ':')
    elif frac.denominator * 8 == subnote.denominator:
      suffix.insert(0, '!')
    else:
      raise ValueError('Fractional note duration too small!')

  #print("-->", frac, suffix)
  #return "{}{}{}".format(frac.denominator, '+'*plusses,  '.'*dots)
  return "{}{}".format(frac.denominator, ''.join(suffix))

def to_dur (size, dots):
  den = size.denominator
  for dot in dots:
    den *= _dotval[dot]
    size += Fraction(1, den)

  return size



def _parts (pitch):
  scale, accidental, octave = _pitch_re.match(pitch).groups()
  try:
    octave = int(octave)
  except TypeError:
    octave = 4

  return scale, accidental, octave

def freq (pitch):
  scale, accidental, octave = _parts(pitch)

  try:
    halfs = (_dist_A[scale] + (octave - 4)*12 +
             (-1 if accidental.startswith('b') else 1)*len(accidental))
    return _A4 * 2**(halfs/12)
  except TypeError:
    return None

def offset (pitch, halfs):
  scale, accidental, octave = _parts(pitch)

  dir = 1
  if accidental.startswith('b'):
    dir = -1

  # Normalize as steps away from A
  halfs += dir*len(accidental) + _dist_A[scale]

  # Raise octaves and reduce halfs so halfs < 12
  octave += halfs // 12
  halfs %= 12

  scale = _semitones[halfs]

  return "{}{}".format(scale, octave)

_note_re = re.compile(r'^([^/]*)(?:/(\d+))?([.:!]*)$')
_dotval = {
  '.': 2,
  ':': 4,
  '!': 8,
}

def PianoRoll (tempo, notes):
  """
  Tempo is in bars/min. Whereas 120bpm usually means 120 quarter notes per
  minute, we would say 40 bars/min. This makes tempo independent of time
  signature.
  """
  beat = 60 / tempo
  notes = notes.split()
  default_size = Fraction(1, 4)

  for note in notes:
    try:
      pitch, size, dots = _note_re.match(note).groups()

      if size:
        size = Fraction(1/int(size))

      if pitch:
        pitch = freq(pitch)
        if not size:
          size = default_size

        if dots:
          size = to_dur(size, dots)

        yield pitch, size*beat
      else:
        if size:
          default_size = size
    except AttributeError:
      # Ignore garbage
      #print("Garbage:", note)
      pass

